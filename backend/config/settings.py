import os
from pathlib import Path
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# OpenAI API 설정
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# GPT 모델 설정
GPT_MODEL = "gpt-3.5-turbo"  # 또는 "gpt-4", "gpt-3.5-turbo"
GPT_TEMPERATURE = 0.5
MAX_TOKENS = 1500

# 🔥 운동 목록 데이터 (운동 목록.txt 기반)
KOREAN_EXERCISE_DATABASE = {
    "하체 운동": {
        "초보자": [
            "에어 스쿼트", "점프 스쿼트", "맨몸 스플릿 스쿼트", "맨몸 카프 레이즈", "맨몸 오버헤드 스쿼트",
            "맨몸 레터럴 런지", "런지", "힙 어브덕션 머신", "이너 싸이 머신", "스탠딩 카프 레이즈",
            "레그 익스텐션", "레그 컬", "시티드 레그 컬", "시티드 카프 레이즈", "글루트 브릿지",
            "라잉 힙 어브덕션", "덤벨 스쿼트", "덤벨 런지", "덤벨 고블릿 스쿼트"
        ],
        "중급자": [
            "루마니안 데드리프트", "스모 데드리프트", "덤벨 루마니안 데드리프트", "덤벨 스티프 레그 데드리프트",
            "케틀벨 고블릿 스쿼트", "케틀벨 데드리프트", "케틀벨 스모 데드리프트", "케틀벨 레터럴 런지",
            "덤벨 레터럴 런지", "바벨 스플릿 스쿼트", "덤벨 불가리안 스플릿 스쿼트", "덤벨 스모 데드리프트",
            "수평 레그 프레스", "힙 쓰러스트 머신", "덤벨 원레그 데드리프트", "피스톨 박스 스쿼트",
            "스미스머신 스쿼트", "스미스머신 데드리프트", "스텝업", "중량 스텝업"
        ],
        "숙련자": [
            "컨벤셔널 데드리프트", "바벨 백스쿼트", "바벨 프론트 랙 런지", "바벨 불가리안 스플릿 스쿼트",
            "저처 스쿼트", "바벨 런지", "바벨 점프 스쿼트", "바벨 박스 스쿼트", "바벨 원레그 데드리프트",
            "정지 데드리프트", "정지 백 스쿼트", "트랩바 데드리프트", "바벨 핵 스쿼트",
            "노르딕 햄스트링 컬", "데피싯 데드리프트", "런지 트위스트", "몬스터 글루트 머신"
        ]
    },
    "어깨 운동": {
        "초보자": [
            "덤벨 프론트 레이즈", "덤벨 레터럴 레이즈", "바벨 프론트 레이즈", "슈러그 머신",
            "바벨 슈러그", "덤벨 슈러그", "숄더 프레스 머신", "레터럴 레이즈 머신", "페이스 풀"
        ],
        "중급자": [
            "덤벨 숄더 프레스", "시티드 덤벨 숄더 프레스", "아놀드 프레스", "바벨 업라이트 로우",
            "이지바 업라이트 로우", "덤벨 업라이트 로우", "시티드 바벨 숄더 프레스", "케이블 레터럴 레이즈",
            "케이블 프론트 레이즈", "시티드 덤벨 리어 레터럴 레이즈", "리어 델토이드 플라이 머신",
            "플레이트 숄더 프레스", "Y 레이즈"
        ],
        "숙련자": [
            "오버헤드 프레스", "스미스머신 오버헤드 프레스", "비하인드 넥 프레스", "핸드스탠드",
            "핸드스탠드 푸시업", "푸시 프레스", "원암 케이블 레터럴 레이즈", "랜드마인 프레스",
            "원암 랜드마인 프레스", "케이블 리버스 플라이", "케이블 익스터널/인터널 로테이션",
            "숄더 탭"
        ]
    },
    "유산소 운동": {
        "초보자": [
            "걷기", "트레드밀 (저속)", "싸이클", "일립티컬 머신"
        ],
        "중급자": [
            "계단 오르기", "줄넘기", "스텝밀", "로잉 머신"
        ],
        "숙련자": [
            "이단 뛰기", "어썰트 바이크", "하이니 스킵", "달리기"
        ]
    },
    "공원 운동": {
        "초보자": [
            "허리돌리기", "팔 돌리기", "공중 걷기", "파도타기", "노젓기",
            "등 허리 지압", "다리 근육풀기", "오금펴기", "역기 내리기"
        ],
        "중급자": [
            "윗몸 일으키기", "달리기"
        ],
        "숙련자": [
            "거꾸로 매달리기"
        ]
    },
    "스트레칭 운동": {
        "초보자": [
            "목 스트레칭", "어깨 스트레칭", "손목 스트레칭", "종아리 스트레칭", "앞벅지 스트레칭",
            "햄스트링 스트레칭", "안쪽 다리 스트레칭", "등 펴기"
        ],
        "중급자": [
            "고관절 열기 스트레칭", "장요근 스트레칭", "대둔근 스트레칭", "가슴열기 스트레칭",
            "와이드 햄스트링 스트레칭", "다운독", "업독"
        ],
        "숙련자": [
            "누워서 척추 스트레칭", "고양이 자세", "와이드 햄스트링 스트레칭 (심화)", "발바닥 스트레칭"
        ]
    }
}

