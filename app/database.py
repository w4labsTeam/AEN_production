

from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import logging
import os

# Create the database directory if it doesn't exist
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_DIR = os.path.join(BASE_DIR, "database")
os.makedirs(DB_DIR, exist_ok=True)

# SQLite database URL
DATABASE_URL = f"sqlite:///{os.path.join(DB_DIR, 'oil_tank_db.db')}"

def test_database_connection():
    try:
        engine = create_engine(DATABASE_URL)
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
            logging.info("Successfully connected to the SQLite database!")
            return True
    except Exception as e:
        logging.error(f"Database connection failed: {str(e)}")
        return False

# Create engine. Note the additional parameters for SQLite
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}  # Required for SQLite
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Test connection when module is imported
if __name__ == "__main__":
    test_database_connection()