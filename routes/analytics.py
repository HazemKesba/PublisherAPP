from fastapi import APIRouter, Depends
from database import get_db
import pyodbc

router = router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/")
async def get(conn: pyodbc.Connection = Depends(get_db)):
    cursor = conn.cursor()
    cursor.execute("Select Book.isbn, "+
                   "Book.title, "+
                   "Book.genre, "+
                   "SUM([Order].quantity * (Format.price - Format.cost)) as total_price, "+
                   "SUM([Order].quantity) as total_quantity " +
                   "From Book, Format, [Order] " +
                   "Where Book.isbn = Format.isbn and Format.format_id = [Order].format_id " +
                   "Group By Book.isbn, Book.title, Book.genre " + 
                   "Order By total_price desc")
    column = [column[0] for column in cursor.description]

    result = []
    for row in cursor.fetchall():
        result.append(dict(zip(column, row)))
    
    return result