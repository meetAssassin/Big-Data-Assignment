# BigData Credit API Documentation

## Overview

The BigData Credit API is a RESTful service that provides access to master records stored in ClickHouse. The API uses a credit-based system where users consume credits to query data. All endpoints (except `/health` and `/auth/signup`) require authentication via API key.

**Base URL:** `http://localhost:8000` (or your deployed URL)

---

## Table of Contents

1. [Authentication](#authentication)
2. [Health Check](#health-check)
3. [Authentication Endpoints](#authentication-endpoints)
4. [Query Endpoints](#query-endpoints)
5. [Admin Endpoints](#admin-endpoints)
6. [Error Responses](#error-responses)
7. [Credit System](#credit-system)

---

## Authentication

Most endpoints require authentication using an API key. Include your API key in the request header:

```
x-api-key: your-api-key-here
```

**Note:** API keys are generated during signup and are only shown once. Store them securely.

---

## Health Check

### GET `/health`

Check the health status of the API and ClickHouse connection.

**Authentication:** Not required

**Response:**
```json
{
  "ok": true,
  "clickhouse_ping": true
}
```

**Example:**
```bash
curl http://localhost:8000/health
```

---

## Authentication Endpoints

### POST `/auth/signup`

Register a new user account and receive an API key.

**Authentication:** Not required

**Request Body:**
```json
{
  "name": "John Doe",
  "email": "john@example.com"
}
```

**Response (200 OK):**
```json
{
  "message": "Signup successful",
  "user_id": 1,
  "api_key": "a9378ae020e1e7f6848b2b2a5c300fff920e16991ad547ea4a5d97999ebe0f93",
  "credits": 100
}
```

**Error Responses:**
- `400 Bad Request`: Email already registered

**Example:**
```bash
curl -X POST http://localhost:8000/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"name": "John Doe", "email": "john@example.com"}'
```

**Important:** Save the `api_key` from the response - it will not be shown again!

---

## Query Endpoints

### GET `/query`

Query master records with optional filters. Credits are deducted based on the number of records returned.

**Authentication:** Required (API key via `x-api-key` header)

**Query Parameters:**
- `limit` (integer, optional): Maximum number of records to return. Default: `100`, Minimum: `1`, Maximum: `1000` (configurable via `MAX_LIMIT`)
- `offset` (integer, optional): Number of records to skip. Default: `0`, Minimum: `0`
- `name_like` (string, optional): Filter records where name contains this string (case-sensitive)
- `email_like` (string, optional): Filter records where email contains this string (case-sensitive)

**Response (200 OK):**
```json
{
  "data": [
    {
      "canonical_key": "c0d1baa9fe8cad17eb14572336eead4e96f0f56a35c9c46d764fb6e168cddc92",
      "name": "John Doe",
      "email": "john@example.com",
      ...
    }
  ],
  "metadata": {
    "total_records": 1500,
    "credits_used": 2,
    "response_time_ms": 45
  }
}
```

**Error Responses:**
- `401 Unauthorized`: Missing or invalid API key
- `402 Payment Required`: Insufficient credits

**Credit Calculation:**
- Credits are calculated as: `max(1, (limit + 99) // 100 * CREDITS_PER_100_RECORDS)`
- Default: 1 credit per 100 records (minimum 1 credit)
- Credits are deducted before the query executes

**Example:**
```bash
curl -X GET "http://localhost:8000/query?limit=200&name_like=John&email_like=example" \
  -H "x-api-key: your-api-key-here"
```

---

### GET `/record/{canonical_key}`

Retrieve a single record by its canonical key.

**Authentication:** Required (API key via `x-api-key` header)

**Path Parameters:**
- `canonical_key` (string, required): The canonical key of the record to retrieve

**Response (200 OK):**
```json
{
  "data": {
    "canonical_key": "c0d1baa9fe8cad17eb14572336eead4e96f0f56a35c9c46d764fb6e168cddc92",
    "name": "John Doe",
    "email": "john@example.com",
    ...
  },
  "metadata": {
    "credits_used": 1,
    "response_time_ms": 12
  }
}
```

**Error Responses:**
- `401 Unauthorized`: Missing or invalid API key
- `402 Payment Required`: Insufficient credits
- `404 Not Found`: Record with the given canonical key does not exist

**Credit Cost:** 1 credit (minimum charge for single record lookup)

**Example:**
```bash
curl -X GET "http://localhost:8000/record/c0d1baa9fe8cad17eb14572336eead4e96f0f56a35c9c46d764fb6e168cddc92" \
  -H "x-api-key: your-api-key-here"
```

---

## Admin Endpoints

Admin endpoints require a special admin API key configured in the environment variable `ADMIN_API_KEY`.

### POST `/admin/topup`

Add credits to a user's account.

**Authentication:** Required (Admin API key via `x-admin-key` header)

**Query Parameters:**
- `user_email` (string, required): Email of the user to top up
- `amount` (integer, required): Number of credits to add

**Response (200 OK):**
```json
{
  "status": "ok",
  "user_id": 1,
  "added": 500
}
```

**Error Responses:**
- `401 Unauthorized`: Invalid or missing admin key
- `404 Not Found`: User with the given email does not exist

**Example:**
```bash
curl -X POST "http://localhost:8000/admin/topup?user_email=user@example.com&amount=500" \
  -H "x-admin-key: your-admin-key-here"
```

**Note:** If the user doesn't have a credit record, one will be created. Otherwise, credits are added to the existing balance.

---

### POST `/admin/promote` (Optional)

Promote a user to admin status. This endpoint may not be available in all deployments.

**Authentication:** Required (Admin API key via `x-admin-key` header)

**Query Parameters:**
- `user_email` (string, required): Email of the user to promote

**Response (200 OK):**
```json
{
  "status": "ok",
  "user_id": 1,
  "email": "user@example.com",
  "is_admin": true
}
```

**Error Responses:**
- `401 Unauthorized`: Invalid or missing admin key
- `404 Not Found`: User with the given email does not exist

**Example:**
```bash
curl -X POST "http://localhost:8000/admin/promote?user_email=user@example.com" \
  -H "x-admin-key: your-admin-key-here"
```

**Note:** To create an admin user, you can either:
1. Use this endpoint (if available)
2. Manually update the database: `UPDATE users SET is_admin = TRUE WHERE email = 'user@example.com';`

---

## Error Responses

All endpoints may return the following error responses:

### 400 Bad Request
```json
{
  "detail": "Email already registered"
}
```

### 401 Unauthorized
```json
{
  "detail": "Missing API key"
}
```
or
```json
{
  "detail": "Invalid API key"
}
```
or
```json
{
  "detail": "Invalid admin key"
}
```

### 402 Payment Required
```json
{
  "detail": "Insufficient Credits"
}
```

### 404 Not Found
```json
{
  "detail": "Not found"
}
```
or
```json
{
  "detail": "User not found"
}
```

### 422 Unprocessable Entity
Returned when request parameters are invalid or missing.

### 500 Internal Server Error
Server error. Check server logs for details.

---

## Credit System

### How Credits Work

1. **Signup Credits:** New users receive 100 credits upon signup
2. **Credit Deduction:** Credits are deducted before queries execute
3. **Credit Calculation:**
   - `/query`: `max(1, (limit + 99) // 100 * CREDITS_PER_100_RECORDS)`
   - `/record/{canonical_key}`: 1 credit (minimum)
4. **Insufficient Credits:** If you don't have enough credits, the request fails with `402 Payment Required` and no credits are deducted

### Configuration

Credit system behavior can be configured via environment variables:
- `CREDITS_PER_100_RECORDS`: Credits charged per 100 records (default: `1`)
- `MAX_LIMIT`: Maximum records per query (default: `1000`)

---

## Usage Examples

### Complete Workflow

1. **Sign up:**
```bash
curl -X POST http://localhost:8000/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"name": "John Doe", "email": "john@example.com"}'
```

2. **Query records:**
```bash
curl -X GET "http://localhost:8000/query?limit=50&name_like=John" \
  -H "x-api-key: your-api-key-here"
```

3. **Get single record:**
```bash
curl -X GET "http://localhost:8000/record/c0d1baa9fe8cad17eb14572336eead4e96f0f56a35c9c46d764fb6e168cddc92" \
  -H "x-api-key: your-api-key-here"
```

4. **Admin: Top up credits:**
```bash
curl -X POST "http://localhost:8000/admin/topup?user_email=john@example.com&amount=1000" \
  -H "x-admin-key: your-admin-key-here"
```

---

## Interactive API Documentation

FastAPI automatically generates interactive API documentation:

- **Swagger UI:** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`
- **OpenAPI Schema:** `http://localhost:8000/openapi.json`

You can test all endpoints directly from the Swagger UI interface.

---

## Rate Limiting

Currently, there is no rate limiting implemented. Credits serve as the primary mechanism for controlling API usage.

---

## Data Format

All record data is returned as JSON objects. The exact fields depend on the schema of the `master_records` table in ClickHouse. Common fields include:
- `canonical_key`: Unique identifier for the record
- `name`: Name field
- `email`: Email field
- Additional fields as defined in your ClickHouse schema

---

## Support

For issues or questions, please refer to the project repository or contact the development team.

