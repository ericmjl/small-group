"""Run the small group management application."""

import argparse
import os
from pathlib import Path
import uvicorn
from dotenv import load_dotenv

load_dotenv()


def main():
    """Run the application."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--db-path",
        type=Path,
        required=False,
        help="Path to SQLite database",
    )
    args = parser.parse_args()

    # Set DB_PATH environment variable for the app
    if args.db_path:
        os.environ["DB_PATH"] = str(args.db_path.absolute())

    # Run the app
    uvicorn.run("app:app", host="0.0.0.0", port=int(os.getenv("PORT")), reload=True)


if __name__ == "__main__":
    main()
