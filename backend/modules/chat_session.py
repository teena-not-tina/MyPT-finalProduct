# backend/modules/chat_session.py
import uuid
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from enum import Enum
import json
import logging

logger = logging.getLogger(__name__)

class SessionState(Enum):
    INITIAL = "initial"
    CHECKING_EXISTING_ROUTINE = "checking_existing_routine"
    ASKING_PDF = "asking_pdf"
    COLLECTING_INBODY = "collecting_inbody"
    COLLECTING_WORKOUT_PREFS = "collecting_workout_prefs"
    ASKING_ROUTINE_MODIFICATION = "asking_routine_modification"
    MODIFYING_ROUTINE = "modifying_routine"
    READY_FOR_RECOMMENDATION = "ready_for_recommendation"
    CHATTING = "chatting"

class ChatSession:
    def __init__(self, session_id: str = None, user_id: str = None):
        self.session_id = session_id or str(uuid.uuid4())
        self.user_id = user_id
        self.state = SessionState.INITIAL
        self.messages: List[Dict] = []
        self.inbody_data: Dict = {}
        self.workout_preferences: Dict = {}
        self.current_question_index = 0
        self.user_intent = None
        self.routine_data = None
        self.existing_routines = None  # 기존 루틴 저장
        self.modification_request = None  # 수정 요청 내용
        self.daily_modifications = {}  # 일일 수정사항 저장
        self.created_at = datetime.now(timezone.utc)
        self.last_activity = datetime.now(timezone.utc)
        
        # 초기 봇 메시지는 _handle_initial_state에서 처리
    
    def add_message(self, sender: str, text: str, message_type: str = 'text', **kwargs) -> Dict:
        """메시지 추가"""
        message = {
            'id': len(self.messages) + 1,
            'sender': sender,
            'text': text,
            'type': message_type,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            **kwargs
        }
        self.messages.append(message)
        self.last_activity = datetime.now(timezone.utc)
        return message
    
    def update_state(self, new_state: SessionState):
        """세션 상태 업데이트"""
        logger.info(f"Session {self.session_id}: {self.state.value} -> {new_state.value}")
        self.state = new_state
        self.last_activity = datetime.now(timezone.utc)
    
    def set_inbody_data(self, data: Dict):
        """인바디 데이터 설정"""
        self.inbody_data.update(data)
    
    def set_workout_preferences(self, data: Dict):
        """운동 선호도 설정"""
        self.workout_preferences.update(data)
    
    def set_existing_routines(self, routines: List[Dict]):
        """기존 루틴 설정"""
        self.existing_routines = routines
    
    def set_daily_modification(self, modification: Dict):
        """일일 수정사항 설정 (당일만 적용)"""
        today = datetime.now(timezone.utc).date().isoformat()
        self.daily_modifications[today] = modification
        
        # 이전 날짜의 수정사항 정리
        to_remove = [date for date in self.daily_modifications.keys() if date != today]
        for date in to_remove:
            del self.daily_modifications[date]
    
    def get_current_routines(self):
        """현재 적용된 루틴 반환 (일일 수정사항 반영)"""
        today = datetime.now(timezone.utc).date().isoformat()
        base_routines = self.existing_routines or []
        
        # 오늘의 수정사항이 있으면 적용
        if today in self.daily_modifications:
            modified_routines = base_routines.copy()
            modification = self.daily_modifications[today]
            # 여기서 수정사항을 적용하는 로직 구현
            # (예: 특정 운동 교체, 강도 조절 등)
            return self._apply_daily_modifications(modified_routines, modification)
        
        return base_routines
    
    def _apply_daily_modifications(self, routines: List[Dict], modification: Dict) -> List[Dict]:
        """일일 수정사항을 루틴에 적용"""
        # 실제 수정 로직 구현
        # 예시: 특정 운동의 강도 조절, 운동 교체 등
        modified_routines = json.loads(json.dumps(routines))  # 깊은 복사
        
        mod_type = modification.get('type')
        if mod_type == 'intensity_adjustment':
            # 강도 조절
            factor = modification.get('factor', 1.0)
            for routine in modified_routines:
                for exercise in routine.get('exercises', []):
                    for set_info in exercise.get('sets', []):
                        if 'weight' in set_info:
                            set_info['weight'] = int(set_info['weight'] * factor)
                        if 'reps' in set_info:
                            set_info['reps'] = int(set_info['reps'] * factor)
        
        elif mod_type == 'exercise_replacement':
            # 운동 교체
            old_exercise = modification.get('old_exercise')
            new_exercise = modification.get('new_exercise')
            if old_exercise and new_exercise:
                for routine in modified_routines:
                    for exercise in routine.get('exercises', []):
                        if old_exercise.lower() in exercise.get('name', '').lower():
                            exercise['name'] = new_exercise
        
        return modified_routines
    
    def get_session_info(self) -> Dict:
        """세션 정보 반환"""
        return {
            'session_id': self.session_id,
            'user_id': self.user_id,
            'state': self.state.value,
            'message_count': len(self.messages),
            'current_question_index': self.current_question_index,
            'has_inbody_data': bool(self.inbody_data),
            'has_workout_preferences': bool(self.workout_preferences),
            'has_routine_data': bool(self.routine_data),
            'has_existing_routines': bool(self.existing_routines),
            'has_daily_modifications': bool(self.daily_modifications),
            'created_at': self.created_at.isoformat(),
            'last_activity': self.last_activity.isoformat()
        }

