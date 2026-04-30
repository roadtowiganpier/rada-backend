"""
seed_data.py
Drops and recreates all tables, then populates 30 days of realistic
grid-scale historical data.

Assets modelled:
  - 30 x Battery BESS units (real-world manufacturers)
  -  9 x Solar farms (park as single asset, one grid connection)
  -  9 x Wind farms (cluster as single asset, one grid connection)

History depth:
  - state_of_charge   : every 10 min  × 30 days = 4,320 records per active battery
  - asset_telemetry   : every hour    × 30 days =   720 records per asset
  - dispatch_commands : 1–3 per day   × 30 days =  ~60  records per active asset
  - grid_signals      : every 5 min   × 30 days = 8,640 records

Units: MW and MWh throughout (grid-scale standard).

Usage:
    Delete grid_assets.db if it exists, then:
    python seed_data.py
"""

import sys
import os
import math
import random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import Base, engine, SessionLocal
from models import (
    Asset, AssetType, DischargeType,
    StateOfCharge, AssetTelemetry,
    DispatchCommand, GridSignal,
)
from datetime import datetime, timezone, timedelta

# ── Reproducible randomness ───────────────────────────────────────────────────
random.seed(42)

# ── Helpers ───────────────────────────────────────────────────────────────────

def utcnow() -> datetime:
    return datetime.now(timezone.utc)

def clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))

# Daylight generation profile — fraction of peak MW per hour of day
SOLAR_PROFILE = [
    0.00, 0.00, 0.00, 0.00, 0.00, 0.00,
    0.04, 0.15, 0.37, 0.60, 0.80, 0.96,
    1.00, 0.98, 0.92, 0.83, 0.68, 0.48,
    0.26, 0.10, 0.02, 0.00, 0.00, 0.00,
]

# ── 1. Recreate all tables ────────────────────────────────────────────────────
print("Dropping and recreating all tables...")
Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)
print("Tables created.\n")

# ── 2. Assets ─────────────────────────────────────────────────────────────────

