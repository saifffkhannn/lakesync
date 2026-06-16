import logging
import sys
import os

# Add parent directory of ingestion_engine to sys.path so the adjacent mdm package can be imported
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from mdm import ConnectionManager, SchemaDeployer, ProcedureDeployer, QueryHandler, PipelineRunner

logger = logging.getLogger("mdm_helper")

class MDMHelper:
    """
    Backward-compatible wrapper for MDM processes. 
    Delegates implementation to the modular 'mdm' subpackage.
    """
    def __init__(self):
        pass

    def get_connection(self, creds: dict):
        return ConnectionManager.get_connection(creds)

    def fetch_tables(self, creds: dict, schema: str):
        return QueryHandler.fetch_tables(creds, schema)

    def fetch_columns(self, creds: dict, schema: str, table: str):
        return QueryHandler.fetch_columns(creds, schema, table)

    def deploy_structures(self, creds: dict):
        return SchemaDeployer.deploy_structures(creds)

    def configure_mapping(self, creds: dict, config_payload: dict):
        return SchemaDeployer.configure_mapping(creds, config_payload)

    def deploy_procedures(self, creds: dict):
        return ProcedureDeployer.deploy_procedures(creds)

    def run_mdm(self, creds: dict, group_name: str):
        return PipelineRunner.run_mdm(creds, group_name)

    def fetch_audit_logs(self, creds: dict, group_name: str):
        return QueryHandler.fetch_audit_logs(creds, group_name)

    def fetch_master_records(self, creds: dict, group_name: str):
        return QueryHandler.fetch_master_records(creds, group_name)

    def fetch_databases(self, creds: dict):
        return QueryHandler.fetch_databases(creds)

    def fetch_schemas(self, creds: dict, database: str):
        return QueryHandler.fetch_schemas(creds, database)

    def replicate_to_bronze(self, creds: dict, tables: list):
        return SchemaDeployer.replicate_to_bronze(creds, tables)

    def configure_batch(self, creds: dict, group_name: str, configs: list):
        return SchemaDeployer.configure_batch(creds, group_name, configs)
