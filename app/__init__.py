"""Small group management application."""

import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .database import init_db

# Create the FastAPI app
app = FastAPI(title="Small Group Manager")

# Mount static files
static_path = Path(__file__).parent / "static"
static_path.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

# Set up templates
templates_path = Path(__file__).parent / "templates"
templates_path.mkdir(exist_ok=True)
templates = Jinja2Templates(directory=str(templates_path))

# Make templates available in app.state
app.state.templates = templates

# Initialize database if DB_PATH is set
db_path = os.environ.get("DB_PATH")
if db_path:
    init_db(Path(db_path))

# Import routes after app is created to avoid circular imports
from . import routes
