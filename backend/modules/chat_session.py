# backend/modules/chat_session.py
import uuid
import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from enum import Enum
import json
import logging
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)

class SessionState(Enum):
    INITIAL = "initial"
    ASKING_PDF = "asking_pdf"
    COLLECTING_INBODY = "collecting_inbody"
    COLLECTING_WORKOUT_PREFS = "collecting_workout_prefs"
    READY_FOR_RECOMMENDATION = "ready_for_recommendation"
    CHATTING = "chatting"
    DIET_CONSULTATION = "diet_consultation"

class ChatSession:
    def __init__(self, session_id: str = None, user_id: str = None):
        self.session_id = session_id or str(uuid.uuid4())
        self.user_id = user_id  # 사용자 ID 추가
        self.state = SessionState.INITIAL
        self.messages: List[Dict] = []
        self.inbody_data: Dict = {}
        self.workout_preferences: Dict = {}
        self.current_question_index = 0
        self.user_intent = None
        self.routine_data = None
        self.created_at = datetime.now(timezone.utc)
        self.last_activity = datetime.now(timezone.utc)
        
        # 초기 봇 메시지 추가
        self.add_message(
            sender='bot',
            text='안녕하세요! AI 피트니스 코치입니다! 💪\n\n다음 중 어떤 도움이 필요하신가요?\n\n🏋️ 운동 루틴 추천\n🍎 식단 추천\n💬 운동/건강 상담\n\n원하시는 서비스를 말씀해주세요!',
            message_type='text'
        )
    
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
    
    def get_session_info(self) -> Dict:
        """세션 정보 반환"""
        return {
            'session_id': self.session_id,
            'user_id': self.user_id,  # 사용자 ID 추가
            'state': self.state.value,
            'message_count': len(self.messages),
            'current_question_index': self.current_question_index,
            'has_inbody_data': bool(self.inbody_data),
            'has_workout_preferences': bool(self.workout_preferences),
            'has_routine_data': bool(self.routine_data),
            'created_at': self.created_at.isoformat(),
            'last_activity': self.last_activity.isoformat()
        }

