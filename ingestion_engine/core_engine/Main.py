from src.incremental_load_pipeline import incremental_load

if __name__ == "__main__":
    incremental_load("sapsqlserver", "aws", "snowflake")
