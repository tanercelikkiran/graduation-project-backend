from datetime import datetime, timezone
from pydantic import BaseModel, EmailStr, Field
from typing import List, Dict, Any, Optional


class UserOut(BaseModel):
    id: str
    username: str
    email: EmailStr
    learning_language: str
    system_language: str = "English"  # Default to English
    purpose: str
    level: str
    pyramids: List[str] = []  # List of pyramid IDs
    vocabulary_lists: List[Dict[str, Any]] = []
    saved_vocabularies: List[Dict[str, Any]] = []  # List of saved vocabulary words
    pyramid_stats: Dict[str, Any] = {}
    vocabulary_stats: Dict[str, Any] = {}
    xp: int = 0  # Kullanıcı deneyim puanı (varsayılan değer 0)


class UserIn(BaseModel):
    username: str
    email: EmailStr
    password: str
    learning_language: str
    system_language: str = "English"  # Default to English
    purpose: str
    level: str


class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    learning_language: Optional[str] = None
    system_language: Optional[str] = None
    purpose: Optional[str] = None
    level: Optional[str] = None
    xp: Optional[int] = None  # İsteğe bağlı XP güncellemesi


class User(BaseModel):
    id: str
    username: str
    email: EmailStr
    password_hash: str

    learning_language: str
    system_language: str = "English"  # Default to English
    purpose: str
    level: str

    is_active: bool = Field(True)

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    vocabulary_lists: List[str] = []
    pyramids: List[str] = []
    saved_vocabularies: List[Dict[str, Any]] = []  # List of saved vocabulary words

    xp: int = 0  # Kullanıcı deneyim puanı (varsayılan değer 0)

    pyramid_stats: Dict[str, Any] = {
        "time": 0,  # saniye cinsinden (integer)
        "sentences": 0,  # toplam cümle sayısı (integer)
        "success_rate": 0.0,  # başarı oranı (float)
    }

    vocabulary_stats: Dict[str, Any] = {
        "time": 0,  # saniye cinsinden (integer)
        "vocabularies": 0,  # toplam kelime sayısı (integer)
        "success_rate": 0.0,  # başarı oranı (float)
    }

class PasswordChange(BaseModel):
    current_password: str
    new_password: str

