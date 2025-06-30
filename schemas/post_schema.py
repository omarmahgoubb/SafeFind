from pydantic import BaseModel, Field
from typing import Optional

class MissingPostSchema(BaseModel):
    missing_name: str
    missing_age: int
    last_seen: str
    notes: Optional[str] = None

class FoundPostSchema(BaseModel):
    found_name: str
    estimated_age: int
    found_location: str
    notes: Optional[str] = None

class UpdatePostSchema(BaseModel):
    missing_name: Optional[str] = None
    missing_age: Optional[int] = None
    last_seen: Optional[str] = None
    notes: Optional[str] = None


