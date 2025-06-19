from fastapi import FastAPI, File, UploadFile, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import os
import shutil
import tempfile
from pathlib import Path
import json
import asyncio
import logging
import traceback
from typing import Optional
from bson import ObjectId
from datetime import datetime
import pytz  # ✅ 추가

# ✅ 한국 시간대 설정
KST = pytz.timezone('Asia/Seoul')

def get_korea_time():
    """한국 시간 반환"""
    return datetime.now(KST)


from config.settings import (
    OPENAI_API_KEY,
    FUNCTION_DEFINITIONS,
    INTENT_RECOGNITION_PROMPT,
    INBODY_QUESTIONS,
    WORKOUT_QUESTIONS,
    SYSTEM_PROMPT
)
from modules.pdf_processor import PDFProcessor
from modules.routine_generator import AIAnalyzer
from modules.vector_store import VectorStore
from modules.user_vector_store import UserVectorStore
from modules.utils import validate_uploaded_file, create_upload_directory, save_uploaded_file
from modules.chat_session import session_manager, SessionState

app = FastAPI()
UPLOAD_DIR = create_upload_directory()

class CustomJSONResponse(JSONResponse):
    def render(self, content) -> bytes:
        def convert_objectid_and_datetime(obj):
            if isinstance(obj, ObjectId):
                return str(obj)
            elif isinstance(obj, datetime):
                return obj.isoformat()
            elif isinstance(obj, dict):
                return {key: convert_objectid_and_datetime(value) for key, value in obj.items()}
            elif isinstance(obj, list):
                return [convert_objectid_and_datetime(item) for item in obj]
            return obj
        
        content = convert_objectid_and_datetime(content)
        return super().render(content)

# 로거 설정
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# CORS 설정 - 다른 컴퓨터에서 접근 허용
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000", 
        "http://127.0.0.1:3000",
        "http://192.168.0.*:3000",  # 같은 네트워크 내 모든 IP
        "*"  # 개발 환경에서만 사용 (보안상 주의)
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# AI 분석기 초기화
analyzer = AIAnalyzer()
pdf_processor = PDFProcessor()

# Request/Response 모델들
class ChatMessage(BaseModel):
    message: str
    session_id: Optional[str] = None
    user_id: Optional[str] = None

class ChatResponse(BaseModel):
    success: bool
    session_id: str
    messages: list
    latest_message: dict
    session_info: dict
    show_buttons: Optional[bool] = False
    button_options: Optional[list] = None
    show_file_upload: Optional[bool] = False
    show_input: Optional[bool] = False
    input_placeholder: Optional[str] = None
    routine_data: Optional[list] = None

@app.get("/")
async def root():
    """루트 엔드포인트"""
    return CustomJSONResponse({"message": "AI Fitness Coach API is running", "status": "healthy"})

@app.get("/health")
async def health_check():
    """헬스 체크"""
    try:
        status = analyzer.get_loading_status()
        user_vector_stats = analyzer.user_vector_store.get_collection_stats()
        
        response_data = {
            "status": "healthy",
            "ai_analyzer": status,
            "pdf_processor": True,
            "user_vector_store": user_vector_stats,
            "active_sessions": len(session_manager.sessions)
        }
        return CustomJSONResponse(response_data)
    except Exception as e:
        return CustomJSONResponse({
            "status": "unhealthy",
            "error": str(e)
        })

@app.post("/api/chat")
async def chat(data: ChatMessage):
    """통합 채팅 엔드포인트 - 모든 대화 상태를 백엔드에서 관리"""
    try:
        logger.info(f"채팅 요청: {data.message[:50]}... (세션: {data.session_id}, 사용자: {data.user_id})")
        
        # 세션 매니저를 통해 메시지 처리 (user_id 전달)
        response = await session_manager.process_message(
            session_id=data.session_id,
            message=data.message,
            analyzer=analyzer,
            user_id=data.user_id
        )
        
        return CustomJSONResponse(response)
        
    except Exception as e:
        logger.error(f"채팅 처리 중 오류: {str(e)}")
        logger.error(traceback.format_exc())
        return CustomJSONResponse({
            "success": False,
            "error": "일시적인 오류가 발생했습니다. 다시 시도해주세요.",
            "detail": str(e)
        })

