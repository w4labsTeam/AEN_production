from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class TankBase(BaseModel):
    TankID: int
    Current_Stage: str
    Updated_At: datetime

    class Config:
        orm_mode = True

class SludgeResponse(BaseModel):
    sludge_level: Optional[str]
    stage: str
    updated_at: datetime
    snapshot: Optional[str]  # Base64 encoded image