class ChatSessionManager:
    def __init__(self):
        self.sessions: Dict[str, ChatSession] = {}
        
        # 질문 템플릿
        self.INBODY_QUESTIONS = [
            {'key': 'gender', 'text': '성별을 선택해주세요.', 'type': 'buttons', 'options': ['남성', '여성'], 'required': True},
            {'key': 'age', 'text': '나이를 입력해주세요.', 'type': 'input', 'required': True},
            {'key': 'height', 'text': '키를 입력해주세요. (cm 단위)', 'type': 'input', 'required': True},
            {'key': 'weight', 'text': '현재 체중을 입력해주세요. (kg 단위)', 'type': 'input', 'required': True},
            {'key': 'muscle_mass', 'text': '골격근량을 알고 계신다면 선택해주세요.', 'type': 'buttons', 'options': ['모름', '30kg 미만', '30-35kg', '35-40kg', '40-45kg', '45kg 이상'], 'required': False},
            {'key': 'body_fat', 'text': '체지방률을 알고 계신다면 선택해주세요.', 'type': 'buttons', 'options': ['모름', '10% 미만', '10-15%', '15-20%', '20-25%', '25-30%', '30% 이상'], 'required': False},
            {'key': 'bmi', 'text': 'BMI를 알고 계신다면 선택해주세요.', 'type': 'buttons', 'options': ['모름', '18.5 미만 (저체중)', '18.5-23 (정상)', '23-25 (과체중)', '25-30 (비만)', '30 이상 (고도비만)'], 'required': False},
            {'key': 'basal_metabolic_rate', 'text': '기초대사율을 알고 계신다면 선택해주세요.', 'type': 'buttons', 'options': ['모름', '1200 미만', '1200-1400', '1400-1600', '1600-1800', '1800-2000', '2000 이상'], 'required': False}
        ]
        
        self.WORKOUT_QUESTIONS = [
            {'key': 'goal', 'text': '운동 목표를 입력해주세요.\n(예: 다이어트, 근육량 증가, 체력 향상, 건강 유지 등)', 'type': 'input', 'required': True},
            {'key': 'experience_level', 'text': '운동 경험 수준을 선택해주세요.', 'type': 'buttons', 'options': ['초보자', '보통', '숙련자'], 'required': True},
            {'key': 'injury_status', 'text': '현재 부상이나 주의사항을 입력해주세요.\n(없으면 \'없음\'이라고 입력해주세요)', 'type': 'input', 'required': True},
            {'key': 'available_time', 'text': '운동 가능 시간을 선택해주세요.', 'type': 'buttons', 'options': ['주 1-2회, 30분', '주 2-3회, 45분', '주 3-4회, 1시간', '주 4-5회, 1시간+', '매일, 30분', '매일, 1시간+'], 'required': True}
        ]
        
        # 루틴 수정 관련 옵션들
        self.ROUTINE_MODIFICATION_OPTIONS = [
            '새로운 루틴으로 완전히 교체',
            '기존 루틴 일부 수정 (오늘만)',
            '운동 강도 조절 (오늘만)',
            '운동 시간 조절 (오늘만)',
            '특정 운동 교체 (오늘만)',
            '기존 루틴 유지하고 상담만'
        ]
        
    MAX_SESSIONS = 1000
    
    def get_or_create_session(self, session_id: str = None, user_id: str = None) -> ChatSession:
        """세션 가져오기 또는 생성 - 빈 세션만 생성"""
        if session_id and session_id in self.sessions:
            session = self.sessions[session_id]
            if user_id and not session.user_id:
                session.user_id = user_id
            return session
        
        session = ChatSession(session_id, user_id)
        self.sessions[session.session_id] = session
        logger.info(f"새 세션 생성: {session.session_id} (사용자: {user_id})")
        
        # 초기 메시지 생성 로직 완전 제거!
        return session
    
    async def create_session_with_welcome_message(self, user_id: str, analyzer) -> Dict:
        """새 세션 생성 + 환영 메시지 생성 (모든 초기화 로직의 중심)"""
        try:
            # 1. 빈 세션 생성
            session = self.get_or_create_session(user_id=user_id)
            
            # 2. 사용자 상황에 따른 환영 메시지 생성
            if user_id and user_id not in ["None", "null", None]:
                # 사용자 ID가 있는 경우 - 기존 루틴 확인
                try:
                    has_routines = analyzer.db.has_user_routines(user_id)
                    logger.info(f"사용자 {user_id} 기존 루틴 존재: {has_routines}")
                    
                    if has_routines:
                        # 기존 루틴이 있는 경우
                        existing_routines = analyzer.db.get_user_routines(user_id)
                        session.set_existing_routines(existing_routines)
                        
                        bot_message = session.add_message(
                            'bot',
                            f'안녕하세요! 💪 기존에 생성하신 운동 루틴({len(existing_routines)}일차)이 있습니다.\n\n어떻게 도와드릴까요?'
                        )
                        session.update_state(SessionState.ASKING_ROUTINE_MODIFICATION)
                        
                        return self._create_response(
                            session, 
                            bot_message,
                            show_buttons=True,
                            button_options=self.ROUTINE_MODIFICATION_OPTIONS,
                            routine_data=existing_routines
                        )
                    else:
                        # 기존 루틴이 없는 경우 - 바로 PDF 질문
                        bot_message = session.add_message(
                            'bot',
                            '운동 루틴 추천을 위해 인바디 정보가 필요합니다.\n\n인바디 측정 결과 PDF가 있으신가요?'
                        )
                        session.update_state(SessionState.ASKING_PDF)
                        
                        return self._create_response(
                            session,
                            bot_message,
                            show_buttons=True,
                            button_options=['예, PDF가 있어요', '아니오, 수동 입력할게요']
                        )
                        
                except Exception as db_error:
                    logger.error(f"DB 조회 실패: {str(db_error)}")
                    # DB 실패시 기본 PDF 질문
                    bot_message = session.add_message(
                        'bot',
                        '운동 루틴 추천을 위해 인바디 정보가 필요합니다.\n\n인바디 측정 결과 PDF가 있으신가요?'
                    )
                    session.update_state(SessionState.ASKING_PDF)
                    
                    return self._create_response(
                        session,
                        bot_message,
                        show_buttons=True,
                        button_options=['예, PDF가 있어요', '아니오, 수동 입력할게요']
                    )
            else:
                # 사용자 ID가 없는 경우 - 바로 PDF 질문
                bot_message = session.add_message(
                    'bot',
                    '안녕하세요! AI 피트니스 코치입니다! 💪\n\n운동 루틴 추천을 위해 인바디 정보가 필요합니다.\n\n인바디 측정 결과 PDF가 있으신가요?'
                )
                session.update_state(SessionState.ASKING_PDF)
                
                return self._create_response(
                    session,
                    bot_message,
                    show_buttons=True,
                    button_options=['예, PDF가 있어요', '아니오, 수동 입력할게요']
                )
                
        except Exception as e:
            logger.error(f"환영 메시지 생성 실패: {str(e)}")
            raise
    
    async def process_message(self, session_id: str, message: str, analyzer, user_id: str = None) -> Dict:
        """메시지 처리 메인 로직 - 초기 상태는 더 이상 여기서 처리하지 않음"""
        session = self.get_or_create_session(session_id, user_id)
        
        # 사용자 메시지 추가
        session.add_message('user', message)
        
        try:
            # INITIAL 상태는 이제 create_session_with_welcome_message에서만 처리됨
            # 여기서는 실제 대화 상태들만 처리
            
            if session.state == SessionState.ASKING_ROUTINE_MODIFICATION:
                return await self._handle_routine_modification_choice(session, message, analyzer)
            
            elif session.state == SessionState.MODIFYING_ROUTINE:
                return await self._handle_routine_modification(session, message, analyzer)
            
            elif session.state == SessionState.ASKING_PDF:
                return await self._handle_pdf_question(session, message)
            
            elif session.state == SessionState.COLLECTING_INBODY:
                return await self._handle_inbody_collection(session, message, analyzer)
            
            elif session.state == SessionState.COLLECTING_WORKOUT_PREFS:
                return await self._handle_workout_prefs_collection(session, message, analyzer)
            
            elif session.state == SessionState.CHATTING:
                return await self._handle_general_chat(session, message, analyzer)
            
            else:
                # 예상치 못한 상태 - 일반 채팅으로 처리
                return await self._handle_general_chat(session, message, analyzer)
                
        except Exception as e:
            logger.error(f"메시지 처리 중 오류: {str(e)}")
            bot_message = session.add_message(
                'bot',
                '죄송합니다. 처리 중 오류가 발생했습니다. 다시 시도해주세요.'
            )
            return self._create_response(session, bot_message)
        
    async def _handle_routine_modification_choice(self, session: ChatSession, message: str, analyzer) -> Dict:
        """루틴 수정 선택 처리"""
        session.modification_request = message
        
        if '새로운 루틴으로 완전히 교체' in message:
            # 기존 루틴 삭제 후 새로운 루틴 생성
            analyzer.db.delete_user_routines(session.user_id)
            # 사용자 벡터DB에서도 기존 데이터 삭제
            if hasattr(analyzer, 'user_vector_store') and session.user_id:
                analyzer.user_vector_store.delete_user_data(session.user_id)
            
            bot_message = session.add_message(
                'bot',
                '기존 루틴을 삭제하고 새로운 루틴을 생성하겠습니다.\n\n인바디 측정 결과 PDF가 있으신가요?'
            )
            session.update_state(SessionState.ASKING_PDF)
            return self._create_response(session, bot_message, show_buttons=True,
                                       button_options=['예, PDF가 있어요', '아니오, 수동 입력할게요'])
        
        elif any(keyword in message for keyword in ['일부 수정', '강도 조절', '시간 조절', '운동 교체']) and '오늘만' in message:
            bot_message = session.add_message(
                'bot',
                '오늘 하루만 적용될 수정사항을 말씀해주세요.\n\n예시:\n- "1일차 스쿼트를 런지로 바꿔주세요"\n- "전체적으로 강도를 20% 낮춰주세요"\n- "운동 시간을 30분으로 줄여주세요"\n\n내일부터는 다시 원래 루틴으로 돌아갑니다.'
            )
            session.update_state(SessionState.MODIFYING_ROUTINE)
            return self._create_response(session, bot_message)
        
        elif '기존 루틴 유지하고 상담만' in message:
            current_routines = session.get_current_routines()
            bot_message = session.add_message(
                'bot',
                '현재 루틴에 대해 궁금한 점이나 조언이 필요한 부분을 말씀해주세요! 💪'
            )
            session.update_state(SessionState.CHATTING)
            return self._create_response(session, bot_message, routine_data=current_routines)
        
        else:
            # 기본 처리
            bot_message = session.add_message(
                'bot',
                '죄송합니다. 다시 선택해주세요.'
            )
            return self._create_response(session, bot_message, show_buttons=True,
                                       button_options=self.ROUTINE_MODIFICATION_OPTIONS)
    
    async def _handle_routine_modification(self, session: ChatSession, message: str, analyzer) -> Dict:
        """루틴 수정 처리 (오늘만 적용)"""
        try:
            # Function calling으로 수정 요청 분석
            response = await analyzer.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{
                    "role": "system",
                    "content": "사용자의 운동 루틴 수정 요청을 분석하고 오늘 하루만 적용될 수정사항을 생성하세요."
                }, {
                    "role": "user",
                    "content": f"현재 루틴: {session.existing_routines}\n\n수정 요청: {message}"
                }],
                tools=[{
                    "type": "function",
                    "function": {
                        "name": "create_daily_modification",
                        "description": "오늘 하루만 적용될 운동 루틴 수정사항 생성",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "modification_type": {
                                    "type": "string",
                                    "enum": ["exercise_replacement", "intensity_adjustment", "time_adjustment", "general_modification"],
                                    "description": "수정 유형"
                                },
                                "details": {"type": "string", "description": "수정 내용 설명"},
                                "parameters": {
                                    "type": "object",
                                    "properties": {
                                        "factor": {"type": "number", "description": "강도 조절 비율 (예: 0.8 = 20% 감소)"},
                                        "old_exercise": {"type": "string", "description": "교체할 기존 운동"},
                                        "new_exercise": {"type": "string", "description": "새로운 운동"},
                                        "time_limit": {"type": "integer", "description": "시간 제한 (분)"}
                                    }
                                },
                                "success": {"type": "boolean", "description": "수정 가능 여부"}
                            }
                        }
                    }
                }],
                tool_choice={"type": "function", "function": {"name": "create_daily_modification"}}
            )
            
            if response.choices[0].message.tool_calls:
                function_call = response.choices[0].message.tool_calls[0].function
                modification_result = json.loads(function_call.arguments)
                
                if modification_result.get('success', False):
                    # 오늘의 수정사항 저장
                    daily_modification = {
                        'type': modification_result.get('modification_type'),
                        'details': modification_result.get('details'),
                        'parameters': modification_result.get('parameters', {}),
                        'applied_date': datetime.now(timezone.utc).date().isoformat()
                    }
                    
                    session.set_daily_modification(daily_modification)
                    
                    # 수정된 루틴 가져오기
                    modified_routines = session.get_current_routines()
                    
                    bot_message = session.add_message(
                        'bot',
                        f"오늘 하루만 적용될 루틴 수정이 완료되었습니다! ✅\n\n📝 수정 내용: {modification_result.get('details', '')}\n\n내일부터는 다시 원래 루틴으로 돌아갑니다.\n\n수정된 오늘의 루틴을 확인해보세요."
                    )
                    session.update_state(SessionState.CHATTING)
                    return self._create_response(session, bot_message, routine_data=modified_routines)
                else:
                    bot_message = session.add_message(
                        'bot',
                        '요청하신 수정이 어려울 수 있습니다. 다른 방식으로 수정해보시겠어요?\n\n구체적인 요청을 다시 말씀해주세요.'
                    )
                    return self._create_response(session, bot_message)
            
        except Exception as e:
            logger.error(f"루틴 수정 중 오류: {str(e)}")
            bot_message = session.add_message(
                'bot',
                '루틴 수정 중 오류가 발생했습니다. 다시 시도해주세요.'
            )
            return self._create_response(session, bot_message)
    
    async def _handle_pdf_question(self, session: ChatSession, message: str) -> Dict:
        """PDF 질문 처리"""
        if '예' in message or 'PDF가 있어요' in message:
            bot_message = session.add_message(
                'bot',
                '인바디 PDF 파일을 업로드해주세요! 📄\n\n파일을 분석하여 더 정확한 맞춤 운동 루틴을 추천해드릴게요.'
            )
            return self._create_response(session, bot_message, show_file_upload=True)
        else:
            session.update_state(SessionState.COLLECTING_INBODY)
            session.current_question_index = 0
            question = self.INBODY_QUESTIONS[0]
            
            bot_message = session.add_message(
                'bot',
                f'인바디 정보를 수동으로 입력하도록 하겠습니다.\n\n{question["text"]}'
            )
            
            if question['type'] == 'buttons':
                return self._create_response(session, bot_message, 
                                           show_buttons=True, 
                                           button_options=question['options'])
            else:
                return self._create_response(session, bot_message, show_input=True)
    
    async def _handle_inbody_collection(self, session: ChatSession, message: str, analyzer) -> Dict:
        """인바디 정보 수집 처리"""
        current_question = self.INBODY_QUESTIONS[session.current_question_index]
        
        # 사용자 정보 처리
        processed_info = await analyzer.process_user_info_async(message, current_question['key'])
        session.set_inbody_data({current_question['key']: processed_info['value']})
        
        # 사용자 벡터DB에 저장 (user_id 포함)
        if hasattr(analyzer, 'user_vector_store') and session.user_id:
            await self._save_inbody_to_vector_db(session, analyzer)
        
        # BMI 및 BMR 계산
        self._calculate_derived_values(session)
        
        # 다음 질문으로 진행
        next_index = session.current_question_index + 1
        
        if next_index < len(self.INBODY_QUESTIONS):
            session.current_question_index = next_index
            next_question = self.INBODY_QUESTIONS[next_index]
            bot_message = session.add_message('bot', next_question['text'])
            
            if next_question['type'] == 'buttons':
                return self._create_response(session, bot_message, 
                                           show_buttons=True, 
                                           button_options=next_question['options'])
            else:
                return self._create_response(session, bot_message, show_input=True)
        else:
            # 운동 선호도 수집으로 전환
            session.update_state(SessionState.COLLECTING_WORKOUT_PREFS)
            session.current_question_index = 0
            first_workout_question = self.WORKOUT_QUESTIONS[0]
            
            bot_message = session.add_message(
                'bot',
                f'신체 정보 수집이 완료되었습니다! 👍\n\n이제 운동 선호도에 대해 알려주세요.\n\n{first_workout_question["text"]}'
            )
            
            if first_workout_question['type'] == 'buttons':
                return self._create_response(session, bot_message, 
                                           show_buttons=True, 
                                           button_options=first_workout_question['options'])
            else:
                return self._create_response(session, bot_message, show_input=True)
    
    async def _handle_workout_prefs_collection(self, session: ChatSession, message: str, analyzer) -> Dict:
        """운동 선호도 수집 처리"""
        current_question = self.WORKOUT_QUESTIONS[session.current_question_index]
        
        # 사용자 정보 처리
        processed_info = await analyzer.process_user_info_async(message, current_question['key'])
        session.set_workout_preferences({current_question['key']: processed_info['value']})
        
        # 사용자 벡터DB에 저장 (user_id 포함)
        if hasattr(analyzer, 'user_vector_store') and session.user_id:
            await self._save_preferences_to_vector_db(session, analyzer)
        
        # 다음 질문으로 진행
        next_index = session.current_question_index + 1
        
        if next_index < len(self.WORKOUT_QUESTIONS):
            session.current_question_index = next_index
            next_question = self.WORKOUT_QUESTIONS[next_index]
            bot_message = session.add_message('bot', next_question['text'])
            
            if next_question['type'] == 'buttons':
                return self._create_response(session, bot_message, 
                                           show_buttons=True, 
                                           button_options=next_question['options'])
            else:
                return self._create_response(session, bot_message, show_input=True)
        else:
            # 운동 루틴 생성
            session.update_state(SessionState.READY_FOR_RECOMMENDATION)
            return await self._generate_workout_routine(session, analyzer)
    
    async def _generate_workout_routine(self, session: ChatSession, analyzer) -> Dict:
        """운동 루틴 생성 - 사용자별 개인화된 추천"""
        bot_message = session.add_message(
            'bot',
            '수집된 정보를 바탕으로 맞춤 운동 루틴을 생성하고 있습니다... ⚡'
        )
        
        try:
            # 사용자별 컨텍스트 가져오기 (user_id 기반)
            user_context = ""
            if hasattr(analyzer, 'user_vector_store') and session.user_id:
                user_context = analyzer.user_vector_store.get_user_context(
                    session.user_id, 
                    f"운동 루틴 추천 {session.workout_preferences.get('goal', '')}"
                )
            
            # 최종 인바디 데이터 구성
            final_inbody_data = {
                'gender': session.inbody_data['gender'],
                'age': int(session.inbody_data['age']),
                'height': int(session.inbody_data['height']),
                'weight': int(session.inbody_data['weight']),
                'muscle_mass': session.inbody_data.get('muscle_mass') if session.inbody_data.get('muscle_mass') != '모름' else None,
                'body_fat': session.inbody_data.get('body_fat') if session.inbody_data.get('body_fat') != '모름' else None,
                'bmi': session.inbody_data.get('bmi') if session.inbody_data.get('bmi') != '모름' else session.inbody_data.get('calculated_bmi'),
                'basal_metabolic_rate': session.inbody_data.get('basal_metabolic_rate') if session.inbody_data.get('basal_metabolic_rate') != '모름' else session.inbody_data.get('calculated_bmr')
            }
            
            # 사용자 데이터 구성 (user_id 포함하여 개인화)
            user_data = {
                'inbody': final_inbody_data,
                'preferences': session.workout_preferences,
                'user_id': session.user_id,
                'user_context': user_context  # 사용자별 컨텍스트
            }
            
            routine_result = await analyzer.generate_enhanced_routine_async(user_data)
            
            if isinstance(routine_result, dict) and routine_result.get('success'):
                # 분석 결과 표시
                analysis_message = session.add_message('bot', routine_result.get('analysis', ''))
                
                # 운동 루틴 표시
                session.routine_data = routine_result.get('routines', [])
                session.set_existing_routines(session.routine_data)  # 기존 루틴으로 설정
                
                routine_message = session.add_message(
                    'bot', 
                    '📋 맞춤 운동 루틴:', 
                    'routine'
                )
                
                session.update_state(SessionState.CHATTING)
                final_message = session.add_message(
                    'bot',
                    '운동 루틴에 대해 궁금한 점이나 조정이 필요한 부분이 있으면 언제든 말씀해주세요! 💪'
                )
                
                return self._create_response(session, final_message, routine_data=session.routine_data)
            else:
                # Fallback 텍스트 응답
                bot_message = session.add_message('bot', routine_result)
                session.update_state(SessionState.CHATTING)
                return self._create_response(session, bot_message)
                
        except Exception as e:
            logger.error(f"운동 루틴 생성 중 오류: {str(e)}")
            error_message = session.add_message(
                'bot',
                '죄송합니다. 운동 루틴 생성 중 오류가 발생했습니다. 다시 시도해주세요.'
            )
            session.update_state(SessionState.INITIAL)
            return self._create_response(session, error_message)
    
    async def _handle_general_chat(self, session: ChatSession, message: str, analyzer) -> Dict:
        """일반 채팅 처리 - 사용자별 컨텍스트 활용"""
        # 사용자별 컨텍스트 가져오기 (user_id 기반)
        user_context = ""
        if (hasattr(analyzer, 'user_vector_store') and session.user_id and 
            session.user_id != "None" and session.user_id != "null"):
            try:
                user_context = analyzer.user_vector_store.get_user_context(session.user_id, message)
            except Exception as e:
                logger.error(f"사용자 컨텍스트 조회 실패: {str(e)}")
        
        # 컨텍스트와 함께 응답 생성
        enhanced_message = message
        if user_context:
            enhanced_message = f"사용자 컨텍스트: {user_context}\n\n사용자 질문: {message}"
        
        response = await analyzer.chat_with_bot_async(enhanced_message, use_vector_search=True)
        bot_message = session.add_message('bot', response)
        
        # 현재 루틴 데이터 포함 (수정사항 반영)
        current_routines = session.get_current_routines()
        return self._create_response(session, bot_message, routine_data=current_routines if current_routines else None)
    
    async def _save_inbody_to_vector_db(self, session: ChatSession, analyzer):
        """인바디 데이터를 사용자별 벡터DB에 저장"""
        try:
            if session.user_id and session.user_id != "None" and session.user_id != "null" and session.inbody_data:
                analyzer.user_vector_store.add_user_inbody_data(session.user_id, session.inbody_data)
                # MongoDB에도 저장
                analyzer.db.save_user_data(session.user_id, 'inbody', session.inbody_data)
                logger.info(f"사용자 {session.user_id}의 인바디 데이터 저장 완료")
        except Exception as e:
            logger.error(f"인바디 데이터 벡터DB 저장 실패: {str(e)}")
    
    async def _save_preferences_to_vector_db(self, session: ChatSession, analyzer):
        """운동 선호도를 사용자별 벡터DB에 저장"""
        try:
            if session.user_id and session.user_id != "None" and session.user_id != "null" and session.workout_preferences:
                analyzer.user_vector_store.add_user_preferences(session.user_id, session.workout_preferences)
                # MongoDB에도 저장
                analyzer.db.save_user_data(session.user_id, 'preferences', session.workout_preferences)
                logger.info(f"사용자 {session.user_id}의 운동 선호도 저장 완료")
        except Exception as e:
            logger.error(f"운동 선호도 벡터DB 저장 실패: {str(e)}")
    
    def _calculate_derived_values(self, session: ChatSession):
        """BMI 및 BMR 계산"""
        try:
            # BMI 계산
            if ('weight' in session.inbody_data and 'height' in session.inbody_data and 
                session.inbody_data['weight'] and session.inbody_data['height']):
                
                weight = float(session.inbody_data['weight'])
                height = float(session.inbody_data['height'])
                bmi = self._calculate_bmi(weight, height)
                if bmi:
                    session.set_inbody_data({'calculated_bmi': bmi})
            
            # BMR 계산
            if ('age' in session.inbody_data and 'weight' in session.inbody_data and 
                'height' in session.inbody_data and 'gender' in session.inbody_data):
                
                bmr = self._calculate_bmr(
                    session.inbody_data['gender'],
                    float(session.inbody_data['weight']),
                    float(session.inbody_data['height']),
                    int(session.inbody_data['age'])
                )
                if bmr:
                    session.set_inbody_data({'calculated_bmr': bmr})
                    
        except Exception as e:
            logger.error(f"수치 계산 중 오류: {str(e)}")
    
    def _calculate_bmi(self, weight: float, height: float) -> float:
        """BMI 계산"""
        if not weight or not height:
            return None
        height_in_meters = height / 100
        return round((weight / (height_in_meters * height_in_meters)), 1)
    
    def _calculate_bmr(self, gender: str, weight: float, height: float, age: int) -> int:
        """BMR 계산"""
        if not weight or not height or not age:
            return None
        
        if gender == '남성':
            bmr = (10 * weight) + (6.25 * height) - (5 * age) + 5
        elif gender == '여성':
            bmr = (10 * weight) + (6.25 * height) - (5 * age) - 161
        else:
            return None
        
        return int(bmr)
    
    def _create_response(self, session: ChatSession, bot_message: Dict, **kwargs) -> Dict:
        """응답 생성"""
        return {
            'success': True,
            'session_id': session.session_id,
            'session_info': session.get_session_info(),
            'messages': session.messages,
            'latest_message': bot_message,
            **kwargs
        }
    
    async def process_inbody_pdf(self, session_id: str, inbody_data: Dict, user_id: str = None) -> Dict:
        """인바디 PDF 처리"""
        session = self.get_or_create_session(session_id, user_id)
        
        # 인바디 데이터 저장
        session.set_inbody_data(inbody_data)
        
        # 사용자별 벡터DB에 저장
        if hasattr(session, 'user_id') and session.user_id:
            try:
                # analyzer는 process_inbody_pdf 호출부에서 전달받아야 함
                # 여기서는 임시로 처리
                pass
            except Exception as e:
                logger.error(f"PDF 인바디 데이터 벡터DB 저장 실패: {str(e)}")
        
        # 추출된 데이터 표시
        formatted_data = self._format_inbody_data(inbody_data)
        bot_message = session.add_message(
            'bot',
            f'PDF 분석이 완료되었습니다! ✅\n\n추출된 인바디 정보:\n{formatted_data}'
        )
        
        # 운동 선호도 질문으로 전환 (첫 번째 질문)
        session.update_state(SessionState.COLLECTING_WORKOUT_PREFS)
        session.current_question_index = 0
        first_workout_question = self.WORKOUT_QUESTIONS[0]
        
        next_message = session.add_message(
            'bot',
            f'이제 운동 선호도에 대해 몇 가지 질문을 드릴게요.\n\n{first_workout_question["text"]}'
        )
        
        # 질문 타입에 따라 응답 형태 결정
        if first_workout_question['type'] == 'buttons':
            return self._create_response(session, next_message, 
                                       show_buttons=True, 
                                       button_options=first_workout_question['options'])
        else:
            return self._create_response(session, next_message, show_input=True)
    
    def _format_inbody_data(self, data: Dict) -> str:
        """인바디 데이터 포맷팅"""
        korean_labels = {
            'gender': '성별',
            'age': '나이',
            'height': '신장',
            'weight': '체중',
            'muscle_mass': '골격근량',
            'body_fat': '체지방률',
            'bmi': 'BMI',
            'basal_metabolic_rate': '기초대사량'
        }
        
        formatted_lines = []
        for key, value in data.items():
            if value is not None:
                label = korean_labels.get(key, key)
                unit = self._get_unit_for_field(key)
                formatted_lines.append(f"- {label}: {value}{unit}")
        
        return '\n'.join(formatted_lines)
    
    def _get_unit_for_field(self, field: str) -> str:
        """필드별 단위 반환"""
        units = {
            'height': 'cm',
            'weight': 'kg',
            'muscle_mass': 'kg',
            'body_fat': '%',
            'basal_metabolic_rate': 'kcal',
            'age': '세'
        }
        return units.get(field, '')
    
    def get_session(self, session_id: str) -> Optional[ChatSession]:
        """세션 가져오기"""
        return self.sessions.get(session_id)
    
    def delete_session(self, session_id: str) -> bool:
        """세션 삭제"""
        if session_id in self.sessions:
            del self.sessions[session_id]
            logger.info(f"세션 삭제: {session_id}")
            return True
        return False
    
    def cleanup_old_sessions(self, max_age_hours: int = 24):
        """오래된 세션 정리"""
        current_time = datetime.now(timezone.utc)
        
        to_delete = []
        for session_id, session in self.sessions.items():
            if current_time - session.last_activity > timedelta(hours=max_age_hours):
                to_delete.append(session_id)
        
        for session_id in to_delete:
            self.delete_session(session_id)
        
        if to_delete:
            logger.info(f"{len(to_delete)}개의 오래된 세션을 정리했습니다.")

# 전역 세션 매니저 인스턴스
session_manager = ChatSessionManager()