

-- ============================================================

-- DATABASE & SCHEMA

-- ============================================================
select * from bronze.all_customers;
USE DATABASE DATA_UNIFICATION_DB;
 
--CREATE SCHEMA IF NOT EXISTS BRONZE;
 
USE SCHEMA BRONZE;
 
-- ============================================================

-- STEP 1 : METADATA CONFIG TABLE

-- ============================================================
 select * from BRONZE.SOURCE_MAPPING_CONFIG;
CREATE OR REPLACE TABLE BRONZE.SOURCE_MAPPING_CONFIG

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
 
-- ============================================================

-- STEP 2 : INSERT SAP METADATA

-- ============================================================
 
INSERT INTO BRONZE.SOURCE_MAPPING_CONFIG

(

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

    COLUMN_MAPPING,

    STREAM_NAME

)

SELECT

    'GROUP_1',

    1,

    'SAP',

    'DATA_UNIFICATION_DB',

    'RAW_STG',

    'SAP_CUSTOMERS_STG',

    'DATA_UNIFICATION_DB',

    'BRONZE',

    'SAP_CUSTOMER_MASTER',

    'CUSTOMER_ID',

    'KUNNR',
 
    PARSE_JSON(

    '[

        {"src":"KUNNR","tgt":"CUSTOMER_ID","match_weight":null,"normalize":"none"},

        {"src":"expr:NAME1 || '' '' || NAME2","tgt":"CUSTOMER_NAME","match_weight":0.15,"normalize":"text"},

        {"src":"SMTP_ADDR","tgt":"EMAIL","match_weight":0.40,"normalize":"email"},

        {"src":"TELF1","tgt":"PHONE","match_weight":0.30,"normalize":"phone"},

        {"src":"CITY","tgt":"CITY","match_weight":0.15,"normalize":"text"},

        {"src":"STATE","tgt":"STATE","match_weight":null,"normalize":"text"},

        {"src":"POST_CODE","tgt":"ZIP_CODE","match_weight":null,"normalize":"none"},

        {"src":"COUNTRY","tgt":"COUNTRY","match_weight":null,"normalize":"text"},

        {"src":"CUSTOMER_GROUP","tgt":"CUSTOMER_TYPE","match_weight":null,"normalize":"text"},

        {"src":"const:SAP","tgt":"SOURCE_SYSTEM","match_weight":null,"normalize":"none"}

    ]'

    ),

    'STM_SAP_CUSTOMER_MASTER';
 
-- ============================================================

-- STEP 3 : INSERT ORACLE METADATA

-- ============================================================
 
INSERT INTO BRONZE.SOURCE_MAPPING_CONFIG

(

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

    COLUMN_MAPPING,

    STREAM_NAME

)

SELECT

    'GROUP_1',

    2,

    'ORACLE',

    'DATA_UNIFICATION_DB',

    'RAW_STG',

    'ORACLE_CUSTOMERS_STG',

    'DATA_UNIFICATION_DB',

    'BRONZE',

    'ORACLE_CUSTOMERS',

    'CUSTOMER_ID',

    'PARTY_ID',
 
    PARSE_JSON(

    '[

        {"src":"PARTY_ID","tgt":"CUSTOMER_ID","match_weight":null,"normalize":"none"},

        {"src":"CUSTOMER_NAME","tgt":"CUSTOMER_NAME","match_weight":0.15,"normalize":"text"},

        {"src":"EMAIL_ADDRESS","tgt":"EMAIL","match_weight":0.40,"normalize":"email"},

        {"src":"PHONE_NUMBER","tgt":"PHONE","match_weight":0.30,"normalize":"phone"},

        {"src":"CITY","tgt":"CITY","match_weight":0.15,"normalize":"text"},

        {"src":"STATE","tgt":"STATE","match_weight":null,"normalize":"text"},

        {"src":"ZIP_CODE","tgt":"ZIP_CODE","match_weight":null,"normalize":"none"},

        {"src":"COUNTRY","tgt":"COUNTRY","match_weight":null,"normalize":"text"},

        {"src":"CUSTOMER_CATEGORY","tgt":"CUSTOMER_TYPE","match_weight":null,"normalize":"text"},

        {"src":"const:ORACLE","tgt":"SOURCE_SYSTEM","match_weight":null,"normalize":"none"}

    ]'

    ),

    'STM_ORACLE_CUSTOMERS';
 
