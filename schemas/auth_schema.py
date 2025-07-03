from pydantic import BaseModel, EmailStr, Field
from typing import Optional

class RegisterSchema(BaseModel):
    email: str
    password: str
    first_name: str
    last_name: str
    phone: str
    photo_url: Optional[str] = None
    gender: str  # Add this line

class LoginSchema(BaseModel):
    email: EmailStr
    password: str

class UpdateProfileSchema(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    photo_url: Optional[str] = None


