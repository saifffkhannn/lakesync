/*==============================================================================
  CUSTOMER MDM MULTI-DATABASE TEST SCENARIO
  ==============================================================================
  Purpose: Validate that the MDM framework works across multiple source databases
           without changing procedure code (after fixing hardcoded references).
  
  Group Name: CUSTOMER_UNIFICATION_MULTI_DB
  Source DBs: SAP_DB, ORACLE_DB, SALESFORCE_DB
  Target DB:  CUSTOMER_MDM_DB
  
  Sections:
    1. Database & Schema Creation
    2. Source Staging Tables
    3. Target Bronze Tables
    4. Streams on Target Bronze Tables
    5. Metadata Configuration (SOURCE_MAPPING_CONFIG)
    6. Audit Log Table in Target
    7. Test Data Insertion
    8. Procedure Fixes (make fully metadata-driven)
    9. Validation Queries
==============================================================================*/

USE ROLE ACCOUNTADMIN;
USE WAREHOUSE COMPUTE_WH;

/*==============================================================================
  SECTION 1: DATABASE & SCHEMA CREATION
==============================================================================*/

-- Source Databases
CREATE DATABASE IF NOT EXISTS SAP_DB;
CREATE DATABASE IF NOT EXISTS ORACLE_DB;
CREATE DATABASE IF NOT EXISTS SALESFORCE_DB;

-- Source Schemas
CREATE SCHEMA IF NOT EXISTS SAP_DB.RAW_STG;
CREATE SCHEMA IF NOT EXISTS ORACLE_DB.RAW_STG;
CREATE SCHEMA IF NOT EXISTS SALESFORCE_DB.RAW_STG;

-- Target Database and Schemas
CREATE DATABASE IF NOT EXISTS CUSTOMER_MDM_DB;
CREATE SCHEMA IF NOT EXISTS CUSTOMER_MDM_DB.BRONZE;
CREATE SCHEMA IF NOT EXISTS CUSTOMER_MDM_DB.MDM;

/*==============================================================================
  SECTION 2: SOURCE STAGING TABLES
==============================================================================*/

CREATE OR REPLACE TABLE SAP_DB.RAW_STG.SAP_CUSTOMERS_STG (
    KUNNR           VARCHAR,
    NAME1           VARCHAR,
    NAME2           VARCHAR,
    CITY            VARCHAR,
    STATE           VARCHAR,
    POST_CODE       VARCHAR,
    TELF1           VARCHAR,
    SMTP_ADDR       VARCHAR,
    COUNTRY         VARCHAR,
    CUSTOMER_GROUP  VARCHAR,
    CREATED_DATE    DATE
);

CREATE OR REPLACE TABLE ORACLE_DB.RAW_STG.ORACLE_CUSTOMERS_STG (
    PARTY_ID          VARCHAR,
    CUSTOMER_NAME     VARCHAR,
    CITY              VARCHAR,
    STATE             VARCHAR,
    ZIP_CODE          VARCHAR,
    PHONE_NUMBER      VARCHAR,
    EMAIL_ADDRESS     VARCHAR,
    COUNTRY           VARCHAR,
    CUSTOMER_CATEGORY VARCHAR,
    CREATION_DATE     DATE
);

CREATE OR REPLACE TABLE SALESFORCE_DB.RAW_STG.SALESFORCE_CUSTOMERS_STG (
    ACCOUNT_ID    VARCHAR,
    ACCOUNT_NAME  VARCHAR,
    BILLING_CITY  VARCHAR,
    STATE         VARCHAR,
    PHONE         VARCHAR,
    EMAIL         VARCHAR,
    COUNTRY       VARCHAR,
    ACCOUNT_TYPE  VARCHAR,
    CREATED_DATE  DATE
);

/*==============================================================================
  SECTION 3: TARGET BRONZE TABLES (with change tracking for streams)
==============================================================================*/

CREATE OR REPLACE TABLE CUSTOMER_MDM_DB.BRONZE.SAP_CUSTOMER_MASTER (
    CUSTOMER_ID         VARCHAR,
    CUSTOMER_NAME       VARCHAR,
    EMAIL               VARCHAR,
    PHONE               VARCHAR,
    CITY                VARCHAR,
    STATE               VARCHAR,
    ZIP_CODE            VARCHAR,
    COUNTRY             VARCHAR,
    CUSTOMER_TYPE       VARCHAR,
    SOURCE_SYSTEM       VARCHAR,
    LOAD_TIMESTAMP      TIMESTAMP_NTZ,
    LAST_MODIFIED_DATE  TIMESTAMP_NTZ
) CHANGE_TRACKING = TRUE;