batteries = [
    # Tesla Megapack 2 XL
    Asset(asset_type=AssetType.BATTERY, name="Tesla Megapack 2 XL - Unit 01",         capacity_mwh=4.0,   max_charge_rate_mw=1.9,   max_discharge_rate_mw=1.9,   efficiency=0.94, is_active=True,  discharge_charge=DischargeType.DISCHARGE),
    Asset(asset_type=AssetType.BATTERY, name="Tesla Megapack 2 XL - Unit 02",         capacity_mwh=4.0,   max_charge_rate_mw=1.9,   max_discharge_rate_mw=1.9,   efficiency=0.94, is_active=True,  discharge_charge=DischargeType.CHARGE),
    Asset(asset_type=AssetType.BATTERY, name="Tesla Megapack 2 XL - Unit 03",         capacity_mwh=4.0,   max_charge_rate_mw=1.9,   max_discharge_rate_mw=1.9,   efficiency=0.94, is_active=False, discharge_charge=DischargeType.HOLD),
    # Fluence Gridstack Pro
    Asset(asset_type=AssetType.BATTERY, name="Fluence Gridstack Pro - Unit 01",       capacity_mwh=2.0,   max_charge_rate_mw=1.0,   max_discharge_rate_mw=1.0,   efficiency=0.95, is_active=True,  discharge_charge=DischargeType.DISCHARGE),
    Asset(asset_type=AssetType.BATTERY, name="Fluence Gridstack Pro - Unit 02",       capacity_mwh=2.0,   max_charge_rate_mw=1.0,   max_discharge_rate_mw=1.0,   efficiency=0.95, is_active=True,  discharge_charge=DischargeType.CHARGE),
    Asset(asset_type=AssetType.BATTERY, name="Fluence Gridstack Pro - Unit 03",       capacity_mwh=2.0,   max_charge_rate_mw=1.0,   max_discharge_rate_mw=1.0,   efficiency=0.95, is_active=False, discharge_charge=DischargeType.HOLD),
    # Sungrow PowerTitan
    Asset(asset_type=AssetType.BATTERY, name="Sungrow PowerTitan ST2236UX - Unit 01", capacity_mwh=2.236, max_charge_rate_mw=1.0,   max_discharge_rate_mw=1.0,   efficiency=0.95, is_active=True,  discharge_charge=DischargeType.DISCHARGE),
    Asset(asset_type=AssetType.BATTERY, name="Sungrow PowerTitan ST2236UX - Unit 02", capacity_mwh=2.236, max_charge_rate_mw=1.0,   max_discharge_rate_mw=1.0,   efficiency=0.95, is_active=True,  discharge_charge=DischargeType.HOLD),
    Asset(asset_type=AssetType.BATTERY, name="Sungrow PowerTitan ST2236UX - Unit 03", capacity_mwh=2.236, max_charge_rate_mw=1.0,   max_discharge_rate_mw=1.0,   efficiency=0.95, is_active=False, discharge_charge=DischargeType.HOLD),
    # BYD MC-Cube
    Asset(asset_type=AssetType.BATTERY, name="BYD MC-Cube - Unit 01",                 capacity_mwh=1.672, max_charge_rate_mw=0.836, max_discharge_rate_mw=0.836, efficiency=0.96, is_active=True,  discharge_charge=DischargeType.DISCHARGE),
    Asset(asset_type=AssetType.BATTERY, name="BYD MC-Cube - Unit 02",                 capacity_mwh=1.672, max_charge_rate_mw=0.836, max_discharge_rate_mw=0.836, efficiency=0.96, is_active=True,  discharge_charge=DischargeType.CHARGE),
    Asset(asset_type=AssetType.BATTERY, name="BYD MC-Cube - Unit 03",                 capacity_mwh=1.672, max_charge_rate_mw=0.836, max_discharge_rate_mw=0.836, efficiency=0.96, is_active=True,  discharge_charge=DischargeType.DISCHARGE),
    # Wartsila GridSolv Quantum
    Asset(asset_type=AssetType.BATTERY, name="Wartsila GridSolv Quantum - Unit 01",   capacity_mwh=1.12,  max_charge_rate_mw=0.56,  max_discharge_rate_mw=0.56,  efficiency=0.96, is_active=True,  discharge_charge=DischargeType.CHARGE),
    Asset(asset_type=AssetType.BATTERY, name="Wartsila GridSolv Quantum - Unit 02",   capacity_mwh=1.12,  max_charge_rate_mw=0.56,  max_discharge_rate_mw=0.56,  efficiency=0.96, is_active=True,  discharge_charge=DischargeType.DISCHARGE),
    Asset(asset_type=AssetType.BATTERY, name="Wartsila GridSolv Quantum - Unit 03",   capacity_mwh=1.12,  max_charge_rate_mw=0.56,  max_discharge_rate_mw=0.56,  efficiency=0.94, is_active=False, discharge_charge=DischargeType.HOLD),
    # GE Reservoir
    Asset(asset_type=AssetType.BATTERY, name="GE Reservoir - Unit 01",                capacity_mwh=4.0,   max_charge_rate_mw=2.0,   max_discharge_rate_mw=2.0,   efficiency=0.94, is_active=True,  discharge_charge=DischargeType.DISCHARGE),
    Asset(asset_type=AssetType.BATTERY, name="GE Reservoir - Unit 02",                capacity_mwh=4.0,   max_charge_rate_mw=2.0,   max_discharge_rate_mw=2.0,   efficiency=0.94, is_active=True,  discharge_charge=DischargeType.CHARGE),
    Asset(asset_type=AssetType.BATTERY, name="GE Reservoir - Unit 03",                capacity_mwh=4.0,   max_charge_rate_mw=2.0,   max_discharge_rate_mw=2.0,   efficiency=0.94, is_active=False, discharge_charge=DischargeType.HOLD),
    # CATL EnerC
    Asset(asset_type=AssetType.BATTERY, name="CATL EnerC - Unit 01",                  capacity_mwh=1.5,   max_charge_rate_mw=0.75,  max_discharge_rate_mw=0.75,  efficiency=0.95, is_active=True,  discharge_charge=DischargeType.DISCHARGE),
    Asset(asset_type=AssetType.BATTERY, name="CATL EnerC - Unit 02",                  capacity_mwh=1.5,   max_charge_rate_mw=0.75,  max_discharge_rate_mw=0.75,  efficiency=0.95, is_active=True,  discharge_charge=DischargeType.CHARGE),
    Asset(asset_type=AssetType.BATTERY, name="CATL EnerC - Unit 03",                  capacity_mwh=1.5,   max_charge_rate_mw=0.75,  max_discharge_rate_mw=0.75,  efficiency=0.95, is_active=False, discharge_charge=DischargeType.HOLD),
    # Stem Athena
    Asset(asset_type=AssetType.BATTERY, name="Stem Athena - Unit 01",                 capacity_mwh=1.0,   max_charge_rate_mw=0.5,   max_discharge_rate_mw=0.5,   efficiency=0.95, is_active=True,  discharge_charge=DischargeType.DISCHARGE),
    Asset(asset_type=AssetType.BATTERY, name="Stem Athena - Unit 02",                 capacity_mwh=1.0,   max_charge_rate_mw=0.5,   max_discharge_rate_mw=0.5,   efficiency=0.94, is_active=True,  discharge_charge=DischargeType.CHARGE),
    Asset(asset_type=AssetType.BATTERY, name="Stem Athena - Unit 03",                 capacity_mwh=1.0,   max_charge_rate_mw=0.5,   max_discharge_rate_mw=0.5,   efficiency=0.94, is_active=True,  discharge_charge=DischargeType.DISCHARGE),
    # Hitachi Energy Gridscale G2
    Asset(asset_type=AssetType.BATTERY, name="Hitachi Energy Gridscale G2 - Unit 01", capacity_mwh=1.2,   max_charge_rate_mw=0.6,   max_discharge_rate_mw=0.6,   efficiency=0.94, is_active=True,  discharge_charge=DischargeType.DISCHARGE),
    Asset(asset_type=AssetType.BATTERY, name="Hitachi Energy Gridscale G2 - Unit 02", capacity_mwh=1.2,   max_charge_rate_mw=0.6,   max_discharge_rate_mw=0.6,   efficiency=0.94, is_active=True,  discharge_charge=DischargeType.CHARGE),
    Asset(asset_type=AssetType.BATTERY, name="Hitachi Energy Gridscale G2 - Unit 03", capacity_mwh=1.2,   max_charge_rate_mw=0.6,   max_discharge_rate_mw=0.6,   efficiency=0.93, is_active=False, discharge_charge=DischargeType.HOLD),
    # Powin Stack750
    Asset(asset_type=AssetType.BATTERY, name="Powin Stack750 - Unit 01",              capacity_mwh=3.0,   max_charge_rate_mw=1.5,   max_discharge_rate_mw=1.5,   efficiency=0.95, is_active=True,  discharge_charge=DischargeType.DISCHARGE),
    Asset(asset_type=AssetType.BATTERY, name="Powin Stack750 - Unit 02",              capacity_mwh=3.0,   max_charge_rate_mw=1.5,   max_discharge_rate_mw=1.5,   efficiency=0.95, is_active=True,  discharge_charge=DischargeType.CHARGE),
    Asset(asset_type=AssetType.BATTERY, name="Powin Stack750 - Unit 03",              capacity_mwh=3.0,   max_charge_rate_mw=1.5,   max_discharge_rate_mw=1.5,   efficiency=0.95, is_active=False, discharge_charge=DischargeType.HOLD),
]

