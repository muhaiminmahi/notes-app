import hmac
import secrets
import hashlib
import os
import sqlite3
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
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
	    user_id INTEGER NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL
        )
        """
    )


    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS sessions (
            token TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
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

class UserIn(BaseModel):
    username: str
    password: str


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)
    return salt.hex() + ":" + digest.hex()

def verify_password(password: str, stored: str) -> bool:
    salt_hex, digest_hex = stored.split(":")
    salt = bytes.fromhex(salt_hex)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)
    return hmac.compare_digest(digest.hex(), digest_hex)

bearer = HTTPBearer()


def get_current_user(
    creds: HTTPAuthorizationCredentials = Depends(bearer),
) -> int:
    conn = get_connection()
    row = conn.execute(
        "SELECT user_id FROM sessions WHERE token = ?", (creds.credentials,)
    ).fetchone()
    conn.close()
    if row is None:
        raise HTTPException(status_code=401, detail="Invalid or missing token")
    return row["user_id"]



@app.get("/")
async def root():
    return {"message": "Hello Mahi"}


@app.post("/notes", status_code=status.HTTP_201_CREATED)
def create_note(note: NoteIn, user_id: int = Depends(get_current_user)):
    conn = get_connection()
    cursor = conn.execute(
        "INSERT INTO notes (title, content, user_id) VALUES (?, ?, ?)",
        (note.title, note.content, user_id),
    )
    conn.commit()
    row = conn.execute(
        "SELECT * FROM notes WHERE id = ?", (cursor.lastrowid,)
    ).fetchone()
    conn.close()
    return dict(row)


@app.get("/notes")
def list_notes(user_id: int = Depends(get_current_user)):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM notes WHERE user_id = ? ORDER BY id", (user_id,)
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


@app.get("/notes/{note_id}")
def get_note(note_id: int, user_id: int = Depends(get_current_user)):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM notes WHERE id = ? AND user_id = ?", (note_id, user_id)
    ).fetchone()
    conn.close()
    if row is None:
        raise HTTPException(status_code=404, detail="Note not found")
    return dict(row)


@app.put("/notes/{note_id}")
def update_note(
    note_id: int, note: NoteIn, user_id: int = Depends(get_current_user)
):
    conn = get_connection()
    cursor = conn.execute(
        "UPDATE notes SET title = ?, content = ? WHERE id = ? AND user_id = ?",
        (note.title, note.content, note_id, user_id),
    )
    conn.commit()
    changed = cursor.rowcount
    row = conn.execute(
        "SELECT * FROM notes WHERE id = ? AND user_id = ?", (note_id, user_id)
    ).fetchone()
    conn.close()
    if changed == 0:
        raise HTTPException(status_code=404, detail="Note not found")
    return dict(row)


@app.delete("/notes/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_note(note_id: int, user_id: int = Depends(get_current_user)):
    conn = get_connection()
    cursor = conn.execute(
        "DELETE FROM notes WHERE id = ? AND user_id = ?", (note_id, user_id)
    )
    conn.commit()
    deleted = cursor.rowcount
    conn.close()
    if deleted == 0:
        raise HTTPException(status_code=404, detail="Note not found")


@app.post("/register", status_code=status.HTTP_201_CREATED)
def register(user: UserIn):
    conn = get_connection()
    try:
        cursor = conn.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (user.username, hash_password(user.password)),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        raise HTTPException(status_code=409, detail="Username already taken")
    user_id = cursor.lastrowid
    conn.close()
    return {"id": user_id, "username": user.username}


@app.post("/login")
def login(user: UserIn):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM users WHERE username = ?", (user.username,)
    ).fetchone()
    if row is None or not verify_password(user.password, row["password_hash"]):
        conn.close()
        raise HTTPException(status_code=401, detail="Invalid username or password")
    token = secrets.token_urlsafe(32)
    conn.execute(
        "INSERT INTO sessions (token, user_id) VALUES (?, ?)", (token, row["id"])
    )
    conn.commit()
    conn.close()
    return {"access_token": token, "token_type": "bearer"}

