from fastapi import FastAPI
from app.api.fraud import router as fraud_router
from app.api.emergency import router as emergency_router
from app.api.language import router as language_router
from app.api.history import router as history_router
from app.api.voice import router as voice_router

app = FastAPI(
    title="SafePay Fraud Detection API",
    description="AI-Based Transaction Fraud Detection System",
    version="1.0.0"
)

# Register API routes
app.include_router(fraud_router)
app.include_router(emergency_router)
app.include_router(language_router)
app.include_router(history_router)
app.include_router(voice_router)


@app.get("/")
def home():
    return {
        "message": "SafePay Backend is Running",
        "status": "Success"
    }