CREATE OR REPLACE TABLE CUSTOMER_MDM_DB.BRONZE.ORACLE_CUSTOMERS (
    CUSTOMER_ID         VARCHAR,
    CUSTOMER_NAME       VARCHAR,
    EMAIL               VARCHAR,
    PHONE               VARCHAR,
    CITY                VARCHAR,
    STATE               VARCHAR,
    ZIP_CODE            VARCHAR,
    COUNTRY             VARCHAR,
    CUSTOMER_TYPE       VARCHAR,
    SOURCE_SYSTEM       VARCHAR,
    LOAD_TIMESTAMP      TIMESTAMP_NTZ,
    LAST_MODIFIED_DATE  TIMESTAMP_NTZ
) CHANGE_TRACKING = TRUE;

CREATE OR REPLACE TABLE CUSTOMER_MDM_DB.BRONZE.SALESFORCE_ACCOUNTS (
    CUSTOMER_ID         VARCHAR,
    CUSTOMER_NAME       VARCHAR,
    EMAIL               VARCHAR,
    PHONE               VARCHAR,
    CITY                VARCHAR,
    STATE               VARCHAR,
    ZIP_CODE            VARCHAR,
    COUNTRY             VARCHAR,
    CUSTOMER_TYPE       VARCHAR,
    SOURCE_SYSTEM       VARCHAR,
    LOAD_TIMESTAMP      TIMESTAMP_NTZ,
    LAST_MODIFIED_DATE  TIMESTAMP_NTZ
) CHANGE_TRACKING = TRUE;

-- Audit Log in target database
CREATE OR REPLACE TABLE CUSTOMER_MDM_DB.BRONZE.MERGE_AUDIT_LOG (
    LOG_ID              NUMBER AUTOINCREMENT,
    RUN_ID              VARCHAR,
    GROUP_NAME          VARCHAR,
    SOURCE_SYSTEM       VARCHAR,
    STG_TABLE           VARCHAR,
    TGT_TABLE           VARCHAR,
    ROWS_INSERTED       NUMBER DEFAULT 0,
    ROWS_UPDATED        NUMBER DEFAULT 0,
    STATUS              VARCHAR,
    ERROR_MESSAGE       VARCHAR,
    GENERATED_SQL       VARCHAR,
    STARTED_TS          TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    COMPLETED_TS        TIMESTAMP_NTZ,
    PRIMARY KEY (LOG_ID)
);

-- SOURCE_MAPPING_CONFIG in target database (so procedures can read from it)
CREATE OR REPLACE TABLE CUSTOMER_MDM_DB.BRONZE.SOURCE_MAPPING_CONFIG (
    CONFIG_ID       NUMBER AUTOINCREMENT,
    GROUP_NAME      VARCHAR,
    EXECUTION_SEQ   NUMBER,
    SOURCE_SYSTEM   VARCHAR NOT NULL,
    SRC_DATABASE    VARCHAR NOT NULL,
    STG_SCHEMA      VARCHAR NOT NULL,
    STG_TABLE       VARCHAR NOT NULL,
    TGT_DATABASE    VARCHAR NOT NULL,
    TGT_SCHEMA      VARCHAR NOT NULL,
    TGT_TABLE       VARCHAR NOT NULL,
    MERGE_KEY       VARCHAR NOT NULL,
    STG_MERGE_KEY   VARCHAR NOT NULL,
    COLUMN_MAPPING  VARIANT NOT NULL,
    IS_ACTIVE       BOOLEAN DEFAULT TRUE,
    CREATED_TS      TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    STREAM_NAME     VARCHAR,
    PRIMARY KEY (CONFIG_ID)
);

-- MDM MASTER_ENTITY in target database
CREATE OR REPLACE TABLE CUSTOMER_MDM_DB.MDM.MASTER_ENTITY (
    MASTER_ID        VARCHAR,
    GROUP_NAME       VARCHAR,
    ENTITY_DATA      VARIANT,
    SOURCE_IDS       VARCHAR,
    SOURCE_SYSTEMS   VARCHAR,
    CLUSTER_SIZE     NUMBER,
    MATCH_CONFIDENCE VARCHAR,
    PIPELINE_RUN_ID  VARCHAR,
    CREATED_TS       TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

/*==============================================================================
  SECTION 4: STREAMS ON TARGET BRONZE TABLES
==============================================================================*/

CREATE OR REPLACE STREAM CUSTOMER_MDM_DB.BRONZE.STM_SAP_CUSTOMER_MASTER
    ON TABLE CUSTOMER_MDM_DB.BRONZE.SAP_CUSTOMER_MASTER;

CREATE OR REPLACE STREAM CUSTOMER_MDM_DB.BRONZE.STM_ORACLE_CUSTOMERS
    ON TABLE CUSTOMER_MDM_DB.BRONZE.ORACLE_CUSTOMERS;

CREATE OR REPLACE STREAM CUSTOMER_MDM_DB.BRONZE.STM_SALESFORCE_ACCOUNTS
    ON TABLE CUSTOMER_MDM_DB.BRONZE.SALESFORCE_ACCOUNTS;

/*==============================================================================
  SECTION 5: METADATA CONFIGURATION INSERT
  Note: Does NOT modify existing GROUP_1 records in DATA_UNIFICATION_DB
==============================================================================*/

CREATE OR REPLACE TABLE CUSTOMER_MDM_DB.BRONZE.SOURCE_MAPPING_CONFIG

(

    CONFIG_ID          NUMBER AUTOINCREMENT PRIMARY KEY,
 
    GROUP_NAME         STRING,
 
    EXECUTION_SEQ      NUMBER,
 
    SOURCE_SYSTEM      STRING NOT NULL,

    SRC_DATABASE       STRING NOT NULL,

    STG_SCHEMA         STRING NOT NULL,

    STG_TABLE          STRING NOT NULL,

    TGT_DATABASE       STRING NOT NULL,
 
    TGT_SCHEMA         STRING NOT NULL,

    TGT_TABLE          STRING NOT NULL,
 
    MERGE_KEY          STRING NOT NULL,

    STG_MERGE_KEY      STRING NOT NULL,
 
    COLUMN_MAPPING     VARIANT NOT NULL,
 
    IS_ACTIVE          BOOLEAN DEFAULT TRUE,
 
    CREATED_TS         TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),

    STREAM_NAME        STRING

);

