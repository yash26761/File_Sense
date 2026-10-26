# PySpark Sample Pipeline Script
from pyspark.sql import SparkSession

def run_pipeline():
    spark = SparkSession.builder.master('local[1]').appName('DemoPipeline').getOrCreate()
    print('Pipeline executed successfully')
    spark.stop()

if __name__ == '__main__':
    run_pipeline()
