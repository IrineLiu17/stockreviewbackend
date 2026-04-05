"""
Verification routes - Handle SMS verification code sending and verification
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional
import random
import string
from datetime import datetime, timedelta
import redis
import os

router = APIRouter()

# In-memory storage for verification codes (for development)
# In production, use Redis or database
verification_codes = {}

# Redis client (optional, for production)
redis_client = None
try:
    redis_url = os.getenv("REDIS_URL")
    if redis_url:
        redis_client = redis.from_url(redis_url, decode_responses=True)
except:
    pass


class SendCodeRequest(BaseModel):
    phone_number: str = Field(..., description="Phone number to send verification code")


class VerifyCodeRequest(BaseModel):
    phone_number: str = Field(..., description="Phone number")
    code: str = Field(..., min_length=4, max_length=6, description="Verification code")


class SendCodeResponse(BaseModel):
    success: bool
    message: str
    expires_in: int = Field(default=300, description="Code expiration time in seconds")


class VerifyCodeResponse(BaseModel):
    success: bool
    message: str
    token: Optional[str] = None  # JWT token for authenticated requests


def generate_code(length: int = 6) -> str:
    """Generate a random numeric verification code"""
    return ''.join(random.choices(string.digits, k=length))


def store_code(phone_number: str, code: str, expires_in: int = 300):
    """Store verification code with expiration"""
    expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
    
    if redis_client:
        # Use Redis for production
        redis_client.setex(
            f"verification:{phone_number}",
            expires_in,
            code
        )
    else:
        # Use in-memory storage for development
        verification_codes[phone_number] = {
            "code": code,
            "expires_at": expires_at
        }


def verify_code(phone_number: str, code: str) -> bool:
    """Verify the code for a phone number"""
    stored_code = None
    
    if redis_client:
        # Get from Redis
        stored_code = redis_client.get(f"verification:{phone_number}")
        if stored_code:
            redis_client.delete(f"verification:{phone_number}")
    else:
        # Get from in-memory storage
        if phone_number in verification_codes:
            stored_data = verification_codes[phone_number]
            if datetime.utcnow() < stored_data["expires_at"]:
                stored_code = stored_data["code"]
                del verification_codes[phone_number]
    
    return stored_code == code


async def send_sms_code(phone_number: str, code: str) -> bool:
    """
    Send SMS verification code
    TODO: Integrate with SMS service provider (Twilio, AWS SNS, etc.)
    
    For now, this is a placeholder. In production, integrate with:
    - Twilio: https://www.twilio.com/docs/sms
    - AWS SNS: https://aws.amazon.com/sns/
    - Alibaba Cloud SMS: https://www.alibabacloud.com/product/sms
    - Tencent Cloud SMS: https://cloud.tencent.com/product/sms
    """
    # TODO: Implement actual SMS sending
    # Example with Twilio:
    # from twilio.rest import Client
    # client = Client(account_sid, auth_token)
    # message = client.messages.create(
    #     body=f"Your verification code is: {code}",
    #     from_='+1234567890',
    #     to=phone_number
    # )
    
    # For development, just log the code
    print(f"[DEV] Verification code for {phone_number}: {code}")
    return True


@router.post("/send", response_model=SendCodeResponse)
async def send_verification_code(request: SendCodeRequest):
    """
    Send verification code to phone number
    """
    # Clean phone number (remove spaces, dashes, etc.)
    phone_number = request.phone_number.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    
    # Validate phone number format
    if not phone_number.startswith("1") or len(phone_number) != 11:
        raise HTTPException(
            status_code=400,
            detail="Invalid phone number format. Expected 11-digit Chinese mobile number."
        )
    
    # Generate 6-digit code
    code = generate_code(6)
    
    # Store code with 5-minute expiration
    store_code(phone_number, code, expires_in=300)
    
    # Send SMS (async, don't wait for it)
    try:
        await send_sms_code(phone_number, code)
    except Exception as e:
        # Log error but don't fail the request
        print(f"Error sending SMS: {e}")
    
    return SendCodeResponse(
        success=True,
        message="Verification code sent successfully",
        expires_in=300
    )


@router.post("/verify", response_model=VerifyCodeResponse)
async def verify_verification_code(request: VerifyCodeRequest):
    """
    Verify the code and return authentication token
    """
    # Clean phone number
    phone_number = request.phone_number.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    
    # Verify code
    if not verify_code(phone_number, request.code):
        raise HTTPException(
            status_code=400,
            detail="Invalid or expired verification code"
        )
    
    # TODO: Create user session/token
    # For now, we'll use Supabase to create or get user
    # In production, you might want to:
    # 1. Create user in Supabase if not exists
    # 2. Generate JWT token
    # 3. Return token to client
    
    # Placeholder: In production, integrate with Supabase auth
    # from supabase import Client
    # supabase = get_supabase()
    # user = supabase.auth.sign_in_with_password({
    #     "phone": phone_number,
    #     "password": code  # Or use OTP
    # })
    
    return VerifyCodeResponse(
        success=True,
        message="Verification successful",
        token=None  # TODO: Return actual JWT token
    )


@router.get("/status/{phone_number}")
async def get_verification_status(phone_number: str):
    """
    Check if a verification code exists for a phone number
    (For debugging purposes)
    """
    has_code = False
    
    if redis_client:
        has_code = redis_client.exists(f"verification:{phone_number}") > 0
    else:
        if phone_number in verification_codes:
            stored_data = verification_codes[phone_number]
            has_code = datetime.utcnow() < stored_data["expires_at"]
    
    return {
        "has_code": has_code,
        "phone_number": phone_number
    }
