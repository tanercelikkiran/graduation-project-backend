from datetime import datetime, timedelta, timezone
import bcrypt
from src.models.user import UserOut
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
import jwt
from src.settings import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES
from pydantic import BaseModel
from src.database.database import user_table
from bson import ObjectId

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")


class Token(BaseModel):
    access_token: str
    token_type: str


def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode = data.copy()
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(data: dict) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=7)
    to_encode = data.copy()
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


async def verify_token(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            raise credentials_exception

        if not ObjectId.is_valid(user_id):
            raise credentials_exception

        user_doc = user_table.find_one({"_id": ObjectId(user_id)})
        if not user_doc:
            raise credentials_exception

        return UserOut(
            id=str(user_doc["_id"]),
            username=user_doc["username"],
            email=user_doc["email"],
            learning_language=user_doc["learning_language"],
            system_language=user_doc["system_language"],
            purpose=user_doc["purpose"],
            level=user_doc["level"],
            xp=user_doc.get("xp", 0),
            refresh_token=user_doc.get("refresh_token", ""),
        )
    except jwt.InvalidTokenError:
        raise credentials_exception


def verify_jwt_token(token: str) -> dict:
    """Verify a JWT token and return the payload."""
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.InvalidTokenError:
        raise credentials_exception


def verify_refresh_token(token: str) -> dict:
    """Verify a refresh token and return the payload."""
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate refresh token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.InvalidTokenError:
        raise credentials_exception


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    salt = bcrypt.gensalt()  # Generate a salt
    hashed_password = bcrypt.hashpw(password.encode(), salt)  # Hash the password
    return hashed_password.decode()  # Convert bytes to string for storage


def verify_password(password: str, hashed_password: str) -> bool:
    """Check if the given password matches the stored hashed password."""
    return bcrypt.checkpw(password.encode(), hashed_password.encode())


async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user_doc = user_table.find_one({"email": form_data.username})
    if not user_doc or not verify_password(
        form_data.password, user_doc["password_hash"]
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user_doc["_id"])}, expires_delta=access_token_expires
    )
    refresh_token = create_refresh_token(data={"sub": str(user_doc["_id"])})
    user_table.update_one(
        {"_id": user_doc["_id"]},
        {"$set": {"refresh_token": hash_password(refresh_token)}},
    )
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user_id": str(user_doc["_id"]),
    }
