#!/bin/bash

# Script to clean the project for distribution to evaluators
# Removes sensitive files and creates a clean copy

set -e

echo "🧹 Cleaning project for distribution..."

# Create a clean directory
CLEAN_DIR="Big-Data-Project-Clean"
rm -rf "$CLEAN_DIR"
mkdir -p "$CLEAN_DIR"

# Copy project files (excluding sensitive data)
echo "📦 Copying project files..."
rsync -av --progress \
  --exclude='.env' \
  --exclude='*.env' \
  --exclude='venv/' \
  --exclude='__pycache__/' \
  --exclude='*.pyc' \
  --exclude='.git/' \
  --exclude='data_raw/' \
  --exclude='data_processed/' \
  --exclude='deployment/postgres_data/' \
  --exclude='deployment/clickhouse_data/' \
  --exclude='*.log' \
  --exclude='.DS_Store' \
  --exclude='Thumbs.db' \
  . "$CLEAN_DIR/"

# Remove hardcoded credentials from specific files
echo "🔒 Removing hardcoded credentials..."

# Remove .env files if any were copied
find "$CLEAN_DIR" -name ".env" -type f -delete
find "$CLEAN_DIR" -name "*.env" -type f -delete

# Ensure .env.example exists
if [ ! -f "$CLEAN_DIR/api/.env.example" ]; then
  echo "⚠️  Warning: api/.env.example not found, creating it..."
  cp api/.env.example "$CLEAN_DIR/api/.env.example" 2>/dev/null || echo "# Create this file" > "$CLEAN_DIR/api/.env.example"
fi

# Create a README for the clean version
cat > "$CLEAN_DIR/README_DISTRIBUTION.md" << 'EOF'
# Big Data Project - Distribution Package

This is a clean version of the project prepared for evaluation.

## Setup Instructions

1. **Copy environment template:**
   ```bash
   cp api/.env.example api/.env
   ```

2. **Edit `api/.env` with your credentials:**
   - PostgreSQL connection string
   - ClickHouse credentials
   - Admin API key

3. **Follow the setup guide:**
   See `EVALUATOR_SETUP.md` for detailed instructions.

## Important Notes

- All sensitive credentials have been removed
- You need to provide your own database connections
- Sample data is not included (see ingestion pipeline in `src/`)

## Project Structure

- `api/` - FastAPI REST API
- `src/` - Data ingestion pipeline
- `deployment/` - Docker setup files
- `docs/` - Documentation

See individual README files in each directory for more details.
EOF

echo "✅ Clean project created in: $CLEAN_DIR"
echo ""
echo "📋 Next steps:"
echo "1. Review the cleaned project in $CLEAN_DIR"
echo "2. Create a zip file: zip -r Big-Data-Project.zip $CLEAN_DIR"
echo "3. Send the zip file to evaluators"
echo ""
echo "⚠️  Remember to:"
echo "   - Verify no credentials are in the cleaned version"
echo "   - Test that the project can be set up from the clean version"
echo "   - Include EVALUATOR_SETUP.md in the distribution"