INSERT INTO CUSTOMER_MDM_DB.BRONZE.SOURCE_MAPPING_CONFIG
(GROUP_NAME, EXECUTION_SEQ, SOURCE_SYSTEM, SRC_DATABASE, STG_SCHEMA, STG_TABLE,
 TGT_DATABASE, TGT_SCHEMA, TGT_TABLE, MERGE_KEY, STG_MERGE_KEY, COLUMN_MAPPING, IS_ACTIVE, STREAM_NAME)
SELECT
    'CUSTOMER_UNIFICATION_MULTI_DB', 1, 'SAP', 'SAP_DB', 'RAW_STG', 'SAP_CUSTOMERS_STG',
    'CUSTOMER_MDM_DB', 'BRONZE', 'SAP_CUSTOMER_MASTER', 'CUSTOMER_ID', 'KUNNR',
    PARSE_JSON('[
      {"src":"KUNNR","tgt":"CUSTOMER_ID","normalize":"none","match_weight":null},
      {"src":"expr:NAME1 || '' '' || NAME2","tgt":"CUSTOMER_NAME","normalize":"text","match_weight":0.15},
      {"src":"SMTP_ADDR","tgt":"EMAIL","normalize":"email","match_weight":0.4},
      {"src":"TELF1","tgt":"PHONE","normalize":"phone","match_weight":0.3},
      {"src":"CITY","tgt":"CITY","normalize":"text","match_weight":0.15},
      {"src":"STATE","tgt":"STATE","normalize":"text","match_weight":null},
      {"src":"POST_CODE","tgt":"ZIP_CODE","normalize":"none","match_weight":null},
      {"src":"COUNTRY","tgt":"COUNTRY","normalize":"text","match_weight":null},
      {"src":"CUSTOMER_GROUP","tgt":"CUSTOMER_TYPE","normalize":"text","match_weight":null},
      {"src":"CREATED_DATE","tgt":"SOURCE_SYSTEM","normalize":"none","match_weight":null}
    ]'),
    TRUE, 'STM_SAP_CUSTOMER_MASTER';

INSERT INTO CUSTOMER_MDM_DB.BRONZE.SOURCE_MAPPING_CONFIG
(GROUP_NAME, EXECUTION_SEQ, SOURCE_SYSTEM, SRC_DATABASE, STG_SCHEMA, STG_TABLE,
 TGT_DATABASE, TGT_SCHEMA, TGT_TABLE, MERGE_KEY, STG_MERGE_KEY, COLUMN_MAPPING, IS_ACTIVE, STREAM_NAME)
SELECT
    'CUSTOMER_UNIFICATION_MULTI_DB', 2, 'ORACLE', 'ORACLE_DB', 'RAW_STG', 'ORACLE_CUSTOMERS_STG',
    'CUSTOMER_MDM_DB', 'BRONZE', 'ORACLE_CUSTOMERS', 'CUSTOMER_ID', 'PARTY_ID',
    PARSE_JSON('[
      {"src":"PARTY_ID","tgt":"CUSTOMER_ID","normalize":"none","match_weight":null},
      {"src":"CUSTOMER_NAME","tgt":"CUSTOMER_NAME","normalize":"text","match_weight":0.15},
      {"src":"EMAIL_ADDRESS","tgt":"EMAIL","normalize":"email","match_weight":0.4},
      {"src":"PHONE_NUMBER","tgt":"PHONE","normalize":"phone","match_weight":0.3},
      {"src":"CITY","tgt":"CITY","normalize":"text","match_weight":0.15},
      {"src":"STATE","tgt":"STATE","normalize":"text","match_weight":null},
      {"src":"ZIP_CODE","tgt":"ZIP_CODE","normalize":"none","match_weight":null},
      {"src":"COUNTRY","tgt":"COUNTRY","normalize":"text","match_weight":null},
      {"src":"CUSTOMER_CATEGORY","tgt":"CUSTOMER_TYPE","normalize":"text","match_weight":null},
      {"src":"CREATION_DATE","tgt":"SOURCE_SYSTEM","normalize":"none","match_weight":null}
    ]'),
    TRUE, 'STM_ORACLE_CUSTOMERS';

