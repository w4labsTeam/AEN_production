from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from fastapi.responses import StreamingResponse
from ..database import SessionLocal
from .. import crud, schemas
from ..services import sludge_service, live_service
from datetime import datetime
from app.services.ml_worker import ml_active_lock

router = APIRouter(prefix="/tank", tags=["Tank"])

STAGES = ["Standby", "Filling", "Extraction", "Finish"]

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 1. /predict/{tank_id}
@router.get("/predict/{tank_id}", response_model=schemas.SludgeResponse)
def predict(tank_id: int, db: Session = Depends(get_db)):
    tank = crud.get_tank(db, tank_id)
    if not tank:
        raise HTTPException(status_code=404, detail="Tank not found")

    sludge_level, snapshot = sludge_service.get_sludge_level(tank_id) #return the latest sludge level and snapshot regardless of stage, as long as the ML worker has produced results for this tank
    return schemas.SludgeResponse(
        sludge_level=sludge_level,
        stage=tank.Current_Stage,
        updated_at=tank.Updated_At,
        snapshot=snapshot
    )

# 2. /change-stage/{tank_id}
@router.post("/change-stage/{tank_id}")
def change_stage(tank_id: int, db: Session = Depends(get_db)):
    tank = crud.get_tank(db, tank_id)
    if not tank:
        raise HTTPException(status_code=404, detail="Tank not found")

    current_index = STAGES.index(tank.Current_Stage)
    new_stage = STAGES[(current_index + 1) % len(STAGES)]
    updated_tank = crud.update_stage(db, tank_id, new_stage)

    # with ml_active_lock:
    #     if new_stage in ["Filling", "Extraction"]:
    #         sludge_level, snapshot = sludge_service.get_sludge_level(tank_id) # only return the results when entering active stages
    #         ml_active_tanks.add(tank_id)
    #         return {
    #             "sludge_level": sludge_level,
    #             "snapshot": snapshot,
    #             "stage": updated_tank.Current_Stage,
    #             "updated_at": updated_tank.Updated_At
    #         }
    #     else:
    #         ml_active_tanks.discard(tank_id)
    #         return {
    #             "stage": updated_tank.Current_Stage,
    #             "updated_at": updated_tank.Updated_At
    #         }
    # with ml_active_lock:
    #     if new_stage in ["Filling", "Extraction"]:
    #         ml_active_tanks.add(tank_id)
    #     else:
    #         ml_active_tanks.discard(tank_id)

    # DO NOT call get_sludge_level() here
    return {
        "stage": updated_tank.Current_Stage,
        "updated_at": updated_tank.Updated_At
    }

# 3. /live-feed/{tank_id}
@router.get("/live-feed/{tank_id}")
def live_feed(tank_id: int, db: Session = Depends(get_db)):
    tank = crud.get_tank(db, tank_id)
    if not tank:
        raise HTTPException(status_code=404, detail="Tank not found")

    if tank.Current_Stage != "Standby":
        raise HTTPException(status_code=400, detail="Live feed only available in Standby stage")

    return StreamingResponse(live_service.generate_frames(tank_id),
                             media_type="multipart/x-mixed-replace; boundary=frame")

# 4. /reset/{tank_id}
@router.post("/reset/{tank_id}")
def reset_tank(tank_id: int, db: Session = Depends(get_db)):
    updated_tank = crud.update_stage(db, tank_id, "Standby")
    # ml_active_tanks.discard(tank_id)
    if not updated_tank:
        raise HTTPException(status_code=404, detail="Tank not found")
    return {"stage": "Standby", "updated_at": updated_tank.Updated_At}

@router.get("/all")
def get_all_tanks(db: Session = Depends(get_db)):
    tanks = crud.get_all_tanks(db)
    return tanks
