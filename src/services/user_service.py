from datetime import datetime, timezone
from fastapi import HTTPException, status
from bson import ObjectId
from typing import Optional
from src.database.database import user_table
from src.models.user import UserIn, UserOut, UserUpdate
from .authentication_service import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
    verify_jwt_token,
    verify_refresh_token,
)


def create_user(user_data: UserIn) -> dict:
    email = user_data.email.strip().lower()
    username = user_data.username.strip()
    password = user_data.password

    if not email or not username or not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email, kullanıcı adı ve şifre gereklidir",
        )

    if user_table.find_one({"email": email}):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email adresi zaten kayıtlı",
        )

    if user_table.find_one({"username": username}):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Kullanıcı adı zaten alınmış",
        )

    if len(password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Şifre en az 8 karakter olmalıdır",
        )

    if not any(char in "!@#$%^&*()-+_=<>?/.,:;{}[]|~" for char in password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Şifre en az bir özel karakter içermelidir",
        )

    if not any(char.isdigit() for char in password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Şifre en az bir rakam içermelidir",
        )

    hashed_password = hash_password(password)

    new_user = {
        "username": username,
        "email": email,
        "password_hash": hashed_password,
        "learning_language": user_data.learning_language.strip(),
        "system_language": user_data.system_language.strip(),
        "purpose": user_data.purpose.strip(),
        "level": user_data.level.strip(),
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
        "pyramids": [],
        "vocabulary_lists": [],
        "saved_vocabularies": [],
        "xp": 0,
        "pyramid_stats": {
            "time": 0,
            "sentences": 0,
            "success_rate": 0.0,
        },
        "vocabulary_stats": {
            "time": 0,
            "vocabularies": 0,
            "success_rate": 0.0,
        },
    }

    inserted = user_table.insert_one(new_user)

    user_out = UserOut(
        id=str(inserted.inserted_id),
        username=new_user["username"],
        email=new_user["email"],
        learning_language=new_user["learning_language"],
        purpose=new_user["purpose"],
        level=new_user["level"],
        xp=new_user["xp"],
        pyramids=new_user["pyramids"],
        vocabulary_lists=new_user["vocabulary_lists"],
        saved_vocabularies=new_user["saved_vocabularies"],
        pyramid_stats=new_user["pyramid_stats"],
        vocabulary_stats=new_user["vocabulary_stats"],
    )

    access_token = create_access_token({"sub": str(user_out.id)})
    refresh_token = create_refresh_token({"sub": str(user_out.id)})

    user_table.update_one(
        {"_id": inserted.inserted_id},
        {"$set": {"refresh_token": hash_password(refresh_token)}},
    )

    return {
        "user": user_out,
        "access_token": access_token,
        "refresh_token": refresh_token,
    }


def get_user_by_id(user_id: str) -> Optional[UserOut]:
    if not ObjectId.is_valid(user_id):
        return None

    user = user_table.find_one({"_id": ObjectId(user_id)})
    if not user:
        return None

    return UserOut(
        id=str(user["_id"]),
        username=user["username"],
        email=user["email"],
        learning_language=user["learning_language"],
        purpose=user["purpose"],
        level=user["level"],
        xp=user.get("xp", 0),
        pyramids=user["pyramids"],
        vocabulary_lists=user["vocabulary_lists"],
        saved_vocabularies=user.get("saved_vocabularies", []),
        pyramid_stats=user["pyramid_stats"],
        vocabulary_stats=user["vocabulary_stats"],
    )


def authenticate_user(email: str, password: str) -> Optional[dict]:
    user = user_table.find_one({"email": email.strip().lower()})
    if not user or not verify_password(password, user["password_hash"]):
        return None

    user_out = UserOut(
        id=str(user["_id"]),
        username=user["username"],
        email=user["email"],
        learning_language=user["learning_language"],
        purpose=user["purpose"],
        level=user["level"],
        xp=user.get("xp", 0),
        pyramids=user["pyramids"],
        vocabulary_lists=user["vocabulary_lists"],
        saved_vocabularies=user.get("saved_vocabularies", []),
        pyramid_stats=user["pyramid_stats"],
        vocabulary_stats=user["vocabulary_stats"],
    )

    access_token = create_access_token({"sub": str(user["_id"])})
    refresh_token = create_refresh_token({"sub": str(user["_id"])})

    user_table.update_one(
        {"_id": user["_id"]},
        {"$set": {"refresh_token": hash_password(refresh_token)}},
    )

    return {
        "user": user_out,
        "access_token": access_token,
        "refresh_token": refresh_token,
    }


