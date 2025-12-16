from fastapi import APIRouter, Depends
from pydantic import BaseModel
from database.database import reports_collection
from utils.oauth2 import verify_token

router = APIRouter(prefix="/api/reports", tags=["Reports"])

class Report(BaseModel):
    title: str
    description: str

@router.post("/")
def create_report(report: Report, phone: str = Depends(verify_token)):
    new_report = {"phone": phone, "title": report.title, "description": report.description}
    reports_collection.insert_one(new_report)
    return {"status": "success", "message": "Report created successfully"}

@router.get("/")
def get_reports(phone: str = Depends(verify_token)):
    reports = list(reports_collection.find({"phone": phone}, {"_id": 0}))
    return {"status": "success", "data": reports}
