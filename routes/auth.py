from fastapi import APIRouter, HTTPException, status, Depends, Request
from models.user import SignupRequest, LoginRequest, VerifyOTPRequest, RefreshRequest
from db.mongo import db
from utils.jwt_handler import create_access_token, create_refresh_token, verify_access_token, get_current_user
import bcrypt
from db.redis_client import redis_client
from utils.limiter import limiter
from utils.otp import generate_otp
from tasks.email_tasks import send_otp_email
from utils.bloom_filter_instance import email_bloom_filter
from utils.kafka_producer import producer

router = APIRouter()

@router.post("/signup", status_code=status.HTTP_201_CREATED)
async def signup(data: SignupRequest):
    """Register a new user via Kafka-based batch writing with write-through Redis cache."""

    # 1. Bloom filter — cheapest possible duplicate check
    if email_bloom_filter.contains(data.email):
        existing = await db.users.find_one({"email": data.email})
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered"
            )
        cached = redis_client.hgetall(f"user:{data.email}")
        if cached:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered"
            )

    # 2. Hash the password
    hashed = bcrypt.hashpw(data.password.encode("utf-8"), bcrypt.gensalt())
    hashed_str = hashed.decode("utf-8")

    # 3. Write-through cache — store in Redis immediately
    redis_client.hset(f"user:{data.email}", mapping={
        "email": data.email,
        "password": hashed_str,
        "verified": "false"
    })

    # 4. Publish to Kafka — consumer will batch insert into MongoDB
    user_payload = {
        "email": data.email,
        "password": hashed_str,
        "verified": False
    }
    producer.send("user_signups", value=user_payload)
    producer.flush()

    # 5. Add to bloom filter
    email_bloom_filter.add(data.email)

    # 6. Generate and send OTP
    otp_code = generate_otp()
    redis_client.setex(f"otp:{data.email}", 300, otp_code)
    send_otp_email.delay(data.email, otp_code)

    return {"message": "User created successfully"}
@router.post("/login")
@limiter.limit("5/minute")
async def login(request: Request, data: LoginRequest):
    """Authenticate a user and issue an access token and refresh token."""
    cached_user = redis_client.hgetall(f"user:{data.email}")

    if cached_user:
        stored_hash = cached_user["password"]
    else:
        user = await db.users.find_one({"email": data.email})
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        stored_hash = user["password"].decode("utf-8")

        redis_client.hset(f"user:{data.email}", mapping={
            "email": data.email,
            "password": stored_hash
        })

    password_matches = bcrypt.checkpw(data.password.encode("utf-8"), stored_hash.encode("utf-8"))
    if not password_matches:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    token = create_access_token({"email": data.email})
    refresh_token = create_refresh_token({"email": data.email})

    redis_client.setex(f"refresh:{data.email}", 60 * 60 * 24 * 7, refresh_token)

    return {
        "message": "Login successful",
        "access_token": token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }


@router.post("/verify-otp")
async def verify_otp(data: VerifyOTPRequest):
    """Verify a user's email using the OTP code sent during signup."""
    stored_otp = redis_client.get(f"otp:{data.email}")

    if stored_otp is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OTP expired or not found"
        )

    if stored_otp != data.otp:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid OTP"
        )

    await db.users.update_one({"email": data.email}, {"$set": {"verified": True}})
    redis_client.delete(f"otp:{data.email}")

    return {"message": "Email verified successfully"}


@router.post("/refresh")
async def refresh_token_route(data: RefreshRequest):
    """Exchange a valid refresh token for a new short-lived access token."""
    stored_token = redis_client.get(f"refresh:{data.email}")

    if stored_token is None or stored_token != data.refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )

    payload = verify_access_token(data.refresh_token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )

    new_access_token = create_access_token({"email": data.email})

    return {"access_token": new_access_token, "token_type": "bearer"}


@router.get("/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    """Return the email of the currently authenticated user."""
    return {"email": current_user["email"]}