def update_user(user_id: str, user_data: UserUpdate, current_user_id: str) -> bool:
    if user_id != current_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bu işlem için yetkiniz yok",
        )

    if not ObjectId.is_valid(user_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Geçersiz kullanıcı ID",
        )

    update_fields = {
        key: value.strip() if isinstance(value, str) else value
        for key, value in user_data.model_dump(exclude_unset=True).items()
    }

    if "username" in update_fields:
        if user_table.find_one(
            {"username": update_fields["username"], "_id": {"$ne": ObjectId(user_id)}}
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Kullanıcı adı zaten alınmış",
            )

    if "password" in update_fields:
        update_fields["password_hash"] = hash_password(update_fields.pop("password"))

    update_fields["updated_at"] = datetime.now(timezone.utc)

    if update_fields:
        user_table.update_one({"_id": ObjectId(user_id)}, {"$set": update_fields})
        return True

    return False


def delete_user(user_id: str, current_user_id: str) -> bool:
    if user_id != current_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bu işlem için yetkiniz yok",
        )

    if not ObjectId.is_valid(user_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Geçersiz kullanıcı ID",
        )

    result = user_table.delete_one({"_id": ObjectId(user_id)})
    return result.deleted_count > 0


def get_current_user(token: str) -> UserOut:
    payload = verify_jwt_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Geçersiz kimlik doğrulama bilgileri",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = get_user_by_id(payload["sub"])
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Kullanıcı bulunamadı",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


def refresh_access_token(refresh_token: str) -> dict:
    payload = verify_refresh_token(refresh_token)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Geçersiz yenileme token'ı",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload["sub"]
    if not ObjectId.is_valid(user_id):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Geçersiz kullanıcı kimliği",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = user_table.find_one({"_id": ObjectId(user_id)})
    if not user or "refresh_token" not in user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Yenileme token'ı ayarlanmamış veya kullanıcı bulunamadı",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not verify_password(refresh_token, user["refresh_token"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Yenileme token'ı geçersiz",
            headers={"WWW-Authenticate": "Bearer"},
        )

    new_access_token = create_access_token({"sub": user_id})
    new_refresh_token = create_refresh_token({"sub": user_id})

    user_table.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"refresh_token": hash_password(new_refresh_token)}},
    )

    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
    }


def invalidate_refresh_token(user_id: str) -> bool:
    if not ObjectId.is_valid(user_id):
        return False

    result = user_table.update_one(
        {"_id": ObjectId(user_id)},
        {"$unset": {"refresh_token": ""}},
    )

    return result.modified_count > 0


def change_password(user_id: str, current_password: str, new_password: str) -> bool:
    """
    Change a user's password after verifying their current password.
    
    Args:
        user_id: The ID of the user
        current_password: The user's current password for verification
        new_password: The new password to set
        
    Returns:
        bool: True if password was changed successfully, False otherwise
    """
    if not ObjectId.is_valid(user_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Geçersiz kullanıcı ID",
        )
    
    user = user_table.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Kullanıcı bulunamadı",
        )
    
    # Verify current password
    if not verify_password(current_password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mevcut şifre yanlış",
        )
    
    # Validate new password
    if len(new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Şifre en az 8 karakter olmalıdır",
        )

    if not any(char in "!@#$%^&*()-+_=<>?/.,:;{}[]|~" for char in new_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Şifre en az bir özel karakter içermelidir",
        )

    if not any(char.isdigit() for char in new_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Şifre en az bir rakam içermelidir",
        )
    
    # Hash and update the new password
    hashed_password = hash_password(new_password)
    result = user_table.update_one(
        {"_id": ObjectId(user_id)},
        {
            "$set": {
                "password_hash": hashed_password,
                "updated_at": datetime.now(timezone.utc)
            }
        }
    )
    
    return result.modified_count > 0
