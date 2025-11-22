import os
import json
import re
import chardet
import xml.etree.ElementTree as ET
from typing import Dict, List, Any, Optional
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, trim, lower, sha2, concat_ws, lit, current_timestamp, when, isnan, isnull
from pyspark.sql.types import StructType, StructField, StringType, DoubleType, FloatType, NumericType
import pandas as pd

# Utility functions for data quality
def detect_encoding_safe(file_path: str, sample_size: int = 10000) -> str:
    """Safely detect file encoding with fallback options."""
    try:
        with open(file_path, 'rb') as f:
            raw_data = f.read(sample_size)
            result = chardet.detect(raw_data)
            encoding = result.get('encoding', 'utf-8')
            if encoding is None or encoding.lower() in ['ascii', 'us-ascii']:
                return 'utf-8'
            return encoding
    except Exception:
        return 'utf-8'

def normalize_field_name(name: str) -> str:
    """Normalize field names to be consistent."""
    name = name.lower().strip()
    name = re.sub(r'[^\w]', '_', name)
    name = re.sub(r'_+', '_', name)
    return name.strip('_')

def sanitize_for_storage(value: Any, max_length: int = 10000) -> str:
    """Sanitize values for safe storage."""
    if value is None:
        return ""
    str_value = str(value)
    if len(str_value) > max_length:
        str_value = str_value[:max_length]
    return str_value.strip()

RAW_DATA_PATH = "../../data_raw/"
OUTPUT_PATH = "../../data_processed/master_dataset/"

def create_spark_session():
    spark = SparkSession.builder \
        .appName("UnifiedIngestionPipeline") \
        .config("spark.sql.session.timeZone", "UTC") \
        .config("spark.sql.adaptive.enabled", "true") \
        .config("spark.sql.adaptive.coalescePartitions.enabled", "true") \
        .getOrCreate()
    return spark

def detect_encoding(file_path: str) -> str:
    """Detect file encoding using chardet with fallbacks."""
    return detect_encoding_safe(file_path)

def detect_format(path: str) -> Optional[str]:
    """Detect file format based on extension."""
    path_lower = path.lower()
    if path_lower.endswith(".csv"):
        return "csv"
    if path_lower.endswith(".json") or path_lower.endswith(".jsonl"):
        return "json"
    if path_lower.endswith(".parquet"):
        return "parquet"
    if path_lower.endswith(".xml"):
        return "xml"
    if path_lower.endswith((".xlsx", ".xls")):
        return "excel"
    if path_lower.endswith((".sql", ".dump")):
        return "sql"
    return None

def flatten_dict(d: Dict, parent_key: str = '', sep: str = '_') -> Dict:
    """Flatten nested dictionary structures."""
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        elif isinstance(v, list):
            # Handle lists by converting to string or taking first element
            if len(v) > 0 and isinstance(v[0], dict):
                # If list of dicts, flatten the first one
                items.extend(flatten_dict(v[0], new_key, sep=sep).items())
            else:
                items.append((new_key, str(v) if v else ""))
        else:
            items.append((new_key, v))
    return dict(items)

def read_xml_to_dicts(file_path: str) -> List[Dict]:
    """Read XML file and convert to list of dictionaries."""
    records = []
    try:
        encoding = detect_encoding(file_path)
        tree = ET.parse(file_path)
        root = tree.getroot()
        
        # Try to find repeating elements (common pattern)
        # Look for direct children that might be records
        for child in root:
            record = {}
            for elem in child.iter():
                if elem.text and elem.text.strip():
                    # Use tag name as key, handle nested tags
                    key = elem.tag
                    if key in record:
                        # If duplicate key, make it a list or append
                        if not isinstance(record[key], list):
                            record[key] = [record[key]]
                        record[key].append(elem.text.strip())
                    else:
                        record[key] = elem.text.strip()
            if record:
                records.append(flatten_dict(record))
        
        # If no records found, try treating root as single record
        if not records:
            record = {}
            for elem in root.iter():
                if elem.text and elem.text.strip() and elem.tag != root.tag:
                    record[elem.tag] = elem.text.strip()
            if record:
                records.append(flatten_dict(record))
                
    except ET.ParseError as e:
        print(f"⚠ XML parsing error in {file_path}: {e}")
        return []
    except Exception as e:
        print(f"⚠ Error reading XML {file_path}: {e}")
        return []
    
    return records

