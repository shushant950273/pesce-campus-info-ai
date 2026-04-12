import os
from pathlib import Path

# Base Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
VECTOR_DB_DIR = DATA_DIR / "vectors" / "faiss_index"

# College Constants
COLLEGE_NAME = "PES College of Engineering (PESCE)"
COLLEGE_WEBSITE = "https://www.pesmandya.org"
COLLEGE_LOCATION = "Mandya, Karnataka, India"

# Info Categories
CATEGORIES = [
    "Academics",
    "Placements",
    "Facilities",
    "Clubs",
    "Administrative"
]
