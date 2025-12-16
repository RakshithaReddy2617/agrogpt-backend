from fastapi import APIRouter, UploadFile, File, HTTPException
import tensorflow as tf
import numpy as np
from PIL import Image
import io
import os

from utils.model_downloader import download_file
from utils.config import MODEL_URLS

router = APIRouter(
    prefix="/binary-classifier",
    tags=["Binary Classification"]
)

IMG_SIZE = (224, 224)
THRESHOLD = 0.5

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_PATH = os.path.join(
    BASE_DIR,
    "binary_classification",
    "agro_classifier_FINAL_CLEAN.keras"
)

model = None


def load_model_once():
    global model

    if model is not None:
        return

    # 🔹 Ensure model file exists (lazy download)
    bc = MODEL_URLS["binary_classifier"]
    download_file(bc["url"], bc["path"])

    try:
        print("🔄 Loading binary classifier model...")
        print("📂 Path:", MODEL_PATH)
        model = tf.keras.models.load_model(MODEL_PATH, compile=False)
        print("✅ Binary classifier model loaded successfully")
    except Exception as e:
        print("❌ Failed to load binary classifier:", e)
        model = None


@router.post("/predict")
async def predict_binary(file: UploadFile = File(...)):
    load_model_once()

    if model is None:
        raise HTTPException(
            status_code=500,
            detail="Binary classifier model is not available."
        )

    if not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Please upload an image."
        )

    try:
        image_bytes = await file.read()
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        img = img.resize(IMG_SIZE)

        img_array = np.asarray(img, dtype="float32") / 255.0
        img_array = np.expand_dims(img_array, axis=0)

        pred = float(model.predict(img_array)[0][0])

        if pred < THRESHOLD:
            result = "plant_pest"
            confidence = (1 - pred) * 100
            is_valid = True
            message = f"Plant pest detected with {confidence:.2f}% confidence."
        else:
            result = "invalid_image"
            confidence = pred * 100
            is_valid = False
            message = "Please upload a clear plant pest image."

        return {
            "status": "success",
            "result": result,
            "confidence": round(confidence, 2),
            "is_valid": is_valid,
            "message": message
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
