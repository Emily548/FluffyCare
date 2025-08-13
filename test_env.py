import os
from dotenv import load_dotenv

load_dotenv()
print("OPENROUTER_API_KEY:", os.getenv("OPENROUTER_API_KEY"))
