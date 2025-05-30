from fastapi import APIRouter
from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import MongoClient
import base64
from typing import Optional
import os
from dotenv import load_dotenv
from urllib.parse import unquote

import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

router = APIRouter()

# MongoDB 연결 설정
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
DATABASE_NAME_USER_IMAGE = os.getenv("DATABASE_NAME_USER_IMAGE", "user_image")
DATABASE_NAME_USER_STATS = os.getenv("DATABASE_NAME_USER_STATS", "user_stats")

# MongoDB 클라이언트 초기화
client = None
db_user_image = None
db_user_stats = None

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

async def get_database_connection():
    """MongoDB 연결을 초기화하고 반환"""
    global client, db_user_image, db_user_stats
    
    if client is None:
        try:
            client = AsyncIOMotorClient(MONGODB_URL)
            # 연결 테스트
            await client.admin.command('ping')
            
            db_user_image = client[DATABASE_NAME_USER_IMAGE]
            db_user_stats = client[DATABASE_NAME_USER_STATS]
            
            logger.info("MongoDB 연결 성공")
        except Exception as e:
            logger.error(f"MongoDB 연결 실패: {e}")
            raise HTTPException(status_code=500, detail="Database connection failed")
    
    return db_user_image, db_user_stats

@router.get("/")
async def root():
    return {"message": "FastAPI MongoDB Image Server"}


@router.get("/user/{user_id}/image")
async def get_user_image(user_id: str):
    """
    user_id를 기반으로 user_stat의 character 값에 따라 
    matching되는 user_results의 이미지를 반환
    """
    # URL 디코딩
    decoded_user_id = unquote(user_id)
    logger.info(f"이미지 요청: user_id={decoded_user_id}")

    try:
        db_user_image, db_user_stats = await get_database_connection()
        
        # 1. user_stats 데이터베이스의 user_stat 컬렉션에서 character 값 조회
        user_stat = await db_user_stats.user_stat.find_one({"user_id": decoded_user_id})
        
        if not user_stat:
            logger.warning(f"사용자 통계 정보 없음: {decoded_user_id}")
            raise HTTPException(status_code=404, detail="User stat not found")
        
        character = user_stat.get("character")
        if not character or character not in CHARACTER_TAG_MAPPING:
            logger.warning(f"잘못된 character 값: {character}")
            raise HTTPException(status_code=400, detail="Invalid character value")
        
        # 2. character 값을 tag로 변환
        required_tag = CHARACTER_TAG_MAPPING[character]
        logger.info(f"태그 매핑: character={character} -> tag={required_tag}")
        
        # 3. user_image 데이터베이스의 user_results 컬렉션에서 이미지 조회
        user_img = await db_user_image.user_results.find_one({
            "user_id": decoded_user_id,
            "tag": required_tag
        })
        
        if not user_img:
            logger.warning(f"이미지 없음: user_id={decoded_user_id}, tag={required_tag}")
            raise HTTPException(
                status_code=404, 
                detail=f"Image not found for user {decoded_user_id} with tag '{required_tag}'"
            )
        
        # 4. Binary 이미지 데이터를 Base64로 인코딩
        image_data = user_img.get("image_data")
        if not image_data:
            raise HTTPException(status_code=404, detail="Image data not found")
        
        # Binary 데이터를 Base64로 인코딩
        base64_image = base64.b64encode(image_data).decode('utf-8')
        
        logger.info(f"이미지 반환 성공: user_id={decoded_user_id}")
        return {
            "user_id": decoded_user_id,
            "character": character,
            "tag": required_tag,
            "image_data": base64_image,
            "image_format": user_img.get("image_format", "jpeg")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"이미지 조회 오류: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
    
@router.get("/user/{user_id}/image/direct")
async def get_user_image_direct(user_id: str):
    """
    이미지를 직접 반환 (img src로 사용 가능)
    """
    decoded_user_id = unquote(user_id)
    
    try:
        db_user_image, db_user_stats = await get_database_connection()
        
        # user_stats에서 character 값 조회
        user_stat = await db_user_stats.user_stat.find_one({"user_id": decoded_user_id})
        
        if not user_stat:
            raise HTTPException(status_code=404, detail="User stat not found")
        
        character = user_stat.get("character")
        if not character or character not in CHARACTER_TAG_MAPPING:
            raise HTTPException(status_code=400, detail="Invalid character value")
        
        required_tag = CHARACTER_TAG_MAPPING[character]
        
        # user_image에서 이미지 조회
        user_img = await db_user_image.user_results.find_one({
            "user_id": decoded_user_id,
            "tag": required_tag
        })
        
        if not user_img:
            raise HTTPException(
                status_code=404, 
                detail=f"Image not found for user {decoded_user_id} with tag '{required_tag}'"
            )
        
        image_data = user_img.get("image_data")
        if not image_data:
            raise HTTPException(status_code=404, detail="Image data not found")
        
        # 이미지 포맷 결정 (기본값: jpeg)
        image_format = user_img.get("image_format", "jpeg")
        media_type = f"image/{image_format}"
        
        return Response(content=image_data, media_type=media_type)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"직접 이미지 조회 오류: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/user/{user_id}/character-info")
async def get_user_character_info(user_id: str):
    """
    사용자의 character 정보와 해당하는 tag 정보를 반환
    """
    decoded_user_id = unquote(user_id)
    
    try:
        db_user_image, db_user_stats = await get_database_connection()
        
        user_stat = await db_user_stats.user_stat.find_one({"user_id": decoded_user_id})
        
        if not user_stat:
            raise HTTPException(status_code=404, detail="User stat not found")
        
        character = user_stat.get("character")
        if not character or character not in CHARACTER_TAG_MAPPING:
            raise HTTPException(status_code=400, detail="Invalid character value")
        
        return {
            "user_id": decoded_user_id,
            "character": character,
            "tag": CHARACTER_TAG_MAPPING[character],
            "all_mappings": CHARACTER_TAG_MAPPING
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"캐릭터 정보 조회 오류: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(app, host="0.0.0.0", port=8000)