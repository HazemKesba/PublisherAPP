from database import get_connection, close_connection
from fastapi import FastAPI
from contextlib import asynccontextmanager
from routes import analytics, authors, books, formats, retail

@asynccontextmanager
async def lifespan(app: FastAPI):
    get_connection()
    yield
    close_connection()

app = FastAPI(lifespan=lifespan)

app.include_router(analytics.router, prefix="/analytics")
app.include_router(authors.router, prefix="/authors")
app.include_router(books.router, prefix="/books")
app.include_router(formats.router, prefix="/formats")
app.include_router(retail.router, prefix="/retail")

@app.get("/")
async def index():
    return { "message": "This is index." }