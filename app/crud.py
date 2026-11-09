from sqlalchemy.orm import Session
from sqlalchemy import inspect, text
from . import models
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def get_all_tanks(db: Session):
    try:
        # Debug: Print table information
        inspector = inspect(db.get_bind())
        logger.debug(f"Database tables: {inspector.get_table_names()}")
        logger.debug(f"Columns in tanks table: {inspector.get_columns('tanks')}")
        
        # Execute query and get results using SQLAlchemy ORM
        tanks = db.query(models.Tank).all()
        
        # Debug: Print raw results using text()
        raw_results = db.execute(text("SELECT * FROM tanks")).fetchall()
        logger.debug(f"Raw SQL results: {raw_results}")
        
        if not tanks and raw_results:
            # If ORM query returns empty but raw SQL shows data,
            # try creating Tank objects manually
            tanks = [
                models.Tank(
                    TankID=row[0],
                    Current_Stage=row[1],
                    Updated_At=row[2]
                ) for row in raw_results
            ]
        
        logger.info(f"Returning {len(tanks)} tanks")
        return tanks
    except Exception as e:
        logger.error(f"Error in get_all_tanks: {str(e)}")
        return []

def get_tank(db: Session, tank_id: int):
    return db.query(models.Tank).filter(models.Tank.TankID == tank_id).first()

def update_stage(db: Session, tank_id: int, new_stage: str):
    tank = get_tank(db, tank_id)
    if not tank:
        return None
    tank.Current_Stage = new_stage
    db.commit()
    db.refresh(tank)
    return tank

# from sqlalchemy.orm import Session
# from sqlalchemy import inspect, text
# from . import models
# import logging
# import os
# import sqlite3

# logging.basicConfig(level=logging.DEBUG)
# logger = logging.getLogger(__name__)

# def get_all_tanks(db: Session):
#     try:
#         # Debug: Print database connection info
#         engine = db.get_bind()
#         db_path = str(engine.url).replace('sqlite:///', '')
#         logger.debug(f"Database URL: {engine.url}")
#         logger.debug(f"Database file exists: {os.path.exists(db_path)}")
        
#         # Try direct SQLite connection
#         with sqlite3.connect(db_path) as conn:
#             conn.row_factory = sqlite3.Row
#             cursor = conn.cursor()
#             cursor.execute("SELECT * FROM tanks")
#             sqlite_results = cursor.fetchall()
#             logger.debug(f"Direct SQLite results: {sqlite_results}")
            
#             if sqlite_results:
#                 # Convert SQLite results to Tank objects
#                 tanks = [
#                     models.Tank(
#                         TankID=row['TankID'],
#                         Current_Stage=row['Current_Stage'],
#                         Updated_At=row['Updated_At']
#                     ) for row in sqlite_results
#                 ]
#                 logger.info(f"Returning {len(tanks)} tanks from SQLite")
#                 return tanks
        
#         # If SQLite direct connection fails, try ORM
#         tanks = db.query(models.Tank).all()
#         logger.debug(f"ORM query results: {tanks}")
        
#         logger.info(f"Returning {len(tanks)} tanks from ORM")
#         return tanks
#     except Exception as e:
#         logger.error(f"Error in get_all_tanks: {str(e)}", exc_info=True)
#         return []