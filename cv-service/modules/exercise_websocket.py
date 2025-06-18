# cv-service/modules/exercise_websocket.py - FIXED VERSION

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import json
import asyncio
from typing import Dict, List, Optional
import traceback
import numpy as np
import cv2
import logging
import time

# 실제 ExerciseAnalyzer 임포트
from .exercise_analyzer import ExerciseAnalyzer, Exercise, PostureFeedback

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/workout", tags=["websocket"])

class WebSocketExerciseAnalyzer:
    """WebSocket용 운동 분석기 - 실제 ExerciseAnalyzer 사용"""
    
    def __init__(self):
        self.analyzer = ExerciseAnalyzer()
        self.exercise_type = None
        self.target_reps = None
        self.target_time = None  # For time-based exercises
        self.is_time_based = False
        self.start_time = None
        
        # FIXED: Add completion tracking to prevent duplicates
        self.completion_triggered = False
        self.completion_api_called = False
        self.last_completion_time = 0
        
        # 운동명 매핑 (한국어 -> 영어)
        self.exercise_mapping = {
            "푸시업": Exercise.PUSHUP,
            "스쿼트": Exercise.SQUAT,
            "레그레이즈": Exercise.LEG_RAISE,
            "덤벨컬": Exercise.DUMBBELL_CURL,
            "원암덤벨로우": Exercise.ONE_ARM_ROW,
            "플랭크": Exercise.PLANK
        }
        
        # Time-based exercises
        self.time_based_exercises = ["플랭크", "워밍업: 러닝머신", "마무리: 러닝머신", "러닝머신"]
        
        logger.info("WebSocketExerciseAnalyzer 초기화 완료")
    
    def get_camera_setup_guide(self, exercise_name: str) -> str:
        """운동별 카메라 설정 가이드"""
        guides = {
            "푸시업": "📷 카메라를 옆쪽 바닥 높이에 3-6피트 거리에 두세요. 전신이 보이도록 해주세요.",
            "스쿼트": "📷 카메라를 정면 또는 옆쪽 허리 높이에 4-6피트 거리에 두세요.",
            "레그레이즈": "📷 카메라를 옆쪽 바닥 높이에 3-5피트 거리에 두세요. 누워있는 전신이 보이도록 해주세요.",
            "덤벨컬": "📷 카메라를 정면 가슴 높이에 3-5피트 거리에 두세요.",
            "원암덤벨로우": "📷 카메라를 옆쪽 허리 높이에 4-6피트 거리에 두세요.",
            "플랭크": "📷 카메라를 옆쪽 바닥 높이에 3-6피트 거리에 두세요. 머리부터 발끝까지 보이도록 해주세요."
        }
        return guides.get(exercise_name, "📷 전신이 잘 보이도록 카메라를 설정해주세요.")
    
    def get_pose_setup_guide(self, exercise_name: str) -> Dict:
        """운동별 시작 자세 가이드"""
        guides = {
            "푸시업": {
                "title": "푸시업 시작 자세",
                "steps": [
                    "1. 엎드려서 손바닥을 어깨 너비로 바닥에 댑니다",
                    "2. 발끝으로 몸을 지탱하며 몸을 일직선으로 만듭니다",
                    "3. 머리부터 발끝까지 한 줄이 되도록 유지합니다",
                    "4. 팔을 완전히 펴고 시작 위치를 잡습니다"
                ],
                "tips": "💡 엉덩이가 너무 올라가거나 처지지 않도록 주의하세요"
            },
            "스쿼트": {
                "title": "스쿼트 시작 자세", 
                "steps": [
                    "1. 발을 어깨 너비로 벌리고 서 있습니다",
                    "2. 발끝을 약간 밖으로 향하게 합니다",
                    "3. 가슴을 펴고 등을 곧게 세웁니다",
                    "4. 팔은 앞으로 뻗거나 가슴에 모읍니다"
                ],
                "tips": "💡 무릎이 발끝을 넘어가지 않도록 주의하세요"
            },
            "레그레이즈": {
                "title": "레그레이즈 시작 자세",
                "steps": [
                    "1. 등을 바닥에 대고 편안히 눕습니다",
                    "2. 팔은 몸 옆에 자연스럽게 둡니다",
                    "3. 다리를 곧게 펴고 모읍니다",
                    "4. 허리가 바닥에서 뜨지 않도록 합니다"
                ],
                "tips": "💡 허리에 무리가 가지 않도록 천천히 움직이세요"
            },
            "덤벨컬": {
                "title": "덤벨컬 시작 자세",
                "steps": [
                    "1. 덤벨을 양손에 들고 서 있습니다",
                    "2. 팔을 몸 옆에 자연스럽게 내립니다",
                    "3. 어깨를 뒤로 당기고 가슴을 펴세요",
                    "4. 팔꿈치는 몸에 고정시킵니다"
                ],
                "tips": "💡 팔꿈치가 흔들리지 않도록 고정하세요"
            },
            "원암덤벨로우": {
                "title": "원암덤벨로우 시작 자세",
                "steps": [
                    "1. 벤치나 의자에 한쪽 무릎과 손을 올립니다",
                    "2. 반대손에 덤벨을 들고 팔을 아래로 늘어뜨립니다",
                    "3. 등을 평평하게 유지합니다",
                    "4. 머리는 중립 위치를 유지합니다"
                ],
                "tips": "💡 등이 둥글게 말리지 않도록 주의하세요"
            },
            "플랭크": {
                "title": "플랭크 시작 자세",
                "steps": [
                    "1. 엎드려서 팔꿈치와 발끝으로 몸을 지탱합니다",
                    "2. 팔꿈치는 어깨 바로 아래에 위치시킵니다",
                    "3. 머리부터 발끝까지 일직선을 만듭니다",
                    "4. 복부에 힘을 주고 자세를 유지합니다"
                ],
                "tips": "💡 엉덩이가 올라가거나 처지지 않도록 하세요"
            }
        }
        return guides.get(exercise_name, {
            "title": "운동 준비",
            "steps": ["올바른 자세로 운동을 준비해주세요"],
            "tips": "💡 안전한 운동을 위해 준비운동을 먼저 하세요"
        })
    
    def set_exercise(self, exercise_name: str, target_reps: int = 10, target_time: int = None):
        """운동 타입 설정 - 시간 기반 운동 지원"""
        logger.info(f"운동 설정: {exercise_name}, 목표 횟수: {target_reps}, 목표 시간: {target_time}")
        
        if exercise_name in self.exercise_mapping:
            self.exercise_type = self.exercise_mapping[exercise_name]
            self.is_time_based = exercise_name in self.time_based_exercises
            
            if self.is_time_based:
                self.target_time = target_time or 30  # Default 30 seconds for plank
                self.target_reps = 1  # For time-based, we just track one "hold"
            else:
                self.target_reps = target_reps
                self.target_time = None
            
            # Reset exercise state
            self.analyzer.reset_exercise_state()
            
            # FIXED: Reset completion tracking
            self.completion_triggered = False
            self.completion_api_called = False
            self.last_completion_time = 0
            
            logger.info(f"운동 매핑 성공: {exercise_name} -> {self.exercise_type}, 시간기반: {self.is_time_based}")
            return True
        else:
            logger.error(f"지원하지 않는 운동: {exercise_name}")
            logger.info(f"지원 가능한 운동: {list(self.exercise_mapping.keys())}")
            return False

    def analyze_landmarks(self, landmarks: List[Dict]) -> Optional[Dict]:
        """Direct landmark analysis with time tracking and completion prevention"""
        if not self.exercise_type:
            logger.warning("Exercise type not set")
            return None
        
        if len(landmarks) < 33:
            logger.warning(f"Insufficient landmarks: {len(landmarks)}/33")
            return None
        
        try:
            # Use direct landmark analysis
            feedback = self.analyzer.analyze_landmarks_directly(landmarks, self.exercise_type)
            
            if feedback:
                result = {
                    "isCorrect": feedback.is_correct,
                    "messages": feedback.feedback_messages,
                    "angleData": feedback.angle_data,
                    "confidence": feedback.confidence,
                    "repQuality": getattr(feedback, 'rep_quality', 1.0)
                }
                
                if self.is_time_based:
                    # For plank, track hold time
                    hold_time = feedback.angle_data.get('hold_time', 0)
                    result["repCount"] = 0  # Don't use rep count for time-based
                    result["holdTime"] = hold_time
                    
                    # FIXED: Check for completion with debouncing
                    is_complete = hold_time >= self.target_time
                    
                    if is_complete and not self.completion_triggered:
                        current_time = time.time()
                        if current_time - self.last_completion_time > 2.0:  # 2 second debounce
                            self.completion_triggered = True
                            self.last_completion_time = current_time
                            result["isComplete"] = True
                            logger.info(f"Plank completion triggered: hold_time={hold_time}, target={self.target_time}")
                        else:
                            result["isComplete"] = False
                    else:
                        result["isComplete"] = False
                    
                    logger.info(f"Plank analysis: hold_time={hold_time}, target={self.target_time}, complete={result['isComplete']}, triggered={self.completion_triggered}")
                else:
                    # For rep-based exercises
                    result["repCount"] = self.analyzer.rep_count
                    
                    # FIXED: Check for completion with debouncing
                    is_complete = (self.target_reps and 
                                 self.analyzer.rep_count >= self.target_reps)
                    
                    if is_complete and not self.completion_triggered:
                        current_time = time.time()
                        if current_time - self.last_completion_time > 2.0:  # 2 second debounce
                            self.completion_triggered = True
                            self.last_completion_time = current_time
                            result["isComplete"] = True
                            logger.info(f"Rep completion triggered: reps={self.analyzer.rep_count}, target={self.target_reps}")
                        else:
                            result["isComplete"] = False
                    else:
                        result["isComplete"] = False
                    
                    logger.info(f"Rep analysis: reps={self.analyzer.rep_count}, target={self.target_reps}, complete={result['isComplete']}, triggered={self.completion_triggered}")
                
                return result
            else:
                logger.warning("No analysis result")
                return None
                
        except Exception as e:
            logger.error(f"Analysis error: {str(e)}")
            logger.error(traceback.format_exc())
            return None

    def reset(self):
        """Reset exercise state"""
        logger.info("운동 상태 리셋")
        self.analyzer.reset_exercise_state()
        self.start_time = None
        
        # FIXED: Reset completion tracking
        self.completion_triggered = False
        self.completion_api_called = False
        self.last_completion_time = 0
        
        return {
            "repCount": 0,
            "holdTime": 0
        }

    def mark_completion_api_called(self):
        """Mark that the completion API has been called"""
        self.completion_api_called = True
        logger.info("Completion API call marked as done")