# 🔥 운동 목록을 텍스트로 변환하는 함수
def format_exercise_database():
    """운동 목록을 프롬프트용 텍스트로 변환"""
    formatted_text = "## 📋 등록된 한국어 운동 목록 (부위별, 숙련도별 분류)\n\n"
    formatted_text += "**⚠️ 중요: 반드시 아래 한국어 운동명만 사용하세요. 영어 운동명은 절대 사용하지 마세요!**\n\n"
    
    for body_part, levels in KOREAN_EXERCISE_DATABASE.items():
        formatted_text += f"### {body_part}\n"
        for level, exercises in levels.items():
            formatted_text += f"**{level}:**\n"
            for exercise in exercises:
                formatted_text += f"- {exercise}\n"
            formatted_text += "\n"
        formatted_text += "\n"
    
    formatted_text += """
**운동 선택 규칙:**
1. 사용자의 경험 수준(초보자/중급자/숙련자)에 맞는 운동만 선택
2. 부상 부위가 있다면 해당 부위 운동은 절대 제외
3. 위 목록에 있는 한국어 운동명만 사용
4. 영어 운동명(Bench Press, Squat 등)은 절대 사용 금지
5. 목록에 없는 운동은 사용하지 말고, 유사한 한국어 운동으로 대체
"""
    
    return formatted_text

# test.routines.json 예시를 프롬프트에 포함
TEST_ROUTINE_PATH = os.path.join(os.path.dirname(__file__), 'test.routines.json')
try:
    with open(TEST_ROUTINE_PATH, encoding='utf-8') as f:
        TEST_ROUTINE_EXAMPLE = f.read()
except FileNotFoundError:
    TEST_ROUTINE_EXAMPLE = "[]"

# Function Calling 정의
FUNCTION_DEFINITIONS = [
    {
        "name": "identify_user_intent",
        "description": "사용자의 메시지에서 의도를 파악합니다",
        "parameters": {
            "type": "object",
            "properties": {
                "intent": {
                    "type": "string",
                    "enum": ["workout_recommendation", "general_chat", "pdf_upload"],
                    "description": "사용자의 의도 (운동 추천, 일반 채팅, PDF 업로드)"
                },
                "has_pdf": {
                    "type": "boolean",
                    "description": "사용자가 PDF 파일이 있다고 언급했는지 여부"
                },
                "confidence": {
                    "type": "number",
                    "description": "의도 파악 확신도 (0-1)"
                }
            },
            "required": ["intent", "has_pdf", "confidence"]
        }
    },
    {
        "name": "extract_user_info",
        "description": "사용자의 답변에서 신체 정보를 추출합니다",
        "parameters": {
            "type": "object",
            "properties": {
                "field_name": {
                    "type": "string",
                    "enum": ["gender", "age", "height", "weight", "muscle_mass", "body_fat", "bmi", "basal_metabolic_rate"],
                    "description": "추출된 정보의 필드명"
                },
                "value": {
                    "type": "string",
                    "description": "추출된 값"
                },
                "unit": {
                    "type": "string",
                    "description": "단위 (kg, cm, %, 세, 등)"
                }
            },
            "required": ["field_name", "value"]
        }
    },
    {
        "name": "extract_workout_preferences",
        "description": "사용자의 운동 선호도 및 목표를 추출합니다",
        "parameters": {
            "type": "object",
            "properties": {
                "goal": {
                    "type": "string",
                    "description": "운동 목표 (다이어트, 근육량 증가, 체력 향상 등)"
                },
                "experience_level": {
                    "type": "string",
                    "enum": ["초보자", "중급자", "숙련자"],
                    "description": "운동 숙련도"
                },
                "injury_status": {
                    "type": "string",
                    "description": "부상 여부 및 상태"
                },
                "daily_workout_time": {
                    "type": "string",
                    "description": "하루 운동 가능 시간"
                }
            },
            "required": ["goal", "experience_level", "injury_status"]
        }
    }
]

