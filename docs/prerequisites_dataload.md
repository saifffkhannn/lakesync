# Prerequisites for Data Load (Full & Incremental Ingestion)

This document outlines the technical requirements, assumptions, and configurations necessary to execute Full and Incremental (CDC) data ingestion pipelines.

---

## 1. Source Database Requirements

To connect to and extract data from operational databases (SAP SQL Server, Oracle, MySQL, Teradata):
- **Read Permissions**: The source database user must have `SELECT` privileges on the target schemas and tables.
- **Metadata Access**: Access to system views (like `INFORMATION_SCHEMA` or system catalogs) is required to dynamically fetch schemas and data types.
- **Port Visibility**: The database host must be reachable from the host machine running the Ingestion Engine (default port `1433` for SQL Server, `1521` for Oracle, `3306` for MySQL, etc.).

---

## 2. Full Ingestion Requirements

- **Staging Area**: An active AWS S3 bucket must be configured to temporarily house the extracted Parquet files.
- **Target Table DDL**: The ingestion engine will automatically generate and execute the target table DDL in the target data warehouse (Snowflake/Databricks) if it does not already exist.

---

## 3. Incremental Ingestion (CDC) Requirements

To stream and update only modified records, the pipeline relies on the following preconditions:
- **Watermark/LastModified Column**: 
  - Every source table selected for incremental load **must have a watermark column** (typically a timestamp, like `LastModifiedDate`, `updated_at`, or a monotonically increasing integer sequence ID).
  - This column is used to filter records that have changed since the last ingestion run.
- **Pre-existing Target Table**:
  - The target table **must already exist** in the target data warehouse (Snowflake/Databricks), irrespective of the name. The pipeline will merge delta files into this pre-existing structure.
- **Primary Keys**:
  - The target table must have a designated primary key (or composite key) configured in the mapping profile so the pipeline knows which rows to update (`UPSERT`) rather than appending duplicates.

---

## 4. Target Warehouse Credentials

- **Snowflake/Databricks Workspace Access**: Credentials (username, password, account/host, warehouse) must be configured in `dev_config.json` or the web UI.
- **Write Permissions**: The target database user role must have permission to create stages, create tables, and run `COPY INTO` or `MERGE` commands inside the staging and production schemas.

---

## 5. Cloud Storage (Staging) Credentials

- **AWS Credentials**: A valid `aws_access_key_id` and `aws_secret_access_key` with permissions to write (`PutObject`), read (`GetObject`), and delete (`DeleteObject`) in the designated S3 bucket.
- **Bucket Paths**: The cloud configurations must provide the S3 bucket name and base folder path where Parquet files will be loaded.
