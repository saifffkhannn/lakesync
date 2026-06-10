-- ============================================================
-- GENERIC DATA UNIFICATION PROCEDURE
-- Works with any database. Reads SRC_DATABASE and TGT_DATABASE
-- from SOURCE_MAPPING_CONFIG to resolve fully qualified paths.
--
-- Parameters:
--   CONFIG_DATABASE: Database where SOURCE_MAPPING_CONFIG lives
--   GROUP_NAME: The group to process
--
-- The config table must have columns: SRC_DATABASE, TGT_DATABASE
-- ============================================================

SET CONFIG_DB = 'DATA_UNIFICATION_DB';

CREATE OR REPLACE PROCEDURE DATA_UNIFICATION_DB.MDM.SP_MASTER_ENTITY("CONFIG_DATABASE" VARCHAR, "GROUP_NAME" VARCHAR)
RETURNS VARCHAR
LANGUAGE PYTHON
RUNTIME_VERSION = '3.10'
PACKAGES = ('snowflake-snowpark-python','pandas','numpy','rapidfuzz')
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
        src_db = src_row['SRC_DATABASE'].strip().upper()
        stream_name = src_row['STREAM_NAME']
        df = session.sql(f"""
            SELECT *
            FROM {src_db}.BRONZE.{stream_name}
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
            'CLUSTER_SIZE': int(row['CLUSTER_SIZE'])
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
            new_id = str(new_rec.get(merge_key_col, ''))
            new_sys = str(new_rec.get('SOURCE_SYSTEM', ''))

            if new_id not in current_ids:
                updated_ids = current_ids + ',' + new_id
                updated_systems = current_systems if new_sys in current_systems else current_systems + ',' + new_sys
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
            source_ids = ','.join([str(r.get(merge_key_col, '')) for r in cluster])
            source_systems = ','.join(sorted(set([str(r.get('SOURCE_SYSTEM', '')) for r in cluster])))

            max_master_id = session.sql(f"""
                SELECT COALESCE(MAX(CAST(REPLACE(MASTER_ID, 'MSTR-', '') AS INT)), 0)
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

            existing_masters.append({
                'MASTER_ID': master_id,
                'ENTITY_DATA': entity_data,
                'SOURCE_IDS': source_ids,
                'SOURCE_SYSTEMS': source_systems,
                'CLUSTER_SIZE': len(cluster)
            })

    updates_count = 0
    for upd in matched_updates:
        session.sql(f"""
            UPDATE {tgt_database}.MDM.MASTER_ENTITY
            SET SOURCE_IDS = '{upd['SOURCE_IDS']}',
                SOURCE_SYSTEMS = '{upd['SOURCE_SYSTEMS']}',
                CLUSTER_SIZE = {upd['CLUSTER_SIZE']},
                MATCH_CONFIDENCE = '{upd['MATCH_CONFIDENCE']}',
                PIPELINE_RUN_ID = '{upd['PIPELINE_RUN_ID']}'
            WHERE MASTER_ID = '{upd['MASTER_ID']}'
        """).collect()
        updates_count += 1

    inserts_count = 0
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


-- The procedure lives in DATA_UNIFICATION_DB, but processes whatever
-- database is specified in SOURCE_MAPPING_CONFIG
CALL DATA_UNIFICATION_DB.MDM.SP_MASTER_ENTITY('DATA_UNIFICATION_DB', 'GROUP_1');

SELECT * FROM DATA_UNIFICATION_DB.MDM.MASTER_ENTITY_FLAT WHERE MASTER_ID = 'MSTR-00006';