@app.post("/api/inbody/analyze")
async def analyze_inbody(file: UploadFile = File(...), session_id: str = None, user_id: str = None):
    """인바디 PDF 분석"""
    try:
        logger.info(f"PDF 분석 시작: {file.filename} (세션: {session_id}, 사용자: {user_id})")
        
        # 파일 검증
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(
                status_code=400,
                detail="PDF 파일만 업로드 가능합니다."
            )

        # 파일 크기 체크 (10MB 제한)
        content = await file.read()
        if len(content) > 10 * 1024 * 1024:
            raise HTTPException(
                status_code=400,
                detail="파일 크기가 너무 큽니다. (최대 10MB)"
            )

        # 임시 파일로 저장
        temp_dir = os.path.join(tempfile.gettempdir(), 'mypt_uploads')
        os.makedirs(temp_dir, exist_ok=True)
        
        temp_path = os.path.join(temp_dir, f"inbody_{file.filename}")
        
        try:
            with open(temp_path, "wb") as buffer:
                buffer.write(content)
            
            logger.info("PDF 텍스트 추출 중...")
            inbody_text = pdf_processor.process_pdf(temp_path)
            
            if not inbody_text or len(inbody_text.strip()) < 50:
                raise ValueError("PDF에서 충분한 텍스트를 추출할 수 없습니다.")
            
            logger.info(f"추출된 텍스트 길이: {len(inbody_text)}")
            
            # 구조화된 인바디 데이터 추출
            inbody_data = await extract_inbody_data_structured(inbody_text)
            
            # 사용자 벡터DB에 인바디 데이터 저장 (user_id 기반)
            if user_id and user_id != "None" and user_id != "null":
                try:
                    analyzer.user_vector_store.add_user_inbody_data(user_id, inbody_data)
                    logger.info(f"사용자 {user_id}의 인바디 데이터를 벡터DB에 저장완료")
                except Exception as e:
                    logger.error(f"인바디 데이터 벡터DB 저장 실패: {str(e)}")
            
            # 세션 매니저를 통해 인바디 데이터 처리 (user_id 전달)
            response = await session_manager.process_inbody_pdf(session_id, inbody_data, user_id)
            
            logger.info("PDF 분석 완료")
            return response
            
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
                
    except Exception as e:
        logger.error(f"PDF 분석 중 오류 발생: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"PDF 분석 실패: {str(e)}"
        )

