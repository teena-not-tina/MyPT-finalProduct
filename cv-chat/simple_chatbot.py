# simple_chatbot.py - OCR 결과 Gemini 분석 통합 버전 + 레시피 추천 + 대화형 챗봇
# -*- coding: utf-8 -*-

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Request
from pydantic import BaseModel
import httpx
import base64
from typing import Dict, Any, List, Optional
import asyncio
import traceback
from io import BytesIO
import time
import json
import sys
import os
from dotenv import load_dotenv
from collections import defaultdict
from datetime import datetime, timedelta
from starlette.middleware.sessions import SessionMiddleware
import re

# .env 파일 로드 (반드시 다른 import보다 먼저!)
load_dotenv()

# 프로젝트 루트 경로 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

app = FastAPI(title="Simple Chatbot Webhook with Recipe Recommendation and Conversational AI")

# CORS 미들웨어 추가
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    SessionMiddleware,
    secret_key="아주_강력한_랜덤_문자열"  # 실제 서비스에서는 안전하게 관리!
)

# Food Detection API URL
FOOD_DETECTION_API = "http://192.168.0.18:8003"

# 요청 모델
class ImageMessage(BaseModel):
    user_id: int
    image_url: str = None
    image_base64: str = None
    platform: str = "generic"
    text: str = None  # 대화형 챗봇을 위해 추가

class TextMessage(BaseModel):
    user_id: int
    ingredients: List[str]
    query: str
    platform: str = "web"



# 영어-한글 변환 매핑 (상수로 분리)
LABEL_MAPPING = {
    'eggplant': '가지', 'onion': '양파', 'apple': '사과', 'bell_pepper': '피망',
    'pepper': '고추', 'tomato': '토마토', 'potato': '감자', 'carrot': '당근',
    'cabbage': '양배추', 'broccoli': '브로콜리', 'cucumber': '오이', 'lettuce': '상추',
    'spinach': '시금치', 'radish': '무', 'garlic': '마늘', 'ginger': '생강',
    'corn': '옥수수', 'mushroom': '버섯', 'pumpkin': '호박', 'sweet_potato': '고구마',
    'banana': '바나나', 'orange': '오렌지', 'grape': '포도', 'strawberry': '딸기',
    'watermelon': '수박', 'melon': '멜론', 'peach': '복숭아', 'pear': '배',
    'cherry': '체리', 'mango': '망고', 'pineapple': '파인애플', 'milk': '우유',
    'yogurt': '요거트', 'cheese': '치즈', 'egg': '계란', 'bread': '빵',
    'bred': '빵', 'rice': '쌀', 'noodle': '면', 'pasta': '파스타',
    'meat': '고기', 'beef': '소고기', 'pork': '돼지고기', 'chicken': '닭고기',
    'fish': '생선', 'shrimp': '새우', 'avocado': '아보카도', 'can': '캔',
    'blueberries': '블루베리', 'blueberry': '블루베리'
}

# 전역 변수
recipe_searcher = None

# 사용자별 대화 컨텍스트 저장 (메모리)
conversation_contexts = defaultdict(dict)

def extract_ocr_text(api_result: Dict) -> Optional[str]:
    """API 응답에서 OCR 텍스트 추출"""
    try:
        enhanced_info = api_result.get('enhanced_info', {})
        if not enhanced_info or not isinstance(enhanced_info, dict):
            print("⚠️ enhanced_info가 없거나 dict가 아님")
            return None
            
        brand_info = enhanced_info.get('brand_info')
        if not brand_info:
            print("⚠️ brand_info가 None이거나 비어있음")
            return None
        
        print(f"🔍 brand_info 발견!")
        
        # brand_info가 dict인 경우
        if isinstance(brand_info, dict):
            print(f"   키들: {list(brand_info.keys())}")
            
            # OCR 텍스트가 있는지 확인
            if 'ocr_text' in brand_info and brand_info['ocr_text']:
                ocr_text = brand_info['ocr_text']
                print(f"✅ OCR 텍스트 발견 (ocr_text): {ocr_text[:50]}...")
                return ocr_text
            
            # detected_text 확인
            elif 'detected_text' in brand_info:
                detected_texts = brand_info['detected_text']
                if isinstance(detected_texts, list) and detected_texts:
                    ocr_text = detected_texts[0]  # 첫 번째 텍스트 사용
                    print(f"✅ OCR 텍스트 발견 (detected_text): {len(detected_texts)}개")
                    return ocr_text
                elif isinstance(detected_texts, str) and detected_texts:
                    print(f"✅ OCR 텍스트 발견 (detected_text): {detected_texts[:50]}...")
                    return detected_texts
        
        # brand_info가 string인 경우
        elif isinstance(brand_info, str) and brand_info:
            print(f"✅ OCR 텍스트 발견 (brand_info as string): {brand_info[:50]}...")
            return brand_info
            
    except Exception as ocr_error:
        print(f"⚠️ OCR 결과 추출 중 오류: {ocr_error}")
        traceback.print_exc()
    
    return None

def format_detections_with_duplicates(detections: List[Dict]) -> List[Dict]:
    """탐지 결과 포맷팅 및 중복 집계"""
    # 중복 집계를 위한 딕셔너리
    label_counts = {}
    label_confidences = {}
    
    for det in detections:
        # 한글 이름 우선 사용
        korean_name = det.get('korean_name')
        label = det.get('label') or det.get('class') or det.get('name') or 'Unknown'
        
        # korean_name이 있으면 사용, 없으면 매핑 테이블에서 찾기
        if korean_name and korean_name != label:
            display_label = korean_name
        elif label.lower() in LABEL_MAPPING:
            display_label = LABEL_MAPPING[label.lower()]
        else:
            display_label = label
        
        confidence = det.get('confidence', 0)
        
        # 중복 집계
        if display_label in label_counts:
            label_counts[display_label] += 1
            # 최대 신뢰도 유지
            if confidence > label_confidences[display_label]:
                label_confidences[display_label] = confidence
        else:
            label_counts[display_label] = 1
            label_confidences[display_label] = confidence
    
    # 집계된 결과를 formatted_detections로 변환
    formatted_detections = []
    for label, count in label_counts.items():
        # 개수가 2개 이상이면 라벨에 개수 표시
        if count > 1:
            display_label = f"{label} ({count}개)"
        else:
            display_label = label
        
        formatted_det = {
            'label': display_label,  # 개수가 포함된 라벨
            'confidence': label_confidences[label],
            'count': count,
            'bbox': [],
            'original_label': label  # 원본 라벨 보존
        }
        formatted_detections.append(formatted_det)
    
    # 신뢰도 순으로 정렬
    formatted_detections.sort(key=lambda x: x['confidence'], reverse=True)
    
    # 중복 집계 통계 출력
    duplicate_items = {k: v for k, v in label_counts.items() if v > 1}
    if duplicate_items:
        print(f"\n📦 중복 항목 발견:")
        for label, count in duplicate_items.items():
            print(f"   - {label}: {count}개")
    
    print(f"\n📊 신뢰도 상위 5개 항목:")
    for det in formatted_detections[:5]:
        print(f"   - {det['label']}: {det['confidence']:.1%}")
    
    return formatted_detections

