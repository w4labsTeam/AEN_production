from app.database import Base, engine, SessionLocal
from app.models import Tank
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_db():
    try:
        # Create tables
        Base.metadata.create_all(bind=engine)
        logger.info("Created database tables")

        db = SessionLocal()
        
        # Check if we already have data
        if db.query(Tank).first() is not None:
            logger.info("Database already contains data, skipping initialization")
            return

        # Create default tanks
        default_tanks = [
            Tank(
                TankID=i,
                Current_Stage="Standby",
                Updated_At=datetime.now()
            ) for i in range(1, 9)  # Creates 8 tanks
        ]

        # Add tanks to database
        db.bulk_save_objects(default_tanks)
        db.commit()
        logger.info("Added default tanks to database")

    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    logger.info("Creating initial database")
    init_db()
    logger.info("Database initialization completed")