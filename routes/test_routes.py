from fastapi import APIRouter
from database.database import db

router = APIRouter()

@router.get("/testdb")
def test_db():
    try:
        collections = db.list_collection_names()
        return {"status": "connected", "collections": collections}
    except Exception as e:
        return {"status": "error", "details": str(e)}
