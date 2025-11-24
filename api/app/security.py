from datetime import datetime, timedelta
import os
from typing import Optional, Union
from passlib.context import CryptContext
from jose import jwt, JWTError

PWD_CTX = CryptContext(schemes=["argon2" , "bcrypt"], deprecated="auto")
SECRET_KEY = os.getenv("SECRET_KEY", "change-me-to-a-strong-secret")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15"))


def hash_password(password: str) -> str:
    if not isinstance(password, (str, bytes)):
        raise TypeError("password must be a string")
    # Argon2 accepts any length
    return PWD_CTX.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return PWD_CTX.verify(plain, hashed)


def create_access_token(subject: Union[str, int], expires_delta: Optional[timedelta] = None) -> str:
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode = {"sub": str(subject), "exp": expire}
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise
