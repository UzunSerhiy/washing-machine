from fastapi import FastAPI
from sqlalchemy import text

from app.db.database import AsyncSessionLocal


app = FastAPI(
    title="Washing Machine",
    version="0.1.0",
)


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.get("/api/health/db")
async def health_db():
    async with AsyncSessionLocal() as session:
        result = await session.execute(text("SELECT 1"))
    return {"status": "ok", "database": result.scalar()}
