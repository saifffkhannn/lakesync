# Snowflake Incremental Data Load Pipeline: Technical Documentation

This document provides a comprehensive overview of the design, architecture, working mechanisms, data flows, and configuration of the **Snowflake Incremental Data Ingestion Engine**.

---

## 1. Overview & Objectives

The Incremental Data Ingestion Engine is a high-performance, cost-effective data pipeline designed to ingest records from relational databases (SAP SQL Server, MySQL, Oracle) and perform an incremental merge into **Snowflake**. 

By processing only modified or new records based on high-watermark tracking, the pipeline minimizes compute resource utilization, reduces Snowflake warehouse uptime, minimizes cloud storage costs, and guarantees eventual data consistency between sources and target systems.

### Key Benefits
* **Compute Savings**: Only new or updated rows are extracted, parquetized, and processed.
* **Network & Storage Efficiency**: Parquet format with Snappy compression minimizes file size transfers.
* **Idempotency & Consistency**: Row-level deduplication during Snowflake `MERGE` handles duplicate events or overlapping read windows gracefully.
* **Auditability**: Complete run logs, duration metrics, row counts (source vs. target), and status tracking are persisted in a Snowflake central control table.

---

## 2. High-Level Architecture

The system is split into three main layers: **Source Layer**, **Orchestration & Cloud Transport Layer**, and the **Snowflake Target Layer**.

```mermaid
graph TD
    subgraph Source Layer
        A1[(SAP SQL Server)]
        A2[(MySQL)]
        A3[(Oracle DB)]
    end

    subgraph Orchestration & Transport (Python Engine)
        B[FastAPI Backend / Orchestrator]
        C[Watermark Checker]
        D[Incremental Extractor]
        E[Pandas/PyArrow Parquet Writer]
        F[Cloud Upload Manager]
        G[Local File System Staging]
    end

    subgraph Cloud Storage Staging
        H[AWS S3 Stage / Azure Blob Stage]
        H_Arch[Archive Directory]
    end

    subgraph Snowflake Data Platform
        I[External Stage]
        J[(RAW Staging Database)]
        K[(Target DW Database)]
        L[PipelineRunControl Table]
    end

    %% Connections
    A1 & A2 & A3 -->|1. Pull Data| D
    B -->|Trigger Pipeline| C
    C -->|Read last watermark| L
    L -.->|2. Watermark value| C
    D -->|3. Memory DataFrame| E
    E -->|4. Save as Parquet| G
    G -->|5. Upload Parquet| F
    F -->|6. Load to Cloud bucket| H
    F -->|7. Delete local file| G
    H -->|8. COPY INTO| J
    J -->|9. Deduplicate & MERGE| K
    K -->|10. Truncate RAW| J
    H -->|11. Move to Archive| H_Arch
    B -->|12. Log execution metrics| L
```

### Architectural Components
1. **Orchestrator Backend (FastAPI / Python)**: Responsible for reading config files, querying target watermarks, coordinating execution threads, performing schema mapping, formatting queries, and logging status.
2. **Local Staging**: Temporary folder (`/Extract`) inside the workspace where data is saved as Snappy-compressed Parquet files before upload. Files are deleted immediately upon successful cloud staging.
3. **Cloud Storage Stage (S3 / ADLS Gen2)**: Acts as the storage stage. It features a standard landing path (e.g. `s3://bucket/<database>/<schema>/<table>/`) and an archive path (e.g. `s3://bucket/archive/<database>/<schema>/<table>/`) to segregate loaded files.
4. **Snowflake RAW Staging**: A dedicated database/schema containing transient tables matching the target schemas. Data is loaded here directly via `COPY INTO`.
5. **Snowflake Target Data Warehouse**: The production analytics store containing consolidated, merged tables and the operational metadata table (`PipelineRunControl`).

---

## 3. Step-by-Step Working & Ingestion Flow

The detailed lifecycle of a single table ingestion task consists of 10 sequential phases:

```
[Target Run Control] ──1. Get Last Watermark──> [Compute Window Start]
                                                       │
                                                2. Query Source DB
                                                       │
                                                       ▼
[Delete Local File] <──4. Upload to Cloud─── [Write Parquet File]
        │
  5. Create RAW objects (Snowflake DDL)
        │
        ▼
[COPY INTO RAW Table] ──6. Load Parquet Data──> [Deduplicated MERGE into Target]
                                                       │
                                                 7. Post-Merge
                                                       │
                                                       ├─ Truncate RAW Table
                                                       ├─ Move Cloud Files to Archive
                                                       └─ Log Run in PipelineRunControl
```

