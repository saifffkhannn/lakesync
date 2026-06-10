from mdm.connection import ConnectionManager

class PipelineRunner:
    @staticmethod
    def run_mdm(creds: dict, group_name: str):
        conn = ConnectionManager.get_connection(creds)
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
