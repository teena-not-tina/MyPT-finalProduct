# AI 피트니스 코치 시스템

개인 맞춤형 운동 루틴을 제공하는 AI 기반 피트니스 코칭 시스템입니다. 인바디 데이터와 사용자 선호도를 분석하여 개인화된 4일간의 운동 루틴을 생성하고, 실시간 상담 기능을 제공합니다.

## 🌟 주요 기능

### 🎯 핵심 기능
- **개인 맞춤형 운동 루틴 생성**: 인바디 데이터와 운동 목표를 바탕으로 4일간의 맞춤 루틴 생성
- **부상 고려 운동 추천**: 부상 부위를 철저히 고려한 안전한 운동 선택
- **실시간 AI 상담**: 운동 관련 질문에 대한 전문적인 AI 상담
- **PDF 인바디 분석**: 인바디 PDF 파일 업로드 및 자동 데이터 추출
- **운동 루틴 수정**: 일일 임시 수정 및 영구 수정 기능

### 💪 운동 관리 기능
- **다단계 운동 수정**:
  - 오늘 하루만 수정 (자동 복원)
  - 특정 일차 영구 수정
  - 전체 루틴 교체
- **부상별 운동 제한**: 무릎, 허리, 어깨, 발목 등 부상 부위별 운동 제외
- **경험 수준별 맞춤**: 초보자/중급자/숙련자 수준에 맞는 운동 강도 조절
- **목표별 최적화**: 다이어트, 근육량 증가, 체력 향상, 건강 유지 목표별 구성

### 🧠 AI 기술 스택
- **Vector Database**: 사용자별 개인화 데이터 저장 및 검색
- **Function Calling**: 구조화된 응답 생성
- **OCR 기술**: PDF 인바디 데이터 자동 추출
- **개인화 엔진**: 사용자 특성 기반 운동 규칙 엔진

## 📁 프로젝트 구조

```
ai-fitness-coach/
├── backend/
│   ├── config/
│   │   ├── __init__.py
│   │   └── settings.py              # 설정 파일 (GPT 모델, 운동 데이터베이스)
│   ├── database/
│   │   ├── __init__.py
│   │   └── db_config.py             # MongoDB 연결 및 데이터 관리
│   ├── modules/
│   │   ├── __init__.py
│   │   ├── chat_session.py          # 세션 관리 및 대화 흐름 제어
│   │   ├── chatbot.py               # 기본 챗봇 기능
│   │   ├── pdf_processor.py         # PDF 처리 및 OCR
│   │   ├── routine_generator.py     # AI 운동 루틴 생성 엔진
│   │   ├── user_vector_store.py     # 사용자별 벡터 데이터베이스
│   │   ├── utils.py                 # 유틸리티 함수
│   │   └── vector_store.py          # 일반 벡터 데이터베이스
│   ├── data/
│   │   ├── uploads/                 # 업로드된 파일 저장소
│   │   └── .vector_store_metadata.json
│   ├── chroma_db/                   # ChromaDB 데이터 저장소
│   ├── user_chroma_db/              # 사용자별 ChromaDB 저장소
│   ├── extracted_images/            # PDF에서 추출된 이미지
│   └── logs/                        # 로그 파일
├── .env                             # 환경 변수 (OpenAI API 키)
├── requirements.txt                 # Python 패키지 의존성
└── README.md                        # 프로젝트 문서
```

## 🚀 설치 및 실행

### 1. 환경 설정

#### 시스템 요구사항
- Python 3.8+
- MongoDB 4.4+
- Tesseract OCR
- Poppler (PDF 처리용)
- **CUDA 11.8** (GPU 가속을 위한 선택사항)

#### 중요: 설치 순서 준수 필수!

**Step 1: CUDA 및 PyTorch 설치 (반드시 conda 사용 권장)**

⚠️ **중요**: PyTorch는 pip으로 설치하면 CUDA 인식 문제가 발생할 수 있습니다. 반드시 conda를 사용하세요!

```bash
# 1-1. Conda 환경 생성 및 활성화
conda create -n ai-fitness python=3.9
conda activate ai-fitness

# 1-2. PyTorch with CUDA 11.8 설치 (필수!)
conda install pytorch torchvision torchaudio pytorch-cuda=11.8 -c pytorch -c nvidia
```

**conda를 사용할 수 없는 환경인 경우 (비권장):**
```bash
# pip 가상환경 생성
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

# PyTorch만 별도 설치 (CUDA 인식 문제 가능성 있음)
pip install -r torch-requirements.txt --extra-index-url https://download.pytorch.org/whl/cu118
```

**Step 2: PyTorch 설치 확인**
```python
import torch
print(f"CUDA available: {torch.cuda.is_available()}")
print(f"CUDA version: {torch.version.cuda}")
print(f"GPU count: {torch.cuda.device_count()}")
```
CUDA available이 True로 나와야 정상입니다!

