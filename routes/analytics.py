from fastapi import APIRouter, Depends
from database import get_db
import pyodbc

router = APIRouter()

@router.get("/")
async def get(conn: pyodbc.Connection = Depends(get_db)):
    return { "message": conn }