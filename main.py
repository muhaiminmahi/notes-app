from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()



class NoteIn(BaseModel):
    title: str
    content: str



@app.get("/")
async def root():
    return {"message": "Hello Mahi"}