### Phase 1: Watermark Identification
The orchestrator connects to the Snowflake Target Database and queries the control table:
```sql
SELECT TO_VARCHAR(MAX(watermark_value), 'YYYY-MM-DD HH24:MI:SS.FF6')
FROM <database>.SampleDB_STG.PipelineRunControl
WHERE UPPER(target_database) = UPPER('<database>')
  AND UPPER(target_schema) = UPPER('<schema>')
  AND UPPER(target_table) = UPPER('<table>')
  AND UPPER(status) = 'SUCCESS';
```
If no previous successful run is found, a default/historic starting timestamp (or full table scan depending on setup) is used.

### Phase 2: Compute Read Window Start
To protect against transaction processing delays and server clock drifts, a customizable **Overlap Window** (e.g., 30 minutes) is subtracted from the watermark value:
$$\text{Window Start} = \text{Watermark Value} - 30 \text{ minutes}$$

### Phase 3: Incremental Extraction
A SQL query is dynamically constructed for the specific source dialect. 
* **Example for SAP SQL Server**:
  ```sql
  SELECT [col1], [col2], [modified_date]
  FROM [SrcDB].[dbo].[SrcTable]
  WHERE [modified_date] > CONVERT(datetime2, '2026-05-27 13:30:00.000000', 121)
  ORDER BY [modified_date] ASC;
  ```
The database driver reads the rows into a Pandas DataFrame.

### Phase 4: Schema Mapping & Parquet Writing
* The source column names are mapped to target column names according to user configurations (defined in the metadata sheet).
* Special rules are processed (e.g., constant values, auto-timestamps, default values, parsing strings).
* The data is converted to an Apache Arrow table and written locally as a compressed Parquet file:
  `Extract/<database>/<schema>/<table>/<table>_YYYYMMDD_HHMMSS.parquet`
* A row-count reconciliation checks that `len(df) == parquet.num_rows`.

### Phase 5: Cloud Stage Upload & Local Cleanup
* The Parquet file is pushed to the target cloud storage folder:
  `s3://<bucket_name>/<source_database>/<source_schema>/<source_table>/`
* Upon successful upload, the local `.parquet` file is deleted from the execution environment to free up local disk space.

### Phase 6: Transient RAW Object Verification
The orchestrator runs Snowflake DDL commands to ensure that the transient RAW table exists:
* A staging table named `<database>_RAW.<schema>.<table>` is verified.
* If missing, it is dynamically created matching the target table's columns.

### Phase 7: Load into Staging RAW (`COPY INTO`)
The orchestrator triggers a COPY command to transfer data from the cloud storage stage into the RAW staging table:
```sql
COPY INTO <database>_RAW.<schema>.<table>
FROM @<database>.<stage_schema>.EXTERNAL_AWS_STAGE/<database>/<schema>/<table>/
FILE_FORMAT = (TYPE = PARQUET)
MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE
FORCE = TRUE;
```
Using `FORCE = TRUE` ensures that files are fully read into RAW even if Snowflake's internal metadata tracks them as previously scanned (crucial for reloading/restart runs).

### Phase 8: Target Table MERGE
A SQL script is generated to merge the RAW table into the Target table. 
Because the source read window uses an overlap buffer, duplicate versions of the same primary key can exist in the RAW table. Therefore, the RAW table is deduplicated on-the-fly using a windowing function:
```sql
MERGE INTO <database>.<schema>.<table> t
USING (
    SELECT * EXCEPT(rn)
    FROM (
        SELECT *,
            ROW_NUMBER() OVER (
                PARTITION BY <primary_key_cols>
                ORDER BY <watermark_expression> DESC
            ) rn
        FROM <database>_RAW.<schema>.<table>
    )
    WHERE rn = 1
) r
ON t.<pk1> = r.<pk1> AND t.<pk2> = r.<pk2>

WHEN MATCHED THEN
    UPDATE SET
        t.col2 = r.col2,
        t.col3 = r.col3,
        ...

WHEN NOT MATCHED THEN
    INSERT (pk1, pk2, col2, col3, ...)
    VALUES (r.pk1, r.pk2, r.col2, r.col3, ...);
```
* `Inserted` and `Updated` metrics are captured from the merge query output.

