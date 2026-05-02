from fastapi import FastAPI, Depends, Query, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
from datetime import datetime
from database import engine, SessionLocal
from models import Base, Asset, AssetType, StateOfCharge
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


@app.get("/assetslist")
def get_assets(db: Session = Depends(get_db)):
    
    # Subquery — most recent state_of_charge timestamp per asset
    latest_soc = (
        db.query(
            StateOfCharge.asset_id,
            func.max(StateOfCharge.timestamp).label("latest_ts")
        )
        .group_by(StateOfCharge.asset_id)
        .subquery()
    )

    # Join assets → latest state_of_charge row
    results = (
        db.query(Asset, StateOfCharge)
        .join(latest_soc, Asset.id == latest_soc.c.asset_id)
        .join(StateOfCharge, (StateOfCharge.asset_id == Asset.id) &
                             (StateOfCharge.timestamp == latest_soc.c.latest_ts))
        #.filter(Asset.asset_type == AssetType.BATTERY)
        .all()
    )

    return [
        {
            "id":                   asset.id,
            "asset_type":            asset.asset_type,
            "eic_code":             asset.eic_code,
            "name":                 asset.name,
            "max_capacity_mwh":     asset.max_capacity_mwh,
            "max_charge_rate_mw":   asset.max_charge_rate_mw,
            "max_discharge_rate_mw": asset.max_discharge_rate_mw,
            "reactive_power_capacity_mvar": asset.reactive_power_capacity_mvar,
            "efficiency":           asset.efficiency,
            # Live data from latest StateOfCharge
            "soc_id":               soc.id,
            "operational_mode":     soc.operational_mode.value if soc.operational_mode else None,
            "asset_status":         soc.asset_status.value if soc.asset_status else None,
            "energy_mwh":           soc.energy_mwh,
            "power_mw":             soc.power_mw,
            "reactive_power_mvar":  soc.reactive_power_mvar,
            "power_factor":         soc.power_factor,
            "last_updated":         soc.timestamp.isoformat(),
        }
        for asset, soc in results
    ]



@app.get("/assets/summary")
def get_asset_summary(db: Session = Depends(get_db)):

    # Subquery — most recent state_of_charge timestamp per asset
    latest_soc = (
        db.query(
            StateOfCharge.asset_id,
            func.max(StateOfCharge.timestamp).label("latest_ts")
        )
        .group_by(StateOfCharge.asset_id)
        .subquery()
    )

    # Join assets → latest state_of_charge row
    results = (
        db.query(Asset, StateOfCharge)
        .join(latest_soc, Asset.id == latest_soc.c.asset_id)
        .join(StateOfCharge, (StateOfCharge.asset_id == Asset.id) &
                             (StateOfCharge.timestamp == latest_soc.c.latest_ts))
        .all()
    )

    # Aggregate in Python across the latest rows
    total_power_mw        = sum(soc.power_mw or 0.0 for _, soc in results)
    total_energy_mwh      = sum(soc.energy_mwh or 0.0 for _, soc in results)
    total_reactive_mvar   = sum(soc.reactive_power_mvar or 0.0 for _, soc in results)

    # Break down by asset type
    by_type = {}
    for asset, soc in results:
        t = asset.asset_type.value
        if t not in by_type:
            by_type[t] = {"power_mw": 0.0, "energy_mwh": 0.0, "asset_count": 0}
        by_type[t]["power_mw"]    += soc.power_mw or 0.0
        by_type[t]["energy_mwh"]  += soc.energy_mwh or 0.0
        by_type[t]["asset_count"] += 1

    return {
        "total_power_mw":      round(total_power_mw, 3),
        "total_energy_mwh":    round(total_energy_mwh, 3),
        "total_reactive_mvar": round(total_reactive_mvar, 3),
        "by_asset_type": {
            "all": {
                "power_mw":    round(total_power_mw, 3),
                "energy_mwh":  round(total_energy_mwh, 3),
                "asset_count": len(results),
            },
            **{
                k: {
                    "power_mw":    round(v["power_mw"], 3),
                    "energy_mwh":  round(v["energy_mwh"], 3),
                    "asset_count": v["asset_count"],
                }
                for k, v in by_type.items()
            }
        }
    }