INSERT INTO CUSTOMER_MDM_DB.BRONZE.SOURCE_MAPPING_CONFIG
(GROUP_NAME, EXECUTION_SEQ, SOURCE_SYSTEM, SRC_DATABASE, STG_SCHEMA, STG_TABLE,
 TGT_DATABASE, TGT_SCHEMA, TGT_TABLE, MERGE_KEY, STG_MERGE_KEY, COLUMN_MAPPING, IS_ACTIVE, STREAM_NAME)
SELECT
    'CUSTOMER_UNIFICATION_MULTI_DB', 3, 'SALESFORCE', 'SALESFORCE_DB', 'RAW_STG', 'SALESFORCE_CUSTOMERS_STG',
    'CUSTOMER_MDM_DB', 'BRONZE', 'SALESFORCE_ACCOUNTS', 'CUSTOMER_ID', 'ACCOUNT_ID',
    PARSE_JSON('[
      {"src":"ACCOUNT_ID","tgt":"CUSTOMER_ID","normalize":"none","match_weight":null},
      {"src":"ACCOUNT_NAME","tgt":"CUSTOMER_NAME","normalize":"text","match_weight":0.15},
      {"src":"EMAIL","tgt":"EMAIL","normalize":"email","match_weight":0.4},
      {"src":"PHONE","tgt":"PHONE","normalize":"phone","match_weight":0.3},
      {"src":"BILLING_CITY","tgt":"CITY","normalize":"text","match_weight":0.15},
      {"src":"STATE","tgt":"STATE","normalize":"text","match_weight":null},
      {"src":"NULL","tgt":"ZIP_CODE","normalize":"none","match_weight":null},
      {"src":"COUNTRY","tgt":"COUNTRY","normalize":"text","match_weight":null},
      {"src":"ACCOUNT_TYPE","tgt":"CUSTOMER_TYPE","normalize":"text","match_weight":null},
      {"src":"CREATED_DATE","tgt":"SOURCE_SYSTEM","normalize":"none","match_weight":null}
    ]'),
    TRUE, 'STM_SALESFORCE_ACCOUNTS';

select * from CUSTOMER_MDM_DB.BRONZE.SOURCE_MAPPING_CONFIG;

/*==============================================================================
  SECTION 6: TEST DATA
==============================================================================*/

COPY INTO SAP_DB.RAW_STG.SAP_CUSTOMERS_STG
FROM @SAP_DB.RAW_STG.SAP_STAGE/SAP_CUSTOMER_MASTER.csv
FILE_FORMAT = (TYPE = 'CSV' SKIP_HEADER = 1 FIELD_OPTIONALLY_ENCLOSED_BY = '"')
ON_ERROR = 'CONTINUE';

COPY INTO ORACLE_DB.RAW_STG.ORACLE_CUSTOMERS_STG
FROM @ORACLE_DB.RAW_STG.ORACLE_STAGE/ORACLE_CUSTOMERS.csv
FILE_FORMAT = (TYPE = 'CSV' SKIP_HEADER = 1 FIELD_OPTIONALLY_ENCLOSED_BY = '"')
ON_ERROR = 'CONTINUE';

COPY INTO SALESFORCE_DB.RAW_STG.SALESFORCE_CUSTOMERS_STG
FROM @SALESFORCE_DB.RAW_STG.SALESFORCE_STAGE/SALESFORCE_ACCOUNTS.csv
FILE_FORMAT = (TYPE = 'CSV' SKIP_HEADER = 1 FIELD_OPTIONALLY_ENCLOSED_BY = '"')
ON_ERROR = 'CONTINUE';

/*==============================================================================
  SECTION 7: PROCEDURE FIXES - MAKE FRAMEWORK FULLY METADATA-DRIVEN
  
  Issues Found:
  1. SP_LOAD_GROUP: Hardcoded DATA_UNIFICATION_DB.BRONZE.SOURCE_MAPPING_CONFIG
     and DATA_UNIFICATION_DB.BRONZE.MERGE_AUDIT_LOG
  2. SP_MASTER_ENTITY(1-param): All references hardcoded to DATA_UNIFICATION_DB
  3. SP_MASTER_ENTITY(2-param): Reads streams from {src_db}.BRONZE.{stream_name}
     but streams live in TGT_DATABASE.BRONZE

  Fix: Create new 2-parameter SP_LOAD_GROUP(CONFIG_DATABASE, GROUP_NAME) and
       fix SP_MASTER_ENTITY(2-param) stream reference bug.
       Deploy to CUSTOMER_MDM_DB.BRONZE for the new test scenario.
==============================================================================*/