async def call_food_detection_api(image_base64: str) -> Dict:
    """Food Detection API 호출 (에러 처리 강화)"""
    print(f"📡 API 호출 중...")
    
    try:
        if not image_base64:
            raise HTTPException(status_code=400, detail="이미지 데이터가 없습니다")
        
        image_bytes = base64.b64decode(image_base64)
        filename = f"chatbot_image_{int(time.time())}.jpg"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            files = {
                'file': (filename, BytesIO(image_bytes), 'image/jpeg')
            }
            data = {
                'confidence': '0.5',
                'use_ensemble': 'true',
                'use_enhanced': 'true'
            }
            
            response = await client.post(
                f"{FOOD_DETECTION_API}/api/detect",
                files=files,
                data=data
            )
            
            print(f"📡 API 응답 상태: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"📡 API 응답 데이터: {result}")
                return result if result else {}  # None 체크
            else:
                print(f"❌ API 오류: {response.status_code} - {response.text}")
                raise HTTPException(status_code=500, detail=f"API 오류: {response.status_code}")
                
    except base64.binascii.Error as e:
        print(f"❌ Base64 디코딩 오류: {e}")
        raise HTTPException(status_code=400, detail="잘못된 이미지 데이터")
    except httpx.TimeoutException as e:
        print(f"❌ API 타임아웃: {e}")
        raise HTTPException(status_code=504, detail="API 타임아웃")
    except Exception as e:
        print(f"❌ API 호출 오류: {e}")
        raise HTTPException(status_code=500, detail=f"API 호출 실패: {str(e)}")

def analyze_with_gemini(ocr_text: str, detections: List[Dict]) -> Optional[str]:
    """Gemini 분석 수행"""
    if not ocr_text:
        return None
        
    print(f"\n🧠 Gemini 분석 시작...")
    try:
        # Gemini 모듈 import
        from modules.gemini import analyze_text_with_gemini, check_if_food_product
        
        # 환경 변수 확인
        gemini_key = os.environ.get("GEMINI_API_KEY")
        if not gemini_key:
            print("⚠️ GEMINI_API_KEY 환경 변수가 설정되지 않았습니다")
            return None
        
        # 먼저 식품인지 확인
        is_food = check_if_food_product(ocr_text)
        print(f"📋 식품 여부: {'식품' if is_food else '비식품'}")
        
        if is_food:
            # 식품이면 상세 분석
            gemini_result = analyze_text_with_gemini(ocr_text, detections)
            if gemini_result:
                print(f"✅ Gemini 분석 성공: {gemini_result}")
                return gemini_result
            else:
                print("⚠️ Gemini 분석 결과 없음")
        else:
            print("ℹ️ 식품이 아니므로 Gemini 분석 생략")
            # API 키가 없어서 실패한 경우, 브랜드 패턴으로 다시 시도
            if not os.environ.get("GEMINI_API_KEY"):
                print("🔄 브랜드 패턴 매칭으로 재시도...")
                try:
                    from modules.gemini import detect_brand_and_product
                    brand, product = detect_brand_and_product(ocr_text)
                    if brand and product:
                        gemini_result = f"{brand} {product}"
                        print(f"✅ 브랜드 패턴 매칭 성공: {gemini_result}")
                        return gemini_result
                    elif brand:
                        print(f"✅ 브랜드만 인식: {brand}")
                        return brand
                except Exception as pattern_error:
                    print(f"❌ 브랜드 패턴 매칭 실패: {pattern_error}")
                    
    except ImportError:
        print("❌ Gemini 모듈을 찾을 수 없습니다")
    except Exception as gemini_error:
        print(f"❌ Gemini 분석 중 오류: {gemini_error}")
        traceback.print_exc()
    
    return None

def try_brand_pattern_matching(ocr_text: str) -> Optional[str]:
    """브랜드 패턴 매칭 시도 (Gemini 분석 실패 시 폴백)"""
    if not ocr_text:
        return None
        
    try:
        from modules.gemini import detect_brand_and_product
        brand, product = detect_brand_and_product(ocr_text)
        
        if brand and product:
            result = f"{brand} {product}"
            print(f"🔍 브랜드 패턴으로 인식: {result}")
            return result
        elif brand:
            print(f"🔍 브랜드만 인식: {brand}")
            return brand
            
    except Exception:
        pass
    
    return None

def extract_ingredients_from_detections(detections: List[Dict]) -> List[str]:
    """탐지 결과에서 식재료만 추출"""
    ingredients = []
    
    # 제외할 브랜드/제품명 키워드
    exclude_keywords = ['CJ', '오뚜기', '농심', '하림', '풀무원', '제품', '브랜드']
    
    for det in detections:
        label = det.get('original_label', det.get('label', ''))
        
        # 개수 정보 제거
        if '(' in label:
            label = label.split('(')[0].strip()
        
        # 브랜드/제품명 제외
        is_ingredient = True
        for keyword in exclude_keywords:
            if keyword in label:
                is_ingredient = False
                break
        
        if is_ingredient and label:
            ingredients.append(label)
    
    # 중복 제거
    unique_ingredients = list(set(ingredients))
    print(f"🥬 추출된 식재료: {unique_ingredients}")
    
    return unique_ingredients

def initialize_recipe_searcher():
    """레시피 검색기 초기화"""
    global recipe_searcher
    try:
        from modules.recipe_search import RecipeSearcher
        recipe_searcher = RecipeSearcher()
        print("✅ 레시피 검색 시스템 초기화 완료")
        return True
    except Exception as e:
        print(f"❌ 레시피 검색 초기화 실패: {e}")
        return False

def cleanup_old_contexts():
    """오래된 컨텍스트 정리 (1시간 이상)"""
    current_time = datetime.now()
    expired_users = []
    
    for user_id, context in conversation_contexts.items():
        if 'last_updated' in context:
            if current_time - context['last_updated'] > timedelta(hours=1):
                expired_users.append(user_id)
    
    for user_id in expired_users:
        del conversation_contexts[user_id]

# Food Detection API 호출 - 분리된 버전
async def analyze_image(image_base64: str, include_recipe: bool = False) -> Dict:
    """이미지 분석 - 메인 오케스트레이션 함수"""
    print(f"🔍 이미지 분석 시작... (크기: {len(image_base64)} bytes)")
    
    try:
        # 1. Food Detection API 호출
        api_result = await call_food_detection_api(image_base64)
        
        # 2. OCR 결과 추출
        ocr_text = extract_ocr_text(api_result)
        
        # 3. detections 포맷팅 및 중복 집계
        detections = api_result.get('detections', [])
        formatted_detections = format_detections_with_duplicates(detections)
        
        # 4. Gemini 분석 수행 (OCR 텍스트가 있을 경우)
        gemini_result = analyze_with_gemini(ocr_text, detections)
        
        # 5. Gemini 분석 실패 시 브랜드 패턴 매칭 시도
        if not gemini_result and ocr_text:
            gemini_result = try_brand_pattern_matching(ocr_text)
        
        # 6. 결과 요약 출력
        print(f"\n📊 분석 결과 요약:")
        print(f"   - 원본 탐지 객체: {len(detections)}개")
        print(f"   - 중복 집계 후: {len(formatted_detections)}개")
        if ocr_text:
            print(f"   - OCR 텍스트: 감지됨 (내부 처리용)")
        if gemini_result:
            print(f"   - Gemini 분석: {gemini_result}")
            print(f"   - 최종 표시: 제품명 + 모든 탐지 결과")
        else:
            print(f"   - Gemini 분석: 없음")
            print(f"   - 최종 표시: 모든 탐지 결과")
        
        # 7. 최종 결과 구성
        result = {
            'detections': formatted_detections,
            'ocr_text': ocr_text,  # 원본 OCR 텍스트 (내부 처리용)
            'gemini_analysis': gemini_result  # Gemini 분석 결과
        }
        
        # 8. 레시피 추천 추가 (옵션)
        if include_recipe and recipe_searcher:
            ingredients = extract_ingredients_from_detections(formatted_detections)
            if ingredients:
                print(f"🥘 레시피 추천을 위한 식재료: {ingredients}")
                recipe_result = await recipe_searcher.get_recipe_recommendations(ingredients)
                result['recipe_recommendations'] = recipe_result
        
        return result
        
    except Exception as e:
        error_msg = f"예상치 못한 오류: {type(e).__name__} - {str(e)}"
        print(f"❌ {error_msg}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=error_msg)

# 이미지 URL에서 base64로 변환
async def download_image(image_url: str) -> str:
    """이미지 다운로드 및 base64 변환"""
    print(f"🌐 이미지 다운로드: {image_url}")
    async with httpx.AsyncClient() as client:
        response = await client.get(image_url)
        return base64.b64encode(response.content).decode()

def analyze_recipe_query(text: str) -> Dict[str, Any]:
    """레시피 관련 쿼리 분석 (개선된 버전)"""
    query_lower = text.lower()
    
    # 쿼리 타입 분류
    query_type = "general"
    specific_dish = None
    
    # 상세 레시피 요청 패턴
    detailed_patterns = [
        '만드는 방법', '만드는 법', '조리 방법', '조리법',
        '구체적으로', '자세히', '상세히', '단계별로',
        '어떻게 만들', '만들기', '레시피 알려', '요리법'
    ]
    
    # 일반 레시피 추천 패턴
    recommendation_patterns = [
        '레시피 추천', '요리 추천', '뭘 만들', '음식 추천',
        '이걸로 뭘', '만들 수 있', '요리 알려'
    ]
    
    # 재료 기반 검색 패턴
    ingredient_patterns = [
        '로 만들', '으로 만들', '가지고', '이용해', '활용'
    ]
    
    # 빠른/간단한 요리 패턴
    quick_patterns = ['빠르', '간단', '쉬운', '간편', '초간단', '10분', '15분']
    
    # 건강/다이어트 패턴
    healthy_patterns = ['건강', '다이어트', '헬시', '저칼로리', '샐러드', '저염']
    
    # 특정 요리명 추출
    specific_dish = extract_dish_name_from_text(text)
    
    # 상세 레시피 요청인지 확인
    if any(pattern in query_lower for pattern in detailed_patterns):
        query_type = "detailed"
    # 일반 추천 요청
    elif any(pattern in query_lower for pattern in recommendation_patterns):
        query_type = "recommendation"
    # 재료 기반 요청
    elif any(pattern in query_lower for pattern in ingredient_patterns):
        query_type = "ingredient_based"
    # 특정 요리명이 있으면 상세 레시피로 분류
    elif specific_dish:
        query_type = "detailed"
    
    # 특성 분석
    characteristics = []
    if any(pattern in query_lower for pattern in quick_patterns):
        characteristics.append("quick")
    if any(pattern in query_lower for pattern in healthy_patterns):
        characteristics.append("healthy")
    
    return {
        'type': query_type,
        'specific_dish': specific_dish,
        'characteristics': characteristics,
        'original_query': text
    }

def extract_dish_name_from_text(text: str) -> Optional[str]:
    """텍스트에서 요리명 추출"""
    # 일반적인 요리명 패턴
    dish_pattern = re.compile(r'([가-힣]+(?:찌개|볶음|구이|탕|전|무침|조림|찜|밥|면|죽|국|수프|샐러드|스테이크|파스타|피자|버거))')
    match = dish_pattern.search(text)
    if match:
        return match.group(1)
    
    # 자주 검색되는 요리명 목록
    common_dishes = [
        '김치찌개', '된장찌개', '순두부찌개', '부대찌개', '제육볶음', 
        '불고기', '비빔밥', '볶음밥', '김치볶음밥', '새우볶음밥',
        '파스타', '스파게티', '까르보나라', '알리오올리오', '리조또', 
        '샐러드', '시저샐러드', '닭볶음탕', '갈비찜', '잡채', 
        '떡볶이', '라면', '짜장면', '짬뽕', '탕수육', '깐풍기',
        '치킨', '피자', '햄버거', '스테이크', '오므라이스',
        '계란말이', '김밥', '초밥', '돈까스', '함박스테이크',
        '미역국', '콩나물국', '김치전', '파전', '감자전'
    ]
    
    text_lower = text.lower()
    for dish in common_dishes:
        if dish in text:
            return dish
    
    # 영어 요리명도 체크
    english_dishes = ['pasta', 'pizza', 'burger', 'steak', 'salad', 'soup']
    for dish in english_dishes:
        if dish in text_lower:
            return dish
    
    return None

@app.post("/")
async def root_webhook(message: ImageMessage):
    """루트 엔드포인트 - 요청 타입에 따라 분기"""
    # 이미지가 있으면 simple_webhook 사용

    if message.image_url or message.image_base64:
        return await simple_webhook(message)
    # 텍스트만 있으면 conversation_webhook 사용
    else:
        return await conversation_webhook(message)
    

@app.post("/webhook/simple")
async def simple_webhook(message: ImageMessage):
    """범용 웹훅 - 즉시 처리"""
    print(f"\n{'='*50}")
    print(f"📥 새 요청: user_id={message.user_id}, platform={message.platform}")
    
    try:
        # 이미지 준비
        if message.image_url:
            image_base64 = await download_image(message.image_url)
        else:
            image_base64 = message.image_base64
            print(f"📷 Base64 이미지 수신 (크기: {len(image_base64)} bytes)")
        
        # 분석 실행
        result = await analyze_image(image_base64)
        
        # ✅ 사용자 컨텍스트에 저장 (추가된 부분)
        user_context = conversation_contexts[message.user_id]
        user_context['last_analysis'] = result
        user_context['last_ingredients'] = extract_ingredients_from_detections(
            result.get("detections", [])
        )
        user_context['last_updated'] = datetime.now()
        
        print(f"💾 사용자 컨텍스트 저장: {message.user_id}")
        print(f"   - 식재료: {user_context['last_ingredients']}")
        
        # 기존 형식의 응답 (프론트엔드 호환성 유지)
        response = {
            "status": "success",
            "user_id": message.user_id,
            "detections": result.get("detections", []),
            "ocr_results": []  # OCR 결과를 빈 배열로 설정하여 표시하지 않음
        }
        
        # 표시 정책:
        # 1. Gemini/브랜드 인식 성공 → 제품명을 맨 위에 추가하고 모든 결과 표시
        # 2. 인식 실패 → 일반 객체 탐지 결과만 표시
        
        # Gemini 분석 결과가 있으면 추가
        if result.get("gemini_analysis"):
            response["food_name"] = result["gemini_analysis"]
            response["recognized_product"] = result["gemini_analysis"]
            
            # Gemini 분석 결과를 detections 맨 앞에 추가 (기존 결과 유지)
            gemini_detection = {
                "label": result["gemini_analysis"],  # 단순하게 제품명만
                "confidence": 1.0,  # 100% 신뢰도
                "bbox": [],
                "class": result["gemini_analysis"],  # class도 동일하게
                "korean_name": result["gemini_analysis"],
                "count": 1,  # 개수 정보 추가
                "original_label": result["gemini_analysis"]
            }
            # detections 맨 앞에 삽입 (기존 결과는 유지)
            response["detections"].insert(0, gemini_detection)
            print(f"🎯 Gemini 인식 결과를 맨 앞에 추가: {result['gemini_analysis']}")
            print(f"   (총 {len(response['detections'])}개 항목 표시)")
        
        # OCR 텍스트가 있지만 Gemini 분석이 없는 경우, 브랜드 패턴 매칭 시도
        elif result.get("ocr_text") and not result.get("gemini_analysis"):
            brand_result = try_brand_pattern_matching(result["ocr_text"])
            if brand_result:
                response["food_name"] = brand_result
                response["recognized_product"] = brand_result
                
                # 브랜드 패턴 매칭 결과를 detections 맨 앞에 추가
                brand_detection = {
                    "label": brand_result if not brand_result.endswith("제품") else brand_result,
                    "confidence": 0.9 if " " in brand_result else 0.8,  # 제품명 포함 시 높은 신뢰도
                    "bbox": [],
                    "class": brand_result,
                    "korean_name": brand_result,
                    "count": 1,
                    "original_label": brand_result
                }
                response["detections"].insert(0, brand_detection)
                print(f"🔍 브랜드 패턴으로 인식: {brand_result}")
                print(f"   (총 {len(response['detections'])}개 항목 표시)")
        
        print(f"✅ 응답 성공: {len(response['detections'])} 항목 표시")
        if "food_name" in response:
            print(f"🍽️ 인식된 제품: {response['food_name']}")
            print(f"   (제품명 + 일반 탐지 결과 모두 표시)")
        print(f"{'='*50}\n")
        
        return response
    
    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)}"
        print(f"❌ 예상치 못한 오류: {error_msg}")
        print(traceback.format_exc())
        print(f"{'='*50}\n")
        
        return {
            "status": "error",
            "message": error_msg,
            "detections": [],
            "ocr_results": []  # 오류 시에도 빈 배열 반환
        }

