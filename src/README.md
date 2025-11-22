# Data Pipeline: From Raw Files to ClickHouse

This directory contains the two main components of our data pipeline: the **ingestion system** that processes raw data files, and the **loader** that pushes everything into ClickHouse. Think of it as a two-stage process: first we clean and prepare your data, then we load it into the database where your API can query it.

## The Big Picture

Here's what happens when you run the pipeline:

```
Raw Data Files → Ingestion → Clean Parquet Files → Loader → ClickHouse Database
   (CSV/JSON/etc)    (Spark)     (data_processed/)    (Python)    (master_records)
```

Let's say you have a CSV file with customer data. The ingestion script reads it, cleans it up, removes duplicates, and saves it as a Parquet file. Then the loader picks up that Parquet file and inserts it into ClickHouse, where your FastAPI can serve it to users.

---

## Part 1: The Ingestion Pipeline

**Location:** `src/ingestion/ingested_data.py`

The ingestion pipeline is like a smart data janitor. It takes messy, inconsistent files from different sources and turns them into a clean, unified dataset. It handles all the annoying stuff like different file formats, encoding issues, missing columns, and duplicate records.

### What It Does

Imagine you have a folder full of customer data files - some are CSV, some are JSON, maybe an Excel file or two. They all have slightly different column names, some have missing fields, and there are probably duplicates across files. The ingestion pipeline:

1. **Reads everything** - Supports CSV, JSON, JSONL, Parquet, XML, Excel, and SQL dumps
2. **Cleans it up** - Handles encoding issues, corrupt records, and missing data
3. **Normalizes it** - Standardizes column names (like `fname` → `first_name`)
4. **Deduplicates** - Finds and removes duplicate records across all files
5. **Saves it** - Writes clean Parquet files ready for loading

### Example: Processing a CSV File

Let's say you have a file called `sample.csv` that looks like this:

```csv
name,email,phone,dob
John Doe,john@example.com,9991112222,1998-05-10
john doe,JOHN@example.com,9991112222,1998-05-10
Alicia Keys,alicia@music.com,8887776666,1990-11-01
```

Notice that "John Doe" appears twice with slightly different formatting (capitalization). When the ingestion pipeline processes this:

1. It reads the CSV file and detects it has 3 records
2. It normalizes the column names (they're already good, but it would handle variations)
3. It creates a `canonical_key` for each record by hashing the combination of name, email, phone, and dob
4. It notices that both "John Doe" entries have the same email and phone, so they get the same canonical key
5. When deduplicating, it keeps only one of them
6. It saves the cleaned data to `data_processed/master_dataset/` as a Parquet file

The output Parquet file will have:
- All the original columns (name, email, phone, dob)
- A `canonical_key` column (SHA256 hash for deduplication)
- An `ingest_timestamp` column (when the record was processed)
- Only unique records (duplicates removed)

### Supported File Formats

The pipeline is pretty flexible about what it can read:

- **CSV** - Your standard comma-separated files. Handles different delimiters (comma, semicolon, tab) automatically.
- **JSON** - Both regular JSON arrays and JSONL (one JSON object per line).
- **Parquet** - Already processed data that just needs to be merged.
- **XML** - Extracts records from XML structures.
- **Excel** - Reads `.xlsx` and `.xls` files, including multiple sheets.
- **SQL Dumps** - Parses SQL INSERT statements from database dumps.

### Handling Real-World Messiness

Real data is messy. Here's how the pipeline handles common problems:

**Problem:** Different files use different column names
```csv
# File 1: fname, lname, email_address
# File 2: first_name, last_name, email
```
**Solution:** The pipeline has a mapping that normalizes these automatically. `fname` becomes `first_name`, `email_address` becomes `email`, etc.

**Problem:** Missing data or null values
```csv
name,email,phone
John Doe,john@example.com,
Alice Smith,,555-1234
```
**Solution:** Missing values are filled with empty strings. The pipeline continues processing even if some records are incomplete.

**Problem:** Encoding issues (special characters, foreign languages)
```
José García,maria@example.com,...
```
**Solution:** The pipeline automatically detects file encoding using `chardet` and falls back to UTF-8 if needed.

**Problem:** Corrupt records or malformed JSON
```json
{"name": "John", "email": "john@example.com"}
{"name": "Alice"  // missing closing brace
{"name": "Bob", "email": "bob@example.com"}
```
**Solution:** Corrupt records are detected and skipped. The pipeline logs warnings but continues processing valid records.

**Problem:** Nested data structures
```json
{
  "user": {
    "name": "John Doe",
    "contact": {
      "email": "john@example.com",
      "phone": "555-1234"
    }
  }
}
```
**Solution:** Nested structures are automatically flattened. The above becomes: `user_name`, `user_contact_email`, `user_contact_phone`.

### Running the Ingestion Pipeline

From the `src/ingestion/` directory:

```bash
python ingested_data.py
```

The script will:
1. Scan `../../data_raw/` for all supported files
2. Process each file and show progress
3. Merge everything together
4. Remove duplicates based on `canonical_key`
5. Save the result to `../../data_processed/master_dataset/`

You'll see output like:
```
🔍 Scanning raw data folder...
📥 Reading sample.csv as csv...
   ✓ Loaded 100 records
📥 Reading customers.json as json...
   ✓ Loaded 250 records
🔄 Merging all dataframes...
🧹 Dropping duplicates using canonical_key...
   Removed 15 duplicate records
💾 Writing output to Parquet: ../../data_processed/master_dataset/
✅ INGESTION COMPLETE
Total Records: 335
```

---

## Part 2: The Loader

**Location:** `src/loaders/loader.py`

Once you have clean Parquet files from the ingestion pipeline, the loader takes over. It reads those Parquet files and inserts them into ClickHouse, which is where your API actually queries the data from.

### What It Does

The loader is simpler than the ingestion pipeline - it's focused on one job: getting data from Parquet files into ClickHouse as efficiently as possible. It:

1. **Connects to ClickHouse** - Uses credentials from `api/.env`
2. **Creates the table** - Sets up `master_records` if it doesn't exist
3. **Reads Parquet files** - Processes all `.parquet` files in the output directory
4. **Adapts the schema** - Automatically adds new columns to ClickHouse if the data has fields that don't exist yet
5. **Inserts in batches** - Loads data in chunks of 50,000 rows for efficiency

### Example: Loading Data into ClickHouse

Let's say the ingestion pipeline created a Parquet file with these records:

| canonical_key | name | email | phone | dob | ingest_timestamp |
|--------------|------|-------|-------|-----|------------------|
| abc123... | John Doe | john@example.com | 9991112222 | 1998-05-10 | 2025-11-22 10:00:00 |
| def456... | Alicia Keys | alicia@music.com | 8887776666 | 1990-11-01 | 2025-11-22 10:00:00 |

When you run the loader:

1. It connects to your ClickHouse instance (using credentials from `api/.env`)
2. It checks if the `master_records` table exists, and creates it if needed
3. It reads the Parquet file and converts it to a pandas DataFrame
4. It ensures all columns in the data exist in ClickHouse (adds them if missing)
5. It inserts the data in batches of 50,000 rows
6. You see progress messages as each batch is inserted

The ClickHouse table will have the same structure as your Parquet data, with all columns stored as strings (except `ingest_timestamp` which is a DateTime).

### Dynamic Schema Handling

One cool feature of the loader is that it adapts to new columns automatically. Let's say your next batch of data has a new field like `company_name` that wasn't in previous loads:

```python
# Your Parquet file has: name, email, phone, company_name
# ClickHouse table only has: name, email, phone
```

The loader will:
1. Detect that `company_name` doesn't exist in ClickHouse
2. Automatically run: `ALTER TABLE master_records ADD COLUMN company_name String`
3. Then insert the data with the new column

This means you don't have to manually update your database schema every time your data structure changes.

### Running the Loader

From the `src/loaders/` directory:

```bash
python loader.py
```

**Important:** Make sure you have a `.env` file in the `api/` directory with your ClickHouse credentials:

```env
CLICKHOUSE_HOST=your-host.clickhouse.cloud
CLICKHOUSE_PORT=8443
CLICKHOUSE_USER=default
CLICKHOUSE_PASSWORD=your-password-here
CLICKHOUSE_SECURE=true
```

The loader will:
1. Load credentials from `api/.env`
2. Find all Parquet files in `../../data_processed/master_dataset/`
3. Process each file and show progress
4. Insert data in batches

You'll see output like:
```
📤 Loading ../../data_processed/master_dataset/part-00000.parquet
  → inserting rows 0 to 50000
  → inserting rows 50000 to 100000
🎉 SUCCESS: All Parquet data inserted into ClickHouse Cloud!
```

---

## The Complete Workflow

Here's how you'd typically use both components together:

### Step 1: Prepare Your Raw Data

Put your data files in `data_raw/`. They can be in any supported format:

```
data_raw/
  ├── customers.csv
  ├── leads.json
  ├── old_data.xlsx
  └── backup.sql
```

### Step 2: Run the Ingestion Pipeline

```bash
cd src/ingestion
python ingested_data.py
```

This processes all files, cleans them, removes duplicates, and creates Parquet files in `data_processed/master_dataset/`.

### Step 3: Load into ClickHouse

```bash
cd ../loaders
python loader.py
```

This reads the Parquet files and inserts them into ClickHouse.

### Step 4: Query via API

Your FastAPI can now query the data from ClickHouse. The API handles authentication, credit tracking, and all that good stuff.

---

## Configuration

### Ingestion Settings

The ingestion pipeline looks for files in:
- **Input:** `../../data_raw/` (relative to `src/ingestion/`)
- **Output:** `../../data_processed/master_dataset/` (relative to `src/ingestion/`)

You can modify these paths at the top of `ingested_data.py`:
```python
RAW_DATA_PATH = "../../data_raw/"
OUTPUT_PATH = "../../data_processed/master_dataset/"
```

### Loader Settings

The loader reads from:
- **Input:** `../../data_processed/master_dataset/` (relative to `src/loaders/`)
- **Batch Size:** 50,000 rows per insert (configurable in `loader.py`)

ClickHouse connection settings come from `api/.env`.

---

## Troubleshooting

### Ingestion Issues

**"Skipping unsupported file"**
- Check that your file has a supported extension (.csv, .json, .xlsx, etc.)
- The pipeline only processes files it recognizes

**"Could not read file"**
- Check file permissions - make sure the file is readable
- Try opening the file manually to see if it's corrupted
- For CSV files, check if it uses a non-standard delimiter

**"Found corrupt rows"**
- This is normal! The pipeline drops corrupt records and continues
- Check the source data quality if you're losing too many records

### Loader Issues

**"CLICKHOUSE_PASSWORD not found"**
- Make sure you have a `.env` file in the `api/` directory
- Check that `CLICKHOUSE_PASSWORD` is set in that file

**"No Parquet files found"**
- Run the ingestion pipeline first to create Parquet files
- Check that the output path is correct

**Connection errors**
- Verify your ClickHouse credentials in `api/.env`
- Check that your network can reach the ClickHouse host
- For ClickHouse Cloud, make sure your IP is whitelisted

---

## Dependencies

Both components share some dependencies. Install them with:

```bash
pip install -r src/requirements.txt
```

Key packages:
- **pyspark** - For distributed data processing (ingestion)
- **pandas** - For data manipulation
- **clickhouse-connect** - For ClickHouse connectivity (loader)
- **pyarrow** - For Parquet file handling
- **openpyxl** - For Excel file support
- **chardet** - For encoding detection
- **python-dotenv** - For loading environment variables

---

## Tips and Best Practices

1. **Run ingestion first, then loader** - Always process your raw data before loading it
2. **Check for duplicates** - The ingestion pipeline removes duplicates, but it's good to understand your data
3. **Monitor batch sizes** - If the loader is too slow, you can adjust `BATCH_SIZE` in `loader.py`
4. **Keep raw data** - Don't delete files from `data_raw/` - they're your source of truth
5. **Incremental loads** - You can run the loader multiple times - it will insert new data alongside existing records
6. **Schema evolution** - The loader handles new columns automatically, but be aware that adding many columns can slow down queries

---

## What's Next?

After running both the ingestion pipeline and the loader, your data is in ClickHouse and ready to be queried through the FastAPI. The API handles:
- User authentication via API keys
- Credit-based access control
- Query filtering and pagination
- Usage logging and analytics

Check out the `api/` directory for API documentation and usage examples.