### Phase 9: Post-Merge Cleanup & File Archiving
To prevent reprocessing and ensure data separation:
1. **Cloud File Archiving**: The cloud stage manager moves files from the active staging folder to an archiving path (`s3://<bucket_name>/archive/...`).
2. **RAW Truncation**: A truncate statement is executed on the RAW table to clean it up for subsequent batches:
   ```sql
   TRUNCATE TABLE <database>_RAW.<schema>.<table>;
   ```
This sequential cleanup ensures that even when the pipeline runs again, the transient staging table starts completely clean, and no old files are left in the active storage directory.

### Phase 10: Control Logging
The statistics of the execution (durations, counts, error details, and the maximum watermark value found in the processed batch) are inserted into `PipelineRunControl` to update the high watermark for the next run.

---

## 4. Ingestion Data Flow diagram

```
  +------------------+
  |  Source Systems  |  (SAP SQL Server, MySQL, Oracle DB)
  +--------+---------+
           |
           | [Select Columns Where Watermark > Last Watermark]
           v
  +------------------+
  |  Python Engine   |  (Mapping, Pandas DataFrame, Parquet compression)
  +--------+---------+
           |
           | [Write local parquet, upload to Cloud Stage, delete local]
           v
  +------------------+
  |   Cloud Stage    |  (Landing Zone: S3 / Azure Container)
  +--------+---------+
           |
           | [Snowflake COPY INTO (Force=True)]
           v
  +------------------+
  |  Snowflake RAW   |  (Transient Staging Table)
  +--------+---------+
           |
           | [Snowflake MERGE with ROW_NUMBER() window function]
           v
  +------------------+
  | Snowflake Target |  (Final Consolidated Production Table)
  +------------------+
```

---

## 5. Metadata Schema & Target Control Structures

### The Metadata Mapping CSV File
Each source-to-target table relationship is defined in a metadata CSV file (e.g., `sapsqlserver_metadata.csv`):
* `source_database`, `source_schema`, `source_table`: Details of the source.
* `target_database`, `target_schema`, `target_table`: Destination details.
* `source_columns`: Comma-separated list of columns to query from the source.
* `target_columns`: Target table schema layout.
* `column_mapping`: JSON string containing direct column mappings, default values, or expressions (e.g., `{"TGT_COL1": "SRC_COL1", "LOAD_TS": "timestamp:now"}`).
* `watermark_column`: Timestamp or numerical column used to track incremental updates.
* `primary_key`: Comma-separated columns identifying unique rows for target merges.

### Control Table DDL (`PipelineRunControl`)
```sql
CREATE TABLE IF NOT EXISTS <database>.SampleDB_STG.PipelineRunControl (
    run_id STRING,
    run_timestamp TIMESTAMP,
    source_system STRING,
    cloud STRING,
    target_system STRING,
    source_database STRING,
    source_schema STRING,
    source_table STRING,
    target_database STRING,
    target_schema STRING,
    target_table STRING,
    source_row_count INTEGER,
    target_row_count INTEGER,
    inserted_rows INTEGER,
    updated_rows INTEGER,
    load_type STRING,
    cloud_path STRING,
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    duration_seconds FLOAT,
    status STRING,
    error_message STRING,
    watermark_value TIMESTAMP
);
```

---

## 6. Failure Recovery & Integrity Protections

The engine contains robust logic to guarantee data integrity:

* **Atomic Staging**: The target database tables are only modified after the data has been safely extracted, successfully written, verified, and uploaded to the cloud storage stages.
* **Transient RAW Tables**: Staging tables are designated as raw, meaning they do not incur historical storage overhead or long-term Time Travel costs.
* **Overlap Ingest Window**: Reading records starting 30 minutes before the last watermark prevents missing records that were in-flight or committed with minor timestamp differences.
* **Target-Side Deduplication**: The windowing function `ROW_NUMBER() OVER (PARTITION BY ... ORDER BY ... DESC)` prevents duplicate keys in the source data from generating duplicates in the target table.
* **Transaction Safety**: The Snowflake merge statement runs as an atomic transaction. If the merge fails, target tables are rolled back to their pre-merge states.