solar_assets = [
    Asset(asset_type=AssetType.SOLAR, name="Parc Solaire Provence — Site A",      capacity_mwh=0.0, max_charge_rate_mw=0.0, max_discharge_rate_mw=50.0,  efficiency=0.97, is_active=True,  discharge_charge=DischargeType.DISCHARGE),
    Asset(asset_type=AssetType.SOLAR, name="Parc Solaire Provence — Site B",      capacity_mwh=0.0, max_charge_rate_mw=0.0, max_discharge_rate_mw=45.0,  efficiency=0.97, is_active=True,  discharge_charge=DischargeType.DISCHARGE),
    Asset(asset_type=AssetType.SOLAR, name="Parc Solaire Provence — Site C",      capacity_mwh=0.0, max_charge_rate_mw=0.0, max_discharge_rate_mw=38.0,  efficiency=0.96, is_active=True,  discharge_charge=DischargeType.DISCHARGE),
    Asset(asset_type=AssetType.SOLAR, name="Parc Solaire Aquitaine — Site A",     capacity_mwh=0.0, max_charge_rate_mw=0.0, max_discharge_rate_mw=32.0,  efficiency=0.97, is_active=True,  discharge_charge=DischargeType.DISCHARGE),
    Asset(asset_type=AssetType.SOLAR, name="Parc Solaire Aquitaine — Site B",     capacity_mwh=0.0, max_charge_rate_mw=0.0, max_discharge_rate_mw=28.0,  efficiency=0.97, is_active=True,  discharge_charge=DischargeType.DISCHARGE),
    Asset(asset_type=AssetType.SOLAR, name="Parc Solaire Aquitaine — Site C",     capacity_mwh=0.0, max_charge_rate_mw=0.0, max_discharge_rate_mw=22.0,  efficiency=0.96, is_active=False, discharge_charge=DischargeType.HOLD),
    Asset(asset_type=AssetType.SOLAR, name="Toiture Industrielle Lyon — Zone A",  capacity_mwh=0.0, max_charge_rate_mw=0.0, max_discharge_rate_mw=8.5,   efficiency=0.96, is_active=True,  discharge_charge=DischargeType.CURTAIL),
    Asset(asset_type=AssetType.SOLAR, name="Toiture Industrielle Lyon — Zone B",  capacity_mwh=0.0, max_charge_rate_mw=0.0, max_discharge_rate_mw=7.2,   efficiency=0.96, is_active=True,  discharge_charge=DischargeType.DISCHARGE),
    Asset(asset_type=AssetType.SOLAR, name="Toiture Industrielle Marseille",      capacity_mwh=0.0, max_charge_rate_mw=0.0, max_discharge_rate_mw=12.0,  efficiency=0.97, is_active=True,  discharge_charge=DischargeType.DISCHARGE),
]

