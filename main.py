import sqlite3
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

DB_PATH = "notes.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.commit()
    conn.close()


init_db()

class NoteIn(BaseModel):
    title: str
    content: str



@app.get("/")
async def root():
    return {"message": "Hello Mahi"}