def read_excel_to_dicts(file_path: str) -> List[Dict]:
    """Read Excel file and convert to list of dictionaries."""
    records = []
    try:
        # Try reading all sheets
        excel_file = pd.ExcelFile(file_path, engine='openpyxl')
        for sheet_name in excel_file.sheet_names:
            df = pd.read_excel(excel_file, sheet_name=sheet_name, engine='openpyxl')
            # Convert to dict, handling nested structures
            for _, row in df.iterrows():
                record = row.to_dict()
                # Flatten any nested structures
                flattened = flatten_dict(record)
                records.append(flattened)
    except Exception as e:
        print(f"⚠ Error reading Excel {file_path}: {e}")
        return []
    return records

def parse_sql_dump(file_path: str) -> List[Dict]:
    """Parse SQL INSERT statements from dump file with robust error handling."""
    records = []
    try:
        encoding = detect_encoding(file_path)
        with open(file_path, 'r', encoding=encoding, errors='ignore') as f:
            content = f.read()
            
        # Pattern to match INSERT INTO ... VALUES (...)
        # Handle multi-line INSERT statements
        insert_pattern = r'INSERT\s+INTO\s+(\w+)\s*\(([^)]+)\)\s*VALUES\s*(.+?)(?=INSERT|$)'
        matches = re.finditer(insert_pattern, content, re.IGNORECASE | re.MULTILINE | re.DOTALL)
        
        for match in matches:
            try:
                table_name = match.group(1)
                columns_str = match.group(2)
                values_str = match.group(3)
                
                # Extract column names
                columns = [col.strip().strip('`"\'') for col in columns_str.split(',')]
                
                # Parse VALUES - handle multiple rows
                # Split by ),( or just ) for single row
                value_rows = re.split(r'\),\s*\(', values_str)
                
                for row_str in value_rows:
                    # Clean up row string
                    row_str = row_str.strip().strip('()')
                    
                    # Parse values - handle quoted strings properly
                    values = []
                    current_value = ""
                    in_quotes = False
                    quote_char = None
                    
                    for char in row_str:
                        if char in ['"', "'"] and (not in_quotes or char == quote_char):
                            in_quotes = not in_quotes
                            quote_char = char if in_quotes else None
                            current_value += char
                        elif char == ',' and not in_quotes:
                            values.append(current_value.strip().strip("'\"`"))
                            current_value = ""
                        else:
                            current_value += char
                    
                    # Add last value
                    if current_value:
                        values.append(current_value.strip().strip("'\"`"))
                    
                    # Create record with column names
                    if len(values) == len(columns):
                        record = {normalize_field_name(col): sanitize_for_storage(val) 
                                 for col, val in zip(columns, values)}
                        records.append(flatten_dict(record))
                    elif len(values) > 0:
                        # Mismatch - create record with available columns
                        record = {normalize_field_name(columns[i]): sanitize_for_storage(val) 
                                 for i, val in enumerate(values) if i < len(columns)}
                        records.append(flatten_dict(record))
                        
            except Exception as e:
                continue  # Skip malformed INSERT statements
                
    except Exception as e:
        print(f"⚠ Error parsing SQL dump {file_path}: {e}")
        return []
    
    return records

