from fastapi import FastAPI, Body, HTTPException, UploadFile, File, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from pymongo import MongoClient
from passlib.hash import bcrypt
import pyotp, qrcode, os
from io import BytesIO
from PIL import Image
import random
from fastapi import Form
from datetime import datetime
from dotenv import load_dotenv
from utils.model_downloader import download_file
from utils.config import MODEL_URLS

#import torch
#from transformers import AutoTokenizer, AutoModelForCausalLM
from agrogpt_captioner import caption_image




from routes.binary_classifier import router as binary_classifier_router
from routes.chat import router as chat_router

def ensure_models():
    # Binary classifier
    bc = MODEL_URLS["binary_classifier"]
    download_file(bc["url"], bc["path"])

    # Merged model
    mm = MODEL_URLS["merged_model"]
    for filename, file_id in mm["files"].items():
        url = f"https://drive.google.com/uc?id={file_id}"
        path = os.path.join(mm["dir"], filename)
        download_file(url, path)

ensure_models()

app = FastAPI()
app.include_router(binary_classifier_router)


# ─── CORS CONFIG ───
#origins = [
   # "http://localhost:3000",
    #"http://127.0.0.1:3000"
#]
origins = ["*"]


app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# ─── DATABASE ───

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")

if not MONGO_URI:
    raise RuntimeError("MONGO_URI not found in environment variables")

client = MongoClient(MONGO_URI)

db = client["agrogpt"]
users = db["users"]
chats = db["chats"]


# ─── TEMP FOLDER FOR QR IMAGES ───
tmp_dir = os.path.join(os.getcwd(), "tmp")
os.makedirs(tmp_dir, exist_ok=True)

# ─── SCHEMAS ───
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
    title: str = None  # optional chat title

# ─── MULTILINGUAL TRANSLATIONS ───
translations = {
    "en": {
        "chat_saved": "Chat saved successfully",
        "image_detected": "Image processed successfully",
        "login_error": "Login failed"
    },
    "hi": {
        "chat_saved": "चैट सफलतापूर्वक सहेजी गई",
        "image_detected": "छवि सफलतापूर्वक संसाधित की गई",
        "login_error": "लॉगिन असफल"
    },
    "te": {
        "chat_saved": "చాట్ విజయవంతంగా సేవ్ చేయబడింది",
        "image_detected": "చిత్రం విజయవంతంగా ప్రాసెస్ చేయబడింది",
        "login_error": "లాగిన్ విఫలమైంది"
    }
}

chat_translations = {
    "en": {
        "default": "I am AgroGPT, how can I help you?",
        "plantHealthy": "The plant looks healthy 🌿",
        "nitrogenDeficiency": "The plant may have nitrogen deficiency 🟡",
        "pestDetected": "Pest detected on the leaves 🐛",
        "userEcho": "You said: "
    },
    "hi": {
        "default": "मैं AgroGPT हूँ, मैं आपकी कैसे मदद कर सकता हूँ?",
        "plantHealthy": "पौधा स्वस्थ दिखता है 🌿",
        "nitrogenDeficiency": "पौधे में नाइट्रोजन की कमी हो सकती है 🟡",
        "pestDetected": "पत्तियों पर कीट देखा गया 🐛",
        "userEcho": "आपने कहा: "
    },
    "te": {
        "default": "నేను AgroGPT, నేను మీకు ఎలా సహాయం చేయగలను?",
        "plantHealthy": "పంట ఆరోగ్యంగా ఉంది 🌿",
        "nitrogenDeficiency": "పంటలో నైట్రోజన్ లోపం ఉండవచ్చు 🟡",
        "pestDetected": "ఆకులపై కీటకాలు కనుగొనబడ్డాయి 🐛",
        "userEcho": "మీరు చెప్పినది: "
    }
}
# ─── AGROGPT MERGED MODEL LOAD ───


#BASE_DIR = os.path.dirname(os.path.abspath(__file__))
#MODEL_PATH = os.path.join(BASE_DIR, "merged_model")

#tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)

#model = AutoModelForCausalLM.from_pretrained(
   # MODEL_PATH,
  #  torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
  #  device_map="auto"
#)

#model.eval()


# ─── SIGNUP ENDPOINT ───
@app.post("/api/auth/signup")
def signup(data: SignupModel):
    name = data.name
    phone = data.phone
    if users.find_one({"phone": phone}):
        return {"status": "exists", "message": "User already exists"}
    secret = pyotp.random_base32()
    users.insert_one({
        "name": name,
        "phone": phone,
        "totp_secret": secret
    })
    return {"status": "success", "message": "Signup successful"}

