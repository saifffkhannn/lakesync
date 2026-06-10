"""
AWS S3 Client Utility Module

This module handles:
    - Creating S3 client
    - Uploading files to S3
    - Archiving existing files in S3
"""

import os
from datetime import datetime
import boto3
from botocore.exceptions import NoCredentialsError, ClientError

from src.config_parser import parse_config
from src.pipeline_logger import get_logger
import time
from boto3.s3.transfer import TransferConfig
logger = get_logger()


# -------------------------------------------------------------------
# S3 Client
# -------------------------------------------------------------------

def create_s3_client(config_path: str):
    """
    Create and return an AWS S3 client using credentials from config file.

    Args:
        config_path (str): Path to configuration file

    Returns:
        boto3.client: S3 client object
    """
    try:
        config = parse_config(config_path)
        aws_config = config["aws"]

        client = boto3.client(
            "s3",
            aws_access_key_id=aws_config["aws_access_key_id"],
            aws_secret_access_key=aws_config["aws_secret_access_key"],
            region_name=aws_config.get("region_name", "us-east-1")
        )

        logger.info("S3 client created successfully")
        return client

    except KeyError as e:
        logger.error(f"Missing AWS config key: {e}")
        raise

    except Exception as e:
        logger.error(f"Error creating S3 client: {str(e)}")
        raise


# -------------------------------------------------------------------
# ARCHIVE EXISTING FILE
# -------------------------------------------------------------------

def move_to_archive_aws(config_path: str, file_name: str, folder_structure: str) -> None:
    """
    Move ALL existing files in S3 folder to archive before uploading new file.

    Args:
        config_path (str): Config file path
        file_name (str): File name (not used for lookup, only for logging)
        folder_structure (str): Folder structure in S3
    """
    try:
        config = parse_config(config_path)
        bucket_name = config["aws"]["s3_bucket_name"]

        s3_client = create_s3_client(config_path)

        prefix = f"{folder_structure}/"

        # logger.info(f"[ARCHIVE DEBUG] Bucket: {bucket_name}")
        # logger.info(f"[ARCHIVE DEBUG] Folder Prefix: {prefix}")

        # List all files in the folder
        response = s3_client.list_objects_v2(
            Bucket=bucket_name,
            Prefix=prefix
        )

        if "Contents" not in response:
            logger.info(f"No existing files found in S3 folder: {prefix}")
            return

        for obj in response["Contents"]:
            source_key = obj["Key"]

            # Skip folder itself (if any) or archive files
            if source_key.endswith("/") or source_key.startswith("archive/"):
                continue

            file_name = os.path.basename(source_key)

            archive_key = (
                f"archive/{folder_structure}/"
                f"{file_name}"
            )

            logger.info(f"Archiving: {source_key} -> {archive_key}")

            # Copy to archive
            s3_client.copy_object(
                Bucket=bucket_name,
                CopySource={"Bucket": bucket_name, "Key": source_key},
                Key=archive_key
            )

            # Delete original
            s3_client.delete_object(
                Bucket=bucket_name,
                Key=source_key
            )

        logger.info("All existing files archived successfully")

    except Exception as e:
        logger.error(f"Error archiving folder {folder_structure}: {str(e)}")
        raise

# -------------------------------------------------------------------
# UPLOAD FILE TO S3
# -------------------------------------------------------------------

def upload_to_s3(
    config_path: str,
    file_name: str,
    file_path: str,
    folder_structure: str
):
    """
    Upload file to AWS S3 bucket with retry + multipart + reconciliation
    """

    try:
        config = parse_config(config_path)
        bucket_name = config["aws"]["s3_bucket_name"]

        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        s3_client = create_s3_client(config_path)

        s3_key = f"{folder_structure}/{file_name}"

        # ---------- MULTIPART UPLOAD ----------
        transfer_config = TransferConfig(
            multipart_threshold=50 * 1024 * 1024,
            multipart_chunksize=50 * 1024 * 1024,
            max_concurrency=5,
            use_threads=True
        )

        max_retry = 3

        for attempt in range(max_retry):
            try:
                logger.info(f"Upload attempt {attempt+1}")
                
                # Uploading file to S3
                s3_client.upload_file(
                    file_path,
                    bucket_name,
                    s3_key,
                    Config=transfer_config
                )

                logger.info("Upload Successful")
                break

            except Exception as e:
                logger.error(f"Upload failed: {str(e)}")

                if attempt < max_retry - 1:
                    time.sleep(10)
                else:
                    raise Exception("Upload failed after retries")

        # ---------- UPLOAD RECONCILIATION ----------
        local_size = os.path.getsize(file_path)

        response = s3_client.head_object(
            Bucket=bucket_name,
            Key=s3_key
        )

        s3_size = response["ContentLength"]

        logger.info(f"Local File Size: {local_size}")
        logger.info(f"S3 File Size: {s3_size}")

        if local_size != s3_size:
            raise Exception("Upload corruption detected")

        s3_full_path = f"s3://{bucket_name}/{s3_key}"
        

        logger.info(f"Uploaded {file_name} to {s3_full_path}")

        return s3_key

    except FileNotFoundError as e:
        logger.error(str(e))
        raise

    except NoCredentialsError:
        logger.error("AWS credentials not found")
        raise

    except Exception as e:
        logger.error(f"Unexpected error during S3 upload: {str(e)}")
        raise