from typing import Optional

@app.get("/assets/{asset_id}/soc")
def get_asset_soc(
    asset_id: int,
    mode: str = Query(..., description="S for summary (latest record), D for detail (history)"),
    from_ts: Optional[str] = Query(None, description="ISO datetime start e.g. 2026-04-25T00:00:00"),
    to_ts: Optional[str] = Query(None, description="ISO datetime end e.g. 2026-05-02T23:59:59"),
    limit: int = Query(288, description="Max records in D mode — default 288 = 24hrs at 10min intervals"),
    db: Session = Depends(get_db)
):
    # Verify asset exists
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail=f"Asset {asset_id} not found")

    if mode.upper() == "S":
        record = (
            db.query(StateOfCharge)
            .filter(StateOfCharge.asset_id == asset_id)
            .order_by(StateOfCharge.timestamp.desc())
            .first()
        )
        if not record:
            raise HTTPException(status_code=404, detail=f"No state of charge records found for asset {asset_id}")

        return {
            "asset_id":         asset.id,
            "asset_name":       asset.name,
            "eic_code":         asset.eic_code,
            "asset_type":       asset.asset_type.value,
            "max_capacity_mwh": asset.max_capacity_mwh,
            "record": {
                "timestamp":           record.timestamp.isoformat(),
                "operational_mode":    record.operational_mode.value if record.operational_mode else None,
                "asset_status":        record.asset_status.value if record.asset_status else None,
                "energy_mwh":          record.energy_mwh,
                "power_mw":            record.power_mw,
                "reactive_power_mvar": record.reactive_power_mvar,
                "power_factor":        record.power_factor,
                "voltage":             record.voltage,
                "current_amps":        record.current_amps,
                "temperature_celsius": record.temperature_celsius,
            }
        }

    elif mode.upper() == "D":
        query = (
            db.query(StateOfCharge)
            .filter(StateOfCharge.asset_id == asset_id)
        )

        if from_ts:
            try:
                query = query.filter(StateOfCharge.timestamp >= datetime.fromisoformat(from_ts))
            except ValueError:
                raise HTTPException(status_code=400, detail="from_ts is not a valid ISO datetime")

        if to_ts:
            try:
                query = query.filter(StateOfCharge.timestamp <= datetime.fromisoformat(to_ts))
            except ValueError:
                raise HTTPException(status_code=400, detail="to_ts is not a valid ISO datetime")

        records = (
            query
            .order_by(StateOfCharge.timestamp.asc())
            .limit(limit)
            .all()
        )

        if not records:
            raise HTTPException(status_code=404, detail=f"No state of charge records found for asset {asset_id}")

        return {
            "asset_id":         asset.id,
            "asset_name":       asset.name,
            "eic_code":         asset.eic_code,
            "asset_type":       asset.asset_type.value,
            "max_capacity_mwh": asset.max_capacity_mwh,
            "record_count":     len(records),
            "from_ts":          records[0].timestamp.isoformat(),
            "to_ts":            records[-1].timestamp.isoformat(),
            "records": [
                {
                    "timestamp":           r.timestamp.isoformat(),
                    "operational_mode":    r.operational_mode.value if r.operational_mode else None,
                    "asset_status":        r.asset_status.value if r.asset_status else None,
                    "energy_mwh":          r.energy_mwh,
                    "power_mw":            r.power_mw,
                    "reactive_power_mvar": r.reactive_power_mvar,
                    "power_factor":        r.power_factor,
                    "voltage":             r.voltage,
                    "current_amps":        r.current_amps,
                    "temperature_celsius": r.temperature_celsius,
                }
                for r in records
            ]
        }

    else:
        raise HTTPException(status_code=400, detail="mode must be S (summary) or D (detail)")

@app.post("/llm/ask")
def ask_llm(question: str):
    return StreamingResponse(
        ask_grid_question_stream(question),
        media_type="text/plain"
    )