async def extract_inbody_data_structured(text: str) -> dict:
    """구조화된 인바디 데이터 추출"""
    try:
        # Function Calling을 사용한 데이터 추출
        response = await analyzer.client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": """인바디 검사 결과에서 다음 정보를 정확히 추출하세요:
                    - 성별: "남성" 또는 "여성"
                    - 나이: 숫자 (단위 제거)
                    - 신장: cm 단위 숫자 (단위 제거)
                    - 체중: kg 단위 숫자 (단위 제거)
                    - 골격근량: kg 단위 숫자 (없으면 null)
                    - 체지방률: % 단위 숫자 (없으면 null)
                    - BMI: 숫자 (없으면 null)
                    - 기초대사율: kcal 단위 숫자 (없으면 null)
                    
                    반드시 숫자 값만 추출하고 단위는 제거하세요."""
                },
                {"role": "user", "content": f"다음 인바디 결과를 분석해주세요:\n\n{text[:3000]}"}
            ],
            tools=[{
                "type": "function",
                "function": {
                    "name": "extract_inbody_data",
                    "description": "인바디 데이터 추출",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "gender": {"type": "string", "enum": ["남성", "여성"]},
                            "age": {"type": "integer", "minimum": 1, "maximum": 120},
                            "height": {"type": "number", "minimum": 100, "maximum": 250},
                            "weight": {"type": "number", "minimum": 30, "maximum": 200},
                            "muscle_mass": {"type": ["number", "null"]},
                            "body_fat": {"type": ["number", "null"]},
                            "bmi": {"type": ["number", "null"]},
                            "basal_metabolic_rate": {"type": ["integer", "null"]}
                        },
                        "required": ["gender", "age", "height", "weight"]
                    }
                }
            }],
            tool_choice={"type": "function", "function": {"name": "extract_inbody_data"}}
        )
        
        if response.choices[0].message.tool_calls:
            function_call = response.choices[0].message.tool_calls[0].function
            inbody_data = json.loads(function_call.arguments)
            
            # 데이터 검증 및 계산
            validated_data = {
                "gender": inbody_data.get("gender"),
                "age": int(inbody_data.get("age", 0)),
                "height": float(inbody_data.get("height", 0)),
                "weight": float(inbody_data.get("weight", 0)),
                "muscle_mass": inbody_data.get("muscle_mass"),
                "body_fat": inbody_data.get("body_fat"),
                "bmi": inbody_data.get("bmi"),
                "basal_metabolic_rate": inbody_data.get("basal_metabolic_rate")
            }
            
            # BMI 계산 (없는 경우)
            if not validated_data["bmi"] and validated_data["height"] and validated_data["weight"]:
                height_m = validated_data["height"] / 100
                validated_data["bmi"] = round(validated_data["weight"] / (height_m ** 2), 1)
            
            # 기초대사율 계산 (없는 경우)
            if not validated_data["basal_metabolic_rate"]:
                if validated_data["gender"] == "남성":
                    bmr = (10 * validated_data["weight"]) + (6.25 * validated_data["height"]) - (5 * validated_data["age"]) + 5
                else:
                    bmr = (10 * validated_data["weight"]) + (6.25 * validated_data["height"]) - (5 * validated_data["age"]) - 161
                validated_data["basal_metabolic_rate"] = int(bmr)
            
            return validated_data
        else:
            raise ValueError("Function calling에서 응답을 받지 못했습니다.")
            
    except Exception as e:
        logger.error(f"구조화된 데이터 추출 실패: {str(e)}")
        raise

@app.get("/api/session/{session_id}")
async def get_session_info(session_id: str):
    """세션 정보 조회"""
    try:
        session = session_manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")
        
        return {
            "success": True,
            "session_info": session.get_session_info(),
            "messages": session.messages
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"세션 정보 조회 실패: {str(e)}")
        raise HTTPException(status_code=500, detail="세션 정보 조회에 실패했습니다.")

@app.delete("/api/session/{session_id}")
async def delete_session(session_id: str):
    """세션 삭제"""
    try:
        deleted = session_manager.delete_session(session_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")
        
        return {"success": True, "message": "세션이 삭제되었습니다."}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"세션 삭제 실패: {str(e)}")
        raise HTTPException(status_code=500, detail="세션 삭제에 실패했습니다.")

@app.post("/api/session/reset")
async def reset_session(data: dict):
    """세션 초기화 - chat_session_manager에 모든 로직 위임"""
    try:
        session_id = data.get("session_id")
        user_id = data.get("user_id")
        
        logger.info(f"세션 초기화 요청: session_id={session_id}, user_id={user_id}")
        
        # 기존 세션 삭제
        if session_id:
            session_manager.delete_session(session_id)
        
        # 새 세션 생성 및 초기 메시지 처리 (모든 로직을 session_manager에 위임)
        response = await session_manager.create_session_with_welcome_message(user_id, analyzer)
        
        return CustomJSONResponse(response)
        
    except Exception as e:
        logger.error(f"세션 초기화 실패: {str(e)}")
        logger.error(traceback.format_exc())
        return CustomJSONResponse({
            "success": False,
            "error": "세션 초기화에 실패했습니다.",
            "detail": str(e)
        })

@app.get("/api/sessions/stats")
async def get_sessions_stats():
    """전체 세션 통계"""
    try:
        total_sessions = len(session_manager.sessions)
        
        # 상태별 세션 수 계산
        states_count = {}
        for session in session_manager.sessions.values():
            state = session.state.value
            states_count[state] = states_count.get(state, 0) + 1
        
        # 사용자 벡터DB 통계
        user_vector_stats = analyzer.user_vector_store.get_collection_stats()
        
        return {
            "success": True,
            "total_sessions": total_sessions,
            "states_distribution": states_count,
            "user_vector_store_stats": user_vector_stats,
            "timestamp": logger.handlers[0].format if logger.handlers else None
        }
    except Exception as e:
        logger.error(f"세션 통계 조회 실패: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

@app.post("/api/sessions/cleanup")
async def cleanup_old_sessions():
    """오래된 세션 정리"""
    try:
        initial_count = len(session_manager.sessions)
        session_manager.cleanup_old_sessions(max_age_hours=24)
        final_count = len(session_manager.sessions)
        
        cleaned_count = initial_count - final_count
        
        return {
            "success": True,
            "message": f"{cleaned_count}개의 오래된 세션을 정리했습니다.",
            "remaining_sessions": final_count
        }
    except Exception as e:
        logger.error(f"세션 정리 실패: {str(e)}")
        raise HTTPException(status_code=500, detail="세션 정리에 실패했습니다.")

# 사용자 데이터 관리 API 추가
@app.get("/api/user/{user_id}/data")
async def get_user_data(user_id: str, data_type: str = None):
    """사용자 데이터 조회 (user_id 기반)"""
    try:
        # user_id 유효성 검증
        if not user_id or user_id in ["None", "null"]:
            raise HTTPException(status_code=400, detail="유효하지 않은 사용자 ID입니다.")
        
        # MongoDB에서 사용자 데이터 조회
        user_data = analyzer.db.get_user_data(user_id, data_type)
        
        # 벡터DB에서 사용자 컨텍스트 조회
        user_context = analyzer.user_vector_store.get_user_latest_data(user_id, data_type)
        
        return {
            "success": True,
            "user_id": user_id,
            "mongodb_data": user_data,
            "vector_context": user_context
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"사용자 데이터 조회 실패: {str(e)}")
        raise HTTPException(status_code=500, detail="사용자 데이터 조회에 실패했습니다.")

@app.delete("/api/user/{user_id}/data")
async def delete_user_data(user_id: str, data_type: str = None):
    """사용자 데이터 삭제 (user_id 기반)"""
    try:
        # user_id 유효성 검증
        if not user_id or user_id in ["None", "null"]:
            raise HTTPException(status_code=400, detail="유효하지 않은 사용자 ID입니다.")
        
        # 벡터DB에서 사용자 데이터 삭제
        vector_deleted = analyzer.user_vector_store.delete_user_data(user_id, data_type)
        
        # MongoDB에서 사용자 루틴 삭제 (data_type이 없거나 'routines'인 경우)
        if not data_type or data_type == 'routines':
            mongo_deleted = analyzer.db.delete_user_routines(user_id)
        else:
            mongo_deleted = True
        
        return {
            "success": True,
            "vector_deleted": vector_deleted,
            "mongo_deleted": mongo_deleted,
            "message": f"사용자 {user_id}의 {data_type or '모든'} 데이터가 삭제되었습니다."
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"사용자 데이터 삭제 실패: {str(e)}")
        raise HTTPException(status_code=500, detail="사용자 데이터 삭제에 실패했습니다.")

@app.get("/api/user/{user_id}/routines")
async def get_user_routines(user_id: str):
    """사용자 운동 루틴 조회 (user_id 기반) - 저장 검증 포함"""
    try:
        # user_id 유효성 검증
        if not user_id or user_id in ["None", "null"]:
            raise HTTPException(status_code=400, detail="유효하지 않은 사용자 ID입니다.")
        
        # 🔥 DB에서 루틴 조회
        routines = analyzer.db.get_user_routines(user_id)
        has_routines = analyzer.db.has_user_routines(user_id)
        
        # 🔥 추가 검증 정보 포함
        verification_info = {
            "db_query_success": True,
            "routines_count": len(routines),
            "has_routines_flag": has_routines,
            "query_time": get_korea_time().isoformat()
        }
        
        logger.info(f"✅ 사용자 {user_id} 루틴 조회 완료: {len(routines)}개")
        
        response_data = {
            "success": True,
            "user_id": user_id,
            "has_routines": has_routines,
            "routines": routines,
            "total_days": len(routines),
            "verification": verification_info
        }
        return CustomJSONResponse(response_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"사용자 루틴 조회 실패: {str(e)}")
        
        # 오류 정보 포함한 응답
        error_response = {
            "success": False,
            "user_id": user_id,
            "has_routines": False,
            "routines": [],
            "total_days": 0,
            "error": str(e),
            "verification": {
                "db_query_success": False,
                "error_details": str(e)
            }
        }
        return CustomJSONResponse(error_response)

# 🔥 NEW: 루틴 저장 상태 디버깅을 위한 엔드포인트
@app.get("/debug/routine-save-status/{user_id}")
async def debug_routine_save_status(user_id: str):
    """루틴 저장 상태 디버깅"""
    try:
        if not user_id or user_id in ["None", "null"]:
            return CustomJSONResponse({
                "success": False,
                "error": "유효하지 않은 사용자 ID"
            })
        
        # DB 연결 테스트
        try:
            db_connection_test = analyzer.db.collection.count_documents({})
            db_connected = True
        except Exception as db_error:
            db_connection_test = 0
            db_connected = False
        
        # 사용자 루틴 조회
        try:
            user_routines = analyzer.db.get_user_routines(user_id)
            has_user_routines = analyzer.db.has_user_routines(user_id)
            routines_query_success = True
        except Exception as query_error:
            user_routines = []
            has_user_routines = False
            routines_query_success = False
        
        # 사용자 벡터DB 상태
        try:
            user_vector_data = analyzer.user_vector_store.get_user_latest_data(user_id)
            vector_db_success = True
        except Exception as vector_error:
            user_vector_data = []
            vector_db_success = False
        
        # 전체 통계
        try:
            total_routines = analyzer.db.collection.count_documents({})
            total_users_with_routines = len(analyzer.db.collection.distinct("user_id"))
        except:
            total_routines = 0
            total_users_with_routines = 0
        
        debug_info = {
            "success": True,
            "user_id": user_id,
            "timestamp": get_korea_time().isoformat(),
            "db_status": {
                "connected": db_connected,
                "total_routines_in_db": total_routines,
                "total_users_with_routines": total_users_with_routines
            },
            "user_specific": {
                "routines_query_success": routines_query_success,
                "has_routines": has_user_routines,
                "routines_count": len(user_routines),
                "routines": user_routines
            },
            "vector_db_status": {
                "query_success": vector_db_success,
                "user_data_count": len(user_vector_data)
            }
        }
        
        return CustomJSONResponse(debug_info)
        
    except Exception as e:
        logger.error(f"루틴 저장 상태 디버깅 실패: {str(e)}")
        return CustomJSONResponse({
            "success": False,
            "error": str(e),
            "user_id": user_id
        })
        
@app.post("/api/user/{user_id}/progress")
async def add_user_progress(user_id: str, progress_data: dict):
    """사용자 운동 진행 상황 추가 (user_id 기반)"""
    try:
        # user_id 유효성 검증
        if not user_id or user_id in ["None", "null"]:
            raise HTTPException(status_code=400, detail="유효하지 않은 사용자 ID입니다.")
        
        # 벡터DB에 진행 상황 저장
        vector_saved = analyzer.user_vector_store.add_user_progress(user_id, progress_data)
        
        # MongoDB에도 저장
        mongo_saved = analyzer.db.save_user_data(user_id, 'progress', progress_data)
        
        return {
            "success": True,
            "vector_saved": vector_saved,
            "mongo_saved": bool(mongo_saved),
            "message": "운동 진행 상황이 저장되었습니다."
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"운동 진행 상황 저장 실패: {str(e)}")
        raise HTTPException(status_code=500, detail="운동 진행 상황 저장에 실패했습니다.")

# 기존 API 엔드포인트들 (하위 호환성 유지)
@app.post("/api/user/info")
async def process_user_info(data: dict):
    """사용자 정보 처리 (레거시 호환)"""
    try:
        answer = data.get("answer", "")
        question_type = data.get("type", "")
        
        logger.info(f"사용자 정보 처리: {question_type} = {answer}")
        
        processed_info = await analyzer.process_user_info_async(answer, question_type)
        
        return {
            "success": True,
            "processed_info": processed_info
        }
        
    except Exception as e:
        logger.error(f"사용자 정보 처리 중 오류: {str(e)}")
        return {
            "success": True,  # 실패해도 기본값 반환
            "processed_info": {
                "value": data.get("answer", ""),
                "unit": None,
                "normalized": False
            }
        }

@app.post("/api/workout/recommend")
async def recommend_workout(data: dict):
    """운동 루틴 추천 (사용자 ID 기반 개인화) - 저장 보장"""
    try:
        inbody_data = data.get("inbody", {})
        preferences = data.get("preferences", {})
        user_id = data.get("user_id")
        
        logger.info("🎯 운동 루틴 추천 시작")
        logger.info(f"사용자 ID: {user_id}")
        logger.info(f"인바디 데이터: {inbody_data}")
        logger.info(f"운동 선호도: {preferences}")
        
        # user_id 유효성 검증 및 기본값 설정
        if not user_id or user_id in ["None", "null"]:
            logger.warning("유효하지 않은 user_id로 운동 루틴 추천 요청 - 기본값 설정")
            user_id = "1"  # 기본값 설정
        
        # 필수 데이터 검증
        required_inbody = ["gender", "age", "height", "weight"]
        for field in required_inbody:
            if field not in inbody_data or not inbody_data[field]:
                raise HTTPException(
                    status_code=400, 
                    detail=f"필수 인바디 정보가 누락되었습니다: {field}"
                )

        required_prefs = ["goal", "experience_level"]
        for field in required_prefs:
            if field not in preferences or not preferences[field]:
                raise HTTPException(
                    status_code=400, 
                    detail=f"필수 운동 선호도 정보가 누락되었습니다: {field}"
                )

        # 🔥 저장 전 DB 연결 상태 확인
        try:
            db_test = analyzer.db.collection.count_documents({})
            logger.info(f"✅ DB 연결 확인: 전체 루틴 수 {db_test}")
        except Exception as db_error:
            logger.error(f"❌ DB 연결 실패: {str(db_error)}")
            raise HTTPException(
                status_code=500,
                detail="데이터베이스 연결에 실패했습니다. 잠시 후 다시 시도해주세요."
            )

        # 🔥 운동 루틴 생성
        routine_result = await analyzer.generate_enhanced_routine_async({
            "inbody": inbody_data,
            "preferences": preferences,
            "user_id": user_id,
            "user_context": user_context
        })

        # 🔥 결과 처리 개선
        if isinstance(routine_result, dict) and routine_result.get('success'):
            saved_routines = routine_result.get('routines', [])
            
            # 🔥 최종 검증
            if user_id and user_id not in ["None", "null"]:
                try:
                    verification_routines = analyzer.db.get_user_routines(user_id)
                    logger.info(f"🔍 최종 검증: 사용자 {user_id}의 DB 저장 루틴 수: {len(verification_routines)}")
                    
                    if len(verification_routines) == 0:
                        raise HTTPException(
                            status_code=500,
                            detail="루틴이 데이터베이스에 저장되지 않았습니다. 다시 시도해주세요."
                        )
                    
                    saved_routines = verification_routines
                    
                except Exception as verification_error:
                    logger.error(f"최종 검증 실패: {str(verification_error)}")
                    if not saved_routines:
                        raise HTTPException(
                            status_code=500,
                            detail="루틴 저장 검증에 실패했습니다."
                        )
            
            logger.info(f"✅ 사용자 {user_id}의 개인화된 운동 루틴 생성 및 저장 완료")
            
            # 🔥 성공 응답
            response_data = {
                "success": True,
                "analysis": routine_result.get('analysis', ''),
                "routines": saved_routines,
                "total_days": len(saved_routines),
                "personalization_applied": routine_result.get('personalization_applied', False),
                "message": f"사용자 {user_id}를 위한 개인화된 {len(saved_routines)}일간의 운동 루틴이 생성되고 저장되었습니다.",
                "save_verification": {
                    "db_saved_count": len(saved_routines),
                    "generation_time": routine_result.get('generation_time'),
                    "save_errors": routine_result.get('save_errors'),
                    "validation_info": routine_result.get('validation_info')
                },
                "ui_hints": {
                    "show_routine": True,
                    "routine_type": "personalized",
                    "enable_modifications": True
                }
            }
            
            return CustomJSONResponse(response_data)
        else:
            # Fallback 응답
            logger.info("Fallback 텍스트 운동 루틴 생성")
            return CustomJSONResponse({
                "success": True,
                "routine": routine_result,
                "message": "운동 루틴이 생성되었습니다.",
                "fallback": True
            })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"운동 루틴 추천 생성 중 오류: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"운동 루틴 추천 생성에 실패했습니다: {str(e)}"
        )

@app.get("/ready")
async def ready():
    """서버 준비 상태 확인"""
    try:
        status = analyzer.get_loading_status()
        user_vector_stats = analyzer.user_vector_store.get_collection_stats()
        
        return {
            "ready": status.get("documents_loaded", False),
            "loading": status.get("loading_in_progress", False),
            "status": status,
            "user_vector_store": user_vector_stats
        }
    except Exception as e:
        return {
            "ready": False,
            "loading": False,
            "error": str(e)
        }

# 전역 예외 핸들러
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"글로벌 예외: {str(exc)}")
    logger.error(traceback.format_exc())
    
    return CustomJSONResponse({
        "success": False,
        "error": "서버 내부 오류가 발생했습니다.",
        "detail": str(exc)
    })

# 주기적 세션 정리 (백그라운드 태스크)
@app.on_event("startup")
async def startup_event():
    """앱 시작시 초기화"""
    logger.info("🚀 AI Fitness Coach API 시작 (식단 기능 제거, 사용자 기반 개인화 강화)")
    
    # 사용자 벡터DB 초기화 확인
    try:
        user_vector_stats = analyzer.user_vector_store.get_collection_stats()
        logger.info(f"사용자 벡터DB 상태: {user_vector_stats}")
    except Exception as e:
        logger.error(f"사용자 벡터DB 상태 확인 실패: {e}")
    
    # 주기적 세션 정리 스케줄링
    async def cleanup_sessions_periodically():
        while True:
            await asyncio.sleep(3600)  # 1시간마다
            try:
                session_manager.cleanup_old_sessions()
                logger.info("주기적 세션 정리 완료")
            except Exception as e:
                logger.error(f"주기적 세션 정리 실패: {e}")
    
    # 백그라운드 태스크 시작
    asyncio.create_task(cleanup_sessions_periodically())
    logger.info("백그라운드 태스크 시작됨")

@app.on_event("shutdown")
async def shutdown_event():
    """앱 종료시 정리"""
    logger.info("🛑 AI Fitness Coach API 종료")
    
    # 세션 정리
    try:
        session_count = len(session_manager.sessions)
        if session_count > 0:
            logger.info(f"{session_count}개의 활성 세션을 정리합니다...")
            for session_id in list(session_manager.sessions.keys()):
                session_manager.delete_session(session_id)
        logger.info("모든 세션이 정리되었습니다.")
    except Exception as e:
        logger.error(f"세션 정리 중 오류: {e}")
    
    # AI 분석기 정리
    try:
        if hasattr(analyzer, '__del__'):
            analyzer.__del__()
        logger.info("AI 분석기 정리 완료")
    except Exception as e:
        logger.error(f"AI 분석기 정리 중 오류: {e}")

# 개발 환경에서만 사용하는 디버그 엔드포인트들
@app.get("/debug/sessions")
async def debug_get_all_sessions():
    """디버그: 모든 세션 정보 조회"""
    try:
        sessions_info = {}
        for session_id, session in session_manager.sessions.items():
            sessions_info[session_id] = {
                "session_info": session.get_session_info(),
                "message_count": len(session.messages),
                "state": session.state.value,
                "user_id": session.user_id,
                "has_existing_routines": bool(session.existing_routines),
                "has_daily_modifications": bool(session.daily_modifications)
            }
        
        return CustomJSONResponse({
            "success": True,
            "total_sessions": len(sessions_info),
            "sessions": sessions_info
        })
    except Exception as e:
        logger.error(f"디버그 세션 조회 실패: {str(e)}")
        return CustomJSONResponse({
            "success": False,
            "error": str(e)
        })

@app.post("/debug/test-user-context/{user_id}")
async def debug_test_user_context(user_id: str, query: str = "운동 루틴 추천"):
    """디버그: 사용자 컨텍스트 테스트"""
    try:
        if not user_id or user_id in ["None", "null"]:
            raise HTTPException(status_code=400, detail="유효하지 않은 사용자 ID입니다.")
        
        # 사용자 컨텍스트 조회
        user_context = analyzer.user_vector_store.get_user_context(user_id, query)
        
        # 사용자 최신 데이터 조회
        latest_data = analyzer.user_vector_store.get_user_latest_data(user_id)
        
        # MongoDB에서 사용자 데이터 조회
        mongo_data = analyzer.db.get_user_data(user_id)
        
        return CustomJSONResponse({
            "success": True,
            "user_id": user_id,
            "query": query,
            "user_context": user_context,
            "latest_vector_data": latest_data,
            "mongo_data": mongo_data,
            "context_length": len(user_context) if user_context else 0
        })
    except Exception as e:
        logger.error(f"사용자 컨텍스트 테스트 실패: {str(e)}")
        return CustomJSONResponse({
            "success": False,
            "error": str(e)
        })

@app.get("/debug/vector-stats")
async def debug_vector_stats():
    """디버그: 벡터DB 통계 정보"""
    try:
        general_stats = analyzer.vector_store.get_collection_stats()
        user_stats = analyzer.user_vector_store.get_collection_stats()
        loading_status = analyzer.get_loading_status()
        
        return CustomJSONResponse({
            "success": True,
            "general_vector_store": general_stats,
            "user_vector_store": user_stats,
            "loading_status": loading_status,
            "analyzer_status": {
                "documents_loaded": analyzer._documents_loaded,
                "loading_in_progress": analyzer._loading_in_progress
            }
        })
    except Exception as e:
        logger.error(f"벡터DB 통계 조회 실패: {str(e)}")
        return CustomJSONResponse({
            "success": False,
            "error": str(e)
        })

@app.get("/api/debug/session/{session_id}")
async def debug_session(session_id: str):
    """세션 디버깅용 엔드포인트"""
    try:
        session = session_manager.get_session(session_id)
        if not session:
            return CustomJSONResponse({
                "success": False,
                "error": "세션을 찾을 수 없습니다."
            })
        
        debug_info = {
            "success": True,
            "session_id": session.session_id,
            "user_id": session.user_id,
            "state": session.state.value,
            "messages": session.messages,
            "message_count": len(session.messages),
            "has_existing_routines": bool(session.existing_routines),
            "routine_modification_options": session_manager.ROUTINE_MODIFICATION_OPTIONS
        }
        
        return CustomJSONResponse(debug_info)
        
    except Exception as e:
        logger.error(f"세션 디버깅 실패: {str(e)}")
        return CustomJSONResponse({
            "success": False,
            "error": str(e)
        })

# 메인 실행부
if __name__ == "__main__":
    import uvicorn
    
    # 환경 변수에서 설정 읽기
    host = os.getenv("HOST", "192.168.0.22")
    port = int(os.getenv("PORT", 8002))
    reload = os.getenv("RELOAD", "True").lower() == "true"
    
    logger.info(f"서버 시작: http://{host}:{port}")
    logger.info(f"개발 모드: {reload}")
    logger.info(f"API 문서: http://{host}:{port}/docs")
    
    uvicorn.run(
        "main:app", 
        host=host, 
        port=port, 
        reload=reload,
        log_level="info",
        access_log=True
    )