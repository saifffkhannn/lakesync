import pandas as pd
import os
import uuid
from datetime import datetime

from src.pipeline_state import append_log, update_table_status



class PipelineLogger:

    def __init__(self, base_dir):
        """
        Initialize Pipeline Logger.

        Flow:
        1. Set base directory
        2. Create logs folder
        3. Generate unique run_id
        4. Capture pipeline start timestamp
        """

        try:
            self.base_dir = base_dir
            self.logs = []

            # Create logs directory
            self.log_dir = os.path.join(base_dir, "logs")
            os.makedirs(self.log_dir, exist_ok=True)

            # Unique pipeline run id
            self.run_id = str(uuid.uuid4())

            # Pipeline timestamp
            self.run_timestamp = datetime.now()

        except Exception as e:
            raise Exception(f"PipelineLogger initialization failed: {str(e)}")

    # -------------------------------------------------------
    # Start log for a table
    # -------------------------------------------------------
    def start_table_log(self, source_system, cloud, target_system,
                        database, schema, table):
        """
        Initialize a log dictionary for a table.
        """

        try:
            log = {
                "run_id": self.run_id,
                "run_timestamp": self.run_timestamp,
                "source_system": source_system,
                "cloud": cloud,
                "target_system": target_system,

                "database_name": database,
                "schema_name": schema,
                "table_name": table,

                "source_row_count": None,
                "parquet_row_count": None,
                "target_row_count": None,

                "parquet_file_path": None,
                "cloud_path": None,

                "start_time": datetime.now(),
                "end_time": None,
                "duration_seconds": None,

                "status": None,
                "error_message": None,

                "extraction_status": None,
                "upload_status": None,
                "table_creation_status": None,
                "load_status": None
            }

            return log

        except Exception as e:
            raise Exception(f"start_table_log failed: {str(e)}")

    # -------------------------------------------------------
    # Update row counts
    # -------------------------------------------------------
    def update_row_counts(self, log,
                          source_count=None,
                          parquet_count=None,
                          target_count=None):
        """
        Updates row counts in log dictionary.
        """

        try:
            if source_count is not None:
                log["source_row_count"] = source_count

            if parquet_count is not None:
                log["parquet_row_count"] = parquet_count

            if target_count is not None:
                log["target_row_count"] = target_count

            return log

        except Exception as e:
            raise Exception(f"update_row_counts failed: {str(e)}")

    # -------------------------------------------------------
    # Update file paths
    # -------------------------------------------------------
    def update_file_paths(self, log,
                         parquet_path=None,
                         cloud_path=None):
        """
        Updates file paths (local + cloud).
        """

        try:
            if parquet_path is not None:
                log["parquet_file_path"] = parquet_path

            if cloud_path is not None:
                log["cloud_path"] = cloud_path

            return log

        except Exception as e:
            raise Exception(f"update_file_paths failed: {str(e)}")

    # -------------------------------------------------------
    # Update step status
    # -------------------------------------------------------
    def update_step_status(self, log, step, status):
        """
        Updates step-level status.
        """

        try:
            step_map = {
                "extraction": "extraction_status",
                "upload": "upload_status",
                "table_creation": "table_creation_status",
                "load": "load_status"
            }

            if step in step_map:
                log[step_map[step]] = status

                table_name = f"{log['schema_name']}.{log['table_name']}"
                status_label = str(status).lower()

                if status_label == "success":
                    ui_status = {
                        "extraction": "extracted",
                        "upload": "uploaded",
                        "table_creation": "creating_table",
                        "load": "completed",
                    }.get(step, "pending")
                elif status_label == "failed":
                    ui_status = f"{step}_failed"
                else:
                    ui_status = status_label

                append_log(f"{step.replace('_', ' ').title()} {status_label} for {table_name}")
                update_table_status(table_name, ui_status)

            return log

        except Exception as e:
            raise Exception(f"update_step_status failed: {str(e)}")

    # -------------------------------------------------------
    # Finalize log
    # -------------------------------------------------------
    def finalize_table_log(self, log):
        """
        Finalizes log:
        - Sets end_time
        - Calculates duration
        - Appends to logs list
        """

        try:
            log["end_time"] = datetime.now()

            log["duration_seconds"] = (
                log["end_time"] - log["start_time"]
            ).total_seconds()

            self.logs.append(log)

        except Exception as e:
            raise Exception(f"finalize_table_log failed: {str(e)}")

    # -------------------------------------------------------
    # Save logs
    # -------------------------------------------------------
    def save_logs(self):
        """
        Saves logs to CSV file.
        """

        try:
            if not self.logs:
                print("No logs to save.")
                return

            df = pd.DataFrame(self.logs)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            csv_path = os.path.join(self.log_dir, "migration_log_master.csv")

            if os.path.exists(csv_path):
                df_existing = pd.read_csv(csv_path)
                df = pd.concat([df_existing, df], ignore_index=True)

            df.to_csv(csv_path, index=False)

        except FileNotFoundError as e:
            raise Exception(f"Log file path error: {str(e)}")

        except PermissionError as e:
            raise Exception(f"Permission error while saving logs: {str(e)}")

        except Exception as e:
            raise Exception(f"save_logs failed: {str(e)}")
