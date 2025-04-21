import os

def get_openai_api_key():
    keys = [
        os.getenv("OPENAI_API_KEY_TASR"),
        os.getenv("OPENAI_API_KEY_IGHI")
    ]
    return next((k for k in keys if k), None)