-- ============================================================

-- STEP 4 : INSERT SALESFORCE METADATA

-- ============================================================
 
INSERT INTO BRONZE.SOURCE_MAPPING_CONFIG

(

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

    COLUMN_MAPPING,

    STREAM_NAME

)

SELECT

    'GROUP_1',

    3,

    'SALESFORCE',

    'DATA_UNIFICATION_DB',

    'RAW_STG',

    'SALESFORCE_CUSTOMERS_STG',

    'DATA_UNIFICATION_DB',

    'BRONZE',

    'SALESFORCE_ACCOUNTS',

    'CUSTOMER_ID',

    'ACCOUNT_ID',
 
    PARSE_JSON(

    '[

        {"src":"ACCOUNT_ID","tgt":"CUSTOMER_ID","match_weight":null,"normalize":"none"},

        {"src":"ACCOUNT_NAME","tgt":"CUSTOMER_NAME","match_weight":0.15,"normalize":"text"},

        {"src":"EMAIL","tgt":"EMAIL","match_weight":0.40,"normalize":"email"},

        {"src":"PHONE","tgt":"PHONE","match_weight":0.30,"normalize":"phone"},

        {"src":"BILLING_CITY","tgt":"CITY","match_weight":0.15,"normalize":"text"},

        {"src":"STATE","tgt":"STATE","match_weight":null,"normalize":"text"},

        {"src":"NULL","tgt":"ZIP_CODE","match_weight":null,"normalize":"none"},

        {"src":"COUNTRY","tgt":"COUNTRY","match_weight":null,"normalize":"text"},

        {"src":"ACCOUNT_TYPE","tgt":"CUSTOMER_TYPE","match_weight":null,"normalize":"text"},

        {"src":"const:SALESFORCE","tgt":"SOURCE_SYSTEM","match_weight":null,"normalize":"none"}

    ]'

    ),

    'STM_SALESFORCE_ACCOUNTS';

 
-- ============================================================

-- STEP 5 : AUDIT LOG TABLE

-- ============================================================
 
CREATE OR REPLACE TABLE BRONZE.MERGE_AUDIT_LOG

(

    LOG_ID             NUMBER AUTOINCREMENT PRIMARY KEY,
 
    RUN_ID             STRING,
 
    GROUP_NAME         STRING,
 
    SOURCE_SYSTEM      STRING,
 
    STG_TABLE          STRING,
 
    TGT_TABLE          STRING,
 
    ROWS_INSERTED      NUMBER DEFAULT 0,
 
    ROWS_UPDATED       NUMBER DEFAULT 0,
 
    STATUS             STRING,
 
    ERROR_MESSAGE      STRING,
 
    GENERATED_SQL      STRING,
 
    STARTED_TS         TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
 
    COMPLETED_TS       TIMESTAMP

);
 
-- ============================================================

-- STEP 6 : DYNAMIC GROUP PROCEDURE

-- ============================================================
 
CREATE OR REPLACE PROCEDURE BRONZE.SP_LOAD_GROUP

(

    P_GROUP_NAME STRING

)

RETURNS VARIANT

LANGUAGE JAVASCRIPT

AS

$$
 
function sql(q, binds)

{

    return binds

        ? snowflake.execute({sqlText:q, binds:binds})

        : snowflake.execute({sqlText:q});

}
 
function scalar(q)

{

    var rs = snowflake.execute({sqlText:q});
 
    return rs.next()

        ? rs.getColumnValue(1)

        : null;

}
 
var RUN_ID = scalar(

    "SELECT UUID_STRING()"

);
 
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
 
FROM DATA_UNIFICATION_DB.BRONZE.SOURCE_MAPPING_CONFIG
 
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
 
while(configs.next())

