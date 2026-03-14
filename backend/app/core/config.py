from pathlib import Path
import os

from dotenv import load_dotenv

root_env = Path(__file__).resolve().parents[3] / ".env"
load_dotenv(root_env)


def get_database_url() -> str:
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return database_url

    db_host = os.getenv("DB_HOST", "localhost")
    db_port = os.getenv("DB_PORT", "5433")
    db_name = os.getenv("DB_NAME", "scout")
    db_user = os.getenv("DB_USER", "scout")
    db_password = os.getenv("DB_PASSWORD", "scout")

    return (
        f"postgresql+psycopg2://{db_user}:{db_password}"
        f"@{db_host}:{db_port}/{db_name}"
    )


DATABASE_URL = get_database_url()