**Step 3: 나머지 패키지 설치**
```bash
# PyTorch 설치 확인 후 나머지 패키지들 설치
pip install -r requirements.txt
```

**설치 문제 해결:**
- CUDA가 인식되지 않는 경우: conda로 PyTorch 재설치
- 패키지 충돌 시: conda와 pip을 혼용하지 말고 conda 위주로 사용
- EasyOCR 오류 시: PyTorch가 먼저 제대로 설치되었는지 확인

#### 시스템 패키지 설치

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install tesseract-ocr tesseract-ocr-kor
sudo apt-get install poppler-utils
```

**macOS:**
```bash
brew install tesseract tesseract-lang
brew install poppler
```

**Windows:**
1. [Tesseract](https://github.com/UB-Mannheim/tesseract/wiki) 다운로드 및 설치
2. [Poppler](https://blog.alivate.com.au/poppler-windows/) 다운로드 및 설치
3. 환경 변수 PATH에 설치 경로 추가

### 2. 환경 변수 설정

`.env` 파일을 생성하고 다음 내용을 추가:

```env
# OpenAI API 설정
OPENAI_API_KEY=your_openai_api_key_here

# MongoDB 설정 (선택사항, 기본값 사용 가능)
MONGO_URL=mongodb://root:example@192.168.0.199:27017/?authSource=admin
DB_NAME=test

# 기타 설정
GPT_MODEL=gpt-3.5-turbo
GPT_TEMPERATURE=0.5
MAX_TOKENS=1500
```

### 3. MongoDB 설정

#### Docker를 사용한 MongoDB 실행
```bash
docker run -d \
  --name mongodb \
  -p 27017:27017 \
  -e MONGO_INITDB_ROOT_USERNAME=root \
  -e MONGO_INITDB_ROOT_PASSWORD=example \
  mongo:latest
```

#### 직접 설치
- [MongoDB Community Edition](https://docs.mongodb.com/manual/installation/) 설치 가이드 참조

### 4. 시스템 실행

#### 기본 설정 확인
```python
python backend/config/settings.py
```

#### 챗봇 테스트
```python
python backend/modules/chatbot.py
```

## 🏗️ 시스템 아키텍처

### 핵심 구성요소

#### 1. 세션 관리 시스템 (`chat_session.py`)
- **다단계 상태 관리**: 초기화 → 정보 수집 → 루틴 생성 → 상담
- **실시간 루틴 수정**: 임시/영구 수정 기능
- **자동 복원 시스템**: 일일 수정의 자동 복원 스케줄링

#### 2. AI 운동 루틴 생성 엔진 (`routine_generator.py`)
- **규칙 기반 엔진**: 부상, 경험 수준, 목표별 운동 선택 규칙
- **Function Calling**: GPT를 통한 구조화된 운동 루틴 생성
- **개인화 분석**: BMI, 체지방률, 근육량 기반 맞춤 조정

#### 3. 데이터베이스 시스템
- **MongoDB**: 운동 루틴, 사용자 데이터 저장
- **ChromaDB**: 벡터 임베딩 기반 지식 검색
- **이중 백업 시스템**: 원본/임시 루틴 분리 관리

#### 4. PDF 처리 시스템 (`pdf_processor.py`)
- **다중 OCR 엔진**: EasyOCR + Tesseract 조합
- **이미지 전처리**: 노이즈 제거, 대비 향상, 이진화
- **자동 인바디 추출**: 체중, 체지방률, 근육량 등 자동 인식

### 데이터 흐름

```mermaid
graph TD
    A[사용자 입력] --> B[세션 관리자]
    B --> C{상태 확인}
    C -->|정보 수집| D[인바디/선호도 수집]
    C -->|루틴 생성| E[AI 엔진]
    C -->|상담| F[벡터DB 검색]
    D --> G[사용자 벡터DB]
    E --> H[MongoDB 저장]
    F --> I[응답 생성]
    H --> I
    G --> E
```

## 🔧 주요 클래스 및 메서드

### ChatSessionManager
```python
# 새 세션 생성 및 환영 메시지
await session_manager.create_session_with_welcome_message(user_id, analyzer)

# 메시지 처리
await session_manager.process_message(session_id, message, analyzer, user_id)
```

### AIAnalyzer
```python
# 개인화된 운동 루틴 생성
result = await analyzer.generate_enhanced_routine_async(user_data)

# AI 상담
response = await analyzer.chat_with_bot_async(message, use_vector_search=True)
```

### DatabaseHandler
```python
# 루틴 저장
routine_id = db.save_routine(routine_data)

# 사용자 루틴 조회
routines = db.get_user_routines(user_id)

