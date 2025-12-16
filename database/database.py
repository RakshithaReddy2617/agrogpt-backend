from pymongo import MongoClient
import certifi
import os
from dotenv import load_dotenv

# ─── Load environment variables ───
load_dotenv()
MONGO_URL = os.getenv("MONGO_URL")

if not MONGO_URL:
    raise ValueError("❌ MONGO_URL not found in .env file. Please check your configuration.")

# ─── SSL/TLS Certificates ───
ca = certifi.where()

try:
    # ─── Create MongoDB client ───
    client = MongoClient(MONGO_URL, tls=True, tlsCAFile=ca)

    # ─── Access database ───
    db = client["agrogpt"]

    # ─── Collections ───
    users_collection = db["users"]         # Stores user info
    reports_collection = db["reports"]     # Stores reports
    chats_collection = db["chats"]         # Stores chat history

    print("✅ Connected to MongoDB successfully!")

except Exception as e:
    print("❌ MongoDB connection failed:", e)
