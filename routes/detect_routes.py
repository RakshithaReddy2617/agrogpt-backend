from fastapi import APIRouter

router = APIRouter(prefix="/api/detect", tags=["Detection"])

@router.get("/")
def detection_demo():
    return {"message": "Detection endpoint placeholder — will connect to YOLO later"}