def read_file(spark: SparkSession, path: str):
    """Read file with robust error handling and format support."""
    fmt = detect_format(path)
    
    if fmt is None:
        print(f"⚠ Unsupported format: {path}")
        return None

    # ---------- SAFETY CHECKS BEFORE SPARK ----------
    try:
        encoding = detect_encoding(path)
        
        if fmt == "csv":
            # Try reading first line safely
            with open(path, 'r', encoding=encoding, errors='ignore') as f:
                first_line = f.readline()
                if not first_line or ("," not in first_line and ";" not in first_line and "\t" not in first_line):
                    print(f"⚠ Skipping corrupt CSV: {path}")
                    return None

        elif fmt == "json":
            # Try loading first JSON line
            with open(path, "r", encoding=encoding, errors="ignore") as f:
                line = f.readline().strip()
                if line and not (line.startswith("{") or line.startswith("[")):
                    print(f"⚠ Skipping corrupt JSON: {path}")
                    return None

        elif fmt == "xml":
            # Basic XML validation
            try:
                ET.parse(path)
            except ET.ParseError:
                print(f"⚠ Skipping corrupt XML: {path}")
                return None
                
        elif fmt == "excel":
            # Excel files will be validated by pandas
            pass
            
        elif fmt == "sql":
            # SQL dumps will be parsed manually
            pass
            
        elif fmt == "parquet":
            pass  # Spark will handle parquet safely
            
    except Exception as e:
        print(f"⚠ Skipping unreadable file: {path} - {e}")
        return None

    # ---------- READ WITH SPARK OR PANDAS ----------
    try:
        if fmt == "csv":
            # Try multiple delimiters and handle encoding issues
            df = spark.read.option("header", "true") \
                .option("inferSchema", "true") \
                .option("mode", "PERMISSIVE") \
                .option("columnNameOfCorruptRecord", "_corrupt_record") \
                .option("encoding", encoding) \
                .csv(path)
            
            # Handle multiple delimiter attempts
            if df.count() == 0:
                # Try semicolon delimiter
                df = spark.read.option("header", "true") \
                    .option("inferSchema", "true") \
                    .option("mode", "PERMISSIVE") \
                    .option("delimiter", ";") \
                    .option("columnNameOfCorruptRecord", "_corrupt_record") \
                    .csv(path)

        elif fmt == "json":
            # Handle both JSON arrays and JSONL
            df = spark.read.option("inferSchema", "true") \
                .option("mode", "PERMISSIVE") \
                .option("columnNameOfCorruptRecord", "_corrupt_record") \
                .json(path)

        elif fmt == "parquet":
            df = spark.read.parquet(path)

        elif fmt == "xml":
            # Convert XML to JSON-like structure first
            records = read_xml_to_dicts(path)
            if not records:
                return None
            # Convert to pandas then Spark
            pdf = pd.DataFrame(records)
            df = spark.createDataFrame(pdf)

        elif fmt == "excel":
            # Read Excel via pandas, then convert to Spark
            records = read_excel_to_dicts(path)
            if not records:
                return None
            pdf = pd.DataFrame(records)
            df = spark.createDataFrame(pdf)

        elif fmt == "sql":
            # Parse SQL dump
            records = parse_sql_dump(path)
            if not records:
                return None
            pdf = pd.DataFrame(records)
            df = spark.createDataFrame(pdf)

        else:
            return None

    except Exception as e:
        print(f"❌ Could not read file: {path}")
        print(f"Reason: {e}")
        return None

    # ---------- DROP CORRUPT RECORDS IF EXIST ----------
    if "_corrupt_record" in df.columns:
        corrupt_count = df.filter(df["_corrupt_record"].isNotNull()).count()
        if corrupt_count > 0:
            print(f"⚠ Found {corrupt_count} corrupt rows in {path}, dropping them.")
        df = df.filter(df["_corrupt_record"].isNull()).drop("_corrupt_record")

    # ---------- HANDLE MISSING FIELDS AND NULL VALUES ----------
    # Fill null values with empty strings for string columns
    for col_name in df.columns:
        df = df.withColumn(col_name, when(col(col_name).isNull(), lit("")).otherwise(col(col_name)))
        # Only apply isnan() to numeric columns (DoubleType, FloatType, etc.)
        # isnan() only works on numeric types and will fail on string columns
        field = next((f for f in df.schema.fields if f.name == col_name), None)
        if field and isinstance(field.dataType, (DoubleType, FloatType)):
            df = df.withColumn(col_name, when(isnan(col(col_name)), lit("")).otherwise(col(col_name)))

    # ---------- FLATTEN NESTED STRUCTURES ----------
    # Spark automatically handles nested structures, but we ensure they're flattened
    # by converting complex types to strings if needed
    for field in df.schema.fields:
        if str(field.dataType).startswith("StructType") or str(field.dataType).startswith("ArrayType"):
            # Convert nested structures to JSON strings
            df = df.withColumn(field.name, when(col(field.name).isNotNull(), 
                                                 col(field.name).cast("string")).otherwise(lit("")))

    return df


