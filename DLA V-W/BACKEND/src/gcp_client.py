from google.cloud import storage
import os
from src.parse_config import parse_config
from src.custom_logger import get_logger
 
logger = get_logger()
 
# -------------------------------------------------------------------
# ARCHIVE EXISTING FILE
# -------------------------------------------------------------------

 
def move_to_archive_gcp(config_path: str, folder_structure: str) -> None:
    """
    Move ALL existing files in the specified GCS folder to archive.
 
    Flow:
    1. Load GCP config
    2. Authenticate using service account
    3. List all blobs in folder
    4. Copy each file to archive/
    5. Delete original file
    """
 
    try:
        # Parse configuration
        config = parse_config(config_path)
        gcp_cfg = config["gcp"]
 
        # Set GCP credentials environment variable
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = gcp_cfg["service_account_json"]
 
        # Initialize GCS client and bucket
        client = storage.Client(project=gcp_cfg["project"])
        bucket = client.bucket(gcp_cfg["bucket_name"])
 
        # Folder prefix
        prefix = f"{folder_structure}/"
 
        logger.info(f"[GCP ARCHIVE] Scanning folder: {prefix}")
 
        # Fetch all blobs under the folder
        blobs = list(client.list_blobs(bucket, prefix=prefix))
 
        # If no files found
        if not blobs:
            logger.info(f"No files found to archive in {prefix}")
            return
 
        # Iterate through all blobs
        for blob in blobs:
            source_blob_name = blob.name
 
            # Skip already archived files
            if source_blob_name.startswith("archive/"):
                continue
 
            # Extract file name
            file_name = os.path.basename(source_blob_name)
 
            # Construct archive path
            archive_blob_name = (
                f"archive/{folder_structure}/"
                f"{file_name}"
            )
 
            logger.info(f"Archiving: {source_blob_name} → {archive_blob_name}")
 
            try:
                # Copy file to archive location
                bucket.copy_blob(
                    blob,
                    bucket,
                    archive_blob_name
                )
 
                # Delete original file after successful copy
                blob.delete()
 
            except Exception as inner_e:
                # Log failure for individual file but continue processing others
                logger.error(f"Failed to archive file {source_blob_name}: {str(inner_e)}")
                raise Exception(f"File archive failed: {source_blob_name} - {str(inner_e)}")
 
        logger.info("GCP archive completed successfully")
 
    except KeyError as e:
        # Missing config keys
        logger.error(f"GCP config missing key: {str(e)}")
        raise KeyError(f"GCP config missing key: {str(e)}")
 
    except FileNotFoundError as e:
        # Service account file issue
        logger.error(f"Service account file not found: {str(e)}")
        raise Exception(f"Service account file not found: {str(e)}")
 
    except Exception as e:
        # Catch-all for unexpected errors
        logger.error(f"GCP archive failed: {str(e)}")
        raise
 
# -------------------------------------------------------------------
# UPLOAD FILE TO S3
# -------------------------------------------------------------------
 
def upload_to_gcp(config_path, file_name, file_path, folder_structure):
    """
    Uploads a file to GCS under given folder structure.
 
    Flow:
    1. Load config
    2. Authenticate
    3. Create blob path
    4. Upload file
    5. Return GCS URI
    """
 
    try:
        # Parse configuration
        config = parse_config(config_path)
        gcp_cfg = config["gcp"]
 
        # Set credentials
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = gcp_cfg["service_account_json"]
 
        bucket_name = gcp_cfg["bucket_name"]
 
        # Initialize client and bucket
        client = storage.Client(project=gcp_cfg["project"])
        bucket = client.bucket(bucket_name)
 
        # Construct blob path
        blob_path = f"{folder_structure}/{file_name}"
 
        blob = bucket.blob(blob_path)
 
        try:
            # Upload file to GCS
            blob.upload_from_filename(file_path)
 
        except Exception as upload_error:
            logger.error(f"Failed to upload file {file_path} to GCP: {str(upload_error)}")
            raise Exception(f"GCP upload failed: {str(upload_error)}")
 
        # Construct GCS URI
        gcs_uri = f"gs://{bucket_name}/{blob_path}"
 
        logger.info(f"Uploaded to GCP {gcs_uri}")
 
        return gcs_uri
 
    except KeyError as e:
        # Missing config keys
        logger.error(f"GCP config missing key: {str(e)}")
        raise KeyError(f"GCP config missing key: {str(e)}")
 
    except FileNotFoundError as e:
        # Local file not found
        logger.error(f"File not found: {str(e)}")
        raise Exception(f"File not found: {str(e)}")
 
    except Exception as e:
        # Catch-all
        logger.error(f"GCP upload failed: {str(e)}")
        raise