# 1. handle_simple_recipe_request 함수 수정
# 간단한 요리 추천 요청을 처리
async def handle_simple_recipe_request(user_id: int, text: str, user_context: Dict) -> Dict:
    """간단한 요리 추천해줘 버튼 처리"""
    print("🍳 간단한 요리 추천 요청")
    
    # 모든 사용자 컨텍스트 확인 (디버깅용)
    print(f"🔍 현재 user_id: {user_id}")
    print(f"📦 전체 컨텍스트 키: {list(conversation_contexts.keys())}")
    
    # 가장 최근 컨텍스트 찾기 (user_id 불일치 시)
    ingredients = user_context.get('last_ingredients', [])
    
    if not ingredients:
        # 가장 최근에 이미지를 업로드한 사용자의 재료 찾기
        latest_time = None
        latest_ingredients = []
        
        for uid, ctx in conversation_contexts.items():
            if 'last_updated' in ctx and ctx.get('last_ingredients'):
                if latest_time is None or ctx['last_updated'] > latest_time:
                    latest_time = ctx['last_updated']
                    latest_ingredients = ctx['last_ingredients']
        
        if latest_ingredients:
            ingredients = latest_ingredients
            # 현재 사용자 컨텍스트에도 저장
            user_context['last_ingredients'] = ingredients
            print(f"✅ 최근 업로드된 재료 사용: {ingredients}")
    
    if not ingredients:
        return {
            "status": "success",
            "user_id": user_id,
            "detections": [{
                "label": "먼저 음식 사진을 보내주시면 간단한 요리를 추천해드릴게요! 📸",
                "confidence": 1.0,
                "class": "info"
            }],
            "ocr_results": []
        }
    
    # 간단한 요리만 필터링
    if recipe_searcher:
        try:
            print(f"🔍 간단한 요리 검색 중: {ingredients}")
            
            # 구글 검색으로 간단한 요리 찾기
            search_query = f"간단한 {' '.join(ingredients)} 요리 레시피 10분 15분"
            search_results = await recipe_searcher.search_recipes(search_query, num_results=5)
            
            response_items = []
            response_items.append({
                "label": f"🍳 {', '.join(ingredients)}로 만들 수 있는 간단한 요리:",
                "confidence": 1.0,
                "class": "header"
            })
            
            # 검색 결과에서 간단한 요리 추출
            simple_recipes = []
            for i, result in enumerate(search_results[:3], 1):
                title = result['title']
                clean_title = re.sub(r'\[.*?\]', '', title).strip()
                
                # 간단한 요리 키워드 확인
                if any(keyword in result['snippet'] for keyword in ['간단', '쉬운', '10분', '15분', '초간단']):
                    simple_recipes.append(clean_title)
                    
                    response_items.append({
                        "label": f"\n{i}. 🍽️ {clean_title}\n   - {result['snippet'][:80]}...\n   - 출처: {result['source']}",
                        "confidence": 0.9,
                        "class": "recipe_option"
                    })
            
            # 사용자 컨텍스트에 저장
            user_context['recommended_recipes'] = simple_recipes
            user_context['last_updated'] = datetime.now()
            
            return {
                "status": "success",
                "user_id": user_id,
                "detections": response_items,
                "ocr_results": [],
                "suggestions": [
                    f"{simple_recipes[0]} 만드는 방법" if simple_recipes else "만드는 방법",
                    "다른 레시피 추천해줘"
                ]
            }
            
        except Exception as e:
            print(f"❌ 간단한 요리 검색 오류: {e}")
            # 오류 시 기본 응답
            response_text = f"🍳 {', '.join(ingredients)}로 만들 수 있는 간단한 요리:\n\n"
            response_text += "감자 버터구이 - 15분\n"
            response_text += "감자전 - 20분\n"
            response_text += "오렌지 샐러드 - 5분"
            
            return {
                "status": "success",
                "user_id": user_id,
                "detections": [{
                    "label": response_text,
                    "confidence": 1.0,
                    "class": "recipe"
                }],
                "ocr_results": []
            }
    
    return {
        "status": "error",
        "message": "레시피 검색 기능이 비활성화되어 있습니다."
    }
