# Execution Guide: Master Data Management (MDM)

This guide details how to configure, deploy, and execute the Master Data Management (MDM) record consolidation and matching pipeline in Snowflake.

---

## 1. Configure Entity Mapping Rules

To define which columns are normalized and how record similarities are computed, you must register configurations.

1. Navigate to the **MDM Unification** dashboard inside the web UI (`http://localhost:5173`).
2. Define the matching group (e.g. `CUSTOMER_UNIFICATION_MULTI_DB`).
3. Set mapping columns and specify normalization rules for each field:
   - **`phone`**: Strips non-digits, normalizes country prefixes.
   - **`email`**: Lowers cases and normalizes address sub-addressing.
   - **`text`**: Strips extra whitespaces and lowers case for fuzzy matching.
4. Assign a **Match Weight** (e.g. `1.0` for Email/Phone, `0.5` for Names) to guide the `rapidfuzz` scoring logic.

---

## 2. Deploy MDM Structures & Stored Procedures

Before executing the matching logic, initialize the schemas andStored Procedures in Snowflake:

1. Through the MDM panel in the Web UI, click **Deploy Database Structures**.
2. Behind the scenes, this calls:
   ```python
   # Via the Python API wrapper
   from mdm_helper import MDMHelper
   helper = MDMHelper()
   helper.deploy_structures(creds)
   helper.deploy_procedures(creds)
   ```
3. This creates schemas `BRONZE` and `MDM`, deploys audit logs, defines the stream-tracking configuration tables, and registers the procedures `SP_LOAD_GROUP` and `SP_MASTER_ENTITY` in Snowflake.

---

## 3. Run the MDM Unification Pipeline

When new data lands in target tables (from ingestion engines or ABAP conversions):

1. **Trigger from UI**: Click **Run Consolidation** on the MDM dashboard, OR:
2. **Execute directly from Snowflake Worksheet**:
   ```sql
   -- 1. Merges data from staging tables into target entities and truncates staging
   CALL DATA_UNIFICATION_DB.BRONZE.SP_LOAD_GROUP('DATA_UNIFICATION_DB', 'CUSTOMER_UNIFICATION_MULTI_DB');
   
   -- 2. Scans streams for delta insertions, performs deduplication, and links records
   CALL DATA_UNIFICATION_DB.MDM.SP_MASTER_ENTITY('DATA_UNIFICATION_DB', 'CUSTOMER_UNIFICATION_MULTI_DB');
   ```

---

## 4. Query Consolidated Master Records

Once the pipeline completes:
- Query the consolidated profiles directly from the flat Master view:
  ```sql
  SELECT * FROM DATA_UNIFICATION_DB.MDM.MASTER_ENTITY_FLAT;
  ```
- Review the clustered record sizes, similarity scores (`HIGH`, `MEDIUM`, `LOW`), and associated source keys.
