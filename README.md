# MyPT-finalProduct

## 프로젝트 개요
**MyPT-finalProduct**는 컴퓨터 비전 기술을 활용한 풀스택 피트니스 웹 애플리케이션입니다. FastAPI 기반의 컴퓨터 비전 백엔드(cv-service)가 실시간으로 운동 자세를 분석하고 반복 횟수를 카운트하며, 모던 JavaScript 프론트엔드에서 운동 루틴과 피드백을 제공합니다.

### 주요 기능
- 컴퓨터 비전을 활용한 실시간 운동 분석 및 피드백 (자세 추정, 반복 횟수 카운트)
- 통합을 위한 RESTful 및 WebSocket API
- 사용자 인증 및 운동 관리를 위한 모던 프론트엔드
- Docker화된 배포 및 쉬운 개발 환경 설정

---

## 프로젝트 구조
- 프론트앤드는 기능 구현 확인을 위해 만들어진 것이니 참고 바랍니다. 
```
MyPT-finalProduct/
├── Dockerfile
├── docker-compose.yml
├── cv-service/
│   ├── main.py
│   ├── requirements.txt
│   ├── .gitignore
│   ├── test.routines.json
│   └── modules/
│        ├── exercise_analyzer.py      # 운동 분석 엔진
│        ├── exercise_api.py           # REST API 엔드포인트
│        ├── exercise_websocket.py     # WebSocket 연결
│        └── workout_routine_api.py    # 운동 루틴 API
├── frontend/
│   ├── .env
│   ├── package.json
│   ├── package-lock.json
│   ├── postcss.config.js
│   ├── tailwind.config.js
│   ├── public/
│   │    └── index.html
│   └── src/
│        ├── App.js
│        ├── index.js
│        ├── pages/
│        │    └── MainPage.js
│        ├── services/
│        │    └── workoutService.js
│        └── components/
│             ├── Auth/                # 인증 관련 컴포넌트
│             │    ├── LandingPage.js
│             │    ├── LoginForm.js
│             │    ├── LoginModal.js
│             │    ├── RegisterForm.js
│             │    └── SocialLoginButtons.js
│             ├── Exercise/             # 운동 관련 컴포넌트
│             │    ├── ExerciseAnalyzer.js
│             │    ├── WorkoutRoutine.js
│             │    └── whatever.json
```

---

## 사용 방법

### 백엔드 (cv-service)
1. **의존성 설치**
   ```bash
   pip install -r cv-service/requirements.txt
   ```

2. **백엔드 실행**
   ```bash
   cd cv-service
   uvicorn main:app --host 0.0.0.0 --port 8001 --reload
   ```

3. **API 문서**
   - 전체 API 문서는 [http://localhost:8001/docs](http://localhost:8001/docs)에서 확인하세요.

### 프론트엔드
1. **의존성 설치**
   ```bash
   cd frontend
   npm install
   ```

2. **프론트엔드 실행**
   ```bash
   npm start
   ```

### Docker 환경 설정
Docker로 전체 환경을 실행하려면:
```bash
docker-compose up --build
```

---

## 주요 API 엔드포인트 (cv-service)

### 기본 정보
- `GET /`  
  서비스 정보 및 사용 가능한 엔드포인트

- `GET /health`  
  서비스 상태 확인

### 운동 분석
- `GET /exercise/exercises`  
  사용 가능한 운동 종류 목록

- `WebSocket /api/workout/ws/analyze`  
  실시간 운동 분석 WebSocket 연결

### 운동 루틴
- `GET /routine/routines`  
  사용 가능한 운동 루틴 목록

- `POST /routine/routines`  
  새로운 운동 루틴 생성

전체 API 목록은 `/docs`에서 확인하세요.

---

## 지원 운동 종류

현재 지원하는 운동:
- **푸시업** - 팔꿈치 각도, 몸 일직선, 손 위치 분석
- **스쿼트** - 무릎 각도, 엉덩이 힌지, 무릎 추적 분석
- **레그레이즈** - 다리 직선성, 코어 안정성, 대칭성 분석
- **덤벨컬** - 팔꿈치 고정, 어깨 안정성, 가동범위 분석
- **원암덤벨로우** - 등 각도, 팔꿈치 위치, 코어 안정성 분석
- **플랭크** - 몸 일직선, 머리 중립, 지속 시간 측정

---

## 기술 스택

### 백엔드
- **FastAPI** - 웹 프레임워크
- **MediaPipe** - 포즈 인식 및 분석
- **OpenCV** - 컴퓨터 비전 처리
- **WebSocket** - 실시간 통신
- **Python 3.8+** - 개발 언어

### 프론트엔드
- **React** - UI 프레임워크
- **Tailwind CSS** - 스타일링
- **JavaScript ES6+** - 개발 언어
- **WebSocket API** - 실시간 통신

### 인프라
- **Docker & Docker Compose** - 컨테이너화
- **CORS** - 크로스 오리진 리소스 공유

---

## 개발 참고사항

### CORS 설정
- 백엔드는 프론트엔드 URL에 대해 CORS를 허용해야 합니다 (cv-service의 `main.py` 참조)

### 카메라 권한
- 웹 브라우저에서 카메라 접근 권한이 필요합니다
- HTTPS 환경에서 카메라 기능이 더 안정적으로 작동합니다

### 성능 최적화
- MediaPipe 모델은 처음 로드 시 시간이 소요될 수 있습니다
- 실시간 분석을 위해 안정적인 네트워크 연결이 필요합니다

---

## 라이선스 및 용도

이 저장소는 교육 및 피트니스 프로젝트 목적으로 제작되었습니다.

---

## 기여 및 지원

프로젝트에 대한 문의사항이나 개선 제안이 있으시면 이슈를 등록해 주세요.

### 문제 해결
- API 문서: [http://localhost:8001/docs](http://localhost:8001/docs)
- WebSocket 상태 확인: [http://localhost:8001/api/workout/ws/health](http://localhost:8001/api/workout/ws/health)
- 로그 확인: Docker 환경에서 `docker-compose logs` 명령어 사용