class ChatSessionManager:
    def __init__(self):
        self.sessions: Dict[str, ChatSession] = {}
        
        # 질문 템플릿
        self.INBODY_QUESTIONS = [
            {'key': 'gender', 'text': '성별을 알려주세요. (남성/여성)', 'required': True},
            {'key': 'age', 'text': '나이를 알려주세요.', 'required': True},
            {'key': 'height', 'text': '키를 알려주세요. (cm 단위)', 'required': True},
            {'key': 'weight', 'text': '현재 체중을 알려주세요. (kg 단위)', 'required': True},
            {'key': 'muscle_mass', 'text': '골격근량을 알고 계신다면 알려주세요. (kg 단위, 모르면 \'모름\'이라고 답해주세요)', 'required': False},
            {'key': 'body_fat', 'text': '체지방률을 알고 계신다면 알려주세요. (% 단위, 모르면 \'모름\'이라고 답해주세요)', 'required': False},
            {'key': 'bmi', 'text': 'BMI를 직접 측정하신 적이 있다면 알려주세요. (모르면 \'모름\'이라고 답해주세요)', 'required': False},
            {'key': 'basal_metabolic_rate', 'text': '기초대사율을 알고 계신다면 알려주세요. (kcal 단위, 모르면 \'모름\'이라고 답해주세요)', 'required': False}
        ]
        
        self.WORKOUT_QUESTIONS = [
            {'key': 'goal', 'text': '운동 목표를 알려주세요.\n(예: 다이어트, 근육량 증가, 체력 향상, 건강 유지 등)', 'required': True},
            {'key': 'experience_level', 'text': '운동 경험 수준을 알려주세요.\n(초보자/보통/숙련자)', 'required': True},
            {'key': 'injury_status', 'text': '현재 부상이 있거나 주의해야 할 신체 부위가 있나요?\n(없으면 \'없음\'이라고 답해주세요)', 'required': True},
            {'key': 'available_time', 'text': '일주일에 몇 번, 한 번에 몇 시간 정도 운동하실 수 있나요?', 'required': True}
        ]
    
    def get_or_create_session(self, session_id: str = None, user_id: str = None) -> ChatSession:
        """세션 가져오기 또는 생성"""
        if session_id and session_id in self.sessions:
            # 기존 세션에 user_id 업데이트
            session = self.sessions[session_id]
            if user_id and not session.user_id:
                session.user_id = user_id
            return session
        
        session = ChatSession(session_id, user_id)
        self.sessions[session.session_id] = session
        logger.info(f"새 세션 생성: {session.session_id} (사용자: {user_id})")
        return session
    
    async def process_message(self, session_id: str, message: str, analyzer, user_id: str = None) -> Dict:
        """메시지 처리 메인 로직"""
        session = self.get_or_create_session(session_id, user_id)
        
        # 사용자 메시지 추가
        session.add_message('user', message)
        
        try:
            # 상태별 메시지 처리 (기존 로직 유지)
            if session.state == SessionState.INITIAL:
                return await self._handle_initial_state(session, message, analyzer)
            
            elif session.state == SessionState.ASKING_PDF:
                return await self._handle_pdf_question(session, message)
            
            elif session.state == SessionState.COLLECTING_INBODY:
                return await self._handle_inbody_collection(session, message, analyzer)
            
            elif session.state == SessionState.COLLECTING_WORKOUT_PREFS:
                return await self._handle_workout_prefs_collection(session, message, analyzer)
            
            elif session.state == SessionState.DIET_CONSULTATION:
                return await self._handle_diet_consultation(session, message, analyzer)
            
            elif session.state == SessionState.CHATTING:
                return await self._handle_general_chat(session, message, analyzer)
            
            else:
                return await self._handle_general_chat(session, message, analyzer)
                
        except Exception as e:
            logger.error(f"메시지 처리 중 오류: {str(e)}")
            bot_message = session.add_message(
                'bot',
                '죄송합니다. 처리 중 오류가 발생했습니다. 다시 시도해주세요.'
            )
            return self._create_response(session, bot_message)
    
    async def _handle_initial_state(self, session: ChatSession, message: str, analyzer) -> Dict:
        """초기 상태 처리"""
        # 의도 파악
        intent = await analyzer.identify_intent(message)
        session.user_intent = intent
        
        if intent['intent'] == 'workout_recommendation':
            bot_message = session.add_message(
                'bot',
                '운동 루틴 추천을 위해 인바디 정보가 필요합니다.\n\n인바디 측정 결과 PDF가 있으신가요? (예/아니오)'
            )
            session.update_state(SessionState.ASKING_PDF)
            
        elif intent['intent'] == 'diet_recommendation':
            bot_message = session.add_message(
                'bot',
                '식단 추천 서비스입니다! 🍽️\n\n어떤 종류의 식단 추천을 원하시나요?\n- 다이어트 식단\n- 근육량 증가 식단\n- 건강 유지 식단\n- 특정 음식에 대한 영양 정보'
            )
            session.update_state(SessionState.DIET_CONSULTATION)
            
        else:
            # 일반 채팅
            response = await analyzer.chat_with_bot_async(message, use_vector_search=True)
            bot_message = session.add_message('bot', response)
        
        return self._create_response(session, bot_message)
    
    async def _handle_pdf_question(self, session: ChatSession, message: str) -> Dict:
        """PDF 질문 처리"""
        if any(word in message.lower() for word in ['예', '네', '있어', '있습']):
            bot_message = session.add_message(
                'bot',
                '인바디 PDF 파일을 업로드해주세요! 📄\n\n파일을 분석하여 더 정확한 맞춤 운동 루틴을 추천해드릴게요.'
            )
            # 프론트엔드에서 파일 업로드 UI를 표시하도록 신호
            return self._create_response(session, bot_message, show_file_upload=True)
        else:
            session.update_state(SessionState.COLLECTING_INBODY)
            session.current_question_index = 0
            question_text = self.INBODY_QUESTIONS[0]['text']
            bot_message = session.add_message(
                'bot',
                f'인바디 정보를 수동으로 입력하도록 하겠습니다.\n\n{question_text}'
            )
            return self._create_response(session, bot_message)
    
    async def _handle_inbody_collection(self, session: ChatSession, message: str, analyzer) -> Dict:
        """인바디 정보 수집 처리"""
        current_question = self.INBODY_QUESTIONS[session.current_question_index]
        
        # 사용자 정보 처리
        processed_info = await analyzer.process_user_info_async(message, current_question['key'])
        session.set_inbody_data({current_question['key']: processed_info['value']})
        
        # BMI 및 BMR 계산
        if current_question['key'] == 'weight' and session.inbody_data.get('height'):
            bmi = self._calculate_bmi(
                float(processed_info['value']), 
                float(session.inbody_data['height'])
            )
            if bmi:
                session.set_inbody_data({'calculated_bmi': bmi})
        
        if (current_question['key'] == 'age' and 
            session.inbody_data.get('weight') and 
            session.inbody_data.get('height') and 
            session.inbody_data.get('gender')):
            bmr = self._calculate_bmr(
                session.inbody_data['gender'],
                float(session.inbody_data['weight']),
                float(session.inbody_data['height']),
                int(processed_info['value'])
            )
            if bmr:
                session.set_inbody_data({'calculated_bmr': bmr})
        
        # 다음 질문으로 진행
        next_index = session.current_question_index + 1
        
        if next_index < len(self.INBODY_QUESTIONS):
            session.current_question_index = next_index
            next_question_text = self.INBODY_QUESTIONS[next_index]['text']
            bot_message = session.add_message('bot', next_question_text)
        else:
            # 운동 선호도 수집으로 전환
            session.update_state(SessionState.COLLECTING_WORKOUT_PREFS)
            session.current_question_index = 0
            bot_message = session.add_message(
                'bot',
                f'신체 정보 수집이 완료되었습니다! 👍\n\n이제 운동 선호도에 대해 알려주세요.\n\n{self.WORKOUT_QUESTIONS[0]["text"]}'
            )
        
        return self._create_response(session, bot_message)
    
    async def _handle_workout_prefs_collection(self, session: ChatSession, message: str, analyzer) -> Dict:
        """운동 선호도 수집 처리"""
        current_question = self.WORKOUT_QUESTIONS[session.current_question_index]
        
        # 사용자 정보 처리
        processed_info = await analyzer.process_user_info_async(message, current_question['key'])
        session.set_workout_preferences({current_question['key']: processed_info['value']})
        
        # 다음 질문으로 진행
        next_index = session.current_question_index + 1
        
        if next_index < len(self.WORKOUT_QUESTIONS):
            session.current_question_index = next_index
            next_question_text = self.WORKOUT_QUESTIONS[next_index]['text']
            bot_message = session.add_message('bot', next_question_text)
        else:
            # 운동 루틴 생성
            session.update_state(SessionState.READY_FOR_RECOMMENDATION)
            return await self._generate_workout_routine(session, analyzer)
        
        return self._create_response(session, bot_message)
    
    async def _generate_workout_routine(self, session: ChatSession, analyzer) -> Dict:
        """운동 루틴 생성"""
        bot_message = session.add_message(
            'bot',
            '수집된 정보를 바탕으로 맞춤 운동 루틴을 생성하고 있습니다... ⚡'
        )
        
        try:
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
            
            user_data = {
                'inbody': final_inbody_data,
                'preferences': session.workout_preferences,
                'user_id': session.user_id  # user_id 전달
            }
            
            routine_result = await analyzer.generate_enhanced_routine_async(user_data)
            
            if isinstance(routine_result, dict) and routine_result.get('success'):
                # 분석 결과 표시
                analysis_message = session.add_message('bot', routine_result.get('analysis', ''))
                
                # 운동 루틴 표시
                session.routine_data = routine_result.get('routines', [])
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
    
    async def _handle_diet_consultation(self, session: ChatSession, message: str, analyzer) -> Dict:
        """식단 상담 처리"""
        response = await analyzer.chat_with_bot_async(
            f"식단 관련 질문: {message}",
            use_vector_search=True
        )
        bot_message = session.add_message('bot', response)
        return self._create_response(session, bot_message)
    
    async def _handle_general_chat(self, session: ChatSession, message: str, analyzer) -> Dict:
        """일반 채팅 처리"""
        response = await analyzer.chat_with_bot_async(message, use_vector_search=True)
        bot_message = session.add_message('bot', response)
        return self._create_response(session, bot_message)
    
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
        
        # 추출된 데이터 표시
        formatted_data = self._format_inbody_data(inbody_data)
        bot_message = session.add_message(
            'bot',
            f'PDF 분석이 완료되었습니다! ✅\n\n추출된 인바디 정보:\n{formatted_data}'
        )
        
        # 운동 선호도 질문으로 전환
        session.update_state(SessionState.COLLECTING_WORKOUT_PREFS)
        session.current_question_index = 0
        
        next_message = session.add_message(
            'bot',
            f'이제 운동 선호도에 대해 몇 가지 질문을 드릴게요.\n\n{self.WORKOUT_QUESTIONS[0]["text"]}'
        )
        
        return self._create_response(session, next_message)
    
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
        from datetime import timedelta
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