def normalize_columns(df):
    """Normalize column names and values."""
    # Normalize typical fields if they exist
    mapping = {
        "fname": "first_name",
        "lname": "last_name",
        "full_name": "name",
        "email_address": "email",
        "e_mail": "email",
        "phone_number": "phone",
        "mobile": "phone",
        "date_of_birth": "dob",
        "birth_date": "dob",
    }

    for old, new in mapping.items():
        if old in df.columns and new not in df.columns:
            df = df.withColumnRenamed(old, new)

    # Lowercase / trim typical fields
    for field in ["name", "first_name", "last_name", "email", "phone"]:
        if field in df.columns:
            df = df.withColumn(field, trim(lower(col(field))))

    # Add ingestion timestamp
    df = df.withColumn("ingest_timestamp", current_timestamp())

    return df

def generate_canonical_key(df):
    """Create deterministic hash for deduplication."""
    key_cols = []

    for c in ["name", "email", "phone", "dob"]:
        if c in df.columns:
            key_cols.append(col(c))

    if len(key_cols) == 0:
        df = df.withColumn("canonical_key", sha2(lit("no_key"), 256))
        return df

    return df.withColumn(
        "canonical_key",
        sha2(concat_ws("||", *key_cols), 256)
    )


def main():
    spark = create_spark_session()

    all_dfs = []

    print("\n🔍 Scanning raw data folder...")
    for file in os.listdir(RAW_DATA_PATH):
        file_path = os.path.join(RAW_DATA_PATH, file)

        fmt = detect_format(file_path)
        if fmt is None:
            print(f"⚠ Skipping unsupported file: {file}")
            continue

        print(f"📥 Reading {file} as {fmt}...")
        df = read_file(spark, file_path)

        if df is None:
            print(f"❌ Could not read: {file}")
            continue

        print(f"   ✓ Loaded {df.count()} records")

        df = normalize_columns(df)
        df = generate_canonical_key(df)

        all_dfs.append(df)

    if not all_dfs:
        print("\n❌ No valid data files found.")
        return

    print("\n🔄 Merging all dataframes...")
    merged_df = all_dfs[0]
    for df in all_dfs[1:]:
        merged_df = merged_df.unionByName(df, allowMissingColumns=True)

    print("🧹 Dropping duplicates using canonical_key...")
    if "canonical_key" in merged_df.columns:
        before_count = merged_df.count()
        merged_df = merged_df.dropDuplicates(["canonical_key"])
        after_count = merged_df.count()
        print(f"   Removed {before_count - after_count} duplicate records")

    print("\n💾 Writing output to Parquet:", OUTPUT_PATH)
    os.makedirs(OUTPUT_PATH, exist_ok=True)
    merged_df.write.mode("overwrite").parquet(OUTPUT_PATH)

    print("\n✅ INGESTION COMPLETE")
    print(f"Total Records: {merged_df.count()}")


if __name__ == "__main__":
    main()
