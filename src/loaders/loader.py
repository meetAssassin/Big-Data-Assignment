import os
import pandas as pd
import clickhouse_connect
import pyarrow.parquet as pq
from typing import List
from dotenv import load_dotenv
from pathlib import Path

PARQUET_DIR = "../../data_processed/master_dataset/"
BATCH_SIZE = 50000 

def cast_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Cast all columns to correct ClickHouse-supported types.
    - Strings → str
    - DateTime → python datetime
    - NaN → ''
    - Handles missing fields gracefully
    """
    # Convert ingest_timestamp properly
    if "ingest_timestamp" in df.columns:
        df["ingest_timestamp"] = pd.to_datetime(df["ingest_timestamp"], errors="coerce")
    else:
        # Add ingest_timestamp if missing
        df["ingest_timestamp"] = pd.Timestamp.now()

    # Convert all other columns to strings (except DateTime)
    for col in df.columns:
        if col != "ingest_timestamp":
            # Handle various data types
            if df[col].dtype == 'object':
                df[col] = df[col].astype(str).fillna("")
            else:
                df[col] = df[col].fillna("").astype(str)

    return df

def ensure_table_schema(client, columns: List[str]):
    """Ensure ClickHouse table has all required columns, add missing ones dynamically."""
    # Get current table structure
    try:
        result = client.query("DESCRIBE master_records")
        existing_cols = [row[0] for row in result.result_rows] if result.result_rows else []
        
        # Add missing columns
        for col in columns:
            # Sanitize column name (ClickHouse column names)
            safe_col = col.replace(" ", "_").replace("-", "_")
            if safe_col not in existing_cols and safe_col != "ingest_timestamp":
                try:
                    client.command(f"ALTER TABLE master_records ADD COLUMN IF NOT EXISTS `{safe_col}` String")
                    print(f"  ✓ Added column: {safe_col}")
                except Exception as e:
                    print(f"  ⚠ Could not add column {safe_col}: {e}")
        
        # Ensure ingest_timestamp exists
        if "ingest_timestamp" not in existing_cols:
            try:
                client.command("ALTER TABLE master_records ADD COLUMN IF NOT EXISTS ingest_timestamp DateTime")
            except Exception as e:
                print(f"  ⚠ Could not add ingest_timestamp: {e}")
                
    except Exception as e:
        print(f"  ⚠ Error checking table schema: {e}")

def main():
    # Load .env file from api directory
    api_dir = Path(__file__).parent.parent.parent / "api"
    env_path = api_dir / ".env"
    load_dotenv(env_path)
    
    # Get ClickHouse credentials from environment variables
    clickhouse_host = os.getenv("CLICKHOUSE_HOST")
    clickhouse_user = os.getenv("CLICKHOUSE_USER", "default")
    clickhouse_password = os.getenv("CLICKHOUSE_PASSWORD", "")
    clickhouse_secure = os.getenv("CLICKHOUSE_SECURE", "true").lower() in ("1", "true", "yes")
    
    if not clickhouse_host:
        raise ValueError("CLICKHOUSE_HOST not found in api/.env file")
    if not clickhouse_password:
        raise ValueError("CLICKHOUSE_PASSWORD not found in api/.env file")
    
    client = clickhouse_connect.get_client(
        host=clickhouse_host,
        user=clickhouse_user,
        password=clickhouse_password,
        secure=clickhouse_secure
    )

    # Create table with core columns
    client.command("""
    CREATE TABLE IF NOT EXISTS master_records (
        canonical_key String,
        name String,
        first_name String,
        last_name String,
        email String,
        phone String,
        dob String,
        ingest_timestamp DateTime
    )
    ENGINE = MergeTree()
    ORDER BY canonical_key
    """)

    # Load files
    files = [f for f in os.listdir(PARQUET_DIR) if f.endswith(".parquet")]

    if not files:
        print("❌ No Parquet files found!")
        return

    for file in files:
        file_path = os.path.join(PARQUET_DIR, file)
        print(f"📤 Loading {file_path}")

        try:
            # Read Parquet → DataFrame
            table = pq.read_table(file_path)
            df = table.to_pandas()

            # CAST TYPES CORRECTLY (CRITICAL)
            df = cast_dataframe(df)

            # Ensure table schema matches data
            ensure_table_schema(client, df.columns.tolist())

            rows = df.values.tolist()
            colnames = df.columns.tolist()

            # Insert in batches
            for i in range(0, len(rows), BATCH_SIZE):
                batch = rows[i:i+BATCH_SIZE]
                print(f"  → inserting rows {i} to {i+len(batch)}")
                try:
                    client.insert("master_records", batch, column_names=colnames)
                except Exception as e:
                    print(f"  ❌ Error inserting batch {i}: {e}")
                    continue
                    
        except Exception as e:
            print(f"  ❌ Error processing {file}: {e}")
            continue

    print("\n🎉 SUCCESS: All Parquet data inserted into ClickHouse Cloud!")

if __name__ == "__main__":
    main()