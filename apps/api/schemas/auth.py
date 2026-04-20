"""Pydantic schemas for authentication and user management."""
from pydantic import BaseModel, EmailStr, Field
from uuid import UUID
from datetime import datetime
from typing import Optional


# --- Auth Schemas ---
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=255)
    org_name: str = Field(min_length=1, max_length=255)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


# --- User Schemas ---
class UserResponse(BaseModel):
    id: UUID
    org_id: Optional[UUID] = None
    role: str
    email: str
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None


# --- Organization Schemas ---
class OrgResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    plan: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class OrgUpdate(BaseModel):
    name: Optional[str] = None


# --- Auth Context ---
class AuthContext(BaseModel):
    """Represents the authenticated user context extracted from JWT."""
    user_id: UUID
    org_id: UUID
    role: str
    email: str
