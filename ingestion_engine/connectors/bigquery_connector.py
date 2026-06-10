import json
import logging
from google.cloud import bigquery

logger = logging.getLogger("data_accelerator")

class BigQueryConnector:
    def __init__(self, project_id, dataset_id, service_account_key_path):
        self.project_id = project_id
        self.dataset_id = dataset_id
        self.service_account_key_path = service_account_key_path
        self.client = bigquery.Client.from_service_account_json(service_account_key_path)
    
    def connect(self):
        # Already connected in __init__ via from_service_account_json
        pass

    def get_schema_tables_map(self):
        schema_table_map = {}
        schemas = [ds.dataset_id for ds in self.client.list_datasets(self.project_id)]

        for schema in schemas:
            tables = [t.table_id for t in self.client.list_tables(f"{self.project_id}.{schema}")]
            schema_table_map[schema] = tables

        return schema_table_map

    def fetch_schemas(self):
        try:
            datasets = list(self.client.list_datasets(self.project_id))
            return [dataset.dataset_id for dataset in datasets]
        except Exception as e:
            logger.error(f"Failed to fetch BigQuery schemas: {e}")
            return []

    def fetch_tables(self, schema: str):
        try:
            tables = list(self.client.list_tables(f"{self.project_id}.{schema}"))
            return [table.table_id for table in tables]
        except Exception as e:
            logger.error(f"Failed to fetch BigQuery tables: {e}")
            return []

    def fetch_table_metadata(self, schema: str, table: str):
        try:
            query = f"""
            SELECT 
                column_name,
                data_type,
                ordinal_position,
                is_nullable,
                column_default,
                is_generated
            FROM `{self.project_id}.{schema}.INFORMATION_SCHEMA.COLUMNS`
            WHERE table_name = '{table}'
            ORDER BY ordinal_position
            """

            rows = self.client.query(query).result()

            metadata = []
            for row in rows:
                metadata.append({
                    "column_name": row.column_name.lower(),
                    "data_type": row.data_type.lower(),
                    "scale": None,
                    "ordinal_position": row.ordinal_position,
                    "nullable": row.is_nullable, # 'YES' or 'NO'
                    "default": row.column_default,
                    "is_identity": True if row.is_generated == "ALWAYS" else False
                })
            return metadata
        except Exception as e:
            logger.error(f"Failed to fetch BigQuery column metadata: {e}")
            return []

    def print_full_metadata(self):
        schema_table_map = self.get_schema_tables_map()
        print("Schemas:", list(schema_table_map.keys()))

        for schema, tables in schema_table_map.items():
            print(f"\nSchema: {schema}")
            print("Tables:", tables)

            for table in tables:
                print(f"\n  Table: {table}")
                metadata = self.fetch_table_metadata(schema, table)
                print("  Metadata:", metadata)

    def load_data(self, df):
        pass


if __name__ == "__main__":
    service_account_json = r"C:/Users/Admin/Downloads/red-tide-482010-a1-449757f8295f.json"
    project_id = "red-tide-482010-a1"

    bq = BigQueryConnector(project_id, None, service_account_json)
    schema_map = bq.get_schema_tables_map()
    print(schema_map)
    bq.print_full_metadata()
