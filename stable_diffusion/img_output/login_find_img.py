from fastapi import APIRouter
from fastapi import FastAPI, HTTPException, Response, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel
import base64
import jwt
import hashlib
import os
from datetime import datetime, timedelta
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

router = APIRouter()

# JWT 설정
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-here")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# MongoDB 연결 설정
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
DATABASE_NAME = os.getenv("DATABASE_NAME", "your_database_name")

client = AsyncIOMotorClient(MONGODB_URL)
db = client[DATABASE_NAME]

# Security
security = HTTPBearer()

# Character 값과 Tag 매핑
CHARACTER_TAG_MAPPING = {
    1: "very fat",
    2: "fat", 
    3: "a little fat",
    4: "normal",
    5: "slightly muscular",
    6: "muscular",
    7: "very muscular"
}

# Pydantic 모델
class LoginRequest(BaseModel):
    username: str
    password: str

class UserResponse(BaseModel):
    user_id: str
    username: str
    character: Optional[int] = None

class ImageResponse(BaseModel):
    user_id: str
    character: int
    tag: str
    image_data: str
    image_format: str

# 유틸리티 함수
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return user_id
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

@router.post("/auth/login")
async def login(login_data: LoginRequest):
    """로그인 엔드포인트"""
    try:
        # users 컬렉션에서 사용자 조회 (username과 password로)
        user = await db.users.find_one({
            "username": login_data.username,
            "password": hash_password(login_data.password)
        })
        
        if not user:
            raise HTTPException(status_code=401, detail="Invalid username or password")
        
        # JWT 토큰 생성
        access_token = create_access_token(data={"sub": user["user_id"]})
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user_id": user["user_id"],
            "username": user["username"]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Login failed: {str(e)}")

@router.get("/auth/me")
async def get_current_user(current_user_id: str = Depends(verify_token)):
    """현재 로그인한 사용자 정보 조회"""
    try:
        user = await db.users.find_one({"user_id": current_user_id})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # user_stat에서 character 정보 가져오기
        user_stat = await db.user_stat.find_one({"user_id": current_user_id})
        character = user_stat.get("character") if user_stat else None
        
        return {
            "user_id": user["user_id"],
            "username": user["username"],
            "character": character
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get user info: {str(e)}")

@router.get("/home/image")
async def get_current_user_image(current_user_id: str = Depends(verify_token)):
    """현재 로그인한 사용자의 캐릭터 이미지 조회"""
    try:
        # user_stat에서 해당 user_id의 character 값 조회
        user_stat = await db.user_stat.find_one({"user_id": current_user_id})
        
        if not user_stat:
            raise HTTPException(status_code=404, detail="User stat not found")
        
        character = user_stat.get("character")
        if not character or character not in CHARACTER_TAG_MAPPING:
            raise HTTPException(status_code=400, detail="Invalid character value")
        
        # character 값을 tag로 변환
        required_tag = CHARACTER_TAG_MAPPING[character]
        
        # user_img에서 user_id와 tag가 일치하는 이미지 조회
        user_img = await db.user_img.find_one({
            "user_id": current_user_id,
            "tag": required_tag
        })
        
        if not user_img:
            raise HTTPException(
                status_code=404, 
                detail=f"Image not found for user {current_user_id} with tag '{required_tag}'"
            )
        
        # Binary 이미지 데이터를 Base64로 인코딩
        image_data = user_img.get("image_data")
        if not image_data:
            raise HTTPException(status_code=404, detail="Image data not found")
        
        base64_image = base64.b64encode(image_data).decode('utf-8')
        
        return {
            "user_id": current_user_id,
            "character": character,
            "tag": required_tag,
            "image_data": base64_image,
            "image_format": user_img.get("image_format", "jpeg")
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/home/image/direct")
async def get_current_user_image_direct(current_user_id: str = Depends(verify_token)):
    """현재 로그인한 사용자의 이미지를 직접 반환"""
    try:
        user_stat = await db.user_stat.find_one({"user_id": current_user_id})
        
        if not user_stat:
            raise HTTPException(status_code=404, detail="User stat not found")
        
        character = user_stat.get("character")
        if not character or character not in CHARACTER_TAG_MAPPING:
            raise HTTPException(status_code=400, detail="Invalid character value")
        
        required_tag = CHARACTER_TAG_MAPPING[character]
        
        user_img = await db.user_img.find_one({
            "user_id": current_user_id,
            "tag": required_tag
        })
        
        if not user_img:
            raise HTTPException(
                status_code=404, 
                detail=f"Image not found for user {current_user_id} with tag '{required_tag}'"
            )
        
        image_data = user_img.get("image_data")
        if not image_data:
            raise HTTPException(status_code=404, detail="Image data not found")
        
        image_format = user_img.get("image_format", "jpeg")
        media_type = f"image/{image_format}"
        
        return Response(content=image_data, media_type=media_type)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# 기존 엔드포인트들 (관리자용 또는 개발용)
@router.get("/user/{user_id}/image")
async def get_user_image_by_id(user_id: str, current_user_id: str = Depends(verify_token)):
    """특정 사용자의 이미지 조회 (인증 필요)"""
    try:
        user_stat = await db.user_stat.find_one({"user_id": user_id})
        
        if not user_stat:
            raise HTTPException(status_code=404, detail="User stat not found")
        
        character = user_stat.get("character")
        if not character or character not in CHARACTER_TAG_MAPPING:
            raise HTTPException(status_code=400, detail="Invalid character value")
        
        required_tag = CHARACTER_TAG_MAPPING[character]
        
        user_img = await db.user_img.find_one({
            "user_id": user_id,
            "tag": required_tag
        })
        
        if not user_img:
            raise HTTPException(
                status_code=404, 
                detail=f"Image not found for user {user_id} with tag '{required_tag}'"
            )
        
        image_data = user_img.get("image_data")
        if not image_data:
            raise HTTPException(status_code=404, detail="Image data not found")
        
        base64_image = base64.b64encode(image_data).decode('utf-8')
        
        return {
            "user_id": user_id,
            "character": character,
            "tag": required_tag,
            "image_data": base64_image,
            "image_format": user_img.get("image_format", "jpeg")
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.post("/auth/logout")
async def logout(current_user_id: str = Depends(verify_token)):
    """로그아웃 (클라이언트에서 토큰 삭제 필요)"""
    return {"message": "Successfully logged out"}

# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(app, host="0.0.0.0", port=8000)