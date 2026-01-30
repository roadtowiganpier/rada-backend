from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

from database import Base


class Battery(Base):
    __tablename__ = "batteries"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    capacity_kwh = Column(Float, nullable=False)
    max_charge_rate_kw = Column(Float, nullable=False)
    max_discharge_rate_kw = Column(Float, nullable=False)
    efficiency = Column(Float, default=0.95)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    state_of_charge_records = relationship("StateOfCharge", back_populates="battery")


class StateOfCharge(Base):
    __tablename__ = "state_of_charge"

    id = Column(Integer, primary_key=True, index=True)
    battery_id = Column(Integer, ForeignKey("batteries.id"), nullable=False)
    soc_percent = Column(Float, nullable=False)
    voltage = Column(Float, nullable=True)
    current_amps = Column(Float, nullable=True)
    temperature_celsius = Column(Float, nullable=True)
    power_kw = Column(Float, nullable=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)

    battery = relationship("Battery", back_populates="state_of_charge_records")

class GridSignal (Base):
    __tablename__ = "grid_signals"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    frequency_hz = Column(Float, nullable=False)
    voltage_kv = Column(Float, nullable=False)
    status = Column(String(50), nullable=False)

class DispatchCommand (Base):
    __tablename__ = "dispatch_commands"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    battery_id = Column(Integer, ForeignKey("batteries.id"), nullable=False)
    command_type = Column(String(50), nullable=False)
    power_target_kw = Column(Float, nullable=False)
    duration_seconds = Column(Integer, nullable=False)


class BatteryTelemetry (Base):
    __tablename__ = "battery_telemetry"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    battery_id = Column(Integer, ForeignKey("batteries.id"), nullable=False)
    state_of_charge_percent = Column(Float, nullable=False) 
    current_power_kw = Column(Float, nullable=False)  
    status = Column(String(50), nullable=False)