import ollama
from database import SessionLocal
from models import Battery


def fetch_battery_context() -> str:
    """Fetch all battery records from the DB and format as a string for the system prompt."""
    db = SessionLocal()
    try:
        batteries = db.query(Battery).all()
        if not batteries:
            return "No battery records found in the database."
        result = []
        for b in batteries:
            result.append(
                f"ID: {b.id}, Name: {b.name}, Capacity: {b.capacity_kwh} kWh, "
                f"Max Charge Rate: {b.max_charge_rate_kw} kW, Active: {b.is_active}"
            )
        return "\n".join(result)
    finally:
        db.close()


def ask_bess_question_stream(question: str):
    """
    Single-pass generator that streams tokens back to FastAPI.

    Battery data is always fetched from the DB and injected into the system
    prompt — no tool-calling round trip, so inference runs once only.
    """
    battery_data = fetch_battery_context()

    messages = [
        {
            "role": "system",
            "content": (
                "You are a BESS (Battery Energy Storage System) expert assistant. "
                "You have access to the following live battery data from the system database:\n\n"
                f"{battery_data}\n\n"
                "Use this data when answering questions about the batteries in the system. "
                "For general BESS questions not related to the database, answer from your expert knowledge."
            )
        },
        {
            "role": "user",
            "content": question
        }
    ]

    stream = ollama.chat(
        model="mistral:7b-instruct",
        messages=messages,
        stream=True
    )

    for chunk in stream:
        token = chunk.message.content
        if token:
            yield token