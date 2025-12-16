from fastapi import APIRouter, File, UploadFile
import torch

router = APIRouter(prefix="/api/model", tags=["Model"])

MODEL_PATH = "static/model.pt"

@router.post("/predict")
async def predict(file: UploadFile = File(...)):
    image_bytes = await file.read()
    # Placeholder: load and run model once your real model is ready
    # model = torch.load(MODEL_PATH, map_location="cpu")
    # results = model(image_bytes)
    return {"status": "success", "message": "Model prediction simulated"}
