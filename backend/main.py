from fastapi import FastAPI, File, UploadFile, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
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
from modules.utils import validate_uploaded_file, create_upload_directory, save_uploaded_file
from modules.chat_session import session_manager, SessionState

app = FastAPI()
UPLOAD_DIR = create_upload_directory()

# 로거 설정
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
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
    user_id: Optional[str] = None  # 사용자 ID 필드 추가

class ChatResponse(BaseModel):
    success: bool
    session_id: str
    messages: list
    latest_message: dict
    session_info: dict
    show_file_upload: Optional[bool] = False
    routine_data: Optional[list] = None

@app.get("/")
async def root():
    """루트 엔드포인트"""
    return {"message": "AI Fitness Coach API is running", "status": "healthy"}

@app.get("/health")
async def health_check():
    """헬스 체크"""
    try:
        status = analyzer.get_loading_status()
        return {
            "status": "healthy",
            "ai_analyzer": status,
            "pdf_processor": True,
            "active_sessions": len(session_manager.sessions)
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }

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
            user_id=data.user_id  # user_id 전달
        )
        
        return response
        
    except Exception as e:
        logger.error(f"채팅 처리 중 오류: {str(e)}")
        logger.error(traceback.format_exc())
        return {
            "success": False,
            "error": "일시적인 오류가 발생했습니다. 다시 시도해주세요.",
            "detail": str(e)
        }
        
    except Exception as e:
        logger.error(f"채팅 처리 중 오류: {str(e)}")
        logger.error(traceback.format_exc())
        return {
            "success": False,
            "error": "일시적인 오류가 발생했습니다. 다시 시도해주세요.",
            "detail": str(e)
        }

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
    """세션 초기화 (새로운 대화 시작)"""
    try:
        session_id = data.get("session_id")
        if session_id:
            session_manager.delete_session(session_id)
        
        # 새 세션 생성
        new_session = session_manager.get_or_create_session()
        
        return {
            "success": True,
            "session_id": new_session.session_id,
            "messages": new_session.messages,
            "session_info": new_session.get_session_info()
        }
    except Exception as e:
        logger.error(f"세션 초기화 실패: {str(e)}")
        raise HTTPException(status_code=500, detail="세션 초기화에 실패했습니다.")

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
        
        return {
            "success": True,
            "total_sessions": total_sessions,
            "states_distribution": states_count,
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
    """운동 루틴 추천 (레거시 호환)"""
    try:
        inbody_data = data.get("inbody", {})
        preferences = data.get("preferences", {})
        user_id = data.get("user_id")  # user_id 추출
        
        logger.info("운동 루틴 추천 시작")
        logger.info(f"사용자 ID: {user_id}")
        logger.info(f"인바디 데이터: {inbody_data}")
        logger.info(f"운동 선호도: {preferences}")
        
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

        # 운동 루틴 생성 (user_id 전달)
        routine_result = await analyzer.generate_enhanced_routine_async({
            "inbody": inbody_data,
            "preferences": preferences,
            "user_id": user_id  # user_id 전달
        })

        # 결과가 딕셔너리 형태인지 확인 (성공적으로 생성된 경우)
        if isinstance(routine_result, dict) and routine_result.get('success'):
            logger.info("운동 루틴 생성 및 DB 저장 완료")
            return {
                "success": True,
                "analysis": routine_result.get('analysis', ''),
                "routines": routine_result.get('routines', []),
                "total_days": routine_result.get('total_days', 0),
                "message": f"{routine_result.get('total_days', 0)}일간의 운동 루틴이 생성되고 저장되었습니다."
            }
        else:
            # Fallback 텍스트 응답
            logger.info("Fallback 텍스트 운동 루틴 생성")
            return {
                "success": True,
                "routine": routine_result,
                "message": "운동 루틴이 생성되었습니다."
            }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"운동 루틴 추천 생성 중 오류: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"운동 루틴 추천 생성에 실패했습니다: {str(e)}"
        )

@app.get("/api/intent/identify")
async def identify_intent(message: str = Query(...)):
    """사용자 의도 파악 (레거시 호환)"""
    try:
        logger.info(f"의도 파악: {message}")
        intent = await analyzer.identify_intent(message)
        return {
            "success": True,
            "intent": intent
        }
    except Exception as e:
        logger.error(f"의도 파악 실패: {str(e)}")
        return {
            "success": False,
            "intent": {
                "intent": "general_chat",
                "has_pdf": False,
                "confidence": 0.0
            }
        }

@app.get("/ready")
async def ready():
    """서버 준비 상태 확인"""
    try:
        status = analyzer.get_loading_status()
        return {
            "ready": status.get("documents_loaded", False),
            "loading": status.get("loading_in_progress", False),
            "status": status
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
    
    return {
        "success": False,
        "error": "서버 내부 오류가 발생했습니다.",
        "detail": str(exc)
    }

# 주기적 세션 정리 (백그라운드 태스크)
@app.on_event("startup")
async def startup_event():
    """앱 시작시 초기화"""
    logger.info("🚀 AI Fitness Coach API 시작")
    
    # 주기적 세션 정리 스케줄링
    async def cleanup_sessions_periodically():
        while True:
            await asyncio.sleep(3600)  # 1시간마다
            try:
                session_manager.cleanup_old_sessions()
            except Exception as e:
                logger.error(f"주기적 세션 정리 실패: {e}")
    
    # 백그라운드 태스크 시작
    asyncio.create_task(cleanup_sessions_periodically())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)