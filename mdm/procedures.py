import logging
import textwrap
from mdm.connection import ConnectionManager

logger = logging.getLogger("mdm.procedures")

class ProcedureDeployer:
    @staticmethod
    def deploy_procedures(creds: dict):
        conn = ConnectionManager.get_connection(creds)
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
                    var noUpdate = [mergeKey];

                    for(var i = 0; i < mapping.length; i++) {{
                        var m = mapping[i];
                        var srcExpr = m.src;
                        var tgtCol  = m.tgt;

                        if(srcExpr === 'NULL') {{
                            selectParts.push('NULL AS ' + tgtCol);
                        }} else if(srcExpr.indexOf('expr:') === 0) {{
                            selectParts.push(srcExpr.replace('expr:','') + ' AS ' + tgtCol);
                        }} else if(srcExpr.indexOf('const:') === 0) {{
                            selectParts.push("'" + srcExpr.replace('const:','') + "' AS " + tgtCol);
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

                    // Add standard load and modification timestamps
                    tgtCols.push('LOAD_TIMESTAMP');
                    srcVals.push('CURRENT_TIMESTAMP()');
                    tgtCols.push('LAST_MODIFIED_DATE');
                    srcVals.push('CURRENT_TIMESTAMP()');
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
            # The Python body MUST have NO leading whitespace inside $$...$$ or
            # Snowflake's Python interpreter will raise IndentationError.
            # textwrap.dedent strips the common leading whitespace from the entire block.
            _snowpark_body = textwrap.dedent("""\
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

                def get_field_val(rec, col):
                    if not rec:
                        return None
                    if col in rec:
                        return rec[col]
                    col_upper = col.upper()
                    for k, v in rec.items():
                        if k.upper() == col_upper:
                            return v
                    return None

                def normalize_field(v, method):
                    if is_empty(v):
                        return ''
                    if method == 'email':
                        return normalize_email(v)
                    elif method == 'phone':
                        return normalize_phone(v)
                    elif method == 'text':
                        return normalize_value(v)
                    else:
                        return str(v).strip()

                def compute_similarity(rec1, rec2, field_config):
                    score = 0.0
                    total_weight = 0.0

                    for cfg in field_config:
                        col = cfg['tgt_col']
                        weight = cfg['match_weight']
                        method = cfg['normalize']

                        if weight is None or (isinstance(weight, float) and pd.isna(weight)) or weight == 0:
                            continue

                        v1 = normalize_field(rec1.get(col), method)
                        v2 = normalize_field(rec2.get(col), method)

                        if v1 and v2:
                            if v1 == v2:
                                sim = 1.0
                            elif method == 'text':
                                sim = fuzz.token_sort_ratio(v1, v2) / 100.0
                            else:
                                sim = fuzz.ratio(v1, v2) / 100.0
                            score += weight * sim
                            total_weight += weight

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
                        FROM {config_db}.BRONZE.SOURCE_MAPPING_CONFIG
                        WHERE GROUP_NAME = '{GROUP_NAME}' AND IS_ACTIVE = TRUE
                        ORDER BY EXECUTION_SEQ
                    \"\"\").to_pandas()

                    if len(sources_df) == 0:
                        return f'ERROR: No active config found for GROUP_NAME={GROUP_NAME}'

                    tgt_database = sources_df.iloc[0]['TGT_DATABASE'].strip().upper()
                    merge_key_col = sources_df.iloc[0]['MERGE_KEY']

                    config_df = session.sql(f\"\"\"
                        SELECT
                            f.value:tgt::STRING AS TGT_COL,
                            f.value:match_weight::FLOAT AS MATCH_WEIGHT,
                            COALESCE(f.value:normalize::STRING, 'none') AS NORMALIZE_METHOD
                        FROM {config_db}.BRONZE.SOURCE_MAPPING_CONFIG c,
                             LATERAL FLATTEN(INPUT => c.COLUMN_MAPPING) f
                        WHERE c.GROUP_NAME = '{GROUP_NAME}'
                        AND c.IS_ACTIVE = TRUE
                        QUALIFY ROW_NUMBER() OVER (PARTITION BY f.value:tgt::STRING ORDER BY c.EXECUTION_SEQ) = 1
                    \"\"\").to_pandas()

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
                        src_db = src_row['SRC_DATABASE'].strip().upper()
                        tgt_db_val = src_row['TGT_DATABASE'].strip().upper()
                        tgt_schema_val = src_row['TGT_SCHEMA'].strip().upper()
                        stream_name = src_row['STREAM_NAME']
                        tgt_table_name = src_row['TGT_TABLE'].strip().upper()
                        
                        try:
                            df = session.sql(f\"\"\"
                                SELECT *
                                FROM {tgt_db_val}.{tgt_schema_val}.{stream_name}
                                WHERE METADATA$ACTION = 'INSERT'
                            \"\"\").to_pandas()
                        except Exception as e:
                            # Stream was likely dropped due to full load table recreation. Recreate stream.
                            session.sql(f\"\"\"
                                CREATE OR REPLACE STREAM {tgt_db_val}.{tgt_schema_val}.{stream_name}
                                ON TABLE {tgt_db_val}.{tgt_schema_val}.{tgt_table_name}
                            \"\"\").collect()
                            df = pd.DataFrame()
                            
                        all_records.extend(df.to_dict('records'))
                        
                        if len(df) > 0:
                            temp_table = f"{tgt_db_val}.{tgt_schema_val}.TEMP_CONSUME_{stream_name}"
                            session.sql(f"CREATE OR REPLACE TABLE {temp_table} AS SELECT * FROM {tgt_db_val}.{tgt_schema_val}.{stream_name}").collect()
                            session.sql(f"DROP TABLE {temp_table}").collect()

                    existing_df = session.sql(f\"\"\"
                        SELECT MASTER_ID, ENTITY_DATA, SOURCE_IDS, SOURCE_SYSTEMS, CLUSTER_SIZE
                        FROM {tgt_database}.MDM.MASTER_ENTITY
                        WHERE GROUP_NAME = '{GROUP_NAME}'
                    \"\"\").to_pandas()

                    if len(all_records) == 0:
                        if len(existing_df) == 0:
                            # Bootstrap run: pull directly from target tables since streams are empty
                            for _, src_row in sources_df.iterrows():
                                tgt_db_val = src_row['TGT_DATABASE'].strip().upper()
                                tgt_schema_val = src_row['TGT_SCHEMA'].strip().upper()
                                tgt_table_name = src_row['TGT_TABLE'].strip().upper()
                                df = session.sql(f\"\"\"
                                    SELECT *
                                    FROM {tgt_db_val}.{tgt_schema_val}.{tgt_table_name}
                                \"\"\").to_pandas()
                                all_records.extend(df.to_dict('records'))
                        
                        if len(all_records) == 0:
                            return 'NO_NEW_DATA: No changes detected in streams.'

                    new_records = all_records

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

                    matched_updates = []
                    new_entities = []
                    processed_new = set()

                    for i, new_rec in enumerate(new_records):
                        if i in processed_new:
                            continue

                        best_match_idx = -1
                        best_score = 0.0

                        for j, master in enumerate(existing_masters):
                            sim = compute_similarity(new_rec, master['ENTITY_DATA'], field_config)
                            if sim >= MATCH_THRESHOLD and sim > best_score:
                                best_score = sim
                                best_match_idx = j

                        if best_match_idx >= 0:
                            master = existing_masters[best_match_idx]
                            current_ids = master['SOURCE_IDS']
                            current_systems = master['SOURCE_SYSTEMS']
                            new_id = str(get_field_val(new_rec, merge_key_col) or '')
                            new_sys = str(get_field_val(new_rec, 'SOURCE_SYSTEM') or '')

                            if new_id not in current_ids.split(','):
                                updated_ids = current_ids + ',' + new_id
                                updated_systems = current_systems if new_sys in current_systems.split(',') else current_systems + ',' + new_sys
                                new_cluster_size = master['CLUSTER_SIZE'] + 1
                                new_confidence = confidence_label(best_score)

                                matched_updates.append({
                                    'MASTER_ID': master['MASTER_ID'],
                                    'SOURCE_IDS': updated_ids,
                                    'SOURCE_SYSTEMS': updated_systems,
                                    'CLUSTER_SIZE': new_cluster_size,
                                    'MATCH_CONFIDENCE': new_confidence,
                                    'PIPELINE_RUN_ID': run_id
                                })

                                existing_masters[best_match_idx]['SOURCE_IDS'] = updated_ids
                                existing_masters[best_match_idx]['SOURCE_SYSTEMS'] = updated_systems
                                existing_masters[best_match_idx]['CLUSTER_SIZE'] = new_cluster_size

                            processed_new.add(i)
                        else:
                            cluster = [new_rec]
                            cluster_indices = [i]

                            for k in range(i + 1, len(new_records)):
                                if k in processed_new:
                                    continue
                                sim = compute_similarity(new_rec, new_records[k], field_config)
                                if sim >= MATCH_THRESHOLD:
                                    cluster.append(new_records[k])
                                    cluster_indices.append(k)
                                    processed_new.add(k)

                            processed_new.add(i)

                            best_rec = cluster[0]
                            source_ids = ','.join([str(get_field_val(r, merge_key_col) or '') for r in cluster])
                            source_systems = ','.join(sorted(set([str(get_field_val(r, 'SOURCE_SYSTEM') or '') for r in cluster])))

                            max_master_id = session.sql(f\"\"\"
                                SELECT COALESCE(MAX(CAST(REPLACE(MASTER_ID, 'MSTR-', '') AS INT)), 0)
                                FROM {tgt_database}.MDM.MASTER_ENTITY
                            \"\"\").collect()[0][0]

                            next_id = max_master_id + len(new_entities) + 1
                            master_id = f'MSTR-{next_id:05d}'

                            entity_data = {}
                            for ef in entity_fields:
                                col = ef['tgt_col']
                                method = ef['normalize']
                                entity_data[col] = normalize_field(get_field_val(best_rec, col), method)

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

                            existing_masters.append({
                                'MASTER_ID': master_id,
                                'ENTITY_DATA': entity_data,
                                'SOURCE_IDS': source_ids,
                                'SOURCE_SYSTEMS': source_systems,
                                'CLUSTER_SIZE': len(cluster)
                            })

                    updates_count = 0
                    for upd in matched_updates:
                        session.sql(f\"\"\"
                            UPDATE {tgt_database}.MDM.MASTER_ENTITY
                            SET SOURCE_IDS = '{upd['SOURCE_IDS']}',
                                SOURCE_SYSTEMS = '{upd['SOURCE_SYSTEMS']}',
                                CLUSTER_SIZE = {upd['CLUSTER_SIZE']},
                                MATCH_CONFIDENCE = '{upd['MATCH_CONFIDENCE']}',
                                PIPELINE_RUN_ID = '{upd['PIPELINE_RUN_ID']}'
                            WHERE MASTER_ID = '{upd['MASTER_ID']}'
                        \"\"\").collect()
                        updates_count += 1

                    inserts_count = 0
                    for ent in new_entities:
                        entity_json = ent['ENTITY_DATA'].replace("'", "''")
                        session.sql(f\"\"\"
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
                        \"\"\").collect()
                        inserts_count += 1

                    keys_df = session.sql(f\"\"\"
                        SELECT DISTINCT f.key
                        FROM {tgt_database}.MDM.MASTER_ENTITY,
                             LATERAL FLATTEN(INPUT => ENTITY_DATA) f
                        ORDER BY f.key
                    \"\"\").to_pandas()

                    if len(keys_df) > 0:
                        entity_cols = ",\\n            ".join(
                            [f"ENTITY_DATA:{row['KEY']}::STRING AS {row['KEY']}" for _, row in keys_df.iterrows()]
                        )
                        view_sql = f\"\"\"
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
                        \"\"\"
                        session.sql(view_sql).collect()

                    return (
                        f'SUCCESS | run_id={run_id} | '
                        f'delta_records={len(new_records)} | '
                        f'matched_to_existing={updates_count} | '
                        f'new_masters_created={inserts_count}'
                    )
            """)

            # The SQL wrapper starts at column 0 so the $$ body has no extra indentation
            sp_master_entity_sql = (
                f"CREATE OR REPLACE PROCEDURE {db}.MDM.SP_MASTER_ENTITY(\n"
                f'    "CONFIG_DATABASE" VARCHAR,\n'
                f'    "GROUP_NAME" VARCHAR\n'
                f")\n"
                f"RETURNS VARCHAR\n"
                f"LANGUAGE PYTHON\n"
                f"RUNTIME_VERSION = '3.10'\n"
                f"PACKAGES = ('snowflake-snowpark-python', 'pandas', 'numpy', 'rapidfuzz')\n"
                f"HANDLER = 'main'\n"
                f"EXECUTE AS OWNER\n"
                f"AS\n"
                f"$$\n"
                f"{_snowpark_body}\n"
                f"$$;\n"
            )
            cursor.execute(sp_master_entity_sql)
        finally:
            conn.close()