-- Fixed SP_LOAD_GROUP: accepts CONFIG_DATABASE parameter to locate config/audit tables
CREATE OR REPLACE PROCEDURE CUSTOMER_MDM_DB.BRONZE.SP_LOAD_GROUP(
    "P_CONFIG_DATABASE" VARCHAR,
    "P_GROUP_NAME" VARCHAR
)
RETURNS VARIANT
LANGUAGE JAVASCRIPT
EXECUTE AS OWNER
AS
$$
function sql(q, binds) {
    return binds
        ? snowflake.execute({sqlText:q, binds:binds})
        : snowflake.execute({sqlText:q});
}

function scalar(q) {
    var rs = snowflake.execute({sqlText:q});
    return rs.next() ? rs.getColumnValue(1) : null;
}

var CONFIG_DB = P_CONFIG_DATABASE.trim().toUpperCase();
var RUN_ID = scalar("SELECT UUID_STRING()");
var results = [];
var anyError = false;

var configSQL = `
SELECT
       GROUP_NAME,
       EXECUTION_SEQ,
       SOURCE_SYSTEM,
       SRC_DATABASE,
       STG_SCHEMA,
       STG_TABLE,
       TGT_DATABASE,
       TGT_SCHEMA,
       TGT_TABLE,
       MERGE_KEY,
       STG_MERGE_KEY,
       COLUMN_MAPPING
FROM ` + CONFIG_DB + `.BRONZE.SOURCE_MAPPING_CONFIG
WHERE IS_ACTIVE = TRUE
AND GROUP_NAME IN
(
    SELECT TRIM(VALUE)
    FROM TABLE
    (
        SPLIT_TO_TABLE(
            '` + P_GROUP_NAME + `',
            ','
        )
    )
)
ORDER BY GROUP_NAME, EXECUTION_SEQ
`;

var configs = sql(configSQL);

while(configs.next()) {
    var groupName    = configs.getColumnValue(1);
    var execSeq      = configs.getColumnValue(2);
    var sourceSystem = configs.getColumnValue(3);
    var srcDatabase  = configs.getColumnValue(4);
    var stgSchema    = configs.getColumnValue(5);
    var stgTable     = configs.getColumnValue(6);
    var tgtDatabase  = configs.getColumnValue(7);
    var tgtSchema    = configs.getColumnValue(8);
    var tgtTable     = configs.getColumnValue(9);
    var mergeKey     = configs.getColumnValue(10);
    var stgMergeKey  = configs.getColumnValue(11);
    var columnMapping = configs.getColumnValue(12);

    var status   = 'SUCCESS';
    var errorMsg = '';
    var rowsIns  = 0;
    var rowsUpd  = 0;
    var mergeSQL = '';

    try {
        var mapping = (typeof columnMapping === 'string') ? JSON.parse(columnMapping) : columnMapping;
        var selectParts = [];
        var tgtCols     = [];
        var srcVals     = [];
        var updateSets  = [];
        var updateConditions = [];
        var noUpdate = [mergeKey, 'LOAD_TIMESTAMP'];

        for(var i = 0; i < mapping.length; i++) {
            var m = mapping[i];
            var srcExpr = m.src;
            var tgtCol  = m.tgt;

            if(srcExpr === 'NULL') {
                selectParts.push('NULL AS ' + tgtCol);
            } else if(srcExpr.indexOf('expr:') === 0) {
                selectParts.push(srcExpr.replace('expr:','') + ' AS ' + tgtCol);
            } else {
                selectParts.push(srcExpr + ' AS ' + tgtCol);
            }

            tgtCols.push(tgtCol);
            srcVals.push('S.' + tgtCol);

            if(noUpdate.indexOf(tgtCol) === -1) {
                updateSets.push('T.' + tgtCol + ' = S.' + tgtCol);
                updateConditions.push('T.' + tgtCol + ' IS DISTINCT FROM S.' + tgtCol);
            }
        }

        if(tgtCols.indexOf('SOURCE_SYSTEM') === -1) {
            selectParts.push("'" + sourceSystem + "' AS SOURCE_SYSTEM");
            tgtCols.push('SOURCE_SYSTEM');
            srcVals.push('S.SOURCE_SYSTEM');
            updateSets.push('T.SOURCE_SYSTEM = S.SOURCE_SYSTEM');
        }

        tgtCols.push('LOAD_TIMESTAMP', 'LAST_MODIFIED_DATE');
        srcVals.push('CURRENT_TIMESTAMP()', 'CURRENT_TIMESTAMP()');
        updateSets.push('T.LAST_MODIFIED_DATE = CURRENT_TIMESTAMP()');

        var fullSrc = srcDatabase + '.' + stgSchema + '.' + stgTable;
        var fullTgt = tgtDatabase + '.' + tgtSchema + '.' + tgtTable;

        mergeSQL = [
            'MERGE INTO ' + fullTgt + ' T',
            'USING (',
            ' SELECT ' + selectParts.join(',\n '),
            ' FROM ' + fullSrc,
            ') S',
            'ON T.' + mergeKey + ' = S.' + mergeKey,
            '',
            'WHEN MATCHED AND (',
            updateConditions.join(' OR\n'),
            ') THEN',
            'UPDATE SET',
            updateSets.join(',\n'),
            '',
            'WHEN NOT MATCHED THEN',
            'INSERT (' + tgtCols.join(', ') + ')',
            'VALUES (' + srcVals.join(', ') + ')'
        ].join('\n');

        var mr = sql(mergeSQL);
        mr.next();
        rowsIns = mr.getColumnValue(1);
        rowsUpd = mr.getColumnValue(2);

        sql('TRUNCATE TABLE ' + fullSrc);
    }
    catch(e) {
        status = 'FAILED';
        errorMsg = e.message || String(e);
        anyError = true;
    }

    sql(`
    INSERT INTO ` + CONFIG_DB + `.BRONZE.MERGE_AUDIT_LOG
    (
        RUN_ID, GROUP_NAME, SOURCE_SYSTEM, STG_TABLE,
        TGT_TABLE, ROWS_INSERTED, ROWS_UPDATED, STATUS,
        ERROR_MESSAGE, GENERATED_SQL, COMPLETED_TS
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP())
    `,
    [RUN_ID, groupName, sourceSystem, stgTable, tgtTable,
     rowsIns, rowsUpd, status, errorMsg, mergeSQL]);

    results.push({
        source_system: sourceSystem,
        stg_table: stgTable,
        tgt_table: tgtTable,
        rows_inserted: rowsIns,
        rows_updated: rowsUpd,
        status: status,
        error: errorMsg
    });
}

