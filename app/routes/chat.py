from fastapi import APIRouter
router = APIRouter(
    prefix="/chat",
    tags=["Chat"]
)

@router.post("/")
def chat(request: dict):
    message = request["message"]
    if "colombo" in message.lower():
        return {"reply": "Colombo's max temperature today is 31°C."}
    return {"reply": "Please ask about a valid location."}