# ─── REGISTER ENDPOINT ───
@app.post("/register")
def register(data: SigninModel = Body(...)):
    email = data.email
    password = data.password
    if users.find_one({"email": email}):
        return {"status": "exists", "message": "User already exists"}
    secret = pyotp.random_base32()
    hashed_pw = bcrypt.hash(password)
    users.insert_one({
        "email": email,
        "password": hashed_pw,
        "totp_secret": secret
    })
    return {"status": "success", "email": email, "message": "User registered"}

# ─── GENERATE TOTP + QR ───
@app.get("/totp-setup/{email}")
def totp_setup(email: str):
    user = users.find_one({"email": email})
    if not user:
        return {"status": "error", "message": "User not found"}
    secret = user["totp_secret"]
    otp_uri = pyotp.TOTP(secret).provisioning_uri(name=email, issuer_name="AgroGPT")
    qr = qrcode.make(otp_uri)
    buffer = BytesIO()
    qr.save(buffer, format="PNG")
    buffer.seek(0)
    file_path = os.path.join(tmp_dir, f"{email}_qr.png")
    with open(file_path, "wb") as f:
        f.write(buffer.getvalue())
    return {"status": "success", "qr_url": f"/get-qr/{email}", "manual_key": secret}

@app.get("/get-qr/{email}")
def get_qr(email: str):
    file_path = os.path.join(tmp_dir, f"{email}_qr.png")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="QR not found")
    return FileResponse(file_path, media_type="image/png")

# ─── VERIFY TOTP LOGIN ───
@app.post("/verify-totp")
def verify_login(data: VerifyTOTPModel = Body(...)):
    user = users.find_one({"email": data.email})
    if not user:
        return {"status": "error", "message": "User not found"}
    if not bcrypt.verify(data.password, user["password"]):
        return {"status": "error", "message": "Invalid password"}
    totp = pyotp.TOTP(user["totp_secret"])
    if not totp.verify(data.code):
        return {"status": "error", "message": "Invalid TOTP code"}
    return {"status": "success", "message": "Login successful"}

# ─── FETCH USER CHATS ───
@app.get("/api/chats/{email}")
def get_chats(email: str):
    user_chats = chats.find({"email": email}).sort("timestamp", 1)
    chat_list = []
    for chat in user_chats:
        chat_list.append({
            "title": chat.get("title", ""),
            "message": chat.get("message"),
            "response": chat.get("response")
        })
    return {"status": "success", "chats": chat_list}

from datetime import datetime

@app.post("/api/migrate-chats/{email}")
def migrate_chats(email: str, chat_data: ChatMessageModel, lang: str = Query("en")):
    user = users.find_one({"email": email})
    if not user:
        t = translations.get(lang, translations["en"])
        return {"status": "error", "message": t["login_error"]}

    ct = chat_translations.get(lang, chat_translations["en"])
    bot_text = chat_data.response or (ct["userEcho"] + chat_data.message if chat_data.message else ct["default"])

    chats.insert_one({
        "email": email,
        "title": chat_data.title or "Untitled",
        "message": chat_data.message,
        "response": bot_text,
        "timestamp": datetime.utcnow()   # ← add timestamp
    })

    t = translations.get(lang, translations["en"])
    return {"status": "success", "message": t["chat_saved"], "bot_response": bot_text}

# ─── IMAGE DETECTION ───
@app.post("/detect-image")
async def detect_image(file: UploadFile = File(...), lang: str = Query("en")):
    ct = chat_translations.get(lang, chat_translations["en"])
    t = translations.get(lang, translations["en"])
    try:
        img_path = os.path.join(tmp_dir, file.filename)
        with open(img_path, "wb") as f:
            f.write(await file.read())

        img = Image.open(img_path)
        width, height = img.size
        outcomes = [ct["plantHealthy"], ct["nitrogenDeficiency"], ct["pestDetected"]]
        bot_text = random.choice(outcomes)

        return {
            "status": "success",
            "filename": file.filename,
            "image_size": {"width": width, "height": height},
            "bot_response": bot_text,
            "message": t["image_detected"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
from fastapi import Form
from datetime import datetime

@app.post("/predict")
async def predict(
    prompt: str = Form(...),
    image: UploadFile = File(...),
    email: str = Form(...)  # pass user's email from frontend
):
    try:
        img_path = os.path.join(tmp_dir, image.filename)
        with open(img_path, "wb") as f:
            f.write(await image.read())

        caption = caption_image(img_path)

        answer = f"Image analysis completed. Detected content: {caption}."

        # ← Save chat history
        chats.insert_one({
            "email": email,
            "title": "Image Analysis",
            "message": prompt,
            "response": answer,
            "timestamp": datetime.utcnow()
        })

        return {
            "status": "success",
            "image_caption": caption,
            "user_prompt": prompt,
            "answer": answer
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
@app.get("/healthz")
def health_check():
    return {"status": "ok"}
