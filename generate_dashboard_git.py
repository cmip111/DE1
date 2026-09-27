import awswrangler as wr
import boto3
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Configuration
DATABASE_NAME = "hk_weather_finance_db"
WEBSITE_BUCKET = ""  # Replace with your S3 website bucket name
PROCESSED_BUCKET = ""        # Replace with your processed S3 bucket name

def build_dashboard():
    print("Querying processed data from Athena...")
    
    sql = """
    SELECT date, open, high, low, close, volume, daily_volatility, meantemp_c, maxtemp_c 
    FROM market_climate_data 
    ORDER BY date ASC;
    """
    
    df = wr.athena.read_sql_query(
        sql=sql, 
        database=DATABASE_NAME,
        s3_output=f"s3://{PROCESSED_BUCKET}/athena-results/"
    )
    
    print("Generating Plotly charts...")
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=(
            "Hang Seng Index (Close) vs. Daily Mean Temperature",
            "Daily Market Volatility vs. Daily Max Temperature"
        ),
        vertical_spacing=0.15
    )
    
    # 1. Plot 1: Close Price vs. Mean Temperature (X-axis = Mean Temp)
    fig.add_trace(
        go.Scatter(
            x=df['meantemp_c'], 
            y=df['close'], 
            mode='markers',
            marker=dict(size=6, color="#1f77b4", opacity=0.6),
            name="Close vs Mean Temp"
        ),
        row=1, col=1
    )
    
    # 2. Plot 2: Volatility vs. Max Temperature (Colour bar removed)
    fig.add_trace(
        go.Scatter(
            x=df['maxtemp_c'], 
            y=df['daily_volatility'], 
            mode='markers',
            marker=dict(size=6, color="#ff7f0e", opacity=0.6, showscale=False),
            name="Volatility vs Max Temp"
        ),
        row=2, col=1
    )
    
    # Set explicit X and Y axis labels for Plot 1
    fig.update_xaxes(title_text="Daily Mean Temperature (°C)", row=1, col=1)
    fig.update_yaxes(title_text="HSI Close Price (HKD)", row=1, col=1)
    
    # Set explicit X and Y axis labels for Plot 2
    fig.update_xaxes(title_text="Daily Max Temperature (°C)", row=2, col=1)
    fig.update_yaxes(title_text="Daily Volatility (High - Low)", row=2, col=1)
    
    # General chart styling
    fig.update_layout(
        height=850,
        title_text="Hong Kong Climate & Financial Market Analytics",
        template="plotly_white",
        showlegend=False
    )
    
    local_html = "index.html"
    fig.write_html(local_html)
    print(f"Dashboard saved locally as {local_html}")
    
    # Upload updated index.html to S3 Website Bucket
    s3 = boto3.client('s3')
    s3.upload_file(
        Filename=local_html,
        Bucket=WEBSITE_BUCKET,
        Key="index.html",
        ExtraArgs={'ContentType': 'text/html'}
    )
    print(f"Successfully uploaded {local_html} to s3://{WEBSITE_BUCKET}/index.html")

if __name__ == "__main__":
    build_dashboard()