# 의도 파악용 시스템 프롬프트
INTENT_RECOGNITION_PROMPT = """
당신은 사용자의 메시지를 분석하여 의도를 파악하는 AI입니다.

사용자의 메시지를 분석하여 다음 중 하나의 의도를 파악하세요:
1. workout_recommendation: 운동 루틴, 운동 추천, 헬스 관련 요청
2. pdf_upload: PDF 파일 업로드 관련 언급
3. general_chat: 일반적인 대화, 인사말, 운동 상담

또한 사용자가 PDF 파일이 있다고 언급했는지 확인하세요.
"""

# 🔥 수정된 정보 수집용 질문 템플릿 (BMI 제거, 운동시간 개선)
INBODY_QUESTIONS = {
    "gender": "성별을 알려주세요. (남성/여성)",
    "age": "나이를 알려주세요.",
    "height": "키를 알려주세요. (cm 단위)",
    "weight": "현재 체중을 알려주세요. (kg 단위)",
    "muscle_mass": "골격근량을 알고 계신다면 알려주세요. (kg 단위, 모르면 '모름'이라고 답해주세요)",
    "body_fat": "체지방률을 알고 계신다면 알려주세요. (% 단위, 모르면 '모름'이라고 답해주세요)",
    # BMI 제거 (백엔드에서 자동 계산)
    "basal_metabolic_rate": "기초대사율을 알고 계신다면 알려주세요. (kcal 단위, 모르면 '모름'이라고 답해주세요)"
}

# 🔥 수정된 운동 질문 (시간 질문 개선)
WORKOUT_QUESTIONS = {
    "goal": "운동 목표를 알려주세요. (예: 다이어트, 근육량 증가, 체력 향상, 건강 유지 등)",
    "experience_level": "운동 경험 수준을 알려주세요. (초보자/중급자/숙련자)",
    "injury_status": "현재 부상이 있거나 주의해야 할 신체 부위가 있나요? (없으면 '없음'이라고 답해주세요)",
    "daily_workout_time": "하루에 운동할 수 있는 시간을 알려주세요. (예: 30분, 1시간 등)"
}

