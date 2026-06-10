import csv
import json


class ColumnMappingLoader:

    def __init__(self, filepath):
        self.filepath = filepath

    def load(self):
        table_mappings = []

        with open(self.filepath, mode="r") as file:
            reader = csv.DictReader(file)

            for row in reader:

                # Normalize table names
                src_table = row["src_table"].strip()
                tgt_table = row["tgt_table"].strip()

                # Load JSON components
                column_map = json.loads(row["column_map_json"])
                audit_columns = json.loads(row.get("audit_columns_json", "{}"))
                source_columns = json.loads(row.get("source_columns_json", "[]"))
                target_columns = json.loads(row.get("target_columns_json", "[]"))
                primary_keys = json.loads(row.get("primary_keys", "[]"))

                table_mappings.append({
                    "src_db": row.get("src_db", "").strip(),
                    "src_schema": row.get("src_schema", "").strip(),
                    "src_table": src_table,
                    "tgt_db": row.get("tgt_db", "").strip(),
                    "tgt_schema": row.get("tgt_schema", "").strip(),
                    "tgt_table": tgt_table,
                    "column_map": column_map,
                    "audit_columns": audit_columns,
                    "source_columns": source_columns,
                    "target_columns": target_columns,
                    "load_type": row.get("load_type", "SNAPSHOT"),
                    "primary_keys": primary_keys,
                    "incremental_col": row.get("incremental_col", ""),
                    "incremental_tgt_col": row.get("incremental_tgt_col", ""),
                    "soft_delete_col": row.get("soft_delete_col", "")
                })

        return table_mappings