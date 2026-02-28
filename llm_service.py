import ollama

def ask_bess_question(question: str) -> str:
    response = ollama.chat(
        model='mistral',
        messages=[
            {
                'role': 'system',
                'content': 'You are a BESS (Battery Energy Storage System) expert assistant. Answer questions about battery storage, grid management, and energy systems.'
            },
            {
                'role': 'user',
                'content': question
            }
        ]
    )
    return response['message']['content']