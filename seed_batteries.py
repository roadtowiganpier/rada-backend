"""
Seed script - populates all five BESS tables with realistic grid-scale data.
Run from your project root with the venv active:
    python seed_batteries.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal
from models import Battery, StateOfCharge, BatteryTelemetry, DispatchCommand, GridSignal
from datetime import datetime, timezone, timedelta
import random

# ── Reproducible randomness ───────────────────────────────────────────────────
random.seed(42)

# ── Helpers ───────────────────────────────────────────────────────────────────

def ts(minutes_ago: int) -> datetime:
    """Return a UTC datetime N minutes in the past."""
    return datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)


def clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


# ── 1. Batteries ──────────────────────────────────────────────────────────────

batteries = [
    # Tesla Megapack 2 XL
    Battery(name="Tesla Megapack 2 XL - Unit 01", capacity_kwh=4000.0, max_charge_rate_kw=1900.0, max_discharge_rate_kw=1900.0, efficiency=0.94, is_active=True),
    Battery(name="Tesla Megapack 2 XL - Unit 02", capacity_kwh=4000.0, max_charge_rate_kw=1900.0, max_discharge_rate_kw=1900.0, efficiency=0.94, is_active=True),
    Battery(name="Tesla Megapack 2 XL - Unit 03", capacity_kwh=4000.0, max_charge_rate_kw=1900.0, max_discharge_rate_kw=1900.0, efficiency=0.94, is_active=False),
    # Fluence Gridstack Pro
    Battery(name="Fluence Gridstack Pro - Unit 01", capacity_kwh=2000.0, max_charge_rate_kw=1000.0, max_discharge_rate_kw=1000.0, efficiency=0.95, is_active=True),
    Battery(name="Fluence Gridstack Pro - Unit 02", capacity_kwh=2000.0, max_charge_rate_kw=1000.0, max_discharge_rate_kw=1000.0, efficiency=0.95, is_active=True),
    Battery(name="Fluence Gridstack Pro - Unit 03", capacity_kwh=2000.0, max_charge_rate_kw=1000.0, max_discharge_rate_kw=1000.0, efficiency=0.93, is_active=False),
    # Sungrow PowerTitan
    Battery(name="Sungrow PowerTitan ST2236UX - Unit 01", capacity_kwh=2236.0, max_charge_rate_kw=1000.0, max_discharge_rate_kw=1000.0, efficiency=0.95, is_active=True),
    Battery(name="Sungrow PowerTitan ST2236UX - Unit 02", capacity_kwh=2236.0, max_charge_rate_kw=1000.0, max_discharge_rate_kw=1000.0, efficiency=0.95, is_active=True),
    Battery(name="Sungrow PowerTitan ST2236UX - Unit 03", capacity_kwh=2236.0, max_charge_rate_kw=1000.0, max_discharge_rate_kw=1000.0, efficiency=0.95, is_active=True),
    # CATL EnerC
    Battery(name="CATL EnerC - Unit 01", capacity_kwh=1500.0, max_charge_rate_kw=750.0, max_discharge_rate_kw=750.0, efficiency=0.95, is_active=True),
    Battery(name="CATL EnerC - Unit 02", capacity_kwh=1500.0, max_charge_rate_kw=750.0, max_discharge_rate_kw=750.0, efficiency=0.95, is_active=True),
    Battery(name="CATL EnerC - Unit 03", capacity_kwh=1500.0, max_charge_rate_kw=750.0, max_discharge_rate_kw=750.0, efficiency=0.95, is_active=False),
    # GE Reservoir
    Battery(name="GE Reservoir - Unit 01", capacity_kwh=4000.0, max_charge_rate_kw=2000.0, max_discharge_rate_kw=2000.0, efficiency=0.94, is_active=True),
    Battery(name="GE Reservoir - Unit 02", capacity_kwh=4000.0, max_charge_rate_kw=2000.0, max_discharge_rate_kw=2000.0, efficiency=0.94, is_active=True),
    Battery(name="GE Reservoir - Unit 03", capacity_kwh=4000.0, max_charge_rate_kw=2000.0, max_discharge_rate_kw=2000.0, efficiency=0.94, is_active=False),
    # Wartsila GridSolv Quantum
    Battery(name="Wartsila GridSolv Quantum - Unit 01", capacity_kwh=1120.0, max_charge_rate_kw=560.0, max_discharge_rate_kw=560.0, efficiency=0.96, is_active=True),
    Battery(name="Wartsila GridSolv Quantum - Unit 02", capacity_kwh=1120.0, max_charge_rate_kw=560.0, max_discharge_rate_kw=560.0, efficiency=0.96, is_active=True),
    Battery(name="Wartsila GridSolv Quantum - Unit 03", capacity_kwh=1120.0, max_charge_rate_kw=560.0, max_discharge_rate_kw=560.0, efficiency=0.94, is_active=False),
    # Stem Athena
    Battery(name="Stem Athena - Unit 01", capacity_kwh=1000.0, max_charge_rate_kw=500.0, max_discharge_rate_kw=500.0, efficiency=0.95, is_active=True),
    Battery(name="Stem Athena - Unit 02", capacity_kwh=1000.0, max_charge_rate_kw=500.0, max_discharge_rate_kw=500.0, efficiency=0.94, is_active=True),
    Battery(name="Stem Athena - Unit 03", capacity_kwh=1000.0, max_charge_rate_kw=500.0, max_discharge_rate_kw=500.0, efficiency=0.94, is_active=True),
    # Hitachi Energy Gridscale G2
    Battery(name="Hitachi Energy Gridscale G2 - Unit 01", capacity_kwh=1200.0, max_charge_rate_kw=600.0, max_discharge_rate_kw=600.0, efficiency=0.94, is_active=True),
    Battery(name="Hitachi Energy Gridscale G2 - Unit 02", capacity_kwh=1200.0, max_charge_rate_kw=600.0, max_discharge_rate_kw=600.0, efficiency=0.94, is_active=True),
    Battery(name="Hitachi Energy Gridscale G2 - Unit 03", capacity_kwh=1200.0, max_charge_rate_kw=600.0, max_discharge_rate_kw=600.0, efficiency=0.93, is_active=False),
    # BYD MC-Cube
    Battery(name="BYD MC-Cube - Unit 01", capacity_kwh=1672.0, max_charge_rate_kw=836.0, max_discharge_rate_kw=836.0, efficiency=0.96, is_active=True),
    Battery(name="BYD MC-Cube - Unit 02", capacity_kwh=1672.0, max_charge_rate_kw=836.0, max_discharge_rate_kw=836.0, efficiency=0.96, is_active=True),
    Battery(name="BYD MC-Cube - Unit 03", capacity_kwh=1672.0, max_charge_rate_kw=836.0, max_discharge_rate_kw=836.0, efficiency=0.96, is_active=True),
    # Powin Stack750
    Battery(name="Powin Stack750 - Unit 01", capacity_kwh=3000.0, max_charge_rate_kw=1500.0, max_discharge_rate_kw=1500.0, efficiency=0.95, is_active=True),
    Battery(name="Powin Stack750 - Unit 02", capacity_kwh=3000.0, max_charge_rate_kw=1500.0, max_discharge_rate_kw=1500.0, efficiency=0.95, is_active=True),
    # Nidec ESS Freqmax
    Battery(name="Nidec ESS Freqmax - Unit 01", capacity_kwh=1800.0, max_charge_rate_kw=900.0, max_discharge_rate_kw=900.0, efficiency=0.95, is_active=True),
    Battery(name="Nidec ESS Freqmax - Unit 02", capacity_kwh=1800.0, max_charge_rate_kw=900.0, max_discharge_rate_kw=900.0, efficiency=0.95, is_active=False),
]


# ── 2. State of Charge — 6 readings per active battery over the last hour ─────
#
# Real-world context: a SCADA system polls each battery every 10 minutes and
# records voltage, current, temperature and computed SoC. Inactive units are
# not polled so they have no recent records.

def make_soc_records(battery_id: int, capacity_kwh: float) -> list:
    records = []
    soc = random.uniform(30.0, 85.0)           # starting SoC for this battery
    for i in range(6):                          # 6 readings, 10 min apart
        delta = random.uniform(-3.0, 3.0)       # SoC drifts slightly each poll
        soc = clamp(soc + delta, 10.0, 98.0)
        power_kw = random.uniform(-capacity_kwh * 0.3, capacity_kwh * 0.3)
        records.append(StateOfCharge(
            battery_id=battery_id,
            soc_percent=round(soc, 2),
            voltage=round(random.uniform(1380.0, 1420.0), 1),   # MV bus ~1400 V
            current_amps=round(random.uniform(-800.0, 800.0), 1),
            temperature_celsius=round(random.uniform(22.0, 38.0), 1),
            power_kw=round(power_kw, 1),
            timestamp=ts(50 - i * 10),          # 50, 40, 30, 20, 10, 0 min ago
        ))
    return records


# ── 3. Battery Telemetry — 1 current snapshot per active battery ──────────────
#
# Real-world context: the BMS (Battery Management System) pushes a telemetry
# heartbeat every minute to a central SCADA/EMS. This table holds the most
# recent snapshot used for dashboards and alarms. Inactive units show
# "offline" status with zeroed power.

def make_telemetry(battery_id: int, is_active: bool) -> BatteryTelemetry:
    if not is_active:
        return BatteryTelemetry(
            battery_id=battery_id,
            state_of_charge_percent=0.0,
            current_power_kw=0.0,
            status="offline",
            timestamp=ts(random.randint(120, 1440)),  # last seen 2–24 hrs ago
        )
    soc = round(random.uniform(15.0, 95.0), 2)
    power = round(random.uniform(-1500.0, 1500.0), 1)
    # Derive a realistic status from SoC and power
    if soc < 10.0:
        status = "low_soc_alarm"
    elif soc > 95.0:
        status = "high_soc_alarm"
    elif power > 50:
        status = "charging"
    elif power < -50:
        status = "discharging"
    else:
        status = "idle"
    return BatteryTelemetry(
        battery_id=battery_id,
        state_of_charge_percent=soc,
        current_power_kw=power,
        status=status,
        timestamp=ts(random.randint(0, 3)),   # updated within last 3 minutes
    )


# ── 4. Dispatch Commands — recent commands sent to active batteries ────────────
#
# Real-world context: the Energy Management System (EMS) issues charge/
# discharge/standby commands in response to market signals (frequency
# response, peak shaving, arbitrage). Each command has a power target
# and a duration. Commands are logged even after execution.

COMMAND_TYPES = ["charge", "discharge", "frequency_response", "standby", "peak_shave"]

def make_dispatch_commands(battery_id: int, max_kw: float) -> list:
    records = []
    for i in range(random.randint(2, 4)):       # 2–4 commands per battery
        cmd = random.choice(COMMAND_TYPES)
        if cmd == "standby":
            power = 0.0
        elif cmd in ("charge", "frequency_response"):
            power = round(random.uniform(max_kw * 0.3, max_kw), 1)
        else:
            power = round(random.uniform(-max_kw, -max_kw * 0.3), 1)
        records.append(DispatchCommand(
            battery_id=battery_id,
            command_type=cmd,
            power_target_kw=power,
            duration_seconds=random.choice([300, 600, 900, 1800, 3600]),
            timestamp=ts(random.randint(5, 480)),
        ))
    return records


# ── 5. Grid Signals — 24 readings over the last 2 hours ──────────────────────
#
# Real-world context: a PMU (Phasor Measurement Unit) or grid analyser
# records frequency and voltage at the point of common coupling every
# 5 minutes. Frequency deviations from 50 Hz trigger automatic dispatch.
# Status reflects the RTE (French TSO) grid condition classification.

def make_grid_signals() -> list:
    records = []
    for i in range(24):                         # one reading every 5 minutes
        total_mw = round(random.uniform(40000.0, 65000.0), 1)
        renewable_mw = round(random.uniform(8000.0, 25000.0), 1)
        renewable_pct = round((renewable_mw / total_mw) * 100, 2)
        imbalance_mw = round(random.gauss(0, 150), 1)  # normally distributed around 0
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
            timestamp=ts(i * 5),
        ))
    return records

# ── Seed function ─────────────────────────────────────────────────────────────

def seed():
    db = SessionLocal()
    try:
        # Clear all tables in reverse FK order
        for model in [BatteryTelemetry, StateOfCharge, DispatchCommand, GridSignal, Battery]:
            deleted = db.query(model).delete()
            if deleted:
                print(f"🗑️  Cleared {deleted} row(s) from {model.__tablename__}")
        db.commit()

        # Insert batteries first so we have IDs
        db.add_all(batteries)
        db.flush()   # assigns .id without committing
        print(f"✅ Inserted {len(batteries)} batteries")

        # Build dependent records now that battery IDs exist
        soc_records = []
        telemetry_records = []
        dispatch_records = []

        for b in batteries:
            telemetry_records.append(make_telemetry(b.id, b.is_active))
            if b.is_active:
                soc_records.extend(make_soc_records(b.id, b.capacity_kwh))
                dispatch_records.extend(make_dispatch_commands(b.id, b.max_discharge_rate_kw))

        grid_signals = make_grid_signals()

        db.add_all(soc_records)
        db.add_all(telemetry_records)
        db.add_all(dispatch_records)
        db.add_all(grid_signals)
        db.commit()

        print(f"✅ Inserted {len(soc_records)} state_of_charge records")
        print(f"✅ Inserted {len(telemetry_records)} battery_telemetry records")
        print(f"✅ Inserted {len(dispatch_records)} dispatch_command records")
        print(f"✅ Inserted {len(grid_signals)} grid_signal records")
        print("\n🎉 Database seeded successfully.")

    except Exception as e:
        db.rollback()
        print(f"❌ Error: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
