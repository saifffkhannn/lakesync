# Prerequisites for Master Data Management (MDM) Unification

This document details the configuration requirements, Snowflake settings, and libraries needed to run the Master Data Management (MDM) entity resolution and unification processes.

---

## 1. Snowflake Environment & Privileges

The MDM engine executes entirely within your Snowflake database, leveraging stored procedures and Snowpark.
- **Python Stored Procedure Support**: The Snowflake warehouse and schema must support Python runtimes (specifically version `3.11`).
- **Snowpark Python Packages**: The database environment must have access to Snowflake's package repository. The `SP_MASTER_ENTITY` procedure requests and imports:
  - `snowflake-snowpark-python`
  - `pandas`
  - `rapidfuzz` (used for calculating similarity metrics)
- **Role Permissions**: The designated Snowflake role must have privileges to create schemas (`BRONZE` and `MDM`), create tables, and deploy stored procedures.

---

## 2. Table-Level Change Tracking & Streams

To capture delta records incrementally and feed them into the matching algorithms, MDM requires target tables to track changes.
- **Change Tracking**: Target tables must have change tracking enabled to support Snowflake streams.
  ```sql
  ALTER TABLE <database>.<schema>.<table_name> SET CHANGE_TRACKING = TRUE;
  ```
- **Snowflake Streams**: A stream must be deployed on top of each target table to capture inserts and updates:
  ```sql
  CREATE STREAM IF NOT EXISTS <database>.<schema>.<stream_name> ON TABLE <database>.<schema>.<table_name>;
  ```

---

## 3. Database Structures

MDM orchestrates deduplication using these structures (deployed by the framework):
- **`SOURCE_MAPPING_CONFIG`**: Holds system configuration mappings, execution sequences, merge keys, and target mappings.
- **`MERGE_AUDIT_LOG`**: Logs rows processed, insertions, updates, and execution statuses.
- **`MASTER_ENTITY`**: The base table holding consolidated record profiles, linked record IDs, cluster sizes, and confidence ranks.
- **`MASTER_ENTITY_FLAT`**: A flat view dynamically compiled on top of the consolidated variant payload for easy SQL querying.

---

## 4. Stored Procedures Deployment

The core unification logic is handled by two stored procedures that must be deployed inside Snowflake:
- **`SP_LOAD_GROUP`**: A JavaScript-based procedure that resolves source configs and merges delta updates from staging to the core tables.
- **`SP_MASTER_ENTITY`**: A Snowpark Python-based procedure that retrieves records from active streams, computes similarity matrices using `rapidfuzz`, and links records to existing master entities or creates new ones.