wind_assets = [
    Asset(asset_type=AssetType.WIND, name="Parc Éolien Normandie — Cluster 1",    capacity_mwh=0.0, max_charge_rate_mw=0.0, max_discharge_rate_mw=120.0, efficiency=0.96, is_active=True,  discharge_charge=DischargeType.DISCHARGE),
    Asset(asset_type=AssetType.WIND, name="Parc Éolien Normandie — Cluster 2",    capacity_mwh=0.0, max_charge_rate_mw=0.0, max_discharge_rate_mw=95.0,  efficiency=0.96, is_active=True,  discharge_charge=DischargeType.DISCHARGE),
    Asset(asset_type=AssetType.WIND, name="Parc Éolien Normandie — Cluster 3",    capacity_mwh=0.0, max_charge_rate_mw=0.0, max_discharge_rate_mw=80.0,  efficiency=0.95, is_active=False, discharge_charge=DischargeType.HOLD),
    Asset(asset_type=AssetType.WIND, name="Parc Éolien Bretagne — Cluster 1",     capacity_mwh=0.0, max_charge_rate_mw=0.0, max_discharge_rate_mw=80.0,  efficiency=0.96, is_active=True,  discharge_charge=DischargeType.DISCHARGE),
    Asset(asset_type=AssetType.WIND, name="Parc Éolien Bretagne — Cluster 2",     capacity_mwh=0.0, max_charge_rate_mw=0.0, max_discharge_rate_mw=65.0,  efficiency=0.96, is_active=True,  discharge_charge=DischargeType.DISCHARGE),
    Asset(asset_type=AssetType.WIND, name="Parc Éolien Bretagne — Cluster 3",     capacity_mwh=0.0, max_charge_rate_mw=0.0, max_discharge_rate_mw=55.0,  efficiency=0.95, is_active=True,  discharge_charge=DischargeType.DISCHARGE),
    Asset(asset_type=AssetType.WIND, name="Parc Éolien Hauts-de-France — Nord",   capacity_mwh=0.0, max_charge_rate_mw=0.0, max_discharge_rate_mw=200.0, efficiency=0.97, is_active=True,  discharge_charge=DischargeType.DISCHARGE),
    Asset(asset_type=AssetType.WIND, name="Parc Éolien Hauts-de-France — Sud",    capacity_mwh=0.0, max_charge_rate_mw=0.0, max_discharge_rate_mw=160.0, efficiency=0.97, is_active=True,  discharge_charge=DischargeType.DISCHARGE),
    Asset(asset_type=AssetType.WIND, name="Parc Éolien Hauts-de-France — Est",    capacity_mwh=0.0, max_charge_rate_mw=0.0, max_discharge_rate_mw=140.0, efficiency=0.96, is_active=False, discharge_charge=DischargeType.HOLD),
]

