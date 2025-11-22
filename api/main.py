from fastapi import FastAPI
from api.routes import query, record, admin, auth
from api.deps.clickhouse import get_clickhouse_client

app = FastAPI(title="BigData Credit API")

# include routers
app.include_router(query.router)
app.include_router(record.router)
app.include_router(admin.router)
app.include_router(auth.router)

@app.get("/health")
async def health():
    ch = get_clickhouse_client()
    return {"ok": True, "clickhouse_ping": ch.ping()}
