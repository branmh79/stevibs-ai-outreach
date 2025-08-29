from fastapi import FastAPI
from routes.events import router as events_router

app = FastAPI()
app.include_router(events_router)

@app.get("/health")
async def health_check():
    return {"status": "healthy", "message": "API is working"}

@app.get("/test")  
async def test_endpoint():
    print("[API] Test endpoint called")
    return {"message": "Test endpoint works"}