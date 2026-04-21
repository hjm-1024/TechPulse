import os
from dotenv import load_dotenv

load_dotenv()

DB_PATH = os.getenv("DB_PATH", "data/techpulse.db")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

SEMANTIC_SCHOLAR_API_KEY = os.getenv("SEMANTIC_SCHOLAR_API_KEY", "")
OPENALEX_EMAIL = os.getenv("OPENALEX_EMAIL", "")
KIPRIS_API_KEY = os.getenv("KIPRIS_API_KEY", "")
EPO_OPS_KEY    = os.getenv("EPO_OPS_KEY", "")
EPO_OPS_SECRET = os.getenv("EPO_OPS_SECRET", "")
LENS_API_KEY   = os.getenv("LENS_API_KEY", "")

KEYWORDS = [
    "physical AI",
    "humanoid robot",
    "6G",
    "mobile communication",
    "autonomous robot",
]

DOMAIN_TAG_MAP = {
    "physical AI": "physical_ai_robotics",
    "humanoid robot": "physical_ai_robotics",
    "autonomous robot": "physical_ai_robotics",
    "6G": "telecom_6g",
    "mobile communication": "telecom_6g",
}