all_assets = batteries + solar_assets + wind_assets


# ── 3. StateOfCharge — every 10 min × 30 days per active battery ─────────────

def make_soc_records(asset: Asset) -> list:
    records = []
    now = utcnow()
    total_minutes = 30 * 24 * 60
    interval = 10
    steps = total_minutes // interval      # 4,320

    soc = random.uniform(40.0, 75.0)

    for i in range(steps):
        ts = now - timedelta(minutes=total_minutes - i * interval)
        hour = ts.hour

        if 0 <= hour < 6:
            delta = random.uniform(0.1, 0.4)
            current = random.uniform(200, 600)
            power_mw = round(random.uniform(0.1, asset.max_charge_rate_mw), 3)
        else:
            delta = random.uniform(-0.4, 0.0)
            current = random.uniform(-600, -100)
            power_mw = round(random.uniform(-asset.max_discharge_rate_mw, -0.05), 3)

        soc = clamp(soc + delta, 10.0, 98.0)

        records.append(StateOfCharge(
            asset_id=asset.id,
            soc_percent=round(soc, 2),
            voltage=round(random.uniform(1380.0, 1420.0), 1),
            current_amps=round(current, 1),
            temperature_celsius=round(22.0 + 6.0 * math.sin(i * math.pi / (6 * 144)), 1),
            power_mw=power_mw,
            timestamp=ts,
        ))

    return records


# ── 4. AssetTelemetry — hourly × 30 days per asset ───────────────────────────

def make_telemetry_battery(asset: Asset) -> list:
    records = []
    now = utcnow()
    total_hours = 30 * 24
    soc = random.uniform(20.0, 80.0)

    for i in range(total_hours):
        ts = now - timedelta(hours=total_hours - i)
        hour = ts.hour

        if not asset.is_active:
            records.append(AssetTelemetry(
                asset_id=asset.id,
                timestamp=ts,
                state_of_charge_percent=None,
                current_power_mw=0.0,
                status="offline",
            ))
            continue

        if 0 <= hour < 6:
            power = round(random.uniform(0.1, asset.max_charge_rate_mw), 3)
        elif 7 <= hour <= 22:
            power = round(random.uniform(-asset.max_discharge_rate_mw, -0.05), 3)
        else:
            power = round(random.uniform(-0.05, 0.05), 3)

        soc = clamp(soc + power * 0.3, 10.0, 98.0)
        soc_val = round(soc, 2)

        if soc_val < 10.0:
            status = "low_soc_alarm"
        elif soc_val > 95.0:
            status = "high_soc_alarm"
        elif power > 0.05:
            status = "charging"
        elif power < -0.05:
            status = "discharging"
        else:
            status = "idle"

        records.append(AssetTelemetry(
            asset_id=asset.id,
            timestamp=ts,
            state_of_charge_percent=soc_val,
            current_power_mw=power,
            status=status,
        ))

    return records


