from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "BESS Grid Manager API", "status": "running"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}