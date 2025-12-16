# routes/auth.py
from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel
from datetime import datetime, timedelta
from jose import jwt
from database.database import users_collection  # adapt if path different
from utils.config import settings  # use your existing config module
import os
import pyotp
import qrcode
import io

# Config (use settings.JWT_SECRET or fallback env)
SECRET_KEY = getattr(settings, "JWT_SECRET", os.getenv("JWT_SECRET", "supersecretjwtkey"))
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 3

router = APIRouter(prefix="/api/auth", tags=["Auth"])

# ------------------ helpers ------------------
def normalize_phone(phone: str) -> str:
    if not phone:
        return phone
    phone = phone.strip().replace(" ", "").replace("-", "")
    if phone.startswith("+91"):
        phone = phone[3:]
    return phone

def create_access_token(data: dict, expires_delta: timedelta = timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)):
    to_encode = data.copy()
    expire = datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# ------------------ request models ------------------
class SignupModel(BaseModel):
    name: str
    phone: str

class LoginModel(BaseModel):
    phone: str
    otp: str

class TOTPVerifyModel(BaseModel):
    phone: str
    token: str

class TOTPLoginModel(BaseModel):
    phone: str
    totp: str

# ------------------ routes ------------------

@router.post("/signup")
def signup(user: SignupModel):
    phone = normalize_phone(user.phone)
    existing_user = users_collection.find_one({"phone": phone})
    if existing_user:
        return {"status": "error", "message": "User already exists"}
    users_collection.insert_one({
        "name": user.name,
        "phone": phone,
        "otp": "1234",
        "totp_secret": None,
        "created_at": datetime.utcnow()
    })
    return {
        "status": "success",
        "message": f"Signup success for {user.name}. Use OTP 1234 to login.",
        "data": {"name": user.name, "phone": phone}
    }

@router.post("/login")
def login(data: LoginModel):
    phone = normalize_phone(data.phone)
    user = users_collection.find_one({"phone": phone})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if data.otp != "1234":
        raise HTTPException(status_code=400, detail="Invalid OTP")
    token = create_access_token({"sub": phone})
    return {
        "status": "success",
        "message": f"Login success for {phone}",
        "token": token,
        "data": {"name": user.get("name"), "phone": phone, "totp_configured": bool(user.get("totp_secret"))}
    }

@router.get("/generate-totp/{phone}")
def generate_totp(phone: str):
    phone = normalize_phone(phone)
    user = users_collection.find_one({"phone": phone})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    totp_secret = user.get("totp_secret")
    if not totp_secret:
        totp_secret = pyotp.random_base32()
        users_collection.update_one({"phone": phone}, {"$set": {"totp_secret": totp_secret}})

    issuer_name = "AgroGPT"
    user_label = user.get("name") or phone
    provisioning_uri = pyotp.totp.TOTP(totp_secret).provisioning_uri(name=user_label, issuer_name=issuer_name)

    qr = qrcode.QRCode(border=2)
    qr.add_data(provisioning_uri)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    bio = io.BytesIO()
    img.save(bio, format="PNG")
    bio.seek(0)
    return Response(content=bio.getvalue(), media_type="image/png")

@router.post("/verify-totp")
def verify_totp(data: TOTPVerifyModel):
    phone = normalize_phone(data.phone)
    user = users_collection.find_one({"phone": phone})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    totp_secret = user.get("totp_secret")
    if not totp_secret:
        raise HTTPException(status_code=400, detail="TOTP not configured for this user")

    totp = pyotp.TOTP(totp_secret)
    if not totp.verify(data.token, valid_window=1):
        raise HTTPException(status_code=400, detail="Invalid TOTP token")

    token = create_access_token({"sub": phone})
    return {"status": "success", "message": f"TOTP verified for {phone}", "token": token, "data": {"name": user.get("name"), "phone": phone}}

@router.post("/login-totp")
def login_totp(data: TOTPLoginModel):
    phone = normalize_phone(data.phone)
    user = users_collection.find_one({"phone": phone})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    totp_secret = user.get("totp_secret")
    if not totp_secret:
        raise HTTPException(status_code=400, detail="TOTP not configured for this user")
    totp = pyotp.TOTP(totp_secret)
    if not totp.verify(data.totp, valid_window=1):
        raise HTTPException(status_code=400, detail="Invalid TOTP token")
    token = create_access_token({"sub": phone})
    return {"status": "success", "message": f"Login success for {phone}", "token": token, "data": {"name": user.get("name"), "phone": phone}}
