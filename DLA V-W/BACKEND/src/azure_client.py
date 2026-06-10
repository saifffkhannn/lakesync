"""
Azure Blob Storage Client Utility Module

This module handles uploading files to Azure Blob Storage / ADLS Gen2.
"""

import os
from azure.storage.blob import BlobServiceClient

from src.parse_config import parse_config
from src.custom_logger import get_logger

logger = get_logger()

# -------------------------------------------------------------------
# ARCHIVE EXISTING FILE
# -------------------------------------------------------------------

def move_to_archive_azure(config_path: str, folder_structure: str) -> None:
    """
    Move ALL existing blobs in Azure folder to archive.
    """
    try:
        config = parse_config(config_path)
        azure_config = config["azure"]

        connection_string = azure_config["connection_string"]
        container_name = azure_config["container_name"]

        blob_service = BlobServiceClient.from_connection_string(connection_string)
        container_client = blob_service.get_container_client(container_name)

        prefix = f"{folder_structure}/"

        logger.info(f"[AZURE ARCHIVE] Scanning folder: {prefix}")

        blobs = container_client.list_blobs(name_starts_with=prefix)

        found = False

        for blob in blobs:
            source_blob_name = blob.name

            # Skip archive folder itself
            if source_blob_name.startswith("archive/"):
                continue

            found = True

            file_name = os.path.basename(source_blob_name)

            archive_blob_name = (
                f"archive/{folder_structure}/"
                f"{file_name}"
            )

            logger.info(f"Archiving: {source_blob_name} → {archive_blob_name}")

            # Copy blob
            source_blob_url = f"{container_client.url}/{source_blob_name}"
            archive_blob = container_client.get_blob_client(archive_blob_name)

            archive_blob.start_copy_from_url(source_blob_url)

            # Delete original
            container_client.delete_blob(source_blob_name)

        if not found:
            logger.info(f"No files found to archive in {prefix}")
        else:
            logger.info("Azure archive completed successfully")

    except Exception as e:
        logger.error(f"Azure archive failed: {str(e)}")
        raise

# -------------------------------------------------------------------
# UPLOAD FILE TO S3
# -------------------------------------------------------------------

def upload_to_azure(
    config_path: str,
    file_name: str,
    file_path: str,
    folder_structure: str
) -> str:
    """
    Upload file to Azure Blob Storage / ADLS Gen2.

    Args:
        config_path (str): Path to configuration file
        file_name (str): Name of file
        file_path (str): Local file path
        folder_structure (str): Folder structure in Azure container

    Returns:
        str: Azure ABFSS URI of uploaded file
    """
    try:
        # Validate local file
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        # Read Azure configuration
        config = parse_config(config_path)
        azure_config = config["azure"]

        connection_string = azure_config["connection_string"]
        container_name = azure_config["container_name"]
        storage_account = azure_config["storage_account"]

        # Create Blob Service Client
        blob_service = BlobServiceClient.from_connection_string(
            connection_string
        )

        container_client = blob_service.get_container_client(container_name)

        # Blob path
        blob_path = f"{folder_structure}/{file_name}"

        # Upload file
        with open(file_path, "rb") as data:
            container_client.upload_blob(
                name=blob_path,
                data=data,
                overwrite=True
            )

        # Construct ABFSS URI
        azure_uri = (
            f"abfss://{container_name}@{storage_account}.dfs.core.windows.net/"
            f"{blob_path}"
        )
        logger.info(f"Azure blob path{blob_path}")

        logger.info(f"Uploaded file to Azure: {azure_uri}")

        return blob_path

    except FileNotFoundError as e:
        logger.error(str(e))
        raise

    except KeyError as e:
        logger.error(f"Missing Azure config key: {e}")
        raise

    except Exception as e:
        logger.error(f"Azure upload failed: {str(e)}")
        raise