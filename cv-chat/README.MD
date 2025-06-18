# 🍽️ CV-Chat: 이미지 기반 음식 추천 챗봇

**CV-Chat**은 음식 이미지로부터 재료를 자동 인식한 뒤, 해당 재료를 활용할 수 있는 요리나 레시피를 추천해주는 AI 기반 챗봇입니다. YOLO와 OCR 기술을 결합하여 재료를 감지하고, Google Custom Search API를 통해 실시간으로 웹에서 레시피를 탐색합니다.

---

## 🔧 주요 기능

### 🔍 1. 재료 인식 파이프라인 (OCR + YOLO)
- 업로드된 음식 이미지에서 **YOLOv1**을 파인튜닝한 모델을 사용하여 음식 재료를 객체 탐지합니다.
- 이미지 내 텍스트(예: 포장지, 라벨 등)는 **OCR**(Clova OCR)을 통해 추출됩니다.
- 두 결과를 통합하여 최종 **재료 리스트**를 생성합니다.

### 🍳 2. Google Search 기반 레시피 추천
- 분석된 재료를 기반으로 **Google Custom Search API**를 통해 요리 레시피를 검색합니다.
- 검색 결과에서 **URL, 제목, 요약** 정보를 사용자에게 제공합니다.

### 🤖 3. 챗봇 인터페이스 API
- 사용자는 챗봇에게 자연어로 "이 재료로 뭐 만들 수 있어?"와 같은 질문을 할 수 있습니다.
- 챗봇은 입력된 질문을 분석하고, 재료 분석 → 검색 → 요약의 흐름을 통해 응답을 제공합니다.
- **FastAPI 기반 REST API**로 구성되어 있어 React / React Native 프론트엔드와 쉽게 연동 가능합니다.

---

## ⚙️ 기술 스택

| 구분 | 기술 |
|------|------|
| **Backend** | Python 3.10, FastAPI, Pydantic, Uvicorn, Starlette, HTTPX |
| **AI 모델** | YOLOv11 (Ultralytics), OCR (Clova OCR) |
| **AI 전략** | Ensemble YOLO 모델 구조 |
| **기타 라이브러리** | OpenCV, dotenv, shutil, os, tempfile, itsdangerous |
| **DB** | MongoDB |
| **API 연동** | Google Custom Search API |
| **세션** | SessionMiddleware 기반 사용자 세션 관리 |

---

## 📦 사전 준비 사항

1. **CUDA 11.8 설치 (선택 사항)**
   - 모델 가속을 위해 CUDA 11.8이 필요합니다.
   - [NVIDIA CUDA Toolkit 11.8 다운로드](https://developer.nvidia.com/cuda-11-8-0-download-archive)

2. **Python 패키지 설치**
   pip install -r requirements.txt

환경 변수 파일 .env

.env 파일은 cv-chat 디렉토리 안에 위치해야 합니다.

🚀 실행 방법
이 프로젝트는 2개의 백엔드 서버로 구성되어 있습니다.

1️⃣ main.py 실행 (요리 추천 API)
cd cv-chat  # 해당 파일이 위치한 폴더로 이동해야 합니다.(디렉토리 구조 확인)
python main.py # 메인 서버 활성화 (각종 라우터 활성화)

2️⃣ simple_chatbot.py 실행 (AI 챗봇 서버)
cd cv-chat  # 해당 파일이 위치한 폴더로 이동해야 합니다.(디렉토리 구조 확인)
python simple_chatbot.py # 챗봇 서버 활성화

📁 디렉토리 구조 예시
cv-chat/
├── .env                  # 환경 변수 파일
├── .env.example          # 환경 변수 예시 파일
├── .gitignore
├── analysis_routes.py    # 분석 관련 라우트
├── chatbot_integrations.py
├── detection_routes.py   # 탐지 관련 라우트
├── fridge_routes.py      # 냉장고 관련 라우트
├── main.py               # FastAPI 진입점 (메인 서버 파일)
├── ocr_routes.py         # OCR 관련 라우트
├── README.MD             # 프로젝트 설명서
├── requirements.txt      # Python 패키지 목록
├── simple_chatbot.py     # 챗봇 메인 로직 (챗봇 서버 파일)
├── __pycache__/          # 파이썬 캐시 파일
├── config/               # 설정 관련 폴더
├── models/               # 모델 파일(예: best.pt 등)
├── modules/              # 기능별 모듈(예: recipe_search.py 등)
├── services/             # 서비스 계층 코드
├── temp/                 # 임시 파일 저장 폴더
├── utils/                # 유틸리티 함수 모음