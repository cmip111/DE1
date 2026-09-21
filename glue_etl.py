import sys
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from pyspark.sql.functions import col, make_date, to_date, when

# Receive bucket names passed from job arguments
args = getResolvedOptions(sys.argv, ['JOB_NAME', 'RAW_BUCKET', 'PROCESSED_BUCKET'])

sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session

RAW_URI = f"s3://{args['RAW_BUCKET']}"
PROCESSED_URI = f"s3://{args['PROCESSED_BUCKET']}/analytics_model/"

# 1. Helper function to process individual weather metric JSONL files
def load_weather_metric(metric_name, output_col):
    path = f"{RAW_URI}/weather/{metric_name}/*.jsonl"
    df = spark.read.json(path)
    
    # Construct standard YYYY-MM-DD Date using make_date (handles single digits automatically)
    df = df.withColumn("Date", make_date(col("Year").cast("int"), col("Month").cast("int"), col("Day").cast("int")))
    # Clean API nulls ("***") and cast to float
    df = df.withColumn(
        output_col,
        when(col("Value") == "***", None).otherwise(col("Value").cast("float"))
    )
    return df.select("Date", output_col)

# Load weather metrics
df_mean = load_weather_metric("mean_temp", "MeanTemp_C")
df_max = load_weather_metric("max_temp", "MaxTemp_C")
df_min = load_weather_metric("min_temp", "MinTemp_C")

# Join weather metrics into a single DataFrame
weather_df = df_mean \
    .join(df_max, "Date", "outer") \
    .join(df_min, "Date", "outer")

# 2. Process HSI Financial Data (CSV)
hsi_df = spark.read.option("header", "true").csv(f"{RAW_URI}/finance/hsi/*.csv")
hsi_df = hsi_df \
    .withColumn("Date", to_date(col("Date"), "yyyy-MM-dd")) \
    .withColumn("Open", col("Open").cast("float")) \
    .withColumn("High", col("High").cast("float")) \
    .withColumn("Low", col("Low").cast("float")) \
    .withColumn("Close", col("Close").cast("float")) \
    .withColumn("Volume", col("Volume").cast("long")) \
    .withColumn("Daily_Volatility", col("High") - col("Low"))

# 3. Join Finance and Weather Data on Date (Inner join drops weekends when market is closed)
final_df = hsi_df.join(weather_df, "Date", "inner")

# 4. Write processed output to S3 as Parquet
final_df.write.mode("overwrite").parquet(PROCESSED_URI)