# Prerequisites for ABAP to Snowflake SQL Conversion

This document details the configuration requirements and system dependencies for executing ABAP and Open SQL to Snowflake translation workflows.

---

## 1. Snowflake Account & Cortex AI Requirements

The AI-driven conversion capabilities rely on Snowflake's Cortex LLM models to translate complex structures.
- **Cortex-Enabled Account**: The target Snowflake account must support Cortex functions (available in Enterprise and higher editions across most AWS and Azure regions).
- **Model Privileges**: The active Snowflake role must have privileges to execute the Cortex LLM functions:
  ```sql
  -- Example Cortex completion call verified at runtime
  SELECT SNOWFLAKE.CORTEX.COMPLETE('llama3-70b', 'Translate this code...');
  ```

---

## 2. Infrastructure Setup (Snowflake Logs & Feedback)

If AI conversion history or user feedback logging is enabled, Snowflake must have the tracking structures pre-deployed. The schema requires table structures to register:
- **`CONVERSION_REQUESTS`**: Registers source checksums, detected features, and original ABAP code.
- **`CONVERSION_RESULTS`**: Stores the output SQL code, translation notes, and confidence scores.
- **`VALIDATION_RESULTS`**: Tracks syntax, object, query plan, and semantic check results.
- **`REVIEW_HISTORY`** & **`FEEDBACK_DATASET`**: Logs user manual reviews and corrections.

*Note: These structures are automatically deployed when running the deployment script (`infra/snowflake/001_storage_model.sql`).*

---

## 3. Environment Configurations

Configure these variables inside your local environment or the `Conversion_ABAP/backend/.env` file:
- `SNOWFLAKE_ACCOUNT`: The full account identifier (e.g. `xy12345.us-east-2.aws`).
- `SNOWFLAKE_USER`: Username with access to Cortex functions.
- `SNOWFLAKE_PASSWORD`: User password.
- `SNOWFLAKE_ROLE`: Role possessing Cortex access privileges.
- `SNOWFLAKE_WAREHOUSE`, `SNOWFLAKE_DATABASE`, `SNOWFLAKE_SCHEMA`: Context settings.

---

## 4. Rule-Engine Dependencies (Local Fallback)

If running the local non-AI offline rules-based converter:
- **Python Runtime**: Python 3.10+ setup.
- **Parser libraries**: Requirements listed in `Conversion_ABAP/backend/pyproject.toml` (such as AST utilities and regular expression modules).
