import jwt
import bcrypt
from datetime import datetime, timedelta
from fastapi import HTTPException, Request

SECRET_KEY = "ce89b8547711875c59e267b9a4369c9d733055e8f3be21a546818b086e26d236"
ALGORITHM = "HS256"

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))

def create_token(data: dict):
    data["exp"] = datetime.utcnow() + timedelta(hours=12)
    return jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str):
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
def get_current_user(request:Request):
    token = request.cookies.get("auth")
    if not token:
        return None
    
    try:
        return decode_token(token)
    except:
        return None