# 이걸로 뭘 만들 수 있어? 버튼 처리
async def handle_what_can_i_make(user_id: int, text: str, user_context: Dict) -> Dict:
    """이걸로 뭘 만들 수 있어? 버튼 처리"""
    print("🤔 뭘 만들 수 있는지 요청")
    
    ingredients = user_context.get('last_ingredients', [])
    
    if not ingredients:
        return {
            "status": "success",
            "user_id": user_id,
            "detections": [{
                "label": "음식 사진을 먼저 보내주세요! 재료를 인식해서 만들 수 있는 요리를 알려드릴게요 😊",
                "confidence": 1.0,
                "class": "info"
            }],
            "ocr_results": []
        }
    
    if recipe_searcher:
        recipe_result = await recipe_searcher.get_recipe_recommendations(ingredients)
        
        # 여러 옵션 제시
        suggestions = recipe_result.get("quick_suggestions", [])
        
        response_items = []
        response_items.append({
            "label": f"🥘 {', '.join(ingredients)}로 만들 수 있는 요리들:",
            "confidence": 1.0,
            "class": "header"
        })
        
        # 메인 추천
        if recipe_result.get("main_recipe"):
            response_items.append({
                "label": recipe_result["main_recipe"],
                "confidence": 1.0,
                "class": "recipe"
            })
        
        # 빠른 아이디어들
        if suggestions:
            response_items.append({
                "label": "\n💡 다른 아이디어:",
                "confidence": 0.9,
                "class": "subheader"
            })
            for suggestion in suggestions[:3]:
                response_items.append({
                    "label": f"• {suggestion}",
                    "confidence": 0.9,
                    "class": "suggestion"
                })
        
        return {
            "status": "success",
            "user_id": user_id,
            "detections": response_items,
            "suggestions": [
                "추천 음식 먹을게요",
                "다른 레시피 추천해줘"
            ],
            "ocr_results": []
        }
    
    return {
        "status": "error",
        "message": "레시피 검색 기능이 비활성화되어 있습니다."
    }