def make_telemetry_solar(asset: Asset) -> list:
    records = []
    now = utcnow()
    total_hours = 30 * 24

    for i in range(total_hours):
        ts = now - timedelta(hours=total_hours - i)
        hour = ts.hour
        day = i // 24
        cloud_factor = 0.85 + 0.15 * math.sin(day * math.pi / 7)
        fraction = SOLAR_PROFILE[hour] * cloud_factor
        noise = random.uniform(-0.04, 0.04) if fraction > 0 else 0.0
        power = round(max(0.0, (fraction + noise) * asset.max_discharge_rate_mw), 3)
        status = "generating" if power > 0.01 else "idle"

        records.append(AssetTelemetry(
            asset_id=asset.id,
            timestamp=ts,
            state_of_charge_percent=None,
            current_power_mw=power,
            status=status,
        ))

    return records


def make_telemetry_wind(asset: Asset) -> list:
    records = []
    now = utcnow()
    total_hours = 30 * 24

    for i in range(total_hours):
        ts = now - timedelta(hours=total_hours - i)

        if not asset.is_active:
            records.append(AssetTelemetry(
                asset_id=asset.id,
                timestamp=ts,
                state_of_charge_percent=None,
                current_power_mw=0.0,
                status="offline",
            ))
            continue

        day_fraction = 0.45 + 0.35 * math.sin(i * math.pi / (24 * 3.5))
        hour_noise = random.uniform(-0.12, 0.12)
        power = round(clamp(
            (day_fraction + hour_noise) * asset.max_discharge_rate_mw,
            0.0, asset.max_discharge_rate_mw), 3)
        status = "generating" if power > 0.5 else "idle"

        records.append(AssetTelemetry(
            asset_id=asset.id,
            timestamp=ts,
            state_of_charge_percent=None,
            current_power_mw=power,
            status=status,
        ))

    return records


# ── 5. Dispatch Commands — 1–3 per day × 30 days per active asset ─────────────

COMMAND_TYPES = {
    AssetType.BATTERY: ["charge", "discharge", "frequency_response", "standby", "peak_shave"],
    AssetType.SOLAR:   ["curtail", "frequency_response", "standby"],
    AssetType.WIND:    ["curtail", "frequency_response", "standby"],
}

def make_dispatch_commands(asset: Asset) -> list:
    records = []
    now = utcnow()

    for day in range(30):
        for _ in range(random.randint(1, 3)):
            cmd = random.choice(COMMAND_TYPES[asset.asset_type])
            power = 0.0 if cmd == "standby" else round(
                random.uniform(asset.max_discharge_rate_mw * 0.3,
                               asset.max_discharge_rate_mw), 3)
            offset_hours = random.uniform(0, 23)
            cmd_ts = now - timedelta(days=30 - day, hours=offset_hours)

            if day < 29:
                status = random.choice(["executed", "executed", "executed", "failed"])
            else:
                status = random.choice(["executed", "pending"])

            records.append(DispatchCommand(
                asset_id=asset.id,
                command_type=cmd,
                power_target_mw=power,
                duration_seconds=random.choice([300, 600, 900, 1800, 3600]),
                timestamp=cmd_ts,
                status=status,
            ))

    return records


# ── 6. Grid Signals — every 5 min × 30 days = 8,640 records ──────────────────