# 🔥 개선된 시스템 프롬프트 - 한국어 강제 및 운동 목록 반영
SYSTEM_PROMPT = f"""
# 한국어 맞춤형 운동 루틴 추천 AI 프롬프트

당신은 퍼스널 트레이너이자 운동 전문가 AI입니다. 사용자의 인바디 데이터와 운동 목적을 바탕으로 **등록된 한국어 운동 목록**에서만 최적의 맞춤형 운동 루틴을 제공해야 합니다.

{format_exercise_database()}

## 🚨 중요 규칙

### 1. 한국어 운동명 강제 사용
- **절대 영어 운동명 사용 금지**: Bench Press, Squat, Deadlift 등 영어명 절대 사용 안됨
- **반드시 위 목록의 한국어 운동명만 사용**: 덤벨 벤치프레스, 스쿼트, 데드리프트 등
- **목록에 없는 운동은 사용 금지**: 유사한 한국어 운동으로 대체

### 2. 사용자 숙련도별 운동 선택
- **초보자**: 초보자 운동만 선택 + 머신 운동 위주
- **중급자**: 초보자 + 중급자 운동 선택 가능
- **숙련자**: 모든 레벨 운동 선택 가능

### 3. 부위별 균형 잡힌 구성
- **하체 운동**: 사용자 레벨에 맞는 하체 운동 포함
- **어깨 운동**: 사용자 레벨에 맞는 어깨 운동 포함
- **유산소 운동**: 체력 수준에 맞는 유산소 포함
- **스트레칭**: 마무리 스트레칭 포함

### 4. 부상 고려 운동 선택
- 부상 부위가 있으면 해당 부위 운동 **완전 제외**
- 안전한 대체 운동으로 구성

## 📋 출력 형식

1. 먼저 사용자 정보 분석 결과를 간단히 설명
2. 그 다음 **반드시** 아래 예시와 동일한 JSON 구조로만 4일차 루틴 출력
3. **설명, 마크다운, 기타 텍스트는 절대 포함하지 마세요**

### JSON 출력 예시:
{TEST_ROUTINE_EXAMPLE}

## 🎯 개인화 추천 가이드라인

### 신체 정보 활용
- BMI와 체지방률을 고려한 운동 강도 조절
- 근육량 대비 적절한 중량 설정
- 기초대사율을 고려한 운동량 조절

### 개인 선호도 반영
- 운동 목표에 따른 운동 구성 (다이어트 vs 근육량 증가)
- 경험 수준에 맞는 운동 난이도 조절
- 부상 부위 고려한 대체 운동 제시
- 하루 운동 시간에 맞는 운동량 배분

### 사용자 개인 데이터 활용
- 사용자별 과거 운동 기록 및 선호도 반영
- 개인별 운동 패턴 및 성과 분석 결과 적용
- 사용자 맞춤형 운동 강도 및 진행도 설정

## ⚠️ 최종 체크리스트
✅ 한국어 운동명만 사용했는가?
✅ 사용자 숙련도에 맞는 운동인가?
✅ 부상 부위 운동을 제외했는가?
✅ 등록된 운동 목록에서만 선택했는가?
✅ JSON 형식으로만 출력했는가?

**반드시 위 체크리스트를 확인하고 JSON 배열만 반환하세요!**
"""

# 챗봇 프롬프트 - 후속 질문 및 상담용 (기존 유지하되 한국어 강조)
CHATBOT_PROMPT = """
당신은 친근하고 전문적인 AI 피트니스 코치입니다. 사용자가 이미 받은 운동 루틴을 바탕으로 추가 질문에 답변하고, 필요에 따라 운동 계획을 조정해줍니다.

## 대화 가이드라인:

### 1. 친근하고 격려하는 톤
- 사용자의 궁금증과 고민을 공감하며 들어주기
- 긍정적이고 동기부여가 되는 언어 사용
- 전문적이지만 어렵지 않게 설명

### 2. 맞춤형 조언 제공
- 기존 추천 루틴을 참고하여 일관성 있는 답변
- 사용자의 상황 변화나 요청에 따른 조정
- 안전하고 실현 가능한 대안 제시

### 3. 한국어 운동명 사용
- **운동명 언급시 반드시 한국어 사용**
- 영어 운동명은 절대 사용하지 않기
- 등록된 운동 목록의 한국어명만 사용

### 4. 다양한 질문 유형 대응
- **운동 조정**: 시간/강도/빈도 변경 요청
- **운동 방법**: 정확한 자세, 호흡법 등
- **진행 상황**: 효과 측정, 다음 단계 계획
- **문제 해결**: 부상 예방, plateau 극복
- **동기부여**: 의지력 저하, 습관 형성

### 5. 안전 우선
- 무리한 운동보다는 꾸준함을 강조
- 부상 위험이 있는 요청은 주의 당부
- 필요시 전문의 상담 권유

### 6. 실용적 조언
- 구체적이고 실행 가능한 팁 제공
- 일상생활에 적용하기 쉬운 방법
- 단계별 접근법 제시

### 7. 사용자 개인화
- 사용자별 운동 히스토리 및 선호도 고려
- 개인 맞춤형 조언 및 격려 메시지
- 사용자의 진행 상황에 따른 동적 조정

응답 시 이모지를 적절히 사용하여 친근함을 표현하고, 사용자가 실천하고 싶어지도록 동기부여해주세요.
필요한 요구사항이 있는지 물어보고, 사용자의 피드백을 적극 반영해주세요.
"""

