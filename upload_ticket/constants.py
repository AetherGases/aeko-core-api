"""Upload ticket configuration."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=False)

INVENTORY_UPLOAD_TICKET_TTL_SECONDS = int(os.environ["INVENTORY_UPLOAD_TICKET_TTL_SECONDS"])
