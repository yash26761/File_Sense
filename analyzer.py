import os
import sys
from typing import Any, Dict, List, Optional

# Ensure PySpark workers use the active virtual environment's Python 3.11 interpreter
os.environ["PYSPARK_PYTHON"] = sys.executable
os.environ["PYSPARK_DRIVER_PYTHON"] = sys.executable

from pyspark.sql import SparkSession
import pyspark.sql.functions as F
from pyspark.sql.types import LongType, StringType, StructField, StructType

# Explicit schema to prevent schema inference failures on empty datasets
FILE_SCHEMA = StructType([
    StructField("name", StringType(), False),
    StructField("path", StringType(), False),
    StructField("size", LongType(), False),
    StructField("extension", StringType(), True),
])

_spark_session: Optional[SparkSession] = None


def get_spark_session() -> SparkSession:
    """
    Creates or reuses a lightweight local SparkSession configured for an 8 GB laptop.
    
    Configs:
      - master: local[1] (single core to preserve CPU and RAM)
      - spark.driver.memory: 1g (controlled memory footprint)
      - spark.ui.enabled: false (Spark UI disabled)
      - spark.sql.shuffle.partitions: 1
    """
    global _spark_session
    if (
        _spark_session is None
        or _spark_session._jsc is None
        or _spark_session._jsc.sc().isStopped()
    ):
        _spark_session = (
            SparkSession.builder
            .appName("FileSenseAnalyzer")
            .master("local[1]")
            .config("spark.ui.enabled", "false")
            .config("spark.driver.memory", "1g")
            .config("spark.driver.bindAddress", "127.0.0.1")
            .config("spark.driver.host", "127.0.0.1")
            .config("spark.sql.shuffle.partitions", "1")
            .getOrCreate()
        )
        _spark_session.sparkContext.setLogLevel("ERROR")
    return _spark_session


def stop_spark_session() -> None:
    """Safely stops the active SparkSession if running."""
    global _spark_session
    if _spark_session is not None:
        try:
            _spark_session.stop()
        except Exception:
            pass
        finally:
            _spark_session = None


def analyze_files(
    files: List[Dict[str, Any]],
    duplicate_results: Optional[Dict[str, Any]] = None,
    stop_session: bool = False
) -> Dict[str, Any]:
    """
    Analyzes scanned file metadata using PySpark 3.5.x DataFrame operations.
    
    Calculates:
      - Total file count
      - Total size in bytes
      - Storage usage aggregated by file extension
      - Top 10 largest files
      - Duplicate statistics (extracted from duplicate_results without rehashing)
      
    Handles empty file datasets gracefully using an explicit schema.
    Reuses or safely stops the SparkSession as configured.
    """
    spark = get_spark_session()

    try:
        # Prepare rows matching FILE_SCHEMA
        rows = []
        if files and isinstance(files, list):
            for f in files:
                if isinstance(f, dict):
                    rows.append((
                        str(f.get("name", "")),
                        str(f.get("path", "")),
                        int(f.get("size", 0)),
                        str(f.get("extension", "")).lower()
                    ))

        # Create DataFrame with explicit schema to prevent empty dataset schema inference errors
        df = spark.createDataFrame(rows, schema=FILE_SCHEMA)

        total_files = df.count()

        if total_files == 0:
            total_size = 0
            extension_summary = []
            top_10_largest = []
        else:
            # Aggregate total size
            agg_row = df.select(
                F.coalesce(F.sum("size"), F.lit(0)).alias("total_size")
            ).collect()[0]
            total_size = int(agg_row["total_size"])

            # Storage usage grouped by file extension
            ext_df = (
                df.groupBy("extension")
                .agg(
                    F.count("*").alias("count"),
                    F.coalesce(F.sum("size"), F.lit(0)).alias("total_size")
                )
                .orderBy(F.col("total_size").desc(), F.col("count").desc(), F.col("extension").asc())
            )

            extension_summary = [
                {
                    "extension": row["extension"] if row["extension"] else "(no extension)",
                    "count": int(row["count"]),
                    "total_size": int(row["total_size"])
                }
                for row in ext_df.collect()
            ]

            # Top 10 largest files
            top_10_df = (
                df.select("name", "path", "size", "extension")
                .orderBy(F.col("size").desc(), F.col("name").asc())
                .limit(10)
            )

            top_10_largest = [
                {
                    "name": row["name"],
                    "path": row["path"],
                    "size": int(row["size"]),
                    "extension": row["extension"] if row["extension"] else ""
                }
                for row in top_10_df.collect()
            ]

        # Extract duplicate statistics directly from duplicate_results without rehashing
        dup_dict = duplicate_results if isinstance(duplicate_results, dict) else {}
        duplicate_group_count = int(
            dup_dict.get("total_duplicate_groups", len(dup_dict.get("duplicate_groups", [])))
        )
        total_duplicate_files = int(dup_dict.get("total_duplicate_files", 0))
        recoverable_bytes = int(dup_dict.get("recoverable_bytes", 0))

        return {
            "total_files": total_files,
            "total_size": total_size,
            "extension_summary": extension_summary,
            "top_10_largest": top_10_largest,
            "duplicate_group_count": duplicate_group_count,
            "total_duplicate_files": total_duplicate_files,
            "recoverable_bytes": recoverable_bytes
        }

    finally:
        if stop_session:
            stop_spark_session()
