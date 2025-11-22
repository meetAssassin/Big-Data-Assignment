# BigData Credit API

A credit-based REST API for querying large-scale datasets in ClickHouse. Each query costs credits, helping manage resource usage.

## Quick Start

### Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Create `.env` file:**
   ```env
   POSTGRES_URL=postgresql://user:password@host:5432/database
   CLICKHOUSE_HOST=your-instance.aws.clickhouse.cloud
   CLICKHOUSE_PORT=8443
   CLICKHOUSE_USER=default
   CLICKHOUSE_PASSWORD=your-password
   CLICKHOUSE_SECURE=true
   ADMIN_API_KEY=your-secret-admin-key
   CREDITS_PER_100_RECORDS=1
   MAX_LIMIT=1000
   ```

3. **Setup database:**
   ```bash
   psql -U postgres -d your_database -f api/db/migrations.sql
   ```

4. **Run server:**
   ```bash
   uvicorn api.main:app --reload
   ```

API available at `http://localhost:8000`, docs at `http://localhost:8000/docs`

## API Endpoints

### Health Check
```bash
GET /health
```

### Signup
```bash
POST /auth/signup
Content-Type: application/json

{
  "name": "John Smith",
  "email": "john@example.com"
}
```
Returns: `user_id`, `api_key`, and `credits: 100`

### Query Records
```bash
GET /query?limit=50&name_like=John&offset=0
Headers: x-api-key: your-api-key
```

**Parameters:**
- `limit`: Records to return (default: 100, max: 1000)
- `offset`: Pagination offset (default: 0)
- `name_like`: Filter by name (partial match)
- `email_like`: Filter by email (partial match)

**Response:**
```json
{
  "data": [
    {
      "canonical_key": "john_doe_12345",
      "name": "John Doe",
      "email": "john@example.com",
      "phone": "9991112222",
      "dob": "1998-05-10"
    }
  ],
  "metadata": {
    "total_records": 1250,
    "credits_used": 1,
    "response_time_ms": 45
  }
}
```

### Get Single Record
```bash
GET /record/{canonical_key}
Headers: x-api-key: your-api-key
```

### Admin: Top Up Credits
```bash
POST /admin/topup?user_email=john@example.com&amount=500
Headers: x-admin-key: your-admin-key
```

## Credit System

- **Query endpoint**: 1 credit per 100 records (rounded up, min 1)
- **Record endpoint**: 1 credit per lookup
- **New users**: Start with 100 credits
- **Insufficient credits**: Returns `402 Payment Required`

Credits are charged based on `limit` parameter, not actual records returned.

## Admin Operations

### Make User Admin
```sql
UPDATE users SET is_admin = TRUE WHERE email = 'admin@example.com';
```

### Check User Credits
```sql
SELECT u.email, c.credits_balance 
FROM users u 
LEFT JOIN credits c ON u.id = c.user_id;
```

### Add Credits (SQL)
```sql
-- Add credits
UPDATE credits 
SET credits_balance = credits_balance + 500 
WHERE user_id = (SELECT id FROM users WHERE email = 'user@example.com');

-- Or insert if doesn't exist
INSERT INTO credits (user_id, credits_balance)
SELECT id, 500 FROM users WHERE email = 'user@example.com';
```

### View Usage Logs
```sql
SELECT u.email, ul.endpoint, ul.credits_used, ul.created_at
FROM usage_logs ul
JOIN users u ON ul.user_id = u.id
ORDER BY ul.created_at DESC
LIMIT 50;
```

## Database Schema

**users**: `id`, `name`, `email`, `is_admin`, `created_at`  
**api_keys**: `id`, `user_id`, `api_key` (SHA-256 hash), `created_at`  
**credits**: `user_id`, `credits_balance`, `updated_at`  
**usage_logs**: `id`, `user_id`, `endpoint`, `query_params`, `records_returned`, `credits_used`, `response_time_ms`, `created_at`

See `api/db/migrations.sql` for full schema.

## Project Structure

```
api/
├── main.py              # FastAPI app
├── config.py           # Environment config
├── routes/              # API endpoints
│   ├── auth.py         # Signup
│   ├── query.py        # Query/search
│   ├── record.py       # Single record
│   └── admin.py        # Admin operations
├── models/             # SQLAlchemy models
├── services/           # Business logic
│   ├── credit_service.py
│   └── clickhouse_service.py
├── deps/               # Dependencies
│   ├── auth.py         # API key validation
│   └── clickhouse.py   # ClickHouse client
└── db/                 # Database config
    ├── postgres.py
    └── migrations.sql
```

## Authentication

All endpoints except `/health` and `/auth/signup` require API key in `x-api-key` header.

API keys are generated during signup and hashed (SHA-256) before storage. If lost, create new user or manually add key to database.

## Troubleshooting

**"POSTGRES_URL not set"**: Check `.env` file exists and has correct connection string.

**"Insufficient Credits"**: Top up via `/admin/topup` or SQL:
```sql
UPDATE credits SET credits_balance = credits_balance + 100 WHERE user_id = X;
```

**"Invalid API key"**: Verify key is in `x-api-key` header. Check database:
```sql
SELECT * FROM api_keys WHERE user_id = X;
```

**ClickHouse connection issues**: Verify credentials in `.env` and test connection.

## Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `POSTGRES_URL` | PostgreSQL connection | Required |
| `CLICKHOUSE_HOST` | ClickHouse hostname | Required |
| `CLICKHOUSE_PASSWORD` | ClickHouse password | Required |
| `ADMIN_API_KEY` | Admin operations key | Required |
| `CREDITS_PER_100_RECORDS` | Credit cost | `1` |
| `MAX_LIMIT` | Max records per query | `1000` |