@router.websocket("/ws/analyze")
async def websocket_analyze(websocket: WebSocket):
    """WebSocket endpoint for real-time posture analysis"""
    await websocket.accept()
    logger.info("WebSocket 연결 성공")
    
    analyzer = WebSocketExerciseAnalyzer()
    
    try:
        while True:
            # 클라이언트로부터 데이터 수신
            data = await websocket.receive_json()
            logger.info(f"수신된 데이터 타입: {data.get('type')}")
            
            if data['type'] == 'init':
                # 운동 초기화
                exercise_name = data.get('exercise')
                target_reps = data.get('targetReps', 10)
                target_time = data.get('targetTime')  # For time-based exercises
                
                logger.info(f"운동 초기화: {exercise_name}, 목표 횟수: {target_reps}, 목표 시간: {target_time}")
                
                success = analyzer.set_exercise(exercise_name, target_reps, target_time)
                
                if success:
                    # 카메라 설정 가이드도 함께 전송
                    camera_guide = analyzer.get_camera_setup_guide(exercise_name)
                    pose_guide = analyzer.get_pose_setup_guide(exercise_name)
                    
                    await websocket.send_json({
                        "type": "init_success",
                        "message": f"✅ {exercise_name} 분석 준비 완료",
                        "status": "ready", 
                        "exercise": exercise_name,
                        "exerciseType": analyzer.exercise_type.value if analyzer.exercise_type else exercise_name,
                        "targetReps": analyzer.target_reps,
                        "targetTime": analyzer.target_time,
                        "isTimeBased": analyzer.is_time_based,
                        "cameraGuide": camera_guide,
                        "poseGuide": pose_guide
                    })
                    logger.info(f"초기화 성공 응답 전송: {exercise_name} -> {analyzer.exercise_type}")
                else:
                    await websocket.send_json({
                        "type": "error",
                        "message": f"지원하지 않는 운동: {exercise_name}",
                        "supportedExercises": list(analyzer.exercise_mapping.keys())
                    })
                    logger.error(f"초기화 실패 응답 전송")
                
            elif data['type'] == 'landmarks':
                # 랜드마크 분석
                if not analyzer.exercise_type:
                    logger.warning("운동 타입 미설정 상태에서 랜드마크 수신")
                    continue
                
                landmarks = data['landmarks']
                
                # 분석 수행
                feedback = analyzer.analyze_landmarks(landmarks)
                
                if feedback:
                    # 피드백 전송
                    response = {
                        "type": "feedback",
                        "feedback": feedback,
                        "repCount": feedback.get("repCount", 0),
                        "holdTime": feedback.get("holdTime", 0),
                        "isComplete": feedback.get("isComplete", False)
                    }
                    
                    await websocket.send_json(response)
                    
                    # FIXED: Log completion status only once
                    if feedback.get("isComplete") and not analyzer.completion_api_called:
                        if analyzer.is_time_based:
                            logger.info(f"시간 기반 운동 완료: {feedback.get('holdTime')}초")
                        else:
                            logger.info(f"횟수 기반 운동 완료: {feedback.get('repCount')}회")
                        analyzer.mark_completion_api_called()
                    
                else:
                    logger.warning("분석 결과 없음")
                
            elif data['type'] == 'reset':
                # 리셋
                logger.info("리셋 요청 수신")
                result = analyzer.reset()
                await websocket.send_json({
                    "type": "status",
                    "message": "리셋 완료",
                    **result
                })
                logger.info("리셋 완료 응답 전송")
                
            elif data['type'] == 'completion_api_called':
                # FIXED: Mark that frontend has called the completion API
                analyzer.mark_completion_api_called()
                logger.info("Frontend reported completion API called")
                
    except WebSocketDisconnect:
        logger.info("클라이언트 연결 해제")
    except Exception as e:
        logger.error(f"WebSocket 오류: {str(e)}")
        logger.error(traceback.format_exc())
        try:
            await websocket.send_json({
                "type": "error",
                "message": str(e)
            })
        except:
            pass
    finally:
        try:
            await websocket.close()
        except:
            pass
        logger.info("WebSocket 연결 정리 완료")


@router.get("/ws/health")
async def websocket_health():
    """WebSocket 서비스 상태 확인"""
    return {
        "status": "healthy",
        "endpoint": "/api/workout/ws/analyze",
        "protocol": "ws",
        "supported_exercises": [
            "푸시업", "스쿼트", "레그레이즈", "덤벨컬", "원암덤벨로우", "플랭크"
        ],
        "time_based_exercises": ["플랭크", "워밍업: 러닝머신", "마무리: 러닝머신", "러닝머신"]
    }


@router.get("/ws/debug")
async def websocket_debug():
    """디버깅용 엔드포인트"""
    analyzer = ExerciseAnalyzer()
    return {
        "analyzer_available": True,
        "exercises": [e.value for e in Exercise],
        "model_loaded": hasattr(analyzer, 'detector'),
        "time_based_exercises": ["플랭크", "워밍업: 러닝머신", "마무리: 러닝머신", "러닝머신"]
    }