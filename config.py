import os
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()
BASE_DIR = Path(__file__).resolve().parent


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-career-roadmap-secret")
    DATABASE_PATH = os.getenv("DATABASE_PATH", str(BASE_DIR / "instance" / "careerroad.db"))
    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    FLASK_DEBUG = os.getenv("FLASK_DEBUG", "False").lower() == "true"
    MOCK_AI_WHEN_NO_KEY = os.getenv("MOCK_AI_WHEN_NO_KEY", "True").lower() == "true"
