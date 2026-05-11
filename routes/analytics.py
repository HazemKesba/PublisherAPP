from fastapi import APIRouter, Depends
from database import get_db
import pyodbc

router = APIRouter()
# غيّره لـ
router = APIRouter(prefix="/analytics", tags=["Analytics"])
@router.get("/")
async def get(conn: pyodbc.Connection = Depends(get_db)):
    return { "message": "running" }