return {
    run_id: RUN_ID,
    overall_status: anyError ? 'PARTIAL_FAILURE' : 'SUCCESS',
    results: results
};
$$;

-- Fixed SP_MASTER_ENTITY: 2-param version with bug fix
-- Bug fix: streams are in TGT_DATABASE.BRONZE, not SRC_DATABASE.BRONZE
CREATE OR REPLACE PROCEDURE CUSTOMER_MDM_DB.MDM.SP_MASTER_ENTITY(
    "CONFIG_DATABASE" VARCHAR,
    "GROUP_NAME" VARCHAR
)
RETURNS VARCHAR
LANGUAGE PYTHON
RUNTIME_VERSION = '3.11'
PACKAGES = ('snowflake-snowpark-python', 'pandas', 'rapidfuzz')
HANDLER = 'main'
EXECUTE AS OWNER
AS
$$
import re
import uuid
import json
import pandas as pd
from rapidfuzz import fuzz

MATCH_THRESHOLD = 0.85

def normalize_phone(v):
    if v is None or (isinstance(v, float) and pd.isna(v)) or str(v).strip() == '':
        return ''
    digits = re.sub(r'\D', '', str(v))
    if len(digits) == 11 and digits.startswith('1'):
        digits = digits[1:]
    return digits

def normalize_email(v):
    if v is None or (isinstance(v, float) and pd.isna(v)) or str(v).strip() == '':
        return ''
    e = str(v).strip().lower()
    e = re.sub(r'\+[^@]*', '', e)
    return e

def normalize_value(v):
    if v is None or (isinstance(v, float) and pd.isna(v)) or str(v).strip() == '':
        return ''
    v = str(v).lower().strip()
    v = re.sub(r'\s+', ' ', v)
    return v

def is_empty(v):
    if v is None:
        return True
    if isinstance(v, float) and pd.isna(v):
        return True
    if str(v).strip() == '':
        return True
    return False

def normalize_field(v, method):
    if is_empty(v):
        return ''
    if method == 'phone':
        return normalize_phone(v)
    elif method == 'email':
        return normalize_email(v)
    elif method == 'text':
        return normalize_value(v)
    return str(v).strip()

def compute_similarity(rec_a, rec_b, field_config):
    score = 0.0
    total_weight = 0.0
    for fc in field_config:
        w = fc['match_weight']
        if w is None or w == 0:
            continue
        col = fc['tgt_col']
        method = fc['normalize']
        val_a = normalize_field(rec_a.get(col), method)
        val_b = normalize_field(rec_b.get(col), method)
        if val_a == '' or val_b == '':
            continue
        total_weight += w
        if method in ('email', 'phone'):
            score += w * (1.0 if val_a == val_b else 0.0)
        else:
            score += w * (fuzz.ratio(val_a, val_b) / 100.0)
    if total_weight == 0:
        return 0.0
    return score / total_weight

def confidence_label(score):
    if score >= 0.95:
        return 'HIGH'
    elif score >= 0.85:
        return 'MEDIUM'
    else:
        return 'LOW'