def make_grid_signals() -> list:
    records = []
    now = utcnow()
    total_minutes = 30 * 24 * 60
    interval = 5
    steps = total_minutes // interval

    for i in range(steps):
        ts = now - timedelta(minutes=total_minutes - i * interval)
        hour = ts.hour
        solar_boost = SOLAR_PROFILE[hour] * 8000
        total_mw      = round(random.uniform(40000.0, 65000.0), 1)
        renewable_mw  = round(clamp(
            8000.0 + solar_boost + random.uniform(-500, 500) +
            4000 * (0.5 + 0.3 * math.sin(i * math.pi / (24 * 12))),
            6000.0, 28000.0), 1)
        renewable_pct = round((renewable_mw / total_mw) * 100, 2)
        imbalance_mw  = round(random.gauss(0, 150), 1)
        imbalance_trend = "upward" if imbalance_mw <= 0 else "downward"
        fcr_activated_mw = round(abs(imbalance_mw) * 0.15, 1)
        calculated_frequency_hz = round(50.0 + (imbalance_mw * 0.00025), 4)

        if abs(calculated_frequency_hz - 50.0) > 0.05:
            status = "frequency_alert"
        elif abs(calculated_frequency_hz - 50.0) > 0.02:
            status = "frequency_warning"
        else:
            status = "nominal"

        records.append(GridSignal(
            total_generation_mw=total_mw,
            renewable_mw=renewable_mw,
            renewable_pct=renewable_pct,
            imbalance_mw=imbalance_mw,
            imbalance_trend=imbalance_trend,
            fcr_activated_mw=fcr_activated_mw,
            calculated_frequency_hz=calculated_frequency_hz,
            status=status,
            timestamp=ts,
        ))

    return records


# ── Seed function ─────────────────────────────────────────────────────────────

def seed():
    db = SessionLocal()
    try:
        db.add_all(all_assets)
        db.flush()
        print(f"✅ Inserted {len(batteries)} battery assets")
        print(f"✅ Inserted {len(solar_assets)} solar assets")
        print(f"✅ Inserted {len(wind_assets)} wind assets")

        # StateOfCharge — active batteries only
        print("Building state_of_charge records (this may take a moment)...")
        soc_records = []
        for asset in batteries:
            if asset.is_active:
                soc_records.extend(make_soc_records(asset))
        db.add_all(soc_records)
        db.flush()
        print(f"✅ Inserted {len(soc_records)} state_of_charge records")

        # AssetTelemetry — all assets
        print("Building asset_telemetry records...")
        telemetry_records = []
        for asset in all_assets:
            if asset.asset_type == AssetType.BATTERY:
                telemetry_records.extend(make_telemetry_battery(asset))
            elif asset.asset_type == AssetType.SOLAR:
                telemetry_records.extend(make_telemetry_solar(asset))
            elif asset.asset_type == AssetType.WIND:
                telemetry_records.extend(make_telemetry_wind(asset))
        db.add_all(telemetry_records)
        db.flush()
        print(f"✅ Inserted {len(telemetry_records)} asset_telemetry records")

        # DispatchCommands — active assets only
        print("Building dispatch_command records...")
        dispatch_records = []
        for asset in all_assets:
            if asset.is_active:
                dispatch_records.extend(make_dispatch_commands(asset))
        db.add_all(dispatch_records)
        db.flush()
        print(f"✅ Inserted {len(dispatch_records)} dispatch_command records")

        # GridSignals
        print("Building grid_signal records (8,640 rows — may take a moment)...")
        grid_signals = make_grid_signals()
        db.add_all(grid_signals)
        db.flush()
        print(f"✅ Inserted {len(grid_signals)} grid_signal records")

        db.commit()
        print("\n🎉 Database seeded successfully.")
        print(f"   Total rows: {len(soc_records) + len(telemetry_records) + len(dispatch_records) + len(grid_signals) + len(all_assets)}")

    except Exception as e:
        db.rollback()
        print(f"❌ Error: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