{
 
    var groupName  = configs.getColumnValue('GROUP_NAME');
 
    var sourceSys  = configs.getColumnValue('SOURCE_SYSTEM');

    var srcDatabase = configs.getColumnValue('SRC_DATABASE');
 
    var stgSchema  = configs.getColumnValue('STG_SCHEMA');
 
    var stgTable   = configs.getColumnValue('STG_TABLE');

    var tgtDatabase = configs.getColumnValue('TGT_DATABASE');
 
    var tgtSchema  = configs.getColumnValue('TGT_SCHEMA');
 
    var tgtTable   = configs.getColumnValue('TGT_TABLE');
 
    var mergeKey   = configs.getColumnValue('MERGE_KEY');
 
    var mapping    = configs.getColumnValue('COLUMN_MAPPING');
 
    var startTs    = scalar(

        "SELECT CURRENT_TIMESTAMP()::STRING"

    );
 
    var rowsIns    = 0;
 
    var rowsUpd    = 0;
 
    var status     = 'SUCCESS';
 
    var errorMsg   = null;
 
    var mergeSQL   = '';
 
    try

    {
 
        if(typeof mapping === 'string')

        {

            mapping = JSON.parse(mapping);

        }
 
        var selectParts = [];
 
        var tgtCols = [];
 
        var srcVals = [];
 
        var updateSets = [];

        var updateConditions = [];
 
        var noUpdate =

        [

            mergeKey.toUpperCase(),

            'SOURCE_SYSTEM',

            'LOAD_TIMESTAMP'

        ];
 
        for(var i=0; i<mapping.length; i++)

        {
 
            var raw    = mapping[i].src;
 
            var tgtCol = mapping[i].tgt.toUpperCase();
 
            var expr;
 
            if(raw.indexOf('const:') === 0)

            {
 
                var v = raw.slice(6);
 
                expr = "'" + v + "'";

            }

            else if(raw.indexOf('expr:') === 0)

            {

                expr = raw.slice(5);

            }

            else

            {

                expr = raw;

            }
 
            selectParts.push(

                expr + ' AS ' + tgtCol

            );
 
            tgtCols.push(tgtCol);
 
            srcVals.push(

                'S.' + tgtCol

            );
 
            if(noUpdate.indexOf(tgtCol) === -1)

            {

                updateSets.push(

                    'T.' + tgtCol + ' = S.' + tgtCol

                );

                updateConditions.push(

                    'T.' + tgtCol +

                    ' IS DISTINCT FROM S.' +

                    tgtCol

                );

            }

        }
 
        tgtCols.push(

            'LOAD_TIMESTAMP',

            'LAST_MODIFIED_DATE'

        );
 
        srcVals.push(

            'CURRENT_TIMESTAMP()',

            'CURRENT_TIMESTAMP()'

        );
 
        updateSets.push(

            'T.LAST_MODIFIED_DATE = CURRENT_TIMESTAMP()'

        );
 
        var fullSrc =

            srcDatabase + '.' +

            stgSchema +

            '.' +

            stgTable;
 
        var fullTgt =

            tgtDatabase + '.' +

            tgtSchema +

            '.' +

            tgtTable;
 
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

    catch(e)

    {

        status = 'FAILED';
 
        errorMsg = e.message || String(e);
 
        anyError = true;

    }
 
    sql(

    `
 
    INSERT INTO DATA_UNIFICATION_DB.BRONZE.MERGE_AUDIT_LOG

    (

        RUN_ID,

        GROUP_NAME,

        SOURCE_SYSTEM,

        STG_TABLE,

        TGT_TABLE,

        ROWS_INSERTED,

        ROWS_UPDATED,

        STATUS,

        ERROR_MESSAGE,

        GENERATED_SQL,

        STARTED_TS,

        COMPLETED_TS

    )
 
    VALUES

    (

        ?,?,?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP()

    )
 
    `,

    [

        RUN_ID,

        groupName,

        sourceSys,

        stgTable,

        tgtTable,

        rowsIns,

        rowsUpd,

        status,

        errorMsg,

        mergeSQL,

        startTs

    ]

    );
 
    results.push(

    {

        source_system : sourceSys,

        rows_inserted : rowsIns,

        rows_updated  : rowsUpd,

        status        : status,

        error         : errorMsg

    });
 
}
 
return {

    run_id      : RUN_ID,

    overall     : anyError ? 'PARTIAL_FAILURE' : 'SUCCESS',

    details     : results

};
 
$$;



 
-- ============================================================

-- STEP 7 : TASK

-- ============================================================
 
CREATE OR REPLACE TASK BRONZE.TASK_GROUP
 
WAREHOUSE = COMPUTE_WH
 
SCHEDULE = '5 MINUTE'
 
AS
 
CALL DATA_UNIFICATION_DB.BRONZE.SP_LOAD_GROUP('GROUP_1');
 
ALTER TASK BRONZE.TASK_GROUP RESUME;
alter task bronze.task_group suspend;
 
-- ============================================================

-- STEP 8 : STREAMS

-- ============================================================
 
CREATE OR REPLACE STREAM BRONZE.STM_SAP_CUSTOMER_MASTER

ON TABLE BRONZE.SAP_CUSTOMER_MASTER;
 
CREATE OR REPLACE STREAM BRONZE.STM_ORACLE_CUSTOMERS

ON TABLE BRONZE.ORACLE_CUSTOMERS;
 
CREATE OR REPLACE STREAM BRONZE.STM_SALESFORCE_ACCOUNTS

ON TABLE BRONZE.SALESFORCE_ACCOUNTS;



-- ============================================================

-- STEP 9 : EXECUTE PROCEDURE

-- ============================================================
 
CALL DATA_UNIFICATION_DB.BRONZE.SP_LOAD_GROUP('GROUP_1');
 
-- ============================================================

-- STEP 10 : CHECK AUDIT LOGS

-- ============================================================
 
SELECT *

FROM BRONZE.MERGE_AUDIT_LOG;

ORDER BY LOG_ID DESC;
 
-- ============================================================

-- STEP 11 : CHECK STREAMS

-- ============================================================
 
SELECT * FROM BRONZE.STM_SAP_CUSTOMER_MASTER;
 
SELECT * FROM BRONZE.STM_ORACLE_CUSTOMERS;
 
SELECT * FROM BRONZE.STM_SALESFORCE_ACCOUNTS;


 
select * from DATA_UNIFICATION_DB.RAW_STG.SAP_CUSTOMERS_STG;

select * from data_unification_db.raw_stg.oracle_customers_stg;

select * from data_unification_db.raw_stg.salesforce_customers_stg;
 
INSERT INTO DATA_UNIFICATION_DB.RAW_STG.SAP_CUSTOMERS_STG

(

    KUNNR,

    NAME1,

    NAME2,

    CITY,

    STATE,

    POST_CODE,

    TELF1,

    SMTP_ADDR,

    COUNTRY,

    CUSTOMER_GROUP,

    CREATED_DATE

)

VALUES

(

    'C011',

    'Daniel',

    'Evans',

    'Phoenix',

    'AZ',

    '85001',

    '480-555-1111',

    'daniel.evans@nexlify.com',

    'USA',

    'A',

    CURRENT_DATE()

);

INSERT INTO DATA_UNIFICATION_DB.RAW_STG.ORACLE_CUSTOMERS_STG
(
    PARTY_ID,
    CUSTOMER_NAME,
    EMAIL_ADDRESS,
    PHONE_NUMBER,
    CITY,
    STATE,
    ZIP_CODE,
    COUNTRY,
    CUSTOMER_CATEGORY
)
VALUES
(
    'P1011',
    'Nathan Brooks',
    'nathan.brooks@quantix.com',
    '(404)555-7788',
    'Atlanta',
    'GA',
    '30301',
    'USA',
    'Premium'
);

INSERT INTO DATA_UNIFICATION_DB.RAW_STG.ORACLE_CUSTOMERS_STG
(
    PARTY_ID,
    CUSTOMER_NAME,
    EMAIL_ADDRESS,
    PHONE_NUMBER,
    CITY,
    STATE,
    ZIP_CODE,
    COUNTRY,
    CUSTOMER_CATEGORY
)
VALUES
(
    'P1012',
    'Grace Mitchell',
    'grace.mitchell@novasphere.com',
    '617-555-8899',
    'Boston',
    'MA',
    '02108',
    'USA',
    'Standard'
);


INSERT INTO DATA_UNIFICATION_DB.RAW_STG.SALESFORCE_CUSTOMERS_STG
(
    ACCOUNT_ID,
    ACCOUNT_NAME,
    EMAIL,
    PHONE,
    BILLING_CITY,
    STATE,
    COUNTRY,
    ACCOUNT_TYPE
)
VALUES
(
    'ACC-10011',
    'Aiden Clark Technologies',
    'aiden.clark@brightcore.com',
    '718-555-6677',
    'Brooklyn',
    'NY',
    'USA',
    'Customer'
);

INSERT INTO DATA_UNIFICATION_DB.RAW_STG.SALESFORCE_CUSTOMERS_STG
(
    ACCOUNT_ID,
    ACCOUNT_NAME,
    EMAIL,
    PHONE,
    BILLING_CITY,
    STATE,
    COUNTRY,
    ACCOUNT_TYPE
)
VALUES
(
    'ACC-10012',
    'Logan Pierce Solutions',
    'logan.pierce@zenitek.com',
    '415-555-7788',
    'Austin',
    'TX',
    'USA',
    'Customer'
);


INSERT INTO DATA_UNIFICATION_DB.RAW_STG.SAP_ACCOUNTS_STG
(
    ACCOUNT_ID,
    ACCOUNT_NAME,
    ACCOUNT_TYPE,
    CITY,
    STATE,
    COUNTRY
)
VALUES
(
    'A011',
    'QuantumEdge Systems',
    'Enterprise',
    'Phoenix',
    'AZ',
    'USA'
);
 
select * from data_unification_db.bronze.oracle_customers;
 
select * from data_unification_db.bronze.sap_customer_master;
 
select * from data_unification_db.bronze.salesforce_accounts;





SELECT *
FROM BRONZE.SOURCE_MAPPING_CONFIG;

UPDATE DATA_UNIFICATION_DB.BRONZE.SOURCE_MAPPING_CONFIG
SET STREAM_NAME = 'STM_SAP_CUSTOMER_MASTER'
WHERE GROUP_NAME = 'GROUP_1'
AND SOURCE_SYSTEM = 'SAP';

UPDATE DATA_UNIFICATION_DB.BRONZE.SOURCE_MAPPING_CONFIG
SET STREAM_NAME = 'STM_ORACLE_CUSTOMERS'
WHERE GROUP_NAME = 'GROUP_1'
AND SOURCE_SYSTEM = 'ORACLE';

UPDATE DATA_UNIFICATION_DB.BRONZE.SOURCE_MAPPING_CONFIG
SET STREAM_NAME = 'STM_SALESFORCE_ACCOUNTS'
WHERE GROUP_NAME = 'GROUP_1'
AND SOURCE_SYSTEM = 'SALESFORCE';

ALTER TABLE DATA_UNIFICATION_DB.BRONZE.SOURCE_MAPPING_CONFIG
ADD COLUMN STREAM_NAME STRING;





SELECT COUNT(*)
FROM RAW_STG.ORACLE_ACCOUNT_STG;

SELECT COUNT(*)
FROM RAW_STG.SAP_ACCOUNTS_STG;

SELECT *
FROM BRONZE.MERGE_AUDIT_LOG
ORDER BY LOG_ID DESC;

SELECT
GROUP_NAME,
SOURCE_SYSTEM,
STG_TABLE,
TGT_TABLE,
STREAM_NAME,
IS_ACTIVE
FROM DATA_UNIFICATION_DB.BRONZE.SOURCE_MAPPING_CONFIG
WHERE GROUP_NAME='GROUP_1';

SELECT DISTINCT GROUP_NAME
FROM DATA_UNIFICATION_DB.BRONZE.SOURCE_MAPPING_CONFIG;

select * from data_unification_db.bronze.source_mapping_config;