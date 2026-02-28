from fastapi import FastAPI

from database import engine
from models import Base
from llm_service import ask_bess_question


Base.metadata.create_all(bind=engine)

app = FastAPI(title="BESS Grid Manager API")


@app.get("/")
def read_root():
    return {"message": "BESS Grid Manager API", "status": "running"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.post("/llm/ask")
def ask_llm(question: str):
    answer = ask_bess_question(question)
    return {"question": question, "answer": answer}