def main(session, CONFIG_DATABASE, GROUP_NAME):
    config_db = CONFIG_DATABASE.strip().upper()
    run_id = str(uuid.uuid4())

    sources_df = session.sql(f"""
        SELECT DISTINCT
            SRC_DATABASE,
            STG_SCHEMA,
            STG_TABLE,
            TGT_DATABASE,
            TGT_SCHEMA,
            TGT_TABLE,
            STREAM_NAME,
            MERGE_KEY,
            EXECUTION_SEQ
        FROM {config_db}.BRONZE.SOURCE_MAPPING_CONFIG
        WHERE GROUP_NAME = '{GROUP_NAME}' AND IS_ACTIVE = TRUE
        ORDER BY EXECUTION_SEQ
    """).to_pandas()

    if len(sources_df) == 0:
        return f'ERROR: No active config found for GROUP_NAME={GROUP_NAME}'

    tgt_database = sources_df.iloc[0]['TGT_DATABASE'].strip().upper()
    merge_key_col = sources_df.iloc[0]['MERGE_KEY']

    config_df = session.sql(f"""
        SELECT
            f.value:tgt::STRING AS TGT_COL,
            f.value:match_weight::FLOAT AS MATCH_WEIGHT,
            COALESCE(f.value:normalize::STRING, 'none') AS NORMALIZE_METHOD
        FROM {config_db}.BRONZE.SOURCE_MAPPING_CONFIG c,
             LATERAL FLATTEN(INPUT => c.COLUMN_MAPPING) f
        WHERE c.GROUP_NAME = '{GROUP_NAME}'
        AND c.IS_ACTIVE = TRUE
        QUALIFY ROW_NUMBER() OVER (PARTITION BY f.value:tgt::STRING ORDER BY c.EXECUTION_SEQ) = 1
    """).to_pandas()

    field_config = []
    entity_fields = []

    for _, row in config_df.iterrows():
        tgt_col = row['TGT_COL']
        match_weight = row['MATCH_WEIGHT'] if not pd.isna(row['MATCH_WEIGHT']) else None
        normalize_method = row['NORMALIZE_METHOD']

        entity_fields.append({
            'tgt_col': tgt_col,
            'normalize': normalize_method
        })

        field_config.append({
            'tgt_col': tgt_col,
            'match_weight': match_weight,
            'normalize': normalize_method
        })

    all_records = []

    for _, src_row in sources_df.iterrows():
        tgt_db = src_row['TGT_DATABASE'].strip().upper()
        tgt_schema = src_row['TGT_SCHEMA'].strip().upper()
        stream_name = src_row['STREAM_NAME']
        df = session.sql(f"""
            SELECT *
            FROM {tgt_db}.{tgt_schema}.{stream_name}
            WHERE METADATA$ACTION = 'INSERT'
        """).to_pandas()
        all_records.extend(df.to_dict('records'))

    if len(all_records) == 0:
        return 'NO_NEW_DATA: No changes detected in streams.'

    new_records = all_records

    existing_df = session.sql(f"""
        SELECT MASTER_ID, ENTITY_DATA, SOURCE_IDS, SOURCE_SYSTEMS, CLUSTER_SIZE
        FROM {tgt_database}.MDM.MASTER_ENTITY
        WHERE GROUP_NAME = '{GROUP_NAME}'
    """).to_pandas()

    existing_masters = []
    for _, row in existing_df.iterrows():
        entity_data = row['ENTITY_DATA']
        if isinstance(entity_data, str):
            entity_data = json.loads(entity_data)
        existing_masters.append({
            'MASTER_ID': row['MASTER_ID'],
            'ENTITY_DATA': entity_data,
            'SOURCE_IDS': row['SOURCE_IDS'],
            'SOURCE_SYSTEMS': row['SOURCE_SYSTEMS'],
            'CLUSTER_SIZE': int(row['CLUSTER_SIZE']) if row['CLUSTER_SIZE'] else 0
        })

    unmatched = []
    updates_count = 0

    for rec in new_records:
        best_score = 0.0
        best_master = None
        for master in existing_masters:
            sim = compute_similarity(rec, master['ENTITY_DATA'], field_config)
            if sim > best_score:
                best_score = sim
                best_master = master

        if best_score >= MATCH_THRESHOLD and best_master is not None:
            src_id = str(rec.get(merge_key_col, ''))
            src_sys = str(rec.get('SOURCE_SYSTEM', ''))
            existing_ids = best_master['SOURCE_IDS']
            existing_sys = best_master['SOURCE_SYSTEMS']
            if src_id not in existing_ids.split(','):
                new_ids = existing_ids + ',' + src_id
                new_sys = existing_sys + ',' + src_sys
                new_size = best_master['CLUSTER_SIZE'] + 1
                session.sql(f"""
                    UPDATE {tgt_database}.MDM.MASTER_ENTITY
                    SET SOURCE_IDS = '{new_ids}',
                        SOURCE_SYSTEMS = '{new_sys}',
                        CLUSTER_SIZE = {new_size}
                    WHERE MASTER_ID = '{best_master['MASTER_ID']}'
                """).collect()
                best_master['SOURCE_IDS'] = new_ids
                best_master['SOURCE_SYSTEMS'] = new_sys
                best_master['CLUSTER_SIZE'] = new_size
                updates_count += 1
        else:
            unmatched.append(rec)

    clusters = []
    used = set()
    for i in range(len(unmatched)):
        if i in used:
            continue
        cluster = [unmatched[i]]
        used.add(i)
        for j in range(i + 1, len(unmatched)):
            if j in used:
                continue
            sim = compute_similarity(unmatched[i], unmatched[j], field_config)
            if sim >= MATCH_THRESHOLD:
                cluster.append(unmatched[j])
                used.add(j)
        clusters.append(cluster)

    new_entities = []
    inserts_count = 0

    for cluster in clusters:
        best_rec = cluster[0]
        source_ids = ','.join([str(r.get(merge_key_col, '')) for r in cluster])
        source_systems = ','.join([str(r.get('SOURCE_SYSTEM', '')) for r in cluster])

        max_master_id = session.sql(f"""
            SELECT COALESCE(MAX(CAST(REPLACE(MASTER_ID, 'MSTR-', '') AS INTEGER)), 0)
            FROM {tgt_database}.MDM.MASTER_ENTITY
        """).collect()[0][0]

        next_id = max_master_id + len(new_entities) + 1
        master_id = f'MSTR-{next_id:05d}'

        entity_data = {}
        for ef in entity_fields:
            col = ef['tgt_col']
            method = ef['normalize']
            entity_data[col] = normalize_field(best_rec.get(col), method)

        avg_score = sum(
            compute_similarity(cluster[0], c, field_config) for c in cluster[1:]
        ) / max(len(cluster) - 1, 1) if len(cluster) > 1 else 1.0

        new_entities.append({
            'MASTER_ID': master_id,
            'GROUP_NAME': GROUP_NAME,
            'ENTITY_DATA': json.dumps(entity_data),
            'SOURCE_IDS': source_ids,
            'SOURCE_SYSTEMS': source_systems,
            'CLUSTER_SIZE': len(cluster),
            'MATCH_CONFIDENCE': confidence_label(avg_score),
            'PIPELINE_RUN_ID': run_id
        })

    for ent in new_entities:
        entity_json = ent['ENTITY_DATA'].replace("'", "''")
        session.sql(f"""
            INSERT INTO {tgt_database}.MDM.MASTER_ENTITY
            (MASTER_ID, GROUP_NAME, ENTITY_DATA, SOURCE_IDS, SOURCE_SYSTEMS, CLUSTER_SIZE, MATCH_CONFIDENCE, PIPELINE_RUN_ID, CREATED_TS)
            SELECT
                '{ent['MASTER_ID']}',
                '{ent['GROUP_NAME']}',
                PARSE_JSON('{entity_json}'),
                '{ent['SOURCE_IDS']}',
                '{ent['SOURCE_SYSTEMS']}',
                {ent['CLUSTER_SIZE']},
                '{ent['MATCH_CONFIDENCE']}',
                '{ent['PIPELINE_RUN_ID']}',
                CURRENT_TIMESTAMP()
        """).collect()
        inserts_count += 1

    keys_df = session.sql(f"""
        SELECT DISTINCT f.key
        FROM {tgt_database}.MDM.MASTER_ENTITY,
             LATERAL FLATTEN(INPUT => ENTITY_DATA) f
        ORDER BY f.key
    """).to_pandas()

    if len(keys_df) > 0:
        entity_cols = ",\n            ".join(
            [f"ENTITY_DATA:{row['KEY']}::STRING AS {row['KEY']}" for _, row in keys_df.iterrows()]
        )
        view_sql = f"""
            CREATE OR REPLACE VIEW {tgt_database}.MDM.MASTER_ENTITY_FLAT AS
            SELECT
                MASTER_ID,
                GROUP_NAME,
                {entity_cols},
                SOURCE_IDS,
                SOURCE_SYSTEMS,
                CLUSTER_SIZE,
                MATCH_CONFIDENCE,
                PIPELINE_RUN_ID,
                CREATED_TS
            FROM {tgt_database}.MDM.MASTER_ENTITY
        """
        session.sql(view_sql).collect()

    return (
        f'SUCCESS | run_id={run_id} | '
        f'delta_records={len(new_records)} | '
        f'matched_to_existing={updates_count} | '
        f'new_masters_created={inserts_count}'
    )
$$;

CALL CUSTOMER_MDM_DB.BRONZE.SP_LOAD_GROUP('CUSTOMER_MDM_DB', 'CUSTOMER_UNIFICATION_MULTI_DB');

CALL CUSTOMER_MDM_DB.MDM.SP_MASTER_ENTITY('CUSTOMER_MDM_DB', 'CUSTOMER_UNIFICATION_MULTI_DB');