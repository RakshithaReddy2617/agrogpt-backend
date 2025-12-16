from pydantic import BaseModel

class User(BaseModel):
    phone: str
    name: str
    password: str
    role: str = "user"
    totp_secret: str = None  # New field for TOTP
