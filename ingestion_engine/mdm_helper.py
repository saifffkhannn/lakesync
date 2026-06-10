import os
import json
import logging
import uuid
import snowflake.connector

logger = logging.getLogger("mdm_helper")

class MDMHelper:
    def __init__(self):
        pass

    def get_connection(self, creds: dict):
        try:
            account = creds.get("account", "").strip()
            user = creds.get("username", creds.get("user", "")).strip()
            password = creds.get("password", "").strip()
            warehouse = creds.get("warehouse", "").strip()
            database = creds.get("database", "").strip()
            schema = creds.get("schema", "PUBLIC").strip()

            return snowflake.connector.connect(
                account=account,
                user=user,
                password=password,
                warehouse=warehouse,
                database=database,
                schema=schema
            )
        except Exception as e:
            logger.error(f"MDM Snowflake connection failed: {e}")
            raise Exception(f"Failed to connect to Snowflake: {e}")

    def fetch_tables(self, creds: dict, schema: str):
        conn = self.get_connection(creds)
        try:
            cursor = conn.cursor()
            db = creds.get("database", "").upper()
            cursor.execute(f"SELECT TABLE_NAME FROM {db}.INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = '{schema.upper()}'")
            return [row[0] for row in cursor.fetchall()]
        finally:
            conn.close()

    def fetch_columns(self, creds: dict, schema: str, table: str):
        conn = self.get_connection(creds)
        try:
            cursor = conn.cursor()
            db = creds.get("database", "").upper()
            cursor.execute(f"""
                SELECT COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH, NUMERIC_PRECISION, NUMERIC_SCALE, ORDINAL_POSITION, IS_NULLABLE
                FROM {db}.INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = '{schema.upper()}' AND TABLE_NAME = '{table.upper()}'
                ORDER BY ORDINAL_POSITION
            """)
            rows = cursor.fetchall()
            return [{
                "column_name": row[0],
                "data_type": row[1].lower(),
                "char_length": row[2],
                "precision": row[3],
                "scale": row[4],
                "ordinal_position": row[5],
                "nullable": row[6]
            } for row in rows]
        finally:
            conn.close()

    def deploy_structures(self, creds: dict):
        conn = self.get_connection(creds)
        try:
            cursor = conn.cursor()
            db = creds.get("database", "").upper()

            # Ensure schemas exist
            cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {db}.BRONZE")
            cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {db}.MDM")

            # Create Config Table
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS {db}.BRONZE.SOURCE_MAPPING_CONFIG (
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
                )
            """)

            # Create Audit Log
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS {db}.BRONZE.MERGE_AUDIT_LOG (
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
                )
            """)

            # Create MASTER_ENTITY Table
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS {db}.MDM.MASTER_ENTITY (
                    MASTER_ID        VARCHAR,
                    GROUP_NAME       VARCHAR,
                    ENTITY_DATA      VARIANT,
                    SOURCE_IDS       VARCHAR,
                    SOURCE_SYSTEMS   VARCHAR,
                    CLUSTER_SIZE     NUMBER,
                    MATCH_CONFIDENCE VARCHAR,
                    PIPELINE_RUN_ID  VARCHAR,
                    CREATED_TS       TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
                )
            """)
        finally:
            conn.close()

    def configure_mapping(self, creds: dict, config_payload: dict):
        conn = self.get_connection(creds)
        try:
            cursor = conn.cursor()
            db = creds.get("database", "").upper()

            group_name = config_payload.get("group_name", "CUSTOMER_UNIFICATION_MULTI_DB")
            source_system = config_payload.get("source_system", "")
            src_db = config_payload.get("src_db", db)
            stg_schema = config_payload.get("stg_schema", "RAW_STG")
            stg_table = config_payload.get("stg_table", "")
            tgt_schema = config_payload.get("tgt_schema", "BRONZE")
            tgt_table = config_payload.get("tgt_table", "")
            merge_key = config_payload.get("merge_key", "")
            stg_merge_key = config_payload.get("stg_merge_key", "")
            column_mapping = config_payload.get("column_mapping", []) # JSON Array of objects: {"src":..., "tgt":..., "normalize":..., "match_weight":...}
            stream_name = config_payload.get("stream_name", f"STM_{stg_table}")

            # Enable Change Tracking on Target Table
            try:
                cursor.execute(f"ALTER TABLE {db}.{tgt_schema}.{tgt_table} SET CHANGE_TRACKING = TRUE")
            except Exception as e:
                logger.warning(f"Failed to enable change tracking: {e}")

            # Create Stream if it doesn't exist
            try:
                cursor.execute(f"CREATE STREAM IF NOT EXISTS {db}.{tgt_schema}.{stream_name} ON TABLE {db}.{tgt_schema}.{tgt_table}")
            except Exception as e:
                logger.warning(f"Failed to create stream: {e}")

            # Delete existing mapping config if matching group_name & source_system to overwrite
            cursor.execute(f"""
                DELETE FROM {db}.BRONZE.SOURCE_MAPPING_CONFIG
                WHERE GROUP_NAME = %s AND SOURCE_SYSTEM = %s
            """, (group_name, source_system))

            # Fetch next execution sequence
            cursor.execute(f"SELECT COALESCE(MAX(EXECUTION_SEQ), 0) + 1 FROM {db}.BRONZE.SOURCE_MAPPING_CONFIG WHERE GROUP_NAME = %s", (group_name,))
            next_seq = cursor.fetchone()[0]

            # Insert Config Row
            cursor.execute(f"""
                INSERT INTO {db}.BRONZE.SOURCE_MAPPING_CONFIG
                (GROUP_NAME, EXECUTION_SEQ, SOURCE_SYSTEM, SRC_DATABASE, STG_SCHEMA, STG_TABLE, TGT_DATABASE, TGT_SCHEMA, TGT_TABLE, MERGE_KEY, STG_MERGE_KEY, COLUMN_MAPPING, STREAM_NAME)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, PARSE_JSON(%s), %s)
            """, (group_name, next_seq, source_system, src_db, stg_schema, stg_table, db, tgt_schema, tgt_table, merge_key, stg_merge_key, json.dumps(column_mapping), stream_name))

        finally:
            conn.close()

    def deploy_procedures(self, creds: dict):
        conn = self.get_connection(creds)
        try:
            cursor = conn.cursor()
            db = creds.get("database", "").upper()

            # 1. Deploy SP_LOAD_GROUP procedure (Javascript)
            sp_load_group_sql = f"""
            CREATE OR REPLACE PROCEDURE {db}.BRONZE.SP_LOAD_GROUP(
                "P_CONFIG_DATABASE" VARCHAR,
                "P_GROUP_NAME" VARCHAR
            )
            RETURNS VARIANT
            LANGUAGE JAVASCRIPT
            EXECUTE AS OWNER
            AS
            $$
            function sql(q, binds) {{
                return binds
                    ? snowflake.execute({{sqlText:q, binds:binds}})
                    : snowflake.execute({{sqlText:q}});
            }}

            function scalar(q) {{
                var rs = snowflake.execute({{sqlText:q}});
                return rs.next() ? rs.getColumnValue(1) : null;
            }}

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

            while(configs.next()) {{
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

                try {{
                    var mapping = (typeof columnMapping === 'string') ? JSON.parse(columnMapping) : columnMapping;
                    var selectParts = [];
                    var tgtCols     = [];
                    var srcVals     = [];
                    var updateSets  = [];
                    var updateConditions = [];
                    var noUpdate = [mergeKey, 'LOAD_TIMESTAMP'];

                    for(var i = 0; i < mapping.length; i++) {{
                        var m = mapping[i];
                        var srcExpr = m.src;
                        var tgtCol  = m.tgt;

                        if(srcExpr === 'NULL') {{
                            selectParts.push('NULL AS ' + tgtCol);
                        }} else if(srcExpr.indexOf('expr:') === 0) {{
                            selectParts.push(srcExpr.replace('expr:','') + ' AS ' + tgtCol);
                        }} else {{
                            selectParts.push(srcExpr + ' AS ' + tgtCol);
                        }}

                        tgtCols.push(tgtCol);
                        srcVals.push('S.' + tgtCol);

                        if(noUpdate.indexOf(tgtCol) === -1) {{
                            updateSets.push('T.' + tgtCol + ' = S.' + tgtCol);
                            updateConditions.push('T.' + tgtCol + ' IS DISTINCT FROM S.' + tgtCol);
                        }}
                    }}

                    if(tgtCols.indexOf('SOURCE_SYSTEM') === -1) {{
                        selectParts.push("'" + sourceSystem + "' AS SOURCE_SYSTEM");
                        tgtCols.push('SOURCE_SYSTEM');
                        srcVals.push('S.SOURCE_SYSTEM');
                        updateSets.push('T.SOURCE_SYSTEM = S.SOURCE_SYSTEM');
                    }}

                    tgtCols.push('LOAD_TIMESTAMP', 'LAST_MODIFIED_DATE');
                    srcVals.push('CURRENT_TIMESTAMP()', 'CURRENT_TIMESTAMP()');
                    updateSets.push('T.LAST_MODIFIED_DATE = CURRENT_TIMESTAMP()');

                    var fullSrc = srcDatabase + '.' + stgSchema + '.' + stgTable;
                    var fullTgt = tgtDatabase + '.' + tgtSchema + '.' + tgtTable;

                    mergeSQL = [
                        'MERGE INTO ' + fullTgt + ' T',
                        'USING (',
                        ' SELECT ' + selectParts.join(',\\n '),
                        ' FROM ' + fullSrc,
                        ') S',
                        'ON T.' + mergeKey + ' = S.' + mergeKey,
                        '',
                        'WHEN MATCHED AND (',
                        updateConditions.join(' OR\\n'),
                        ') THEN',
                        'UPDATE SET',
                        updateSets.join(',\\n'),
                        '',
                        'WHEN NOT MATCHED THEN',
                        'INSERT (' + tgtCols.join(', ') + ')',
                        'VALUES (' + srcVals.join(', ') + ')'
                    ].join('\\n');

                    var mr = sql(mergeSQL);
                    mr.next();
                    rowsIns = mr.getColumnValue(1);
                    rowsUpd = mr.getColumnValue(2);

                    sql('TRUNCATE TABLE ' + fullSrc);
                }}
                catch(e) {{
                    status = 'FAILED';
                    errorMsg = e.message || String(e);
                    anyError = true;
                }}

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

                results.push({{
                    source_system: sourceSystem,
                    stg_table: stgTable,
                    tgt_table: tgtTable,
                    rows_inserted: rowsIns,
                    rows_updated: rowsUpd,
                    status: status,
                    error: errorMsg
                }});
            }}

            return {{
                run_id: RUN_ID,
                overall_status: anyError ? 'PARTIAL_FAILURE' : 'SUCCESS',
                results: results
            }};
            $$;
            """
            cursor.execute(sp_load_group_sql)

            # 2. Deploy SP_MASTER_ENTITY procedure (Python / Snowpark)
            sp_master_entity_sql = f"""
            CREATE OR REPLACE PROCEDURE {db}.MDM.SP_MASTER_ENTITY(
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
                digits = re.sub(r'\\D', '', str(v))
                if len(digits) == 11 and digits.startswith('1'):
                    digits = digits[1:]
                return digits

            def normalize_email(v):
                if v is None or (isinstance(v, float) and pd.isna(v)) or str(v).strip() == '':
                    return ''
                e = str(v).strip().lower()
                e = re.sub(r'\\+[^@]*', '', e)
                return e

            def normalize_value(v):
                if v is None or (isinstance(v, float) and pd.isna(v)) or str(v).strip() == '':
                    return ''
                v = str(v).lower().strip()
                v = re.sub(r'\\s+', ' ', v)
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

                sources_df = session.sql(f\"\"\"
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
                    FROM {{config_db}}.BRONZE.SOURCE_MAPPING_CONFIG
                    WHERE GROUP_NAME = '{{GROUP_NAME}}' AND IS_ACTIVE = TRUE
                    ORDER BY EXECUTION_SEQ
                \"\"\").to_pandas()

                if len(sources_df) == 0:
                    return f'ERROR: No active config found for GROUP_NAME={{GROUP_NAME}}'

                tgt_database = sources_df.iloc[0]['TGT_DATABASE'].strip().upper()
                merge_key_col = sources_df.iloc[0]['MERGE_KEY']

                config_df = session.sql(f\"\"\"
                    SELECT
                        f.value:tgt::STRING AS TGT_COL,
                        f.value:match_weight::FLOAT AS MATCH_WEIGHT,
                        COALESCE(f.value:normalize::STRING, 'none') AS NORMALIZE_METHOD
                    FROM {{config_db}}.BRONZE.SOURCE_MAPPING_CONFIG c,
                         LATERAL FLATTEN(INPUT => c.COLUMN_MAPPING) f
                    WHERE c.GROUP_NAME = '{{GROUP_NAME}}'
                    AND c.IS_ACTIVE = TRUE
                    QUALIFY ROW_NUMBER() OVER (PARTITION BY f.value:tgt::STRING ORDER BY c.EXECUTION_SEQ) = 1
                \"\"\").to_pandas()

                field_config = []
                entity_fields = []

                for _, row in config_df.iterrows():
                    tgt_col = row['TGT_COL']
                    match_weight = row['MATCH_WEIGHT'] if not pd.isna(row['MATCH_WEIGHT']) else None
                    normalize_method = row['NORMALIZE_METHOD']

                    entity_fields.append({{
                        'tgt_col': tgt_col,
                        'normalize': normalize_method
                    }})

                    field_config.append({{
                        'tgt_col': tgt_col,
                        'match_weight': match_weight,
                        'normalize': normalize_method
                    }})

                all_records = []

                for _, src_row in sources_df.iterrows():
                    tgt_db = src_row['TGT_DATABASE'].strip().upper()
                    tgt_schema = src_row['TGT_SCHEMA'].strip().upper()
                    stream_name = src_row['STREAM_NAME']
                    df = session.sql(f\"\"\"
                        SELECT *
                        FROM {{tgt_db}}.{{tgt_schema}}.{{stream_name}}
                        WHERE METADATA$ACTION = 'INSERT'
                    \"\"\").to_pandas()
                    all_records.extend(df.to_dict('records'))

                if len(all_records) == 0:
                    return 'NO_NEW_DATA: No changes detected in streams.'

                new_records = all_records

                existing_df = session.sql(f\"\"\"
                    SELECT MASTER_ID, ENTITY_DATA, SOURCE_IDS, SOURCE_SYSTEMS, CLUSTER_SIZE
                    FROM {{tgt_database}}.MDM.MASTER_ENTITY
                    WHERE GROUP_NAME = '{{GROUP_NAME}}'
                \"\"\").to_pandas()

                existing_masters = []
                for _, row in existing_df.iterrows():
                    entity_data = row['ENTITY_DATA']
                    if isinstance(entity_data, str):
                        entity_data = json.loads(entity_data)
                    existing_masters.append({{
                        'MASTER_ID': row['MASTER_ID'],
                        'ENTITY_DATA': entity_data,
                        'SOURCE_IDS': row['SOURCE_IDS'],
                        'SOURCE_SYSTEMS': row['SOURCE_SYSTEMS'],
                        'CLUSTER_SIZE': int(row['CLUSTER_SIZE']) if row['CLUSTER_SIZE'] else 0
                    }})

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
                            session.sql(f\"\"\"
                                UPDATE {{tgt_database}}.MDM.MASTER_ENTITY
                                SET SOURCE_IDS = '{{new_ids}}',
                                    SOURCE_SYSTEMS = '{{new_sys}}',
                                    CLUSTER_SIZE = {{new_size}}
                                WHERE MASTER_ID = '{{best_master['MASTER_ID']}}'
                            \"\"\").collect()
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

                    max_master_id = session.sql(f\"\"\"
                        SELECT COALESCE(MAX(CAST(REPLACE(MASTER_ID, 'MSTR-', '') AS INTEGER)), 0)
                        FROM {{tgt_database}}.MDM.MASTER_ENTITY
                    \"\"\").collect()[0][0]

                    next_id = max_master_id + len(new_entities) + 1
                    master_id = f'MSTR-{{next_id:05d}}'

                    entity_data = {{}}
                    for ef in entity_fields:
                        col = ef['tgt_col']
                        method = ef['normalize']
                        entity_data[col] = normalize_field(best_rec.get(col), method)

                    avg_score = sum(
                        compute_similarity(cluster[0], c, field_config) for c in cluster[1:]
                    ) / max(len(cluster) - 1, 1) if len(cluster) > 1 else 1.0

                    new_entities.append({{
                        'MASTER_ID': master_id,
                        'GROUP_NAME': GROUP_NAME,
                        'ENTITY_DATA': json.dumps(entity_data),
                        'SOURCE_IDS': source_ids,
                        'SOURCE_SYSTEMS': source_systems,
                        'CLUSTER_SIZE': len(cluster),
                        'MATCH_CONFIDENCE': confidence_label(avg_score),
                        'PIPELINE_RUN_ID': run_id
                    }})

                for ent in new_entities:
                    entity_json = ent['ENTITY_DATA'].replace("'", "''")
                    session.sql(f\"\"\"
                        INSERT INTO {{tgt_database}}.MDM.MASTER_ENTITY
                        (MASTER_ID, GROUP_NAME, ENTITY_DATA, SOURCE_IDS, SOURCE_SYSTEMS, CLUSTER_SIZE, MATCH_CONFIDENCE, PIPELINE_RUN_ID, CREATED_TS)
                        SELECT
                            '{{ent['MASTER_ID']}}',
                            '{{ent['GROUP_NAME']}}',
                            PARSE_JSON('{{entity_json}}'),
                            '{{ent['SOURCE_IDS']}}',
                            '{{ent['SOURCE_SYSTEMS']}}',
                            {{ent['CLUSTER_SIZE']}},
                            '{{ent['MATCH_CONFIDENCE']}}',
                            '{{ent['PIPELINE_RUN_ID']}}',
                            CURRENT_TIMESTAMP()
                    \"\"\").collect()
                    inserts_count += 1

                keys_df = session.sql(f\"\"\"
                    SELECT DISTINCT f.key
                    FROM {{tgt_database}}.MDM.MASTER_ENTITY,
                         LATERAL FLATTEN(INPUT => ENTITY_DATA) f
                    ORDER BY f.key
                \"\"\").to_pandas()

                if len(keys_df) > 0:
                    entity_cols = \",\\n            \".join(
                        [f\"ENTITY_DATA:{{row['KEY']}}::STRING AS {{row['KEY']}}\" for _, row in keys_df.iterrows()]
                    )
                    view_sql = f\"\"\"
                        CREATE OR REPLACE VIEW {{tgt_database}}.MDM.MASTER_ENTITY_FLAT AS
                        SELECT
                            MASTER_ID,
                            GROUP_NAME,
                            {{entity_cols}},
                            SOURCE_IDS,
                            SOURCE_SYSTEMS,
                            CLUSTER_SIZE,
                            MATCH_CONFIDENCE,
                            PIPELINE_RUN_ID,
                            CREATED_TS
                        FROM {{tgt_database}}.MDM.MASTER_ENTITY
                    \"\"\"
                    session.sql(view_sql).collect()

                return (
                    f'SUCCESS | run_id={{run_id}} | '
                    f'delta_records={{len(new_records)}} | '
                    f'matched_to_existing={{updates_count}} | '
                    f'new_masters_created={{inserts_count}}'
                )

            $$;
            """
            cursor.execute(sp_master_entity_sql)

        finally:
            conn.close()

    def run_mdm(self, creds: dict, group_name: str):
        conn = self.get_connection(creds)
        try:
            cursor = conn.cursor()
            db = creds.get("database", "").upper()

            # Execute Stage Load
            cursor.execute(f"CALL {db}.BRONZE.SP_LOAD_GROUP(%s, %s)", (db, group_name))
            load_result_raw = cursor.fetchone()[0]

            # Execute Master Entity MDM Matching
            cursor.execute(f"CALL {db}.MDM.SP_MASTER_ENTITY(%s, %s)", (db, group_name))
            mdm_result = cursor.fetchone()[0]

            return {
                "load_result": load_result_raw,
                "mdm_result": mdm_result
            }
        finally:
            conn.close()

    def fetch_audit_logs(self, creds: dict, group_name: str):
        conn = self.get_connection(creds)
        try:
            cursor = conn.cursor()
            db = creds.get("database", "").upper()
            cursor.execute(f"""
                SELECT LOG_ID, RUN_ID, SOURCE_SYSTEM, STG_TABLE, TGT_TABLE, ROWS_INSERTED, ROWS_UPDATED, STATUS, ERROR_MESSAGE, STARTED_TS
                FROM {db}.BRONZE.MERGE_AUDIT_LOG
                WHERE GROUP_NAME = %s
                ORDER BY STARTED_TS DESC
                LIMIT 50
            """, (group_name,))
            rows = cursor.fetchall()
            return [{
                "log_id": row[0],
                "run_id": row[1],
                "source_system": row[2],
                "stg_table": row[3],
                "tgt_table": row[4],
                "rows_inserted": row[5],
                "rows_updated": row[6],
                "status": row[7],
                "error_message": row[8],
                "timestamp": str(row[9])
            } for row in rows]
        finally:
            conn.close()

    def fetch_master_records(self, creds: dict, group_name: str):
        conn = self.get_connection(creds)
        try:
            cursor = conn.cursor()
            db = creds.get("database", "").upper()
            
            # Check if Master Entity Flat view exists before querying
            try:
                cursor.execute(f"SELECT * FROM {db}.MDM.MASTER_ENTITY_FLAT WHERE GROUP_NAME = %s LIMIT 100", (group_name,))
                columns = [desc[0] for desc in cursor.description]
                rows = cursor.fetchall()
                return [dict(zip(columns, row)) for row in rows]
            except Exception as view_err:
                logger.warning(f"Flat view query failed: {view_err}. Trying direct query.")
                # Fallback to direct query from MASTER_ENTITY
                cursor.execute(f"SELECT MASTER_ID, ENTITY_DATA, SOURCE_IDS, SOURCE_SYSTEMS, CLUSTER_SIZE, MATCH_CONFIDENCE FROM {db}.MDM.MASTER_ENTITY WHERE GROUP_NAME = %s LIMIT 100", (group_name,))
                rows = cursor.fetchall()
                return [{
                    "MASTER_ID": r[0],
                    "ENTITY_DATA": json.loads(r[1]) if isinstance(r[1], str) else r[1],
                    "SOURCE_IDS": r[2],
                    "SOURCE_SYSTEMS": r[3],
                    "CLUSTER_SIZE": r[4],
                    "MATCH_CONFIDENCE": r[5]
                } for r in rows]
        finally:
            conn.close()
