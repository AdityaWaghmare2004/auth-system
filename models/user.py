
from pydantic import BaseModel, EmailStr

class SignupRequest(BaseModel):
    email: EmailStr
    password: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str   

class VerifyOTPRequest(BaseModel):
    email: EmailStr
    otp: str

class RefreshRequest(BaseModel):
    email: EmailStr
    refresh_token: str