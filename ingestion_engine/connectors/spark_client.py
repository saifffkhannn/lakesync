from pyspark.sql import SparkSession
import os


def create_spark_session(sql_jar):

    

    spark = (
        SparkSession.builder
        .master("local[*]")
        .appName("data_accelerator")
        .config("spark.driver.memory", "4g")
        .config("spark.jars", sql_jar)
        .getOrCreate()
    )

    return spark