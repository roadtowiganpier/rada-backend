from fastapi import FastAPI, Depends
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func
from database import engine, SessionLocal
from models import Base, Asset,  AssetType
from llm_service import ask_grid_question_stream

Base.metadata.create_all(bind=engine)
app = FastAPI(title="Grid Asset Manager API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependency to get a DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/")
def read_root():
    return {"message": "Asset Grid Manager API", "status": "running"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.get("/batteries/summary")
def get_battery_summary(db: Session = Depends(get_db)):
    rows = db.query(
        Asset.is_active,
        func.count(Asset.id),
        func.sum(Asset.capacity_mwh),
        func.sum(Asset.max_discharge_rate_mw)
    ).filter(Asset.asset_type == AssetType.BATTERY)\
    .group_by(Asset.is_active).all()

    return [
        {
            "is_active": row[0],
            "battery_count": row[1],
            "total_capacity_mwh": row[2],
            "total_max_discharge_rate_mw": row[3]
        }
        for row in rows

        
    ]


@app.get("/batteries")
def get_batteries(db: Session = Depends(get_db)):
    batteries = db.query(Asset).filter(Asset.asset_type == AssetType.BATTERY).all()
    return [
        {
            "id": b.id,
            "name": b.name,
            "capacity_mwh": b.capacity_mwh,
            "max_charge_rate_mw": b.max_charge_rate_mw,
            "is_active": b.is_active
        }
        for b in batteries
    ]

@app.post("/llm/ask")
def ask_llm(question: str):
    return StreamingResponse(
        ask_grid_question_stream(question),
        media_type="text/plain"
    )

