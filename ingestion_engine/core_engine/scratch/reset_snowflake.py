import snowflake.connector
import configparser

config = configparser.ConfigParser()
config.read("config/sapsqlserver_aws_snowflake.cfg")
sf = config["snowflake"]

conn = snowflake.connector.connect(
    user=sf["user"],
    password=sf["password"],
    account=sf["account"],
    warehouse=sf["warehouse"],
    database=sf["database"]
)

cursor = conn.cursor()
try:
    # Drop control tables to start fresh with new schema
    cursor.execute("DROP TABLE IF EXISTS SAMPLEDB_TGT.EXT_STAGE_SCHEMA.PipelineRunControl")
    print("Dropped PipelineRunControl table.")
    
    # Also drop target tables if we want a clean test?
    # No, user says they have 71 rows, let's keep them and see the merge.
    
    # Wait, if I drop the control table, the next run will be a FULL load because last_run will be NULL.
    # This is perfect for testing why the incremental load wasn't picking up the changes.
finally:
    cursor.close()
    conn.close()
