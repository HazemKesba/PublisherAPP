from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from typing import Optional
import pyodbc

from database import get_db

router = APIRouter()


# ── Schemas ───────────────────────────────────────────────────────────────────

class BookCreate(BaseModel):
    isbn: str = Field(..., min_length=10, max_length=20)
    title: str = Field(..., min_length=1, max_length=200)
    genre: str = Field(..., max_length=50)
    target_age_group: Optional[str] = Field(None, max_length=50)
    author_ids: list[int] = Field(..., min_length=1)


class BookUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    genre: Optional[str] = Field(None, max_length=50)
    target_age_group: Optional[str] = Field(None, max_length=50)
    author_ids: Optional[list[int]] = Field(None, min_length=1)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _fetch_book_by_isbn(cursor, isbn: str) -> dict:
    """Returns book dict with its authors list, or raises 404."""
    cursor.execute("""
        SELECT ISBN, TITLE, GENRE, TARGET_AGE_GROUP
        FROM BOOK
        WHERE ISBN = ?
    """, isbn)
    row = cursor.fetchone()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Book with ISBN '{isbn}' not found."
        )

    book = {
        "isbn":             row[0],
        "title":            row[1],
        "genre":            row[2],
        "target_age_group": row[3],
        "authors":          []
    }

    cursor.execute("""
        SELECT a.AUTHOR_ID, a.NAME
        FROM AUTHOR a
        INNER JOIN BOOK_AUTHOR ba ON a.AUTHOR_ID = ba.AUTHOR_ID
        WHERE ba.ISBN = ?
    """, isbn)
    book["authors"] = [{"author_id": r[0], "name": r[1]} for r in cursor.fetchall()]
    return book


def _validate_authors_exist(cursor, author_ids: list[int]):
    """Raises 422 if any author_id doesn't exist in AUTHOR table."""
    placeholders = ",".join("?" * len(author_ids))
    cursor.execute(
        f"SELECT AUTHOR_ID FROM AUTHOR WHERE AUTHOR_ID IN ({placeholders})",
        *author_ids
    )
    found = {row[0] for row in cursor.fetchall()}
    missing = set(author_ids) - found
    if missing:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Author IDs not found: {sorted(missing)}"
        )


def _sync_book_authors(cursor, isbn: str, author_ids: list[int]):
    """Replaces all BOOK_AUTHOR rows for this ISBN."""
    cursor.execute("DELETE FROM BOOK_AUTHOR WHERE ISBN = ?", isbn)
    for author_id in set(author_ids):
        cursor.execute(
            "INSERT INTO BOOK_AUTHOR (AUTHOR_ID, ISBN) VALUES (?, ?)",
            author_id, isbn
        )


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/")
def list_books(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    genre: Optional[str] = Query(None, description="Filter by genre (partial match)"),
    author_id: Optional[int] = Query(None, description="Filter by author ID"),
    db: pyodbc.Connection = Depends(get_db)
):
    cursor = db.cursor()

    base_query = """
        SELECT DISTINCT b.ISBN, b.TITLE, b.GENRE, b.TARGET_AGE_GROUP
        FROM BOOK b
    """
    conditions = []
    params = []

    if author_id:
        base_query += " INNER JOIN BOOK_AUTHOR ba ON b.ISBN = ba.ISBN"
        conditions.append("ba.AUTHOR_ID = ?")
        params.append(author_id)

    if genre:
        conditions.append("b.GENRE LIKE ?")
        params.append(f"%{genre}%")

    if conditions:
        base_query += " WHERE " + " AND ".join(conditions)

    # Total count
    cursor.execute(f"SELECT COUNT(*) FROM ({base_query}) AS sub", *params)
    total = cursor.fetchone()[0]

    # Paginated results
    paged_query = base_query + " ORDER BY b.ISBN OFFSET ? ROWS FETCH NEXT ? ROWS ONLY"
    cursor.execute(paged_query, *params, skip, limit)
    rows = cursor.fetchall()

    books = []
    for row in rows:
        book = {
            "isbn":             row[0],
            "title":            row[1],
            "genre":            row[2],
            "target_age_group": row[3],
            "authors":          []
        }
        cursor.execute("""
            SELECT a.AUTHOR_ID, a.NAME
            FROM AUTHOR a
            INNER JOIN BOOK_AUTHOR ba ON a.AUTHOR_ID = ba.AUTHOR_ID
            WHERE ba.ISBN = ?
        """, row[0])
        book["authors"] = [{"author_id": r[0], "name": r[1]} for r in cursor.fetchall()]
        books.append(book)

    return {"total": total, "books": books}


@router.get("/{isbn}")
def get_book(isbn: str, db: pyodbc.Connection = Depends(get_db)):
    cursor = db.cursor()
    return _fetch_book_by_isbn(cursor, isbn)


@router.post("/", status_code=status.HTTP_201_CREATED)
def create_book(payload: BookCreate, db: pyodbc.Connection = Depends(get_db)):
    cursor = db.cursor()

    # 1. Validate all authors exist first
    _validate_authors_exist(cursor, payload.author_ids)

    # 2. Check ISBN uniqueness
    cursor.execute("SELECT ISBN FROM BOOK WHERE ISBN = ?", payload.isbn)
    if cursor.fetchone():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Book with ISBN '{payload.isbn}' already exists."
        )

    # 3. Insert the book
    cursor.execute("""
        INSERT INTO BOOK (ISBN, TITLE, GENRE, TARGET_AGE_GROUP)
        VALUES (?, ?, ?, ?)
    """, payload.isbn, payload.title, payload.genre, payload.target_age_group)

    # 4. Link authors in BOOK_AUTHOR
    _sync_book_authors(cursor, payload.isbn, payload.author_ids)

    db.commit()
    return _fetch_book_by_isbn(cursor, payload.isbn)


@router.patch("/{isbn}")
def update_book(isbn: str, payload: BookUpdate, db: pyodbc.Connection = Depends(get_db)):
    cursor = db.cursor()

    # Make sure book exists
    cursor.execute("SELECT ISBN FROM BOOK WHERE ISBN = ?", isbn)
    if not cursor.fetchone():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Book with ISBN '{isbn}' not found."
        )

    # Validate new authors if provided
    if payload.author_ids is not None:
        _validate_authors_exist(cursor, payload.author_ids)

    # Build SET clause from provided fields only
    fields = {
        "TITLE":            payload.title,
        "GENRE":            payload.genre,
        "TARGET_AGE_GROUP": payload.target_age_group,
    }
    updates = {k: v for k, v in fields.items() if v is not None}

    if updates:
        set_clause = ", ".join(f"{col} = ?" for col in updates)
        cursor.execute(
            f"UPDATE BOOK SET {set_clause} WHERE ISBN = ?",
            *updates.values(), isbn
        )

    # Replace authors if provided
    if payload.author_ids is not None:
        _sync_book_authors(cursor, isbn, payload.author_ids)

    db.commit()
    return _fetch_book_by_isbn(cursor, isbn)


@router.delete("/{isbn}", status_code=status.HTTP_204_NO_CONTENT)
def delete_book(isbn: str, db: pyodbc.Connection = Depends(get_db)):
    cursor = db.cursor()

    cursor.execute("SELECT ISBN FROM BOOK WHERE ISBN = ?", isbn)
    if not cursor.fetchone():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Book with ISBN '{isbn}' not found."
        )

    # Delete BOOK_AUTHOR first (FK), then BOOK
    cursor.execute("DELETE FROM BOOK_AUTHOR WHERE ISBN = ?", isbn)
    cursor.execute("DELETE FROM BOOK WHERE ISBN = ?", isbn)
    db.commit()