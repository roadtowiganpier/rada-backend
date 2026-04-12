import ollama
from database import SessionLocal
from models import Battery
import json

# --- Tool definition for Ollama ---
BATTERY_TOOL = {
    "type": "function",
    "function": {
        "name": "get_all_batteries",
        "description": "Query the batteries table in the BESS database and return all battery records including id, name, capacity_kwh, max_charge_rate_kw, and is_active.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    }
}

def execute_battery_query() -> str:
    """Run the actual SQL via SQLAlchemy and return results as a string."""
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
    """Generator that streams tokens back to FastAPI."""
    messages = [
        {
            "role": "system",
            "content": (
                "You are a BESS (Battery Energy Storage System) expert assistant. "
                "You have access to a live database of battery assets. "
                "Use the get_all_batteries tool when the user asks about batteries in the system."
            )
        },
        {"role": "user", "content": question}
    ]

    # First call — let Mistral decide if it needs to use a tool
    response = ollama.chat(
        model="mistral:7b-instruct-q8_0",
        messages=messages,
        tools=[BATTERY_TOOL]
    )

    # Check if Mistral wants to call our SQL tool
    if response.message.tool_calls:
        for tool_call in response.message.tool_calls:
            if tool_call.function.name == "get_all_batteries":
                tool_result = execute_battery_query()

                # Append the tool interaction to the message history
                messages.append(response.message)
                messages.append({
                    "role": "tool",
                    "content": tool_result
                })

    # Final call — now stream the answer
    stream = ollama.chat(
        model="mistral:7b-instruct-q8_0",
        messages=messages,
        stream=True
    )

    for chunk in stream:
        token = chunk.message.content
        if token:
            yield token