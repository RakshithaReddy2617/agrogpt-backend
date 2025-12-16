from fastapi import APIRouter

router = APIRouter(
    prefix="/api/chat",
    tags=["Chat"]
)

@router.get("/")
def chat_demo():
    return {
        "message": "Chat endpoint placeholder — will connect to AgroGPT model later"
    }
