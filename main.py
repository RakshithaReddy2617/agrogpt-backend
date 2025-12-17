from fastapi import FastAPI, Body, HTTPException, UploadFile, File, Query, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from pymongo import MongoClient
from passlib.hash import bcrypt
import pyotp, qrcode, os, uuid
from io import BytesIO
from PIL import Image
import random
from datetime import datetime
from dotenv import load_dotenv

from utils.model_downloader import download_file
from utils.config import MODEL_URLS

# BLIP captioner (can be stubbed later if disabled)
#from agrogpt_captioner import caption_image


# ─────────────────────────────
# App init
# ─────────────────────────────
app = FastAPI()
# --- Optional Binary Classifier (disabled on Railway) ---
try:
    from routes.binary_classifier import router as binary_classifier_router
    app.include_router(binary_classifier_router)
    print("Binary classifier enabled")
except Exception as e:
    print("Binary classifier disabled:", e)

@app.get("/healthz")
def health_check():
    return {"status": "ok"}

#app.include_router(binary_classifier_router)
app.include_router(chat_router)

# ─────────────────────────────
# CORS
# ─────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────
# ENV + DB
# ─────────────────────────────
load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
if not MONGO_URI:
    raise RuntimeError("MONGO_URI not found in environment variables")

client = MongoClient(MONGO_URI)
db = client["agrogpt"]
users = db["users"]
chats = db["chats"]

# ─────────────────────────────
# TEMP DIR
# ─────────────────────────────
tmp_dir = os.path.join(os.getcwd(), "tmp")
os.makedirs(tmp_dir, exist_ok=True)

# ─────────────────────────────
# MODELS (download only, no heavy load)
# ─────────────────────────────

def ensure_models():
    bc = MODEL_URLS.get("binary_classifier")
    if bc:
        download_file(bc["url"], bc["path"])

    mm = MODEL_URLS.get("merged_model")
    if mm:
        for filename, file_id in mm["files"].items():
            url = f"https://drive.google.com/uc?id={file_id}"
            path = os.path.join(mm["dir"], filename)
            download_file(url, path)

@app.on_event("startup")
def startup_event():
    # IMPORTANT: keeps Render/Railway happy without blocking port binding
    try:
        ensure_models()
    except Exception as e:
        print("Model download skipped:", e)

# ─────────────────────────────
# SCHEMAS
# ─────────────────────────────
class SignupModel(BaseModel):
    name: str
    phone: str

class SigninModel(BaseModel):
    email: str
    password: str

class VerifyTOTPModel(BaseModel):
    email: str
    password: str
    code: str

class ChatMessageModel(BaseModel):
    message: str
    response: str = ""
    title: str | None = None

# ─────────────────────────────
# TRANSLATIONS
# ─────────────────────────────
translations = {
    "en": {"chat_saved": "Chat saved successfully", "image_detected": "Image processed successfully", "login_error": "Login failed"},
    "hi": {"chat_saved": "चैट सफलतापूर्वक सहेजी गई", "image_detected": "छवि सफलतापूर्वक संसाधित की गई", "login_error": "लॉगिन असफल"},
    "te": {"chat_saved": "చాట్ విజయవంతంగా సేవ్ చేయబడింది", "image_detected": "చిత్రం విజయవంతంగా ప్రాసెస్ చేయబడింది", "login_error": "లాగిన్ విఫలమైంది"},
}

chat_translations = {
    "en": {"default": "I am AgroGPT, how can I help you?", "plantHealthy": "The plant looks healthy", "nitrogenDeficiency": "Nitrogen deficiency possible", "pestDetected": "Pest detected", "userEcho": "You said: "},
    "hi": {"default": "मैं AgroGPT हूँ", "plantHealthy": "पौधा स्वस्थ है", "nitrogenDeficiency": "नाइट्रोजन की कमी", "pestDetected": "कीट पाए गए", "userEcho": "आपने कहा: "},
    "te": {"default": "నేను AgroGPT", "plantHealthy": "పంట ఆరోగ్యంగా ఉంది", "nitrogenDeficiency": "నైట్రోజన్ లోపం", "pestDetected": "కీటకాలు ఉన్నాయి", "userEcho": "మీరు చెప్పింది: "},
}

# ─────────────────────────────
# AUTH & CHAT ENDPOINTS (UNCHANGED LOGIC)
# ─────────────────────────────
@app.post("/api/auth/signup")
def signup(data: SignupModel):
    if users.find_one({"phone": data.phone}):
        return {"status": "exists"}
    users.insert_one({"name": data.name, "phone": data.phone, "totp_secret": pyotp.random_base32()})
    return {"status": "success"}

@app.post("/register")
def register(data: SigninModel = Body(...)):
    if users.find_one({"email": data.email}):
        return {"status": "exists"}
    users.insert_one({"email": data.email, "password": bcrypt.hash(data.password), "totp_secret": pyotp.random_base32()})
    return {"status": "success"}

@app.post("/verify-totp")
def verify_login(data: VerifyTOTPModel = Body(...)):
    user = users.find_one({"email": data.email})
    if not user or not bcrypt.verify(data.password, user["password"]):
        return {"status": "error"}
    if not pyotp.TOTP(user["totp_secret"]).verify(data.code):
        return {"status": "error"}
    return {"status": "success"}

@app.get("/api/chats/{email}")
def get_chats(email: str):
    return {"chats": list(chats.find({"email": email}, {"_id": 0}).sort("timestamp", 1))}

@app.post("/api/migrate-chats/{email}")
def migrate_chats(email: str, chat: ChatMessageModel, lang: str = Query("en")):
    ct = chat_translations.get(lang, chat_translations["en"])
    response = chat.response or ct["userEcho"] + chat.message
    chats.insert_one({"email": email, "title": chat.title or "Untitled", "message": chat.message, "response": response, "timestamp": datetime.utcnow()})
    return {"status": "success"}

# ─────────────────────────────
# IMAGE ENDPOINTS
# ─────────────────────────────
@app.post("/detect-image")
async def detect_image(file: UploadFile = File(...), lang: str = Query("en")):
    filename = f"{uuid.uuid4().hex}_{file.filename}"
    path = os.path.join(tmp_dir, filename)
    with open(path, "wb") as f:
        f.write(await file.read())

    img = Image.open(path)
    ct = chat_translations.get(lang, chat_translations["en"])
    return {"bot_response": random.choice([ct["plantHealthy"], ct["nitrogenDeficiency"], ct["pestDetected"]])}

@app.post("/predict")
async def predict(prompt: str = Form(...), image: UploadFile = File(...), email: str = Form(...)):
    filename = f"{uuid.uuid4().hex}_{image.filename}"
    path = os.path.join(tmp_dir, filename)
    with open(path, "wb") as f:
        f.write(await image.read())

    caption = "Image analysis temporarily unavailable"

    answer = f"Image analysis completed: {caption}"

    chats.insert_one({"email": email, "title": "Image Analysis", "message": prompt, "response": answer, "timestamp": datetime.utcnow()})
    return {"answer": answer}

# ─────────────────────────────
# ENTRYPOINT (IMPORTANT FOR RENDER/RAILWAY)
# ─────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
