import yfinance as yf
import requests
import boto3
import json
from datetime import datetime

# You would pass your Terraform-generated bucket name here via environment variables
S3_BUCKET = "MyBucketName"  # Replace with your actual bucket name
s3_client = boto3.client('s3')

def ingest_weather_data(year):
    print(f"Fetching HKO Weather Data for {year}...")
    base_url = "https://data.weather.gov.hk/weatherAPI/opendata/opendata.php"
    
    # HKO climate data codes: CLMTEMP = Daily Mean Temp, CLMRAIN = Daily Total Rainfall
    metrics = {
        "mean_temp": "CLMTEMP",
        "max_temp": "CLMMAXT",
        "min_temp": "CLMMINT",
    }
    
    for name, dtype in metrics.items():
        params = {
            "dataType": dtype,
            "rformat": "json",
            "station": "HKO",
            "year": str(year)
        }
        
        try:
            res = requests.get(base_url, params=params)
            if res.status_code == 200:
                payload = res.json()
                records = payload.get("data", [])
                
                # Format to JSON-Lines string
                jsonl = "\n".join([
                    json.dumps({"Year": r[0], "Month": r[1], "Day": r[2], "Value": r[3]}) 
                    for r in records if len(r) >= 4
                ])
                
                if jsonl:
                    s3_client.put_object(
                        Bucket=S3_BUCKET, 
                        Key=f"weather/{name}/{year}.jsonl", 
                        Body=jsonl
                    )
                    print(f"Successfully uploaded {name} for {year}")
                else:
                    print(f"No records found for {name} ({year})")
            else:
                print(f"HTTP {res.status_code} error for {name} ({year})")
        except Exception as e:
            print(f"Failed to process {name} ({year}): {e}")

def ingest_hsi_data():
    print("Fetching Hang Seng Index Data...")
    hsi = yf.download("^HSI", period="10y")
    hsi.reset_index(inplace=True)
    hsi['Date'] = hsi['Date'].dt.strftime('%Y-%m-%d')
    
    csv_buffer = hsi[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']].to_csv(index=False)
    s3_client.put_object(Bucket=S3_BUCKET, Key="finance/hsi/historical.csv", Body=csv_buffer)

if __name__ == "__main__":
    current_year = datetime.now().year
    for y in range(current_year - 10, current_year + 1):
        ingest_weather_data(y)
    ingest_hsi_data()
    print("Ingestion Complete.")