from fastapi import APIRouter, Depends, HTTPException
from database import get_db
from pydantic import BaseModel, field_validator
from decimal import Decimal
import pyodbc

router = APIRouter()

# ─── Schemas ────────────────────────────────────────────────────────────────

VALID_TYPES = {"Hardcover", "Paperback", "E-book", "Audiobook"}

class FormatCreate(BaseModel):
    isbn: str
    cost: Decimal
    price: Decimal
    type: str

    @field_validator("type")
    @classmethod
    def validate_type(cls, v):
        if v not in VALID_TYPES:
            raise ValueError(f"type must be one of: {', '.join(VALID_TYPES)}")
        return v

    @field_validator("cost", "price")
    @classmethod
    def validate_positive(cls, v):
        if v <= 0:
            raise ValueError("cost and price must be greater than 0")
        return v


class FormatUpdate(BaseModel):
    cost: Decimal | None = None
    price: Decimal | None = None
    type: str | None = None

    @field_validator("type")
    @classmethod
    def validate_type(cls, v):
        if v is not None and v not in VALID_TYPES:
            raise ValueError(f"type must be one of: {', '.join(VALID_TYPES)}")
        return v

    @field_validator("cost", "price")
    @classmethod
    def validate_positive(cls, v):
        if v is not None and v <= 0:
            raise ValueError("cost and price must be greater than 0")
        return v


# ─── Helpers ────────────────────────────────────────────────────────────────

def row_to_dict(row):
    return {
        "format_id": row.FORMAT_ID,
        "isbn":      row.ISBN,
        "cost":      float(row.COST),
        "price":     float(row.PRICE),
        "type":      row.TYPE,
    }


def book_exists(conn: pyodbc.Connection, isbn: str) -> bool:
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM BOOK WHERE ISBN = ?", isbn)
    return cursor.fetchone() is not None

def format_exists(conn: pyodbc.Connection, format_id: int) -> bool:
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM FORMAT WHERE FORMAT_ID = ?", format_id)
    return cursor.fetchone() is not None


# ─── Routes ─────────────────────────────────────────────────────────────────

@router.get("/")
async def get_all_formats(conn: pyodbc.Connection = Depends(get_db)):
    """Get all formats, joined with book title."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT f.FORMAT_ID, f.ISBN, f.COST, f.PRICE, f.TYPE, b.TITLE
        FROM FORMAT f
        JOIN BOOK b ON f.ISBN = b.ISBN
        ORDER BY f.FORMAT_ID
    """)
    rows = cursor.fetchall()
    return [
        {
            "format_id":  r.FORMAT_ID,
            "isbn":       r.ISBN,
            "book_title": r.TITLE,
            "cost":       float(r.COST),
            "price":      float(r.PRICE),
            "type":       r.TYPE,
            "margin":     round(float(r.PRICE) - float(r.COST), 2),
        }
        for r in rows
    ]


@router.get("/{format_id}")
async def get_format(format_id: int, conn: pyodbc.Connection = Depends(get_db)):
    """Get a single format by ID."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT f.FORMAT_ID, f.ISBN, f.COST, f.PRICE, f.TYPE, b.TITLE
        FROM FORMAT f
        JOIN BOOK b ON f.ISBN = b.ISBN
        WHERE f.FORMAT_ID = ?
    """, format_id)
    row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail=f"Format {format_id} not found")
    return {
        "format_id":  row.FORMAT_ID,
        "isbn":       row.ISBN,
        "book_title": row.TITLE,
        "cost":       float(row.COST),
        "price":      float(row.PRICE),
        "type":       row.TYPE,
        "margin":     round(float(row.PRICE) - float(row.COST), 2),
    }


@router.get("/book/{isbn}")
async def get_formats_by_book(isbn: str, conn: pyodbc.Connection = Depends(get_db)):
    """Get all formats for a specific book by ISBN."""
    if not book_exists(conn, isbn):
        raise HTTPException(status_code=404, detail=f"Book with ISBN '{isbn}' not found")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT FORMAT_ID, ISBN, COST, PRICE, TYPE
        FROM FORMAT
        WHERE ISBN = ?
        ORDER BY TYPE
    """, isbn)
    rows = cursor.fetchall()
    return [row_to_dict(r) for r in rows]


@router.post("/", status_code=201)
async def create_format(payload: FormatCreate, conn: pyodbc.Connection = Depends(get_db)):
    """
    Add a new format for an existing book.
    A book cannot have two formats of the same type.
    """
    if not book_exists(conn, payload.isbn):
        raise HTTPException(status_code=404, detail=f"Book with ISBN '{payload.isbn}' not found")

    cursor = conn.cursor()
    cursor.execute(
        "SELECT 1 FROM FORMAT WHERE ISBN = ? AND TYPE = ?",
        payload.isbn, payload.type
    )
    if cursor.fetchone():
        raise HTTPException(
            status_code=409,
            detail=f"A '{payload.type}' format already exists for this book"
        )

    cursor.execute(
        "INSERT INTO FORMAT (ISBN, COST, PRICE, TYPE) VALUES (?, ?, ?, ?)",
        payload.isbn, payload.cost, payload.price, payload.type
    )
    cursor.execute("SELECT SCOPE_IDENTITY()")
    new_id = int(cursor.fetchone()[0])
    conn.commit()
    return {"message": "Format created successfully", "format_id": new_id}

@router.put("/{format_id}")
async def update_format(
    format_id: int,
    payload: FormatUpdate,
    conn: pyodbc.Connection = Depends(get_db)
):
    """Update cost, price, and/or type of a format."""
    if not format_exists(conn, format_id):
        raise HTTPException(status_code=404, detail=f"Format {format_id} not found")

    updates = []
    values = []

    if payload.cost is not None:
        updates.append("COST = ?")
        values.append(payload.cost)
    if payload.price is not None:
        updates.append("PRICE = ?")
        values.append(payload.price)
    if payload.type is not None:
        updates.append("TYPE = ?")
        values.append(payload.type)

    if not updates:
        raise HTTPException(status_code=400, detail="No fields provided to update")

    values.append(format_id)
    cursor = conn.cursor()
    cursor.execute(
        f"UPDATE FORMAT SET {', '.join(updates)} WHERE FORMAT_ID = ?",
        *values
    )
    conn.commit()
    return {"message": "Format updated successfully"}


@router.delete("/{format_id}")
async def delete_format(format_id: int, conn: pyodbc.Connection = Depends(get_db)):
    """
    Delete a format.
    Fails if existing orders reference this format.
    """
    if not format_exists(conn, format_id):
        raise HTTPException(status_code=404, detail=f"Format {format_id} not found")

    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM [ORDER] WHERE FORMAT_ID = ?", format_id)
    order_count = cursor.fetchone()[0]
    if order_count > 0:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot delete: {order_count} order(s) reference this format"
        )

    cursor.execute("DELETE FROM FORMAT WHERE FORMAT_ID = ?", format_id)
    conn.commit()
    return {"message": "Format deleted successfully"}