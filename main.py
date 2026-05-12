from fastapi import FastAPI
from routes import analytics, authors, books, formats, retail
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(analytics.router)
app.include_router(authors.router)
app.include_router(books.router)
app.include_router(formats.router)
app.include_router(retail.router)

@app.get("/")
async def index():
    return {"message": "This is index."}