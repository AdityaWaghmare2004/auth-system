from fastapi import FastAPI
from routes.auth import router as auth_router
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from utils.limiter import limiter

app = FastAPI()
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.include_router(auth_router, prefix ="/auth", tags=["auth"])

@app.get("/")
async def root():
    return {"message": "auth system running"}