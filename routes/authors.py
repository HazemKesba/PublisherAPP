from fastapi import APIRouter, Depends, HTTPException
from database import get_db
from pydantic import BaseModel
from typing import Optional
import pyodbc

router = APIRouter(prefix="/authors", tags=["Authors"])


# ─────────────────────────────────────────────
# Pydantic Schemas (request / response bodies)
# ─────────────────────────────────────────────

class AuthorCreate(BaseModel):
    name: str
    biography: Optional[str] = None
    royalty_percentage: Optional[float] = None


class AuthorUpdate(BaseModel):
    name: Optional[str] = None
    biography: Optional[str] = None
    royalty_percentage: Optional[float] = None


# ─────────────────────────────────────────────
# Helper: map a raw DB row → dict
# ─────────────────────────────────────────────

def row_to_author(row) -> dict:
    return {
        "author_id": row[0],
        "name": row[1],
        "biography": row[2],
        "royalty_percentage": row[3],
    }


# ─────────────────────────────────────────────
# 1. CREATE — POST /authors/
# ─────────────────────────────────────────────

@router.post("/", status_code=201)
def create_author(author: AuthorCreate, conn: pyodbc.Connection = Depends(get_db)):
    """Insert a new author into the AUTHOR table."""
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO AUTHOR (NAME, BIOGRAPHY, ROYALTY_PERCENTAGE)
            VALUES (?, ?, ?)
            """,
            author.name,
            author.biography,
            author.royalty_percentage,
        )
        conn.commit()

        cursor.execute("SELECT SCOPE_IDENTITY()")
        new_id = int(cursor.fetchone()[0])

        return {"message": "Author created successfully", "author_id": new_id}

    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────
# 2. READ ALL — GET /authors/
# ─────────────────────────────────────────────

@router.get("/")
def get_all_authors(conn: pyodbc.Connection = Depends(get_db)):
    """Return every author in the database."""
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT AUTHOR_ID, NAME, BIOGRAPHY, ROYALTY_PERCENTAGE FROM AUTHOR"
        )
        rows = cursor.fetchall()
        return [row_to_author(r) for r in rows]

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────
# 3. READ ONE — GET /authors/{author_id}
# ─────────────────────────────────────────────

@router.get("/{author_id}")
def get_author(author_id: int, conn: pyodbc.Connection = Depends(get_db)):
    """Return a single author by ID."""
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT AUTHOR_ID, NAME, BIOGRAPHY, ROYALTY_PERCENTAGE
            FROM AUTHOR
            WHERE AUTHOR_ID = ?
            """,
            author_id,
        )
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Author not found")
        return row_to_author(row)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────
# 4. UPDATE — PUT /authors/{author_id}
# ─────────────────────────────────────────────

@router.put("/{author_id}")
def update_author(author_id: int, author: AuthorUpdate, conn: pyodbc.Connection = Depends(get_db)):
    """Update one or more fields of an existing author."""
    try:
        cursor = conn.cursor()

        cursor.execute(
            "SELECT AUTHOR_ID FROM AUTHOR WHERE AUTHOR_ID = ?", author_id
        )
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Author not found")

        fields, values = [], []
        if author.name is not None:
            fields.append("NAME = ?")
            values.append(author.name)
        if author.biography is not None:
            fields.append("BIOGRAPHY = ?")
            values.append(author.biography)
        if author.royalty_percentage is not None:
            fields.append("ROYALTY_PERCENTAGE = ?")
            values.append(author.royalty_percentage)

        if not fields:
            raise HTTPException(status_code=400, detail="No fields provided to update")

        values.append(author_id)
        sql = f"UPDATE AUTHOR SET {', '.join(fields)} WHERE AUTHOR_ID = ?"
        cursor.execute(sql, *values)
        conn.commit()

        return {"message": "Author updated successfully", "author_id": author_id}

    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────
# 5. DELETE — DELETE /authors/{author_id}
# ─────────────────────────────────────────────

@router.delete("/{author_id}")
def delete_author(author_id: int, conn: pyodbc.Connection = Depends(get_db)):
    """Delete an author and their entries in BOOK_AUTHOR."""
    try:
        cursor = conn.cursor()

        cursor.execute(
            "SELECT AUTHOR_ID FROM AUTHOR WHERE AUTHOR_ID = ?", author_id
        )
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Author not found")

        cursor.execute(
            "DELETE FROM BOOK_AUTHOR WHERE AUTHOR_ID = ?", author_id
        )
        cursor.execute(
            "DELETE FROM AUTHOR WHERE AUTHOR_ID = ?", author_id
        )
        conn.commit()

        return {"message": "Author deleted successfully", "author_id": author_id}

    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────
# 6. AUTHORS WITH BOOKS — GET /authors/{author_id}/books
# ─────────────────────────────────────────────

@router.get("/{author_id}/books")
def get_author_with_books(author_id: int, conn: pyodbc.Connection = Depends(get_db)):
    """Return an author together with all books they are linked to."""
    try:
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT AUTHOR_ID, NAME, BIOGRAPHY, ROYALTY_PERCENTAGE
            FROM AUTHOR
            WHERE AUTHOR_ID = ?
            """,
            author_id,
        )
        author_row = cursor.fetchone()
        if not author_row:
            raise HTTPException(status_code=404, detail="Author not found")

        author_data = row_to_author(author_row)

        cursor.execute(
            """
            SELECT B.ISBN, B.TITLE, B.GENRE, B.TARGET_AGE_GROUP
            FROM BOOK B
            INNER JOIN BOOK_AUTHOR BA ON B.ISBN = BA.ISBN
            WHERE BA.AUTHOR_ID = ?
            """,
            author_id,
        )
        books = [
            {
                "isbn": r[0],
                "title": r[1],
                "genre": r[2],
                "target_age_group": r[3],
            }
            for r in cursor.fetchall()
        ]

        author_data["books"] = books
        return author_data

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────
# 7. ALL AUTHORS WITH THEIR BOOKS — GET /authors/with-books/all
# ─────────────────────────────────────────────

@router.get("/with-books/all")
def get_all_authors_with_books(conn: pyodbc.Connection = Depends(get_db)):
    """Return every author with their associated books in one call."""
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                A.AUTHOR_ID,
                A.NAME,
                A.BIOGRAPHY,
                A.ROYALTY_PERCENTAGE,
                B.ISBN,
                B.TITLE,
                B.GENRE,
                B.TARGET_AGE_GROUP
            FROM AUTHOR A
            LEFT JOIN BOOK_AUTHOR BA ON A.AUTHOR_ID = BA.AUTHOR_ID
            LEFT JOIN BOOK B         ON BA.ISBN = B.ISBN
            ORDER BY A.AUTHOR_ID
            """
        )
        rows = cursor.fetchall()

        authors: dict = {}
        for r in rows:
            aid = r[0]
            if aid not in authors:
                authors[aid] = {
                    "author_id": r[0],
                    "name": r[1],
                    "biography": r[2],
                    "royalty_percentage": r[3],
                    "books": [],
                }
            if r[4]:
                authors[aid]["books"].append(
                    {
                        "isbn": r[4],
                        "title": r[5],
                        "genre": r[6],
                        "target_age_group": r[7],
                    }
                )

        return list(authors.values())

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))