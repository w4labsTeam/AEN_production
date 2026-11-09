# from sqlalchemy import Column, Integer, String, DateTime, func
# from .database import Base

# class Tank(Base):
#     __tablename__ = "tanks"

#     # TankID = Column(Integer, primary_key=True, index=True)
#     # Current_Stage = Column(String, nullable=False, default="Standby")
#     # Updated_At = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

#     TankID = Column(Integer, primary_key=True, index=True)  # Changed to match database column
#     Current_Stage = Column(String)
#     Updated_At = Column(DateTime)


from sqlalchemy import Column, Integer, String, DateTime, func
from .database import Base

class Tank(Base):
    __tablename__ = "tanks"  # Matches the actual table name

    TankID = Column(Integer, primary_key=True)  # Remove index=True as it might not match DB
    Current_Stage = Column(String)
    Updated_At = Column(DateTime)

    def __repr__(self):
        return f"<Tank(TankID={self.TankID}, Current_Stage={self.Current_Stage})>"
