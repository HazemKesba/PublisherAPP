from fastapi import FastAPI
from routes import analytics, authors, books, formats, retail

app = FastAPI()


app.include_router(analytics.router)
app.include_router(authors.router)
app.include_router(books.router)
app.include_router(formats.router)
app.include_router(retail.router)

@app.get("/")
async def index():
    return {"message": "This is index."}