# 임시 백업 및 복원
db.backup_user_routines_to_temp(user_id, routines, backup_type="daily_modification")
db.restore_user_routines_from_temp(user_id, backup_type="daily_modification")
```

## 🎯 운동 루틴 생성 로직

### 1. 사용자 분석
- **BMI 카테고리**: 저체중/정상/과체중/비만
- **부상 제약사항**: 부위별 금지/추천 운동 매핑
- **경험 수준**: 초보자/중급자/숙련자별 강도 조절
- **목표별 구성**: 다이어트/근육증가/체력향상/건강유지

### 2. 운동 선택 규칙
```python
# 부상별 제외 운동 예시
injury_restrictions = {
    "무릎": {
        "avoid": ["런지", "스쿼트", "레그프레스"],
        "recommend": ["레그컬", "레그익스텐션"],
        "modifications": "낮은 무게, 부분 가동범위"
    },
    "허리": {
        "avoid": ["데드리프트", "굿모닝", "로우"],
        "recommend": ["플랭크", "레그레이즈"],
        "modifications": "코어 강화 우선"
    }
}
```

### 3. 개인화 파라미터
- **기본 중량**: 체중 × 경험 계수 × BMI 조정 계수
- **세트/반복**: 목표와 경험 수준에 따른 자동 조절
- **휴식 시간**: 목표별 최적 휴식 시간 설정

## 🔄 운동 루틴 수정 시스템

### 일일 임시 수정
1. **백업 생성**: 원본 루틴을 temp_routines에 저장
2. **AI 수정**: 사용자 요청에 따른 맞춤 수정
3. **자동 복원**: 설정된 시간 후 원본 루틴으로 자동 복원

### 영구 수정
1. **특정 일차 수정**: 선택한 일차만 영구 변경
2. **여러 일차 수정**: 다중 일차 동시 수정
3. **전체 교체**: 완전히 새로운 루틴으로 교체

## 🛡️ 안전 기능

### 부상 고려 시스템
- **실시간 부상 감지**: 사용자 입력에서 부상 키워드 자동 인식
- **운동 제외 로직**: 부상 부위 관련 운동 완전 제외
- **대체 운동 추천**: 안전한 대체 운동 자동 선택

### 데이터 백업 시스템
- **이중 백업**: 원본(routines) + 임시(temp_routines) 컬렉션
- **자동 복원**: 백그라운드 스레드를 통한 자동 복원
- **버전 관리**: 수정 이력 추적 및 롤백 기능

## 🔍 벡터 데이터베이스 활용

### 일반 지식 베이스 (VectorStore)
- **피트니스 문서**: PDF 기반 전문 지식 저장
- **텍스트 + 이미지**: 다중 모달 임베딩 지원
- **컨텍스트 검색**: 사용자 질문과 관련된 전문 정보 제공

### 사용자별 데이터 (UserVectorStore)
- **개인화 컨텍스트**: 사용자별 인바디, 선호도, 진행 상황
- **학습 기반 추천**: 사용자 히스토리 기반 개선된 추천
- **프라이버시 보장**: 사용자별 분리된 데이터 관리

## 🧪 테스트 및 디버깅

### 기본 테스트
```python
# 설정 검증
python backend/config/settings.py

# 챗봇 기능 테스트
python backend/modules/chatbot.py

# 데이터베이스 연결 테스트
python backend/database/db_config.py
```

### 로그 확인
- **로그 위치**: `./logs/` 디렉토리
- **로그 레벨**: INFO, DEBUG, ERROR
- **주요 로그**: 루틴 생성, 수정, 데이터베이스 작업

## 📈 성능 최적화

### AI 모델 최적화
- **모델 선택**: GPT-3.5-turbo (속도/비용 최적화)
- **토큰 관리**: 컨텍스트 길이 제한으로 비용 절약
- **캐싱 시스템**: 벡터 임베딩 캐싱으로 응답 속도 향상

### 데이터베이스 최적화
- **인덱싱**: user_id, day 기반 복합 인덱스
- **백그라운드 작업**: 복원 스케줄링을 별도 스레드에서 처리
- **연결 풀링**: MongoDB 연결 풀 관리

## 🚨 주의사항

### 보안
- **.env 파일**: API 키 등 민감 정보 포함, git에 커밋하지 말 것
- **사용자 데이터**: 개인정보 보호 규정 준수
- **API 제한**: OpenAI API 사용량 모니터링

### 의료 면책
- **의료 조언 아님**: 시스템은 일반적인 운동 정보만 제공
- **전문의 상담**: 심각한 부상이나 질환이 있는 경우 전문의 상담 권장
- **자가 판단**: 모든 운동은 사용자 자신의 판단과 책임 하에 실행

## 🤝 기여 방법

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다. 자세한 내용은 `LICENSE` 파일을 참조하세요.

## 📞 문의

프로젝트와 관련된 문의사항이나 개선 제안이 있으시면 이슈를 등록해 주세요.

---

**주의**: 이 시스템은 일반적인 운동 정보를 제공하는 도구로, 의료 조언을 대체하지 않습니다. 심각한 부상이나 건강 문제가 있는 경우 전문의와 상담하시기 바랍니다.