# 레시피 추천해줘 버튼 처리 
async def handle_recipe_recommendation(user_id: int, text: str, user_context: Dict) -> Dict:
    """레시피 추천해줘 버튼 처리 - 구글 검색 3가지 결과"""
    print("📖 레시피 추천 요청 (3가지 요리)")
    
    ingredients = user_context.get('last_ingredients', [])
    print(f"🥬 저장된 재료: {ingredients}")
    
    if not ingredients:
        response = {
            "status": "success", 
            "user_id": user_id,
            "detections": [{
                "label": "레시피를 추천하려면 먼저 재료가 필요해요! 음식 사진을 보내주세요 📸",
                "confidence": 1.0,
                "class": "info"
            }],
            "ocr_results": []
        }
        print(f"📤 재료 없음 응답 반환: {response}")
        return response
    
    if not recipe_searcher:
        print("❌ recipe_searcher가 초기화되지 않았습니다")
        return {
            "status": "error",
            "user_id": user_id,
            "detections": [{
                "label": "레시피 검색 기능이 비활성화되어 있습니다. 잠시 후 다시 시도해주세요.",
                "confidence": 1.0,
                "class": "error"
            }],
            "ocr_results": []
        }
    
    try:
        print(f"🔍 레시피 검색 시작: {ingredients}")
        
        # 구글 검색으로 레시피 찾기
        search_query = f"{' '.join(ingredients)} 요리 레시피"
        search_results = await recipe_searcher.search_recipes(search_query, num_results=5)
        
        response_items = []
        response_items.append({
            "label": f"🍳 {', '.join(ingredients)}로 만들 수 있는 요리 3가지를 찾았어요!",
            "confidence": 1.0,
            "class": "header"
        })
        
        # 검색 결과에서 상위 3개 추출
        recipes_found = []
        for i, result in enumerate(search_results[:3], 1):
            # 제목 정리
            title = result['title']
            clean_title = re.sub(r'\[.*?\]', '', title).strip()
            
            # 요리명 저장
            dish_name = clean_title.split('-')[0].strip()
            recipes_found.append(dish_name)
            
            # 조리시간 찾기
            cooking_time = "30분"
            if "분" in result['snippet']:
                time_match = re.search(r'(\d+)분', result['snippet'])
                if time_match:
                    cooking_time = f"{time_match.group(1)}분"
            
            response_items.append({
                "label": f"\n{i}. 🍽️ {clean_title}\n   - {result['snippet'][:100]}...\n   - 조리시간: {cooking_time}\n   - 출처: {result['source']}",
                "confidence": 0.9,
                "class": "recipe_option"
            })
        
        # 대체 레시피 추가 (검색 결과가 적을 경우)
        if len(search_results) < 3:
            # 기본 레시피 추천
            if "김치" in ingredients:
                response_items.append({
                    "label": f"\n{len(search_results)+1}. 🍽️김치찌개\n   - 김치와 돼지고기로 만드는 한국 대표 찌개\n   - 조리시간: 20분",
                    "confidence": 0.9,
                    "class": "recipe_option"
                })
                recipes_found.append("김치찌개")
        
        # 사용자 컨텍스트에 저장
        user_context['recommended_recipes'] = recipes_found
        user_context['last_search_results'] = search_results[:3]
        
        # 선택 유도 메시지
        response_items.append({
            "label": "\n💡 어떤 요리가 마음에 드시나요?",
            "confidence": 1.0,
            "class": "tip"
        })
        
        response = {
            "status": "success",
            "user_id": user_id,
            "detections": response_items,
            "ocr_results": [],
            "suggestions": [
                f"{recipes_found[0]} 만드는 방법" if recipes_found else "1번 음식",
                f"{recipes_found[1]} 만드는 방법" if recipes_found else "2번 음식",
                f"{recipes_found[2]} 만드는 방법" if recipes_found else "3번 음식"
            ]
        }
        
        print(f"📤 레시피 추천 성공 응답 반환:")
        print(f"   - 검색 결과: {len(search_results)}개")
        print(f"   - 추천 요리: {recipes_found}")
        
        return response
        
    except Exception as e:
        print(f"❌ 레시피 추천 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        
        return {
            "status": "error",
            "user_id": user_id,
            "detections": [{
                "label": "레시피 추천 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.",
                "confidence": 1.0,
                "class": "error"
            }],
            "ocr_results": []
        }
# 특정 요리 레시피 요청 처리 (만드는 방법 순서대로 출력)
async def handle_specific_recipe(user_id: int, text: str, user_context: Dict) -> Dict:
    """특정 요리 레시피 요청 처리 - 만드는 방법을 순서대로 출력"""
    print(f"🍽️ 특정 요리 요청: {text}")
    
    # 요리명 추출 - 다양한 패턴 처리
    dish_name = None
    
    # "1번 만드는 방법" 패턴 처리
    if "번" in text and ("만드는" in text or "레시피" in text):
        match = re.search(r'(\d)번', text)
        if match:
            idx = int(match.group(1)) - 1
            recipes = user_context.get('recommended_recipes', [])
            if 0 <= idx < len(recipes):
                dish_name = recipes[idx]
                print(f"📌 번호로 선택: {idx+1}번 = {dish_name}")
    
    # 직접 요리명 언급
    if not dish_name:
        dish_name = extract_dish_name_from_text(text)
        if not dish_name:
            dish_name = text.replace(" 만드는 방법", "").replace(" 레시피", "").replace(" 만들기", "").strip()
    
    # 컨텍스트에서 마지막 추천 요리
    if not dish_name and user_context.get('last_recommended_dish'):
        dish_name = user_context['last_recommended_dish']
    
    if not dish_name:
        return {
            "status": "success",
            "user_id": user_id,
            "detections": [{
                "label": "어떤 요리의 만드는 방법을 알려드릴까요? 요리명을 말씀해주세요!",
                "confidence": 1.0,
                "class": "info"
            }],
            "ocr_results": []
        }
    
    if recipe_searcher:
        try:
            print(f"🍳 {dish_name} 만드는 방법 검색 중...")
            
            # 구글에서 상세 레시피 검색
            detailed_query = f"{dish_name} 레시피 만드는 방법 조리법 재료 순서"
            search_results = await recipe_searcher.search_recipes(detailed_query, num_results=3)
            
            # 상세 레시피 가져오기
            detailed_result = await recipe_searcher.get_cooking_method(
                dish_name,
                {'last_ingredients': user_context.get('last_ingredients', [])}
            )
            
            # 상세 레시피 텍스트를 순서대로 정리
            recipe_text = detailed_result.get("detailed_recipe", "")
            
            # 순서를 명확하게 표시
            lines = recipe_text.split('\n')
            formatted_lines = []
            step_number = 1
            
            for line in lines:
                line = line.strip()
                if line:
                    # 재료 섹션인지 확인
                    if '재료' in line and step_number == 1:
                        formatted_lines.append(f"📋 재료")
                        formatted_lines.append(line.replace('재료:', '').strip())
                    # 조리 단계인지 확인
                    elif any(keyword in line for keyword in ['1.', '2.', '3.', '①', '②', '③', '첫째', '둘째', '셋째']):
                        formatted_lines.append(f"\n{step_number}단계: {line}")
                        step_number += 1
                    elif len(line) > 10 and not line.startswith('-'):
                        # 일반 조리 단계로 추정
                        formatted_lines.append(f"\n{step_number}단계: {line}")
                        step_number += 1
                    else:
                        formatted_lines.append(line)
            
            # 최종 텍스트 구성
            final_text = f"<b>🍳 {dish_name} 만드는 방법 (순서대로)</b><br><br>"
            final_text += '<br>'.join(formatted_lines)
            
            # 팁 추가
            if detailed_result.get("tips"):
                final_text += "<br><br><b>💡 요리 팁:</b><br>"
                final_text += detailed_result.get("tips", "")
            
            # 참고 링크 추가
            if search_results:
                final_text += "<br><br><b>📚 더 자세한 레시피:</b><br>"
                for i, result in enumerate(search_results[:2], 1):
                    final_text += f"{i}. {result['title']}<br>"
            
            # 관련 요리 추가
            if detailed_result.get("related_dishes"):
                final_text += f"<br><b>🍽️ 이런 요리도 어때요?</b> {', '.join(detailed_result['related_dishes'][:3])}"
            
            # 마지막 추천 요리 저장
            user_context['last_recommended_dish'] = dish_name
            
            return {
                "status": "success",
                "user_id": user_id,
                "detections": [{
                    "label": final_text,
                    "confidence": 1.0,
                    "class": "detailed_recipe"
                }],
                "ocr_results": [],
                "suggestions": [
                    "추천 음식 먹을게요",
                    "다른 레시피 추천해줘",
                ]
            }
            
        except Exception as e:
            print(f"❌ 상세 레시피 조회 오류: {e}")
            return {
                "status": "error",
                "message": f"레시피 조회 중 오류가 발생했습니다: {str(e)}"
            }
    
    return {
        "status": "error",
        "message": "레시피 검색 기능이 비활성화되어 있습니다."
    }

# 답변을 준비 중입니다 처리
async def handle_general_text(user_id: int, text: str, user_context: Dict) -> Dict:
    """일반 텍스트 처리"""
    query_analysis = analyze_recipe_query(text)
    print(f"📊 일반 텍스트 분석: {query_analysis}")
    
    # 기존 로직 사용...
    # (기존 conversation_webhook의 텍스트 처리 로직)
    
    suggestions = [
        "요리 추천해줘",
        "추천 음식 먹을게요",
        "처음으로 돌아가기"
    ]

    return {
        "status": "success",
        "user_id": user_id,
        "detections": [{
            "label": "잘못된 요청입니다. 다시 시도해주세요.",
            "confidence": 1.0,
            "class": "processing"
        }],
        "ocr_results": [],
        "suggestions": suggestions  # ← 이 부분 추가!
    }
    
# 추천 음식 먹을게요 버튼 클릭 처리
def handle_pass_text(user_id: int, text: str, user_context: Dict) -> Dict:
    """추천 음식 먹을게요 버튼 클릭 처리"""
    
    return {
        "status": "success",
        "user_id": user_id,
        "detections": [{
            "label": "이미지가 반영됩니다. 잠시 후 메인 페이지로 이동합니다.",
            "confidence": 1.0,
            "class": "processing"
        }],
        "ocr_results": []
    }


# 이미지 업로드 처리 (식재료 탐지 및 출력)
async def handle_image_upload(message: ImageMessage, user_context: Dict) -> Dict:
    """이미지 업로드 처리 - 식재료 탐지 및 출력"""
    # 기존 이미지 처리 로직...
    if message.image_url:
        image_base64 = await download_image(message.image_url)
    else:
        image_base64 = message.image_base64
    
    result = await analyze_image(image_base64)
    
    # 컨텍스트에 저장
    user_context['last_analysis'] = result
    user_context['last_ingredients'] = extract_ingredients_from_detections(
        result.get("detections", [])
    )
    user_context['last_updated'] = datetime.now()
    
    response = {
        "status": "success",
        "user_id": message.user_id,
        "detections": result.get("detections", []),
        "ocr_results": []
    }
    
    if result.get("gemini_analysis"):
        response["food_name"] = result["gemini_analysis"]
        response["recognized_product"] = result["gemini_analysis"]
    
    # 재료 인식 성공 시 안내 메시지 추가
    if user_context.get('last_ingredients'):
        ingredients = user_context['last_ingredients']
        response["detections"].append({
            "label": f"\n✨ 인식된 재료: {', '.join(ingredients)}\n💡 '요리 추천해줘'라고 말씀해주세요!",
            "confidence": 1.0,
            "class": "tip"
        })
        response["suggestions"] = [
            "요리 추천해줘",
            "이걸로 뭘 만들 수 있어?"
        ]
    
    return response

# 2. conversation_webhook 수정 - user_id 문제 해결
@app.post("/webhook/conversation")
async def conversation_webhook(message):
    """대화형 웹훅 - 버튼 클릭 처리 개선"""
    print(f"\n{'='*50}")
    print(f"💬 대화형 요청: user_id={message.user_id}")
    print(f"📝 텍스트: {message.text}")
    print(f"🔍 전체 메시지: {message}")
    
    # 오래된 컨텍스트 정리
    cleanup_old_contexts()
    
    # 사용자 컨텍스트 가져오기 또는 생성
    user_context = conversation_contexts[message.user_id]
    user_context['last_updated'] = datetime.now()
    
    # user_id 불일치 문제 해결을 위한 로직
    if not user_context.get('last_ingredients') and message.text and not (message.image_url or message.image_base64):
        # 가장 최근 컨텍스트에서 재료 가져오기
        latest_context = None
        latest_time = None
        
        for uid, ctx in conversation_contexts.items():
            if 'last_updated' in ctx and ctx.get('last_ingredients'):
                if latest_time is None or ctx['last_updated'] > latest_time:
                    latest_time = ctx['last_updated']
                    latest_context = ctx
        
        if latest_context:
            # 최근 컨텍스트의 데이터를 현재 사용자에게 복사
            user_context['last_ingredients'] = latest_context.get('last_ingredients', [])
            user_context['last_analysis'] = latest_context.get('last_analysis', {})
            print(f"✅ 최근 컨텍스트 데이터 복사: {user_context['last_ingredients']}")
    
    try:
        response = None  # 응답 초기화
        
        # 텍스트 메시지 처리 (버튼 클릭 포함)
        if message.text and not (message.image_url or message.image_base64):
            text = message.text.strip()
            print(f"🔤 텍스트 요청 처리: '{text}'")

            
            # 버튼 텍스트와 정확히 매칭
            button_responses = {
                "간단한 요리 추천해줘": handle_simple_recipe_request,
                "이걸로 뭘 만들 수 있어?": handle_what_can_i_make,
                "요리 추천해줘": handle_recipe_recommendation,
                "레시피 추천해줘": handle_recipe_recommendation,
                "다른 레시피 추천해줘" : handle_recipe_recommendation,
            }
            
            # 정확한 매칭 확인
            if text in button_responses:
                print(f"✅ 버튼 매칭: '{text}'")
                handler = button_responses[text]
                response = await handler(message.user_id, text, user_context)
            # 번호 선택 패턴 처리
            elif text == "처음으로 돌아가기":
                print(f"✅ 처음으로 돌아가기 요청: '{text}'")
                response = await handle_recipe_recommendation(message.user_id, text, user_context)
            elif re.match(r'\d번.*만드는.*방법', text):
                print(f"✅ 번호 선택 패턴: '{text}'")
                response = await handle_specific_recipe(message.user_id, text, user_context)
            # "요리방법 알려줘" 패턴
            elif "요리방법" in text or "만드는 방법" in text or "만드는 법" in text:
                print(f"✅ 요리방법 요청: '{text}'")
                response = await handle_specific_recipe(message.user_id, text, user_context)
            elif text == "추천 음식 먹을게요":
                print(f"✅ 추천 음식 먹을게요 요청: '{text}'")
    
                # 즉시 응답 반환
                response = handle_pass_text(message.user_id, text, user_context)
    
                # 백그라운드에서 비동기 작업 실행
                async def background_task():
                    try:
                        print(f"🔄 백그라운드 작업 시작: handle_suggestion_click")
                        await handle_suggestion_click(text, user_context, message)
                        print(f"✅ 백그라운드 작업 완료: handle_suggestion_click")
                    except Exception as e:
                        print(f"❌ 백그라운드 작업 실패: {e}")
    
                # 백그라운드 태스크 생성 (응답 대기 없음)
                asyncio.create_task(background_task())
    
                # 즉시 응답 반환

                return response
            else :
                print(f"🔤 일반 텍스트 처리: '{text}'")
                response = await handle_general_text(message.user_id, text, user_context)

        # 이미지가 있는 경우
        elif message.image_url or message.image_base64:
            response = await handle_image_upload(message, user_context)
        
        # 빈 요청
        else:
            response = {
                "status": "success",
                "user_id": message.user_id,
                "detections": [{
                    "label": "무엇을 도와드릴까요? 😊",
                    "confidence": 1.0,
                    "class": "help"
                }],
                "ocr_results": []
            }
        
        # 응답 로깅 (중요!)
        print(f"\n📤 응답 전송:")
        print(f"   Status: {response.get('status', 'unknown')}")
        print(f"   Detections 개수: {len(response.get('detections', []))}")
        if response.get('detections'):
            print(f"   첫 번째 detection: {response['detections'][0]}")
        print(f"   전체 응답: {json.dumps(response, ensure_ascii=False, indent=2)}")
        print(f"{'='*50}\n")
        
        return response
            
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        print(traceback.format_exc())
        error_response = {
            "status": "error",
            "message": str(e),
            "detections": [],
            "ocr_results": []
        }
        print(f"📤 오류 응답: {error_response}")
        return error_response

async def test_connection():
    """Food Detection API 연결 테스트"""
    print("🔧 연결 테스트 시작...")
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{FOOD_DETECTION_API}/")
            api_status = response.status_code == 200
            print(f"✅ Food Detection API 상태: {'연결됨' if api_status else '연결 실패'}")
            
            # 모델 정보도 확인
            models_response = await client.get(f"{FOOD_DETECTION_API}/api/models/info")
            models_info = models_response.json() if models_response.status_code == 200 else {}
            
            # Gemini 모듈 확인
            gemini_available = False
            try:
                from modules.gemini import test_gemini_setup
                gemini_available = test_gemini_setup()
            except:
                pass
            
            # 레시피 검색 확인
            recipe_available = recipe_searcher is not None
            google_search_status = "비활성화"
            if recipe_searcher:
                try:
                    success, message = recipe_searcher.test_google_search()
                    google_search_status = "정상" if success else "오류"
                except:
                    pass
            
            return {
                "chatbot_status": "ok",
                "food_detection_api": api_status,
                "api_response": response.status_code,
                "models_loaded": models_info.get("loaded_count", 0),
                "ensemble_ready": models_info.get("ensemble_ready", False),
                "gemini_available": gemini_available,
                "recipe_search": recipe_available,
                "google_search": google_search_status,
                "conversation_contexts": len(conversation_contexts)
            }
    except Exception as e:
        print(f"❌ 연결 테스트 실패: {type(e).__name__}")
        return {
            "chatbot_status": "ok",
            "food_detection_api": False,
            "error": str(e)
        }

async def get_current_user_id(massage) -> int:

    user_id = massage.user_id
    print(f"[DEBUG] X-User-ID 헤더 값: {user_id}")
    
    if not user_id:
        raise HTTPException(status_code=401, detail="사용자 ID가 필요합니다")
    
    # 문자열을 정수로 변환
    try:
        return int(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="잘못된 사용자 ID 형식입니다")

# 비동기 방식 
async def request_food_generation_async(dish_name: str, user_id) -> Dict:
    print(f"[DEBUG] request_food_generation_async - user_id: {user_id}")
    print(f"[DEBUG] 요청할 dish_name: {dish_name}")
    
    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            # JSON body에 food와 user_id 둘 다 포함
            request_data = {
                "food": dish_name,
                "user_id": user_id  # 이것도 포함
            }
            
            # 헤더에도 user-id 포함
            headers = {
                "user-id": str(user_id),
                "Content-Type": "application/json"
            }
            
            print(f"[DEBUG] 보낼 데이터: {request_data}")
            print(f"[DEBUG] 보낼 헤더: {headers}")
            
            response = await client.post(
                "http://192.168.0.21:8000/generate-food",
                json=request_data,
                headers=headers
            )
                    
        print(f"[DEBUG] 응답 상태 코드: {response.status_code}")
        print(f"[DEBUG] 응답 헤더: {response.headers}")
        print(f"[DEBUG] 응답 내용: {response.text}")

        if response.status_code == 200:
            return response.json()
        elif response.status_code == 422:
            print("❌ 요청 데이터 형식 오류 (422)")
            return {"error": "요청 데이터 형식이 잘못되었습니다", "detail": response.text}
        elif response.status_code == 404:
            print("❌ API 엔드포인트를 찾을 수 없음 (404)")
            return {"error": "API 엔드포인트를 찾을 수 없습니다"}
        elif response.status_code == 500:
            print("❌ 서버 내부 오류 (500)")
            return {"error": "서버 내부 오류가 발생했습니다", "detail": response.text}
        else:
            print(f"❌ 예상치 못한 상태 코드: {response.status_code}")
            return {"error": f"HTTP {response.status_code} 오류", "detail": response.text}
            
    except httpx.ConnectError as e:
        print(f"❌ 연결 오류: {e}")
        return {"error": "서버에 연결할 수 없습니다", "detail": str(e)}
    except httpx.TimeoutException as e:
        print(f"❌ 타임아웃 오류: {e}")
        return {"error": "요청 시간이 초과되었습니다", "detail": str(e)}
    except httpx.RequestError as e:
        print(f"❌ 요청 오류: {e}")
        return {"error": "요청 처리 중 오류가 발생했습니다", "detail": str(e)}
    except Exception as e:
        print(f"❌ 예상치 못한 오류: {e}")
        return {"error": "예상치 못한 오류가 발생했습니다", "detail": str(e)}


async def handle_suggestion_click(suggestion: str, user_context: Dict, message) -> Dict:
    try:
        user_id = message.user_id
    except Exception as e:
        print(f"❌ user_id 가져오기 실패: {e}")
        user_id = 0  # 기본값

    if suggestion == "추천 음식 먹을게요":
        dish_name = user_context.get('last_recommended_dish')
        print(f"[DEBUG] dish_name: {dish_name}")
        print(f"[DEBUG] request_food_generation_async - user_id: {user_id}")  # user_id 확인용 디버그 코드
        try:
            await request_food_generation_async(dish_name, user_id)
            return {
                "status": "success",
                "user_id": user_id,
                "detections": [{
                    "label": f"✅ {dish_name} 주문이 접수되었습니다! 🍽️",
                    "confidence": 1.0,
                    "class": "success"
                }],
                "ocr_results": []
            }
        except Exception as e:
            print(f"❌ 음식 생성 요청 실패: {e}")
            import traceback
            traceback.print_exc()
            try:
                user_id = message.user_id
            except:
                user_id = 0
            return {
                "status": "error",
                "user_id": user_id,
                "detections": [{
                    "label": f"❌ 주문 처리 중 오류가 발생했습니다: {str(e)}",
                    "confidence": 1.0,
                    "class": "error"
                }],
                "ocr_results": []
            }
    else:
            try:
                user_id = message.user_id
            except:
                user_id = 0  # 기본값
                
            return {
                "status": "error",
                "user_id": user_id,
                "detections": [{
                    "label": "❌ 추천된 음식이 없습니다. 먼저 재료를 분석해주세요! 📸",
                    "confidence": 1.0,
                    "class": "error"
                }],
                "ocr_results": []
        }
if __name__ == "__main__":
    import uvicorn
    # 시작 시 연결 테스트
    import requests
    try:
        test_response = requests.get(f"{FOOD_DETECTION_API}/", timeout=2)
        if test_response.status_code == 200:
            print("✅ Food Detection API 연결 확인됨!")
        else:
            print("⚠️  Food Detection API 응답 이상")
    except:
        print("❌ Food Detection API에 연결할 수 없습니다!")
        print("   main.py가 실행 중인지 확인하세요.")
    
    # Gemini 설정 확인
    try:
        from modules.gemini import test_gemini_setup
        if test_gemini_setup():
            print("✅ Gemini API 설정 확인됨!")
        else:
            print("⚠️  Gemini API 설정 필요")
    except:
        print("❌ Gemini 모듈을 찾을 수 없습니다!")
    
    # 레시피 검색 초기화
    if initialize_recipe_searcher():
        print("✅ 레시피 검색 시스템 초기화!")
        
        # Google Search API 테스트
        try:
            from modules.recipe_search import RecipeSearcher
            searcher = RecipeSearcher()
            success, message = searcher.test_google_search()
            print(f"🔍 Google Search API: {message}")
        except:
            print("⚠️  Google Search API 테스트 실패")
    else:
        print("⚠️  레시피 검색 기능 비활성화")
    
    print("=" * 50 + "\n")
    
    uvicorn.run(app, host="192.168.0.18", port=8004)