import os

DATA_FILE = os.environ.get("FIRSTAID_DATA", "firstaid_data.json")
REPORT_DIR = "reports"
ERROR_LOG = "import_errors.log"
PAGE_SIZE = 10
OVERDUE_DAYS = 365
CATEGORIES = [
    "Bleeding & Wounds", "Burns", "Bones & Joints", "Breathing & Choking",
    "Heart & Circulation", "Poisoning & Allergy", "Heat & Cold",
    "Head & Neurological", "Bites, Eyes & Teeth", "Other",
]
