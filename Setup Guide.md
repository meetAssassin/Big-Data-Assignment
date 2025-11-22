# Setup Guide for Evaluators

This guide will help you set up and run the BigData Credit API project locally.

## Prerequisites

- Python 3.10 or higher
- PostgreSQL 12+ (or use Docker)
- ClickHouse Cloud account (free tier available) or Docker
- Git

## Quick Setup

### 1. Clone and Navigate

```bash
git clone <repository-url>
cd Big-Data-Project
```

### 2. Setup Environment Variables

```bash
# Copy the example environment file
cp api/.env.example api/.env

# Edit api/.env with your credentials
nano api/.env  # or use your preferred editor
```

**Required values in `api/.env`:**
```env
POSTGRES_URL=postgresql://user:password@localhost:5432/bigdata_api
CLICKHOUSE_HOST=your-instance.aws.clickhouse.cloud
CLICKHOUSE_PASSWORD=your-password
ADMIN_API_KEY=your-secret-key
```

### 3. Setup Databases

**Option A: Using Docker (Easiest)**

```bash
cd deployment
docker-compose up -d
```

This starts PostgreSQL and ClickHouse locally.

**Option B: Manual Setup**

- **PostgreSQL:** Install and create database `bigdata_api`
- **ClickHouse:** Sign up at https://clickhouse.com/cloud (free tier available)

### 4. Initialize Database

```bash
# If using Docker PostgreSQL
psql -h localhost -U admin -d creditsystem -f api/db/migrations.sql
# Password: admin123 (or check docker-compose.yml)

# If using your own PostgreSQL
psql -U your_user -d bigdata_api -f api/db/migrations.sql
```

### 5. Install Dependencies

```bash
pip install -r api/requirements.txt
```

### 6. Run the API

```bash
cd api
uvicorn main:app --reload
```

The API will be available at:
- **API:** http://localhost:8000
- **Interactive Docs:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

## Testing the API

### 1. Health Check

```bash
curl http://localhost:8000/health
```

Expected: `{"ok": true, "clickhouse_ping": true}`

### 2. Create a User

```bash
curl -X POST "http://localhost:8000/auth/signup" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test User",
    "email": "test@example.com"
  }'
```

Save the `api_key` from the response!

### 3. Query Records

```bash
curl "http://localhost:8000/query?limit=10" \
  -H "x-api-key: YOUR_API_KEY_HERE"
```

### 4. Get Single Record

```bash
curl "http://localhost:8000/record/canonical_key_here" \
  -H "x-api-key: YOUR_API_KEY_HERE"
```

## Loading Sample Data

If you want to test with actual data:

1. **Ingest data** (see `src/README.md`):
   ```bash
   cd src/ingestion
   python ingested_data.py
   ```

2. **Load to ClickHouse**:
   ```bash
   cd ../loaders
   python loader.py
   ```

## Common Issues

**"POSTGRES_URL not set"**
- Make sure `api/.env` exists and has `POSTGRES_URL` set

**"CLICKHOUSE_PASSWORD not found"**
- Check `api/.env` has `CLICKHOUSE_PASSWORD` set

**"Insufficient Credits"**
- New users get 100 credits. Top up via SQL:
  ```sql
  UPDATE credits SET credits_balance = 1000 WHERE user_id = 1;
  ```

**Connection errors**
- Verify PostgreSQL is running: `pg_isready` or `docker ps`
- Check ClickHouse credentials in `.env`
- For ClickHouse Cloud, ensure your IP is whitelisted

## Project Structure

```
Big-Data-Project/
├── api/              # FastAPI application
│   ├── main.py      # Entry point
│   ├── routes/      # API endpoints
│   ├── models/      # Database models
│   └── .env         # Configuration (create from .env.example)
├── src/             # Data ingestion pipeline
└── deployment/      # Docker setup
```

## Next Steps

- Explore the API at http://localhost:8000/docs
- Read `api/README.md` for API documentation
- Read `src/README.md` for data ingestion details
- Check `DEPLOYMENT.md` for production deployment

## Support

If you encounter issues:
1. Check the error message - it usually indicates what's wrong
2. Verify all environment variables are set correctly
3. Ensure databases are running and accessible
4. Check the logs for detailed error information

