# backend/modules/routine_generator.py - 개선된 버전

import asyncio
import hashlib
import threading
import os
import json
import re
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any, Optional, List
from openai import OpenAI
import openai
from config.settings import OPENAI_API_KEY, SYSTEM_PROMPT, GPT_MODEL, GPT_TEMPERATURE, CHATBOT_PROMPT         
import glob
from modules.vector_store import VectorStore
from modules.user_vector_store import UserVectorStore
from openai.types.chat import (
    ChatCompletionSystemMessageParam,
    ChatCompletionUserMessageParam,
    ChatCompletionAssistantMessageParam,
)
import logging
import traceback
from database.db_config import DatabaseHandler
from datetime import datetime, timezone
import pytz

# 한국 시간대 설정
KST = pytz.timezone('Asia/Seoul')

def get_korea_time():
    """한국 시간 반환"""
    return datetime.now(KST)

# 로깅 설정
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class WorkoutRuleEngine:
    """운동 규칙 엔진 - 사용자 특성에 따른 맞춤형 운동 추천 로직"""
    
    def __init__(self):
        # 부상별 금지/추천 운동 매핑
        self.injury_restrictions = {
            "무릎": {
                "avoid": ["런지", "스쿼트", "레그프레스", "점프", "버피", "하이니킥"],
                "recommend": ["레그컬", "레그익스텐션", "힙어브덕션", "상체운동"],
                "modifications": "낮은 무게, 부분 가동범위"
            },
            "허리": {
                "avoid": ["데드리프트", "굿모닝", "로우", "오버헤드프레스", "스쿼트"],
                "recommend": ["플랭크", "레그레이즈", "사이드플랭크", "상체머신운동"],
                "modifications": "코어 강화 우선, 앉은 자세 운동"
            },
            "어깨": {
                "avoid": ["오버헤드프레스", "래터럴레이즈", "풀업", "딥스"],
                "recommend": ["체스트프레스", "레그운동", "코어운동"],
                "modifications": "어깨 아래 높이에서만 운동"
            },
            "목": {
                "avoid": ["업라이트로우", "슈러그", "헤드스탠드"],
                "recommend": ["하체운동", "가벼운상체운동"],
                "modifications": "목 중립 유지"
            },
            # 🔥 NEW: 발목 관련 추가
            "발목": {
                "avoid": ["런지", "점프", "달리기", "버피", "플라이오메트릭", "하이니킥"],
                "recommend": ["상체운동", "시티드운동", "수중운동", "자전거"],
                "modifications": "앉은 자세 운동, 체중 부하 최소화"
            },
            "손목": {
                "avoid": ["푸시업", "플랭크", "바벨운동"],
                "recommend": ["머신운동", "하체운동", "케이블운동"],
                "modifications": "리스트스트랩 사용"
            }
        }
        
        # 경험 수준별 운동 강도 및 복잡도
        self.experience_levels = {
            "초보자": {
                "sets_range": (2, 3),
                "reps_range": (8, 12),
                "weight_multiplier": 0.6,  # 체중의 60%부터 시작
                "exercises_per_day": (4, 6),
                "complex_movements": False,
                "recommended_exercises": [
                    "머신 체스트프레스", "레그프레스", "래터럴풀다운", 
                    "시티드로우", "레그컬", "레그익스텐션", "플랭크"
                ]
            },
            "보통": {
                "sets_range": (3, 4),
                "reps_range": (8, 15),
                "weight_multiplier": 0.8,
                "exercises_per_day": (5, 7),
                "complex_movements": True,
                "recommended_exercises": [
                    "벤치프레스", "스쿼트", "데드리프트", "풀업", 
                    "딥스", "런지", "바벨로우"
                ]
            },
            "숙련자": {
                "sets_range": (4, 5),
                "reps_range": (6, 20),
                "weight_multiplier": 1.0,
                "exercises_per_day": (6, 8),
                "complex_movements": True,
                "recommended_exercises": [
                    "스쿼트", "데드리프트", "벤치프레스", "오버헤드프레스",
                    "풀업", "딥스", "클린앤저크", "스내치"
                ]
            }
        }
        
        # 목표별 운동 구성
        self.goal_configurations = {
            "다이어트": {
                "cardio_ratio": 0.4,  # 40% 유산소
                "strength_ratio": 0.6,  # 60% 근력
                "rep_range": (12, 20),
                "rest_time": "30-45초",
                "focus": ["전신운동", "복합운동", "서킷트레이닝"]
            },
            "근육량 증가": {
                "cardio_ratio": 0.1,
                "strength_ratio": 0.9,
                "rep_range": (6, 12),
                "rest_time": "60-90초",
                "focus": ["큰근육우선", "복합운동", "점진적과부하"]
            },
            "체력 향상": {
                "cardio_ratio": 0.5,
                "strength_ratio": 0.5,
                "rep_range": (10, 15),
                "rest_time": "45-60초",
                "focus": ["기능적운동", "전신운동", "지구력"]
            },
            "건강 유지": {
                "cardio_ratio": 0.3,
                "strength_ratio": 0.7,
                "rep_range": (10, 15),
                "rest_time": "45-60초",
                "focus": ["균형잡힌운동", "유연성", "일상기능향상"]
            }
        }
        
        # BMI별 운동 강도 조절
        self.bmi_adjustments = {
            "저체중": {"weight_multiplier": 0.7, "focus": "근력증가"},
            "정상": {"weight_multiplier": 1.0, "focus": "목표따라조절"},
            "과체중": {"weight_multiplier": 0.8, "focus": "유산소증가"},
            "비만": {"weight_multiplier": 0.6, "focus": "저강도장시간"}
        }

    def get_bmi_category(self, bmi: float) -> str:
        """BMI 카테고리 반환"""
        if bmi < 18.5:
            return "저체중"
        elif bmi < 23:
            return "정상"
        elif bmi < 25:
            return "과체중"
        else:
            return "비만"

    def analyze_user_constraints(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """사용자 제약사항 분석"""
        inbody = user_data.get("inbody", {})
        preferences = user_data.get("preferences", {})
        
        # BMI 분석
        bmi = float(inbody.get("bmi", 22))
        bmi_category = self.get_bmi_category(bmi)
        
        # 부상 분석
        injury_status = preferences.get("injury_status", "없음")
        injury_constraints = self._analyze_injuries(injury_status)
        
        # 경험 수준 분석
        experience = preferences.get("experience_level", "보통")
        experience_config = self.experience_levels.get(experience, self.experience_levels["보통"])
        
        # 목표 분석
        goal = preferences.get("goal", "건강 유지")
        goal_config = self.goal_configurations.get(goal, self.goal_configurations["건강 유지"])
        
        # BMI 조정 적용
        bmi_adjustment = self.bmi_adjustments.get(bmi_category, self.bmi_adjustments["정상"])
        
        return {
            "bmi_category": bmi_category,
            "bmi_adjustment": bmi_adjustment,
            "injury_constraints": injury_constraints,
            "experience_config": experience_config,
            "goal_config": goal_config,
            "weight": float(inbody.get("weight", 70)),
            "age": int(inbody.get("age", 30)),
            "gender": inbody.get("gender", "남성")
        }
    
    def _analyze_injuries(self, injury_text: str) -> Dict[str, Any]:
        """부상 텍스트 분석"""
        if not injury_text or injury_text.lower() in ["없음", "없다", "no", "none"]:
            return {"has_injury": False, "restrictions": {}}
        
        restrictions = {
            "avoid_exercises": [],
            "recommended_exercises": [],
            "modifications": []
        }
        
        # 부상 키워드 매칭
        for injury_type, rules in self.injury_restrictions.items():
            if injury_type in injury_text:
                restrictions["avoid_exercises"].extend(rules["avoid"])
                restrictions["recommended_exercises"].extend(rules["recommend"])
                restrictions["modifications"].append(rules["modifications"])
        
        return {
            "has_injury": True,
            "injury_text": injury_text,  # 기존 키 유지
            "injury_status": injury_text,  # 🔥 NEW: 추가 키 제공
            "restrictions": restrictions
        }
    
    def generate_exercise_parameters(self, constraints: Dict[str, Any]) -> Dict[str, Any]:
        """제약사항 기반 운동 파라미터 생성"""
        experience_config = constraints["experience_config"]
        goal_config = constraints["goal_config"]
        bmi_adjustment = constraints["bmi_adjustment"]
        
        # 기본 파라미터
        base_weight = constraints["weight"]
        
        # 중량 계산 (체중 기반)
        weight_multiplier = (
            experience_config["weight_multiplier"] * 
            bmi_adjustment["weight_multiplier"]
        )
        
        # 세트/반복 수 결정
        sets_min, sets_max = experience_config["sets_range"]
        reps_min, reps_max = goal_config["rep_range"]
        
        return {
            "base_weight_kg": int(base_weight * weight_multiplier * 0.3),  # 시작 중량
            "sets_range": (sets_min, sets_max),
            "reps_range": (reps_min, reps_max),
            "exercises_per_day": experience_config["exercises_per_day"],
            "rest_time": goal_config["rest_time"],
            "cardio_ratio": goal_config["cardio_ratio"],
            "allow_complex_movements": experience_config["complex_movements"],
            "recommended_exercises": experience_config["recommended_exercises"],
            "focus_areas": goal_config["focus"]
        }

class AIAnalyzer:
    
    def __init__(self):
        self.client = openai.AsyncClient(api_key=OPENAI_API_KEY)
        self.conversation_history = []
        self.db = DatabaseHandler()
        
        # 운동 규칙 엔진 추가
        self.rule_engine = WorkoutRuleEngine()
        
        # 기존 VectorStore 초기화 (일반 피트니스 지식)
        self.vector_store = VectorStore(
            collection_name="fitness_knowledge_base",
            openai_api_key=OPENAI_API_KEY
        )
        
        # 사용자 전용 VectorStore 초기화 (개인 데이터)
        self.user_vector_store = UserVectorStore(
            collection_name="user_personal_data",
            persist_directory="./user_chroma_db",
            openai_api_key=OPENAI_API_KEY
        )
        
        # 문서 메타데이터 파일 경로
        self.metadata_file = "./data/.vector_store_metadata.json"
        
        # 문서 로딩 상태 관리
        self._documents_loaded = False
        self._loading_in_progress = False
        self._loading_thread = None
        self._executor = ThreadPoolExecutor(max_workers=2)
        
        # 백그라운드에서 문서 초기화 시작
        self._start_background_initialization()

    async def generate_enhanced_routine_async(self, user_data: Dict[str, Any]) -> str:
        """사용자 맞춤형 운동 루틴 생성 - 저장 보장"""
        try:
            # 사용자 데이터 검증
            inbody = user_data.get("inbody", {})
            preferences = user_data.get("preferences", {})
            user_id = user_data.get("user_id")
            user_context = user_data.get("user_context", "")
            
            logger.info(f"🎯 개인화된 운동 루틴 생성 시작 - 사용자: {user_id}")
            logger.info(f"📊 목표: {preferences.get('goal')}, 경험: {preferences.get('experience_level')}")
            logger.info(f"🏥 부상상태: {preferences.get('injury_status')}")
            
            # 필수 필드 확인
            required_fields = ["gender", "age", "height", "weight"]
            for field in required_fields:
                if field not in inbody or not inbody[field]:
                    raise ValueError(f"필수 인바디 정보 누락: {field}")
            
            required_prefs = ["goal", "experience_level"]
            for field in required_prefs:
                if field not in preferences or not preferences[field]:
                    raise ValueError(f"필수 운동 선호도 정보 누락: {field}")
            
            # 🔥 NEW: 규칙 엔진을 통한 사용자 제약사항 분석
            constraints = self.rule_engine.analyze_user_constraints(user_data)
            exercise_params = self.rule_engine.generate_exercise_parameters(constraints)
            
            logger.info(f"🎮 제약사항 분석 완료:")
            logger.info(f"  - BMI 카테고리: {constraints['bmi_category']}")
            logger.info(f"  - 부상 제약: {constraints['injury_constraints']['has_injury']}")
            logger.info(f"  - 권장 시작 중량: {exercise_params['base_weight_kg']}kg")
            logger.info(f"  - 세트 범위: {exercise_params['sets_range']}")
            logger.info(f"  - 반복 범위: {exercise_params['reps_range']}")
            
            # 일반 피트니스 지식 VectorDB 컨텍스트 검색
            general_context = ""
            if self._documents_loaded:
                search_query = f"운동 루틴 {inbody['gender']} {preferences.get('goal', '')} {preferences.get('experience_level', '')} {preferences.get('injury_status', '')}"
                general_context = self.vector_store.get_relevant_context(search_query, max_context_length=800)
            
            # 사용자별 컨텍스트 가져오기 (개인화 강화)
            enhanced_user_context = ""
            if user_id and user_id != "None" and user_id != "null":
                try:
                    enhanced_user_context = self.user_vector_store.get_user_context(
                        user_id, 
                        f"운동 루틴 추천 {preferences.get('goal', '')} 개인화 부상고려",
                        n_results=3
                    )
                    logger.info(f"👤 사용자 {user_id}의 개인화 컨텍스트 조회 완료: {len(enhanced_user_context)} chars")
                except Exception as e:
                    logger.error(f"사용자 컨텍스트 조회 실패: {str(e)}")
            
            # 🔥 NEW: 부상 고려 및 맞춤형 시스템 프롬프트 생성
            customized_prompt = self._create_personalized_system_prompt(
                user_data, constraints, exercise_params, general_context, enhanced_user_context
            )
            
            # Function Calling을 사용한 구조화된 운동 루틴 생성
            response = await self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{ 
                    "role": "system", 
                    "content": customized_prompt
                }, {
                    "role": "user", 
                    "content": f"사용자 ID {user_id}를 위한 완전히 개인화된 4일간의 운동 루틴을 생성해주세요."
                }],
                tools=[{
                    "type": "function",
                    "function": {
                        "name": "generate_personalized_workout_routine",
                        "description": "사용자별 제약사항을 반영한 개인화된 4일간의 운동 루틴을 생성합니다",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "routines": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "user_id": {"type": "integer"},
                                            "day": {"type": "integer"},
                                            "title": {"type": "string"},
                                            "exercises": {
                                                "type": "array",
                                                "items": {
                                                    "type": "object",
                                                    "properties": {
                                                        "id": {"type": "integer"},
                                                        "name": {"type": "string"},
                                                        "sets": {
                                                            "type": "array",
                                                            "items": {
                                                                "type": "object",
                                                                "properties": {
                                                                    "id": {"type": "integer"},
                                                                    "reps": {"type": "integer"},
                                                                    "weight": {"type": "integer"},
                                                                    "time": {"type": "string"},
                                                                    "completed": {"type": "boolean"}
                                                                },
                                                                "required": ["id", "completed"]
                                                            }
                                                        }
                                                    },
                                                    "required": ["id", "name", "sets"]
                                                }
                                            }
                                        },
                                        "required": ["user_id", "day", "title", "exercises"]
                                    }
                                }
                            },
                            "required": ["routines"]
                        }
                    }
                }],
                tool_choice={"type": "function", "function": {"name": "generate_personalized_workout_routine"}},
                temperature=0.9
            )
            
            # 🔥 개선된 Function calling 응답 처리
            if not response.choices[0].message.tool_calls:
                raise ValueError("Function calling 응답을 받지 못했습니다.")
            
            function_call = response.choices[0].message.tool_calls[0].function
            
            try:
                routine_data = json.loads(function_call.arguments)
            except json.JSONDecodeError as e:
                logger.error(f"Function calling JSON 파싱 실패: {e}")
                raise ValueError(f"AI 응답 파싱 실패: {str(e)}")
            
            # 🔥 강화된 데이터 검증
            if 'routines' not in routine_data:
                raise ValueError("응답에 'routines' 필드가 없습니다.")
            
            routines = routine_data['routines']
            if not isinstance(routines, list) or len(routines) == 0:
                raise ValueError("생성된 루틴이 비어있습니다.")
            
            # 각 루틴의 필수 필드 검증
            for i, routine in enumerate(routines):
                required_fields = ['day', 'title', 'exercises']
                for field in required_fields:
                    if field not in routine:
                        raise ValueError(f"루틴 {i+1}에 필수 필드 '{field}'가 없습니다.")
                
                if not isinstance(routine['exercises'], list) or len(routine['exercises']) == 0:
                    raise ValueError(f"루틴 {i+1}에 운동이 없습니다.")
            
            # 🔥 user_id 설정 및 검증
            for routine in routines:
                if user_id:
                    try:
                        routine['user_id'] = int(user_id)
                    except (ValueError, TypeError):
                        logger.warning(f"user_id 변환 실패: {user_id}, 기본값 1 사용")
                        routine['user_id'] = 1
                else:
                    routine['user_id'] = 1
            
            # 🔥 제약사항 후처리 검증
            validated_routines = self._validate_and_adjust_routines(routines, constraints, exercise_params)
            
            if not validated_routines:
                raise ValueError("검증된 루틴이 없습니다.")
            
            # 🔥 개선된 MongoDB 저장 처리
            saved_routines = []
            save_errors = []
            
            # DB 연결 상태 사전 확인
            try:
                connection_test = self.db.collection.count_documents({})
                logger.info(f"✅ DB 연결 확인: 총 {connection_test}개 문서")
            except Exception as db_error:
                raise ValueError(f"데이터베이스 연결 실패: {str(db_error)}")
            
            for i, routine in enumerate(validated_routines):
                try:
                    logger.info(f"루틴 {i+1}/{len(validated_routines)} 저장 시도...")
                    
                    saved_id = self.db.save_routine(routine)
                    
                    if saved_id:
                        routine['_id'] = str(saved_id)
                        routine['created_at'] = get_korea_time().isoformat()
                        saved_routines.append(routine)
                        logger.info(f"✅ 루틴 {i+1} 저장 성공: ID={saved_id}")
                    else:
                        error_msg = f"루틴 {i+1} 저장 실패: save_routine이 None 반환"
                        save_errors.append(error_msg)
                        logger.error(error_msg)
                        
                except Exception as e:
                    error_msg = f"루틴 {i+1} 저장 중 예외: {str(e)}"
                    save_errors.append(error_msg)
                    logger.error(error_msg)
            
            # 🔥 저장 결과 검증
            if not saved_routines:
                error_summary = "; ".join(save_errors)
                raise ValueError(f"모든 루틴 저장 실패: {error_summary}")
            
            # 일부만 저장된 경우 경고
            if len(saved_routines) < len(validated_routines):
                logger.warning(f"일부 루틴만 저장됨: {len(saved_routines)}/{len(validated_routines)}")
                for error in save_errors:
                    logger.warning(f"저장 실패: {error}")
            
            # 🔥 DB 재확인 검증
            if user_id:
                try:
                    verification_routines = self.db.get_user_routines(str(user_id))
                    if len(verification_routines) < len(saved_routines):
                        logger.error(f"DB 검증 실패: 저장됐다고 했지만 실제 조회 결과가 다름")
                        # 재저장 시도 로직...
                    else:
                        logger.info(f"✅ DB 검증 성공: {len(verification_routines)}개 루틴 확인")
                        saved_routines = verification_routines  # 실제 DB 데이터 사용
                except Exception as verify_error:
                    logger.error(f"DB 검증 중 오류: {str(verify_error)}")
            
            # 🔥 상세한 개인화 분석 텍스트 생성
            personalized_analysis = self._create_detailed_analysis_text(
                inbody, preferences, user_id, constraints, exercise_params
            )
            
            # 성공 응답 반환
            return {
                'success': True,
                'routines': saved_routines,
                'analysis': personalized_analysis,
                'total_days': len(saved_routines),
                'personalization_applied': True,
                'constraints_considered': constraints,
                'generation_time': get_korea_time().isoformat(),
                'save_errors': save_errors if save_errors else None,
                'validation_info': {
                    'original_count': len(validated_routines),
                    'saved_count': len(saved_routines),
                    'success_rate': f"{len(saved_routines)}/{len(validated_routines)}"
                }
            }
            
        except Exception as e:
            logger.error(f"개인화된 운동 루틴 생성 중 오류: {str(e)}")
            logger.error(traceback.format_exc())
            return await self._generate_fallback_routine_text(user_data)

    def _create_personalized_system_prompt(self, user_data, constraints, exercise_params, general_context, user_context):
        """개인화된 시스템 프롬프트 생성 - 구체적 운동명 강제"""
        from config.settings import format_exercise_database
        
        inbody = user_data.get("inbody", {})
        preferences = user_data.get("preferences", {})
        user_id = user_data.get("user_id", "Unknown")
        
        # 🔥 부상 정보 처리 개선
        injury_text = ""
        if constraints['injury_constraints']['has_injury']:
            restrictions = constraints['injury_constraints']['restrictions']
            avoid_exercises = restrictions.get('avoid_exercises', [])
            recommended_exercises = restrictions.get('recommended_exercises', [])
            
            injury_status = (
                constraints['injury_constraints'].get('injury_status') or 
                constraints['injury_constraints'].get('injury_text', '부상 있음')
            )
            
            injury_text = f"""
    🚨 **중요: 부상 고려사항**
    - 부상 상태: {injury_status}
    - 피해야 할 운동: {', '.join(avoid_exercises[:5])}
    - 추천 운동: {', '.join(recommended_exercises[:5])}

    **절대 금지**: 위의 '피해야 할 운동' 목록에 있는 운동은 절대 포함하지 마세요!
    **반드시 구체적인 운동명만 사용**: "상체운동", "가벼운운동" 등 모호한 표현 금지!
    """
        else:
            injury_text = "✅ **부상 없음:** 모든 운동 유형 가능 (단, 등록된 구체적인 한국어 운동만 사용)"
        
        # 경험 수준별 가이드라인
        experience_level = preferences.get('experience_level', '보통')
        if experience_level == '보통':
            experience_level = '중급자'
        
        min_exercises, max_exercises = exercise_params['exercises_per_day']
        
        # 🔥 운동 개수 및 품질 가이드라인 강화
        exercise_quality_guide = f"""
    💪 **운동 구성 품질 기준**
    - 일차별 운동 개수: {min_exercises}-{max_exercises}개 (부족해도 품질 우선)
    - **반드시 구체적인 운동명만 사용**: "덤벨 벤치프레스", "바벨 스쿼트" 등
    - **모호한 표현 절대 금지**: "상체운동", "가벼운운동", "기본운동" 등 사용 안됨
    - **카테고리명 사용 금지**: "하체 운동", "유산소 운동" 등 추상적 표현 안됨
    - 등록된 운동 목록에서만 선택, 없으면 유사한 구체적 운동으로 대체
    """
        
        # 한국어 운동 목록 포함
        korean_exercise_db = format_exercise_database()
        
        # 최종 통합 프롬프트
        return f"""당신은 최고 수준의 개인 맞춤형 피트니스 전문가입니다. 
    사용자 ID {user_id}를 위한 완전히 개인화된 4일간의 운동 루틴을 생성해주세요.

    **사용자 프로필:**
    - 성별: {inbody.get('gender')} / 나이: {inbody.get('age')}세
    - 체중: {inbody.get('weight')}kg / 신장: {inbody.get('height')}cm
    - 목표: {preferences.get('goal')}
    - 경험 수준: {experience_level}
    - 부상 상태: {preferences.get('injury_status')}

    {korean_exercise_db}

    {injury_text}

    {exercise_quality_guide}

    ## 🚨 필수 준수 사항

    ### 1. 구체적인 한국어 운동명 강제 사용
    - **절대 영어 운동명 사용 금지**: Bench Press, Squat 등 절대 사용 안됨
    - **등록된 구체적한 운동명만 사용**: "덤벨 벤치프레스", "바벨 백스쿼트" 등
    - **모호한 표현 완전 금지**: "상체운동", "가벼운운동", "기본운동" 등 절대 사용 안됨
    - **카테고리명 사용 금지**: "하체 운동", "유산소 운동" 등 사용 안됨

    ### 2. 운동 품질 우선
    - 개수보다 품질: 모호한 운동으로 채우지 말고 구체적인 운동만 선택
    - {experience_level} 수준에 맞는 운동만 선택
    - 부상 고려: 금지 운동은 완전 제외

    ### 3. JSON 출력 형식
    - 설명 없이 순수 JSON만 출력
    - 각 운동은 반드시 구체적이고 실행 가능한 운동명 사용

    ⚠️ **최종 체크리스트**
    ✅ 모든 운동명이 구체적이고 명확한가?
    ✅ "운동", "가벼운", "기본" 등 모호한 단어가 없는가?
    ✅ 등록된 운동 목록에서만 선택했는가?
    ✅ 부상 금지 운동을 제외했는가?

    **예시 (올바른 운동명)**: "덤벨 벤치프레스", "바벨 백스쿼트", "래터럴 레이즈"
    **예시 (금지된 표현)**: "상체운동", "가벼운운동", "기본 근력운동"

    반드시 JSON 형태로만 응답하세요!"""

    def _validate_and_adjust_routines(self, routines: List[Dict], constraints: Dict, exercise_params: Dict) -> List[Dict]:
        """생성된 루틴을 제약사항에 따라 검증 및 조정"""
        validated_routines = []
        
        for routine in routines:
            validated_routine = routine.copy()
            validated_exercises = []
            
            for exercise in routine.get('exercises', []):
                exercise_name = exercise.get('name', '').lower()
                
                # 🔥 모호한 운동명 필터링 추가
                if (not exercise_name or 
                    '운동' in exercise_name or  # "상체운동", "하체운동" 등
                    '가벼운' in exercise_name or  # "가벼운상체운동" 등
                    len(exercise_name.split()) > 4):  # 너무 긴 설명
                    logger.warning(f"⚠️ 모호한 운동명 제외: {exercise['name']}")
                    continue
                
                # 부상 제약사항 검증
                if constraints['injury_constraints']['has_injury']:
                    avoid_exercises = constraints['injury_constraints']['restrictions'].get('avoid_exercises', [])
                    should_avoid = any(avoid.lower() in exercise_name for avoid in avoid_exercises)
                    
                    if should_avoid:
                        logger.warning(f"⚠️ 부상으로 인해 운동 제외: {exercise['name']}")
                        continue  # 이 운동은 제외
                
                # 세트/반복수 조정
                adjusted_sets = []
                for set_info in exercise.get('sets', []):
                    adjusted_set = set_info.copy()
                    
                    # 반복수 조정
                    if 'reps' in adjusted_set:
                        min_reps, max_reps = exercise_params['reps_range']
                        current_reps = adjusted_set['reps']
                        if current_reps < min_reps:
                            adjusted_set['reps'] = min_reps
                        elif current_reps > max_reps:
                            adjusted_set['reps'] = max_reps
                    
                    # 중량 조정
                    if 'weight' in adjusted_set:
                        base_weight = exercise_params['base_weight_kg']
                        if constraints['experience_config']['complex_movements']:
                            adjusted_set['weight'] = max(base_weight, adjusted_set['weight'])
                        else:
                            adjusted_set['weight'] = min(base_weight + 10, adjusted_set['weight'])
                    
                    adjusted_sets.append(adjusted_set)
                
                # 세트 수 조정
                sets_min, sets_max = exercise_params['sets_range']
                if len(adjusted_sets) < sets_min:
                    # 세트 추가
                    last_set = adjusted_sets[-1].copy() if adjusted_sets else {"id": 1, "completed": False}
                    for i in range(len(adjusted_sets), sets_min):
                        new_set = last_set.copy()
                        new_set['id'] = i + 1
                        adjusted_sets.append(new_set)
                elif len(adjusted_sets) > sets_max:
                    # 세트 제거
                    adjusted_sets = adjusted_sets[:sets_max]
                
                exercise['sets'] = adjusted_sets
                validated_exercises.append(exercise)
            
            # 🔥 운동 개수 조정 - 구체적인 안전 운동으로만 보충
            min_exercises, max_exercises = exercise_params['exercises_per_day']
            if len(validated_exercises) < min_exercises:
                logger.warning(f"⚠️ {routine['day']}일차 운동 개수 부족: {len(validated_exercises)}/{min_exercises}")
                # 🔥 수정된 _get_safe_exercises 호출 (구체적인 운동만 추가)
                safe_exercises = self._get_safe_exercises(constraints, min_exercises - len(validated_exercises))
                validated_exercises.extend(safe_exercises)
            elif len(validated_exercises) > max_exercises:
                validated_exercises = validated_exercises[:max_exercises]
            
            validated_routine['exercises'] = validated_exercises
            validated_routines.append(validated_routine)
        
        return validated_routines

    def _get_safe_exercises(self, constraints: Dict, needed_count: int) -> List[Dict]:
        """부상을 고려한 구체적인 안전 운동 추가"""
        from config.settings import KOREAN_EXERCISE_DATABASE
        
        safe_exercises = []
        
        # 부상별 안전한 운동 카테고리 선택
        if constraints['injury_constraints']['has_injury']:
            injury_text = constraints['injury_constraints'].get('injury_status', '').lower()
            
            # 부상별 안전한 운동 카테고리 매핑
            if any(word in injury_text for word in ['무릎', '발목', '다리']):
                safe_categories = ['어깨 운동', '스트레칭 운동']
            elif any(word in injury_text for word in ['어깨', '목', '팔']):
                safe_categories = ['하체 운동', '스트레칭 운동']
            elif '허리' in injury_text:
                safe_categories = ['스트레칭 운동']
            else:
                safe_categories = ['스트레칭 운동']
        else:
            safe_categories = ['어깨 운동', '스트레칭 운동']  # 기본 안전 운동
        
        # 사용자 경험 수준 확인
        user_experience = constraints.get('experience_config', {})
        experience_level = '초보자'  # 안전을 위해 기본값은 초보자
        
        # 구체적인 운동명 수집
        specific_exercises = []
        for category in safe_categories:
            if category in KOREAN_EXERCISE_DATABASE:
                exercises_by_level = KOREAN_EXERCISE_DATABASE[category]
                # 초보자 레벨 운동만 사용 (안전성 우선)
                if '초보자' in exercises_by_level:
                    specific_exercises.extend(exercises_by_level['초보자'])
        
        # 중복 제거 및 구체적인 운동명만 필터링
        unique_exercises = []
        for exercise in specific_exercises:
            if (exercise and 
                exercise not in unique_exercises and
                '운동' not in exercise and  # 카테고리명 제외
                '가벼운' not in exercise and  # 모호한 표현 제외
                len(exercise.split()) <= 3):  # 적당한 길이
                unique_exercises.append(exercise)
        
        # 필요한 만큼 운동 추가
        exercise_params = self.rule_engine.generate_exercise_parameters(constraints)
        
        for i in range(min(needed_count, len(unique_exercises))):
            exercise_name = unique_exercises[i]
            safe_exercise = {
                "id": 100 + i,
                "name": exercise_name,  # 🔥 깨끗한 운동명만 사용
                "sets": [{
                    "id": 1,
                    "reps": exercise_params['reps_range'][0],
                    "weight": max(5, exercise_params['base_weight_kg'] - 10),  # 안전을 위해 가벼운 중량
                    "completed": False
                }]
            }
            safe_exercises.append(safe_exercise)
        
        if safe_exercises:
            logger.info(f"구체적인 안전 운동 {len(safe_exercises)}개 추가: {[ex['name'] for ex in safe_exercises]}")
        
        return safe_exercises

    def _create_detailed_analysis_text(self, inbody: Dict, preferences: Dict, user_id: str, constraints: Dict, exercise_params: Dict) -> str:
        """상세한 개인화 분석 텍스트 생성 - 마크다운 제거"""
        try:
            # BMI 계산 및 상태
            bmi_raw = inbody.get('bmi', 0)
            try:
                if isinstance(bmi_raw, str):
                    bmi_numbers = re.findall(r'\d+\.?\d*', bmi_raw)
                    bmi = float(bmi_numbers[0]) if bmi_numbers else 0
                else:
                    bmi = float(bmi_raw) if bmi_raw else 0
            except (ValueError, TypeError, IndexError):
                bmi = 0
            
            bmi_category = constraints['bmi_category']
            
            # 부상 분석
            injury_analysis = ""
            if constraints['injury_constraints']['has_injury']:
                injury_status = (
                    constraints['injury_constraints'].get('injury_status') or 
                    constraints['injury_constraints'].get('injury_text', '부상 있음')
                )
                avoid_count = len(constraints['injury_constraints']['restrictions'].get('avoid_exercises', []))
                injury_analysis = f"""🏥 부상 고려사항:
- 현재 상태: {injury_status}
- 제외된 운동 유형: {avoid_count}개 카테고리
- 안전성 우선으로 운동 선택 및 강도 조절"""
            else:
                injury_analysis = "✅ 부상 없음: 모든 운동 유형 가능"
            
            # 경험 수준 분석
            experience = preferences.get('experience_level', '보통')
            experience_analysis = f"""💪 경험 수준 분석 ({experience}):
- 적정 세트: {exercise_params['sets_range'][0]}-{exercise_params['sets_range'][1]}세트
- 적정 반복: {exercise_params['reps_range'][0]}-{exercise_params['reps_range'][1]}회
- 시작 중량: {exercise_params['base_weight_kg']}kg
- 복합운동: {'가능' if exercise_params['allow_complex_movements'] else '제한적'}"""
            
            # 목표별 운동 구성
            goal = preferences.get('goal', '건강 유지')
            cardio_ratio = exercise_params['cardio_ratio']
            strength_ratio = 1 - cardio_ratio
            
            goal_analysis = f"""🎯 목표 최적화 ({goal}):
- 유산소 운동: {cardio_ratio*100:.0f}%
- 근력 운동: {strength_ratio*100:.0f}%
- 집중 영역: {', '.join(exercise_params['focus_areas'])}
- 휴식 시간: {exercise_params['rest_time']}"""
            
            # BMI 기반 조정
            bmi_analysis = f"""📊 체형별 맞춤 조정:
- BMI: {bmi:.1f} ({bmi_category})
- 운동 강도: {constraints['bmi_adjustment']['focus']}
- 중량 조절: 기본값의 {constraints['bmi_adjustment']['weight_multiplier']*100:.0f}%"""
            
            # 개인화 요약
            personalization_level = "최고" if constraints['injury_constraints']['has_injury'] else "높음"
            
            analysis = f"""🎯 완전 개인화된 분석 결과 (사용자 ID: {user_id})

개인화 수준: {personalization_level} ⭐⭐⭐⭐⭐

{injury_analysis}

{experience_analysis}

{goal_analysis}

{bmi_analysis}

💡 이 루틴의 특별한 점:

1. 🛡️ 안전성 최우선: 부상 부위를 철저히 고려한 운동 선택
2. 📈 단계적 진행: 현재 수준에서 시작하여 점진적 발전
3. 🎯 목표 최적화: {goal} 달성을 위한 과학적 운동 구성
4. 👤 개인 맞춤: 당신만의 신체 조건과 제약사항을 100% 반영

🚀 성공 팁:
- 첫 주는 제시된 중량의 80%로 시작하세요
- 부상 부위에 통증이 느껴지면 즉시 중단하세요
- 2주마다 운동 강도를 5-10% 증가시키세요
- 충분한 휴식과 수면을 취하세요"""
            
            return analysis.strip()
            
        except Exception as e:
            logger.error(f"상세 분석 텍스트 생성 실패: {str(e)}")
            return f"""🎯 개인화된 분석 결과 (사용자 ID: {user_id})

귀하의 신체 조건과 목표를 반영한 맞춤형 4일간의 운동 루틴이 생성되었습니다.

주요 고려사항:
- 목표: {preferences.get('goal', '건강 유지')}
- 경험 수준: {preferences.get('experience_level', '보통')}
- 안전성을 최우선으로 고려하여 설계되었습니다.

꾸준히 실행하시면 목표 달성에 큰 도움이 될 것입니다! 💪"""

    # 기존 메서드들 유지 (생략된 부분들)
    async def identify_intent(self, message: str) -> Dict[str, Any]:
        """Function Calling을 사용하여 사용자 의도 파악"""
        try:
            response = await self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "사용자의 의도를 정확히 파악하세요."},
                    {"role": "user", "content": message}
                ],
                tools=[{
                    "type": "function",
                    "function": {
                        "name": "identify_user_intent",
                        "description": "사용자의 메시지에서 의도를 파악합니다",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "intent": {
                                    "type": "string",
                                    "enum": ["workout_recommendation", "general_chat"],
                                    "description": "사용자의 의도 (운동 추천, 일반 채팅)"
                                },
                                "has_pdf": {
                                    "type": "boolean",
                                    "description": "PDF 파일 보유/언급 여부"
                                },
                                "confidence": {
                                    "type": "number",
                                    "description": "의도 파악 확신도 (0-1)"
                                }
                            },
                            "required": ["intent", "has_pdf", "confidence"]
                        }
                    }
                }],
                tool_choice={"type": "function", "function": {"name": "identify_user_intent"}}
            )
            
            function_response = response.choices[0].message.tool_calls[0].function
            return json.loads(function_response.arguments)

        except Exception as e:
            logger.error(f"의도 파악 중 오류 발생: {str(e)}")
            return {
                "intent": "general_chat",
                "has_pdf": False,
                "confidence": 0.0
            }

    # [기존의 다른 메서드들은 동일하게 유지]
    
    def _get_file_hash(self, file_path: str) -> str:
        """파일의 해시값(MD5) 반환"""
        try:
            hash_md5 = hashlib.md5()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except (IOError, OSError) as e:
            logger.error(f"파일 해시 계산 실패 {file_path}: {e}")
            return "error_hash"
        except Exception as e:
            logger.error(f"예상치 못한 해시 계산 오류 {file_path}: {e}")
            return "unknown_hash"

    def _initialize_vector_store_sync(self):
        """동기적 VectorStore 초기화 (백그라운드 스레드에서 실행)"""
        try:
            self._loading_in_progress = True
            
            # PDF 파일들 찾기
            pdf_files = glob.glob("./data/*.pdf")
            existing_files = [f for f in pdf_files if self._file_exists(f)]
            
            if not existing_files:
                logger.info("추가할 PDF 파일이 없습니다.")
                self._documents_loaded = True
                return

            # VectorStore에 데이터가 존재하는지 확인
            vector_store_exists = self._check_vector_store_exists()
            
            if vector_store_exists:
                logger.info("기존 VectorStore 데이터를 사용합니다.")
                self._documents_loaded = True
                return
            
            # 문서 처리
            if existing_files:
                logger.info(f"VectorStore에 {len(existing_files)}개 문서 처리 중...")
                self.vector_store.add_documents(existing_files, extract_images=True)
                logger.info("문서 처리 완료")
        
            self._documents_loaded = True

        except Exception as e:
            logger.error(f"VectorStore 초기화 중 오류: {e}")
        finally:
            self._loading_in_progress = False

    def _start_background_initialization(self):
        """백그라운드에서 VectorStore 초기화 시작"""
        self._loading_thread = threading.Thread(
            target=self._initialize_vector_store_sync,
            daemon=True
        )
        self._loading_thread.start()

    def _file_exists(self, filepath: str) -> bool:
        """파일 존재 여부 확인"""
        try:
            return os.path.exists(filepath)
        except:
            return False

    def _check_vector_store_exists(self) -> bool:
        """VectorStore에 데이터가 존재하는지 확인"""
        try:
            stats = self.vector_store.get_collection_stats()
            total_docs = stats.get('total_documents', 0)
            return total_docs > 0
        except Exception as e:
            logger.error(f"VectorStore 상태 확인 실패: {e}")
            return False

    def get_loading_status(self) -> Dict[str, Any]:
        """문서 로딩 상태 반환"""
        return {
            "documents_loaded": self._documents_loaded,
            "loading_in_progress": self._loading_in_progress,
            "can_use_vector_search": self._documents_loaded
        }

    async def chat_with_bot_async(self, user_message: str, use_vector_search: bool = True) -> str:
        """비동기 챗봇 대화"""
        try:
            additional_context = ""
            
            if use_vector_search and self._documents_loaded:
                additional_context = self._get_relevant_context_for_chat(user_message)
            
            enhanced_chatbot_prompt = self._create_enhanced_chatbot_prompt(additional_context)
            
            messages = [
                {"role": "system", "content": enhanced_chatbot_prompt},
                {"role": "user", "content": user_message}
            ]
            
            response = await self.client.chat.completions.create(
                model=GPT_MODEL,
                messages=messages,
                temperature=GPT_TEMPERATURE,
                max_tokens=1000
            )
            
            bot_response = response.choices[0].message.content
            
            if bot_response is None:
                bot_response = "죄송합니다, 응답을 생성할 수 없습니다."

            return bot_response
            
        except Exception as e:
            logger.error(f"챗봇 응답 생성 중 오류: {str(e)}")
            return "죄송합니다. 일시적인 오류가 발생했습니다. 다시 시도해주세요."

    def _get_relevant_context_for_chat(self, user_message: str) -> str:
        """채팅 메시지 기반 관련 컨텍스트 검색"""
        if not self._documents_loaded:
            return ""
            
        try:
            relevant_context = self.vector_store.get_relevant_context(
                f"{user_message} 운동 피트니스 건강", 
                max_context_length=700
            )
            
            return relevant_context if relevant_context.strip() else ""
            
        except Exception as e:
            logger.error(f"채팅 컨텍스트 검색 중 오류: {e}")
            return ""

    def _create_enhanced_chatbot_prompt(self, context: str) -> str:
        """컨텍스트를 포함한 향상된 챗봇 프롬프트 생성"""
        if context.strip():
            enhanced_prompt = f"""{CHATBOT_PROMPT}

            관련 전문 정보:
            {context}

            위의 전문 정보를 참고하여 더욱 정확하고 전문적인 답변을 제공해주세요."""
        else:
            enhanced_prompt = CHATBOT_PROMPT
        
        return enhanced_prompt

    async def process_user_info_async(self, answer: str, question_type: str) -> Dict[str, Any]:
        """사용자 응답 정보 처리"""
        try:
            messages = [
                {"role": "system", "content": "사용자의 답변에서 관련 정보를 정확히 추출하세요."},
                {"role": "user", "content": f"질문 유형: {question_type}\n답변: {answer}"}
            ]

            response = await self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages,
                tools=[{
                    "type": "function",
                    "function": {
                        "name": "extract_user_info",
                        "description": "사용자 답변에서 정보 추출",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "value": {"type": "string"},
                                "unit": {"type": "string"},
                                "normalized": {"type": "boolean"}
                            }
                        }
                    }
                }],
                tool_choice={"type": "function", "function": {"name": "extract_user_info"}}
            )
            
            function_response = response.choices[0].message.tool_calls[0].function
            return json.loads(function_response.arguments)
        except Exception as e:
            logger.error(f"사용자 정보 처리 중 오류: {str(e)}")
            return {"value": answer, "unit": None, "normalized": False}

    async def _generate_fallback_routine_text(self, user_data: Dict[str, Any]) -> str:
        """오류 발생 시 기본 텍스트 형태 운동 루틴 생성"""
        try:
            inbody = user_data.get("inbody", {})
            preferences = user_data.get("preferences", {})
            user_id = user_data.get("user_id", "Unknown")
            
            gender = inbody.get('gender', '미지정')
            age = inbody.get('age', '미지정')
            goal = preferences.get('goal', '건강 유지')
            experience = preferences.get('experience_level', '보통')
            injury = preferences.get('injury_status', '없음')
            
            user_info_text = f"""사용자 정보:
    - 사용자 ID: {user_id}
    - 성별: {gender}
    - 나이: {age}세
    - 운동 목표: {goal}
    - 경험 수준: {experience}
    - 부상 상태: {injury}

    이 사용자의 부상 상태와 경험 수준을 철저히 고려하여 안전하고 효과적인 4일간의 운동 루틴을 체계적으로 추천해주세요."""
            
            response = await self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{
                    "role": "system",
                    "content": f"전문 피트니스 코치로서 사용자 ID {user_id}에게 부상을 고려한 안전한 맞춤 운동 루틴을 제공해주세요."
                }, {
                    "role": "user",
                    "content": user_info_text
                }],
                temperature=0.8,
                max_tokens=2000
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Fallback 루틴 생성 실패: {str(e)}")
            return "죄송합니다. 운동 루틴 생성 중 오류가 발생했습니다. 다시 시도해주세요."

    def get_conversation_summary(self) -> Dict[str, Any]:
        """대화 요약 정보 반환"""
        vector_stats = {}
        user_vector_stats = {}
        
        try:
            if self._documents_loaded:
                vector_stats = self.vector_store.get_collection_stats()
            user_vector_stats = self.user_vector_store.get_collection_stats()
        except Exception as e:
            logger.error(f"벡터 스토어 통계 조회 실패: {e}")
            
        return {
            "message_count": len(self.conversation_history),
            "has_recommendation": len(self.conversation_history) > 2,
            "last_recommendation": self.conversation_history[1]["content"] if len(self.conversation_history) > 1 else None,
            "general_vector_store_stats": vector_stats,
            "user_vector_store_stats": user_vector_stats,
            "loading_status": self.get_loading_status()
        }

    def __del__(self):
        """소멸자 - 스레드 풀 정리"""
        try:
            if hasattr(self, '_executor'):
                self._executor.shutdown(wait=False)
        except Exception:
            pass