# 사용자 상태 관리용 열거형
class UserState:
    INITIAL = "initial"
    COLLECTING_INBODY = "collecting_inbody"
    COLLECTING_WORKOUT_PREFS = "collecting_workout_prefs"
    READY_FOR_RECOMMENDATION = "ready_for_recommendation"
    CHATTING = "chatting"

# 파일 및 디렉토리 설정
UPLOAD_DIR = Path("data/uploads")
VECTOR_DB_DIR = Path("chroma_db")
USER_VECTOR_DB_DIR = Path("user_chroma_db")  # 사용자 전용 벡터DB
EXTRACTED_IMAGES_DIR = Path("extracted_images")

# PDF 처리 설정
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_FILE_TYPES = ['pdf']

# OCR 설정
OCR_LANGUAGES = ['ko', 'en']
USE_GPU = True  # CUDA 사용 여부

# Vector Store 설정
VECTOR_COLLECTION_NAME = "fitness_knowledge_base"
USER_VECTOR_COLLECTION_NAME = "user_personal_data"  # 사용자 개인 데이터 컬렉션
EMBEDDING_MODEL = "text-embedding-3-small"
MAX_CONTEXT_LENGTH = 3000
SEARCH_RESULTS_LIMIT = 10

# 챗봇 설정
MAX_CONVERSATION_HISTORY = 20  # 대화 기록 최대 저장 수
SESSION_TIMEOUT_HOURS = 24  # 세션 타임아웃 (시간)
DAILY_MODIFICATION_TIMEOUT_HOURS = 24  # 일일 수정사항 타임아웃

# Streamlit 설정
PAGE_TITLE = "AI 피트니스 코치"
PAGE_ICON = "💪"
LAYOUT = "wide"

# 로깅 설정
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# 디렉토리 생성 함수
def create_directories():
    """필요한 디렉토리들을 생성합니다."""
    directories = [
        UPLOAD_DIR,
        VECTOR_DB_DIR,
        USER_VECTOR_DB_DIR,  # 사용자 벡터DB 디렉토리 추가
        EXTRACTED_IMAGES_DIR,
        Path("logs")
    ]
    
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)

# 환경 변수 검증
def validate_environment():
    """필수 환경 변수들이 설정되어 있는지 확인합니다."""
    required_vars = ["OPENAI_API_KEY"]
    missing_vars = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        raise EnvironmentError(f"다음 환경 변수들이 설정되지 않았습니다: {', '.join(missing_vars)}")
    
    return True

# 설정 요약 함수
def get_config_summary():
    """현재 설정 정보를 반환합니다."""
    return {
        "gpt_model": GPT_MODEL,
        "gpt_temperature": GPT_TEMPERATURE,
        "max_tokens": MAX_TOKENS,
        "embedding_model": EMBEDDING_MODEL,
        "vector_collection": VECTOR_COLLECTION_NAME,
        "user_vector_collection": USER_VECTOR_COLLECTION_NAME,
        "max_file_size_mb": MAX_FILE_SIZE / (1024 * 1024),
        "ocr_languages": OCR_LANGUAGES,
        "use_gpu": USE_GPU,
        "session_timeout_hours": SESSION_TIMEOUT_HOURS,
        "daily_modification_timeout_hours": DAILY_MODIFICATION_TIMEOUT_HOURS,
        "korean_exercise_categories": len(KOREAN_EXERCISE_DATABASE),
        "total_korean_exercises": sum(len(exercises) for category in KOREAN_EXERCISE_DATABASE.values() for exercises in category.values())
    }

if __name__ == "__main__":
    # 설정 검증 및 디렉토리 생성
    try:
        validate_environment()
        create_directories()
        print("✅ 환경 설정이 완료되었습니다.")
        
        # 설정 정보 출력
        config = get_config_summary()
        print("\n📋 현재 설정:")
        for key, value in config.items():
            print(f"  {key}: {value}")
            
        # 🔥 운동 목록 요약 출력
        print(f"\n🏋️ 등록된 한국어 운동:")
        for category, levels in KOREAN_EXERCISE_DATABASE.items():
            total_exercises = sum(len(exercises) for exercises in levels.values())
            print(f"  {category}: {total_exercises}개")
            
    except Exception as e:
        print(f"❌ 설정 오류: {e}")