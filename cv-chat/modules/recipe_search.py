# modules/recipe_search.py
# -*- coding: utf-8 -*-

import os
import json
import httpx
import requests
from typing import List, Dict, Optional
import asyncio
from urllib.parse import quote
import re

class RecipeSearcher:
    def __init__(self):
        """레시피 검색기 초기화"""
        # Google Search API 설정
        self.google_api_key = os.environ.get("GOOGLE_API_KEY")
        self.google_cx = os.environ.get("GOOGLE_SEARCH_CX")
        
        # Gemini API 설정 (REST API 사용)
        self.gemini_api_key = os.environ.get("GEMINI_API_KEY")
        self.gemini_api_url = "https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent"
        
        if self.gemini_api_key:
            print("✅ Gemini 1.5 Flash API 설정 완료")
        else:
            print("⚠️ GEMINI_API_KEY가 설정되지 않았습니다")
        
        # 레시피 사이트 우선순위
        self.preferred_sites = [
            "10000recipe.com",
            "haemukja.com", 
            "wtable.co.kr",
            "cookpad.com",
            "maangchi.com"
        ]
    
    def test_google_search(self) -> tuple[bool, str]:
        """Google Search API 테스트"""
        if not self.google_api_key or not self.google_cx:
            return False, "Google Search API 키가 설정되지 않았습니다"
        
        try:
            test_url = f"https://www.googleapis.com/customsearch/v1?key={self.google_api_key}&cx={self.google_cx}&q=test"
            response = requests.get(test_url, timeout=5)
            
            if response.status_code == 200:
                return True, "Google Search API 정상 작동"
            else:
                return False, f"API 응답 오류: {response.status_code}"
        except Exception as e:
            return False, f"연결 오류: {str(e)}"
    
    async def search_recipes(self, query: str, num_results: int = 5) -> List[Dict]:
        """Google 검색으로 레시피 찾기"""
        if not self.google_api_key or not self.google_cx:
            print("⚠️ Google Search API가 설정되지 않았습니다")
            return []
        
        search_url = "https://www.googleapis.com/customsearch/v1"
        params = {
            'key': self.google_api_key,
            'cx': self.google_cx,
            'q': query,
            'num': num_results,
            'hl': 'ko'
        }
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(search_url, params=params)
                
                if response.status_code == 200:
                    data = response.json()
                    results = []
                    
                    for item in data.get('items', []):
                        results.append({
                            'title': item.get('title', ''),
                            'link': item.get('link', ''),
                            'snippet': item.get('snippet', ''),
                            'source': self._extract_domain(item.get('link', ''))
                        })
                    
                    return results
                else:
                    print(f"❌ 검색 API 오류: {response.status_code}")
                    return []
                    
        except Exception as e:
            print(f"❌ 검색 중 오류: {e}")
            return []
    
    def _extract_domain(self, url: str) -> str:
        """URL에서 도메인 추출"""
        try:
            from urllib.parse import urlparse
            domain = urlparse(url).netloc
            return domain.replace('www.', '')
        except:
            return ""
    
    async def get_recipe_recommendations(self, ingredients: List[str], preferences: List[str] = None) -> Dict:
        """재료 기반 레시피 추천"""
        if not ingredients:
            return {
                "ingredients": [],
                "main_recipe": "재료를 먼저 인식시켜주세요.",
                "quick_suggestions": [],
                "search_urls": []
            }
        
        # 검색 쿼리 생성
        base_query = f"{' '.join(ingredients)} 레시피"
        if preferences:
            base_query = f"{' '.join(preferences)} {base_query}"
        
        print(f"🔍 레시피 검색 중: {base_query}")
        
        # Google 검색 실행
        search_results = await self.search_recipes(base_query)
        
        # Gemini로 레시피 생성 (가능한 경우)
        main_recipe = await self._generate_recipe_with_gemini(ingredients, search_results, preferences)
        
        # 빠른 아이디어 생성
        quick_suggestions = self._generate_quick_suggestions(ingredients, search_results)
        
        # 검색 URL 목록
        search_urls = [result['link'] for result in search_results[:3]]
        
        return {
            "ingredients": ingredients,
            "main_recipe": main_recipe,
            "quick_suggestions": quick_suggestions,
            "search_urls": search_urls,
            "search_count": len(search_results)
        }
    
    async def _generate_recipe_with_gemini(self, ingredients: List[str], search_results: List[Dict], preferences: List[str] = None) -> str:
        """Gemini를 사용한 레시피 생성 (REST API)"""
        if not self.gemini_api_key:
            # Gemini 없이 기본 레시피 생성
            return self._generate_basic_recipe(ingredients, search_results)
        
        try:
            # 검색 결과에서 정보 추출
            recipe_info = "\n".join([f"- {r['title']}: {r['snippet']}" for r in search_results[:3]])
            
            preference_text = ""
            if preferences:
                preference_text = f"특히 {', '.join(preferences)} 요리를 원합니다."
            
            prompt = f"""
다음 재료로 만들 수 있는 한국 요리 레시피를 추천해주세요.
특수문자는 최대한 빼주세요.

재료: {', '.join(ingredients)}
{preference_text}

참고할 레시피 정보:
{recipe_info}

요구사항:
1. 추천 요리 1가지를 명확히 제시
2. 간단한 조리 방법 요약 (3-5단계)
3. 조리 시간과 난이도 표시
4. 팁이나 대체 재료 제안

형식:
추천 요리: [요리명]
조리 시간: [시간] | 난이도: [상/중/하]

[조리 방법]
1. ...
2. ...

💡 팁: ...
"""
            
            # API 요청 데이터
            request_data = {
                "contents": [{
                    "parts": [{
                        "text": prompt
                    }]
                }],
                "generationConfig": {
                    "temperature": 0.7,
                    "maxOutputTokens": 1024,
                    "topP": 0.95,
                    "topK": 40
                }
            }
            
            headers = {
                "Content-Type": "application/json",
                "x-goog-api-key": self.gemini_api_key
            }
            
            json_data = json.dumps(request_data, ensure_ascii=False).encode('utf-8')
            
            response = requests.post(
                self.gemini_api_url,
                headers=headers,
                data=json_data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                if 'candidates' in result and len(result['candidates']) > 0:
                    if 'content' in result['candidates'][0]:
                        content = result['candidates'][0]['content']
                        if 'parts' in content and len(content['parts']) > 0:
                            return content['parts'][0]['text'].strip()
            
            print(f"❌ Gemini API 오류: {response.status_code}")
            return self._generate_basic_recipe(ingredients, search_results)
            
        except Exception as e:
            print(f"❌ Gemini 레시피 생성 오류: {e}")
            return self._generate_basic_recipe(ingredients, search_results)
    
    def _generate_basic_recipe(self, ingredients: List[str], search_results: List[Dict]) -> str:
        """기본 레시피 생성 (Gemini 없을 때)"""
        if not search_results:
            return f"{', '.join(ingredients)}로 만들 수 있는 다양한 요리가 있습니다. 구글에서 '{' '.join(ingredients)} 레시피'로 검색해보세요!"
        
        # 첫 번째 검색 결과 기반
        first_result = search_results[0]
        recipe_text = f"추천 요리: {first_result['title']}\n\n"
        recipe_text += f"{first_result['snippet']}\n\n"
        recipe_text += f"🔗 자세한 레시피: {first_result['link']}"
        
        return recipe_text
    
    def _generate_quick_suggestions(self, ingredients: List[str], search_results: List[Dict]) -> List[str]:
        """빠른 요리 아이디어 생성"""
        suggestions = []
        
        # 기본 아이디어
        if "김치" in ingredients:
            suggestions.append("김치볶음밥 - 15분 완성")
            suggestions.append("김치전 - 바삭하고 간단")
        
        if "계란" in ingredients or "달걀" in ingredients:
            suggestions.append("계란말이 - 기본 반찬")
            suggestions.append("스크램블 에그 - 5분 완성")
        
        if "밥" in ingredients:
            suggestions.append("볶음밥 - 남은 재료 활용")
        
        # 검색 결과에서 추가
        for result in search_results[:2]:
            title = result['title']
            if "간단" in title or "쉬운" in title:
                clean_title = re.sub(r'\[.*?\]', '', title).strip()
                suggestions.append(clean_title)
        
        return suggestions[:5]  # 최대 5개
    
    async def get_cooking_method(self, dish_name: str, context: Dict = None) -> Dict:
        """특정 요리의 상세 조리법 검색"""
        print(f"👨‍🍳 상세 레시피 검색: {dish_name}")
        
        # 상세 검색
        if self.google_api_key and self.google_cx:
            query = f"{dish_name} 레시피 만들기 요리법"
            search_results = await self.search_recipes(query)
            
            if search_results:
                print(f"🔍 '{query}' 검색 결과: {len(search_results)}개 발견")
        else:
            search_results = []
            print("ℹ️ Google Search API 없음 - 기본 레시피 제공")
        
        # 상세 레시피 생성
        detailed_recipe = await self.generate_detailed_recipe(dish_name, context)
        
        # 빠른 요약
        quick_summary = self._generate_quick_summary(dish_name, search_results)
        
        # 관련 요리 추천
        related_dishes = self._find_related_dishes(dish_name)
        
        return {
            "dish_name": dish_name,
            "detailed_recipe": detailed_recipe,
            "quick_summary": quick_summary,
            "reference_urls": [r['link'] for r in search_results[:3]] if search_results else [],
            "related_dishes": related_dishes
        }
    
    async def generate_detailed_recipe(self, dish_name: str, context: Dict = None) -> str:
        """Gemini를 사용한 상세 레시피 생성 (REST API)"""
        if not self.gemini_api_key:
            # Gemini API가 없으면 기본 레시피 반환
            return self._get_default_recipe(dish_name)
        
        try:
            ingredients_hint = ""
            if context and context.get('last_ingredients'):
                ingredients_hint = f"사용 가능한 재료: {', '.join(context['last_ingredients'])}"
            
            prompt = f"""
{dish_name}의 간단한 조리법을 알려주세요.
{ingredients_hint}

간결하게 다음 형식으로 작성해주세요:

재료 
주재료: (3-4개만)
양념: (필수만)

🍳 조리법
1. (핵심 단계만)
2. (최대 5단계)

⏱️ 조리시간: X분
💡 핵심 팁: (1-2개)

각 섹션은 짧게 작성하고, 전체 길이는 500자 이내로 해주세요.
"""
            
            request_data = {
                "contents": [{
                    "parts": [{
                        "text": prompt
                    }]
                }],
                "generationConfig": {
                    "temperature": 0.7,
                    "maxOutputTokens": 500,
                    "topP": 0.95,
                    "topK": 40
                }
            }
            
            headers = {
                "Content-Type": "application/json",
                "x-goog-api-key": self.gemini_api_key
            }
            
            json_data = json.dumps(request_data, ensure_ascii=False).encode('utf-8')
            
            response = requests.post(
                self.gemini_api_url,
                headers=headers,
                data=json_data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                if 'candidates' in result and len(result['candidates']) > 0:
                    if 'content' in result['candidates'][0]:
                        content = result['candidates'][0]['content']
                        if 'parts' in content and len(content['parts']) > 0:
                            return content['parts'][0]['text'].strip()
            
            print(f"❌ Gemini API 오류: {response.status_code}")
            return self._get_default_recipe(dish_name)
            
        except Exception as e:
            print(f"❌ 상세 레시피 생성 오류: {e}")
            return self._get_default_recipe(dish_name)
    
    def _get_default_recipe(self, dish_name: str) -> str:
        """기본 레시피 제공"""
        default_recipes = {
            "김치찌개": """📋 재료 (2인분)
주재료: 김치 200g, 돼지고기 150g, 두부 1/2모
양념: 고춧가루 1T, 다진마늘 1T, 국간장 1T

🍳 조리법
1. 돼지고기를 볶아 기름을 냅니다
2. 김치를 넣고 함께 볶습니다
3. 물 2컵을 붓고 끓입니다
4. 양념을 넣고 10분간 끓입니다
5. 두부를 넣고 5분 더 끓입니다

⏱️ 조리시간: 20분
💡 팁: 신김치를 사용하면 더 맛있어요""",

            "된장찌개": """📋 재료 (2인분)
주재료: 된장 2T, 두부 1/2모, 감자 1개, 양파 1/2개
양념: 다진마늘 1T, 고춧가루 약간

🍳 조리법
1. 물 2컵에 된장을 풀어줍니다
2. 감자, 양파를 넣고 끓입니다
3. 두부와 마늘을 넣습니다
4. 5분간 더 끓여 완성합니다

⏱️ 조리시간: 15분
💡 팁: 멸치육수를 사용하면 더 깊은 맛""",

            "볶음밥": """📋 재료 (2인분)
주재료: 밥 2공기, 계란 2개, 대파 1대
양념: 간장 2T, 참기름 1T, 소금 약간

🍳 조리법
1. 계란을 스크램블로 볶습니다
2. 밥을 넣고 잘 볶아줍니다
3. 간장으로 간을 맞춥니다
4. 대파와 참기름을 넣어 마무리

⏱️ 조리시간: 10분
💡 팁: 찬밥을 사용하면 더 고슬고슬""",

            "파스타": """📋 재료 (2인분)
주재료: 파스타면 200g, 올리브오일 3T, 마늘 3개
양념: 소금, 후추, 페페론치노 약간

🍳 조리법
1. 파스타면을 8분간 삶습니다
2. 올리브오일에 마늘을 볶습니다
3. 면을 넣고 섞어줍니다
4. 면수를 조금 넣어 유화시킵니다

⏱️ 조리시간: 15분
💡 팁: 면수를 꼭 남겨두세요""",

            "순두부찌개": """📋 재료 (2인분)
주재료: 순두부 1봉, 계란 2개, 대파 1대
양념: 고춧가루 1T, 국간장 1T, 다진마늘 1T

🍳 조리법
1. 물 1.5컵을 끓입니다
2. 고춧가루와 양념을 넣습니다
3. 순두부를 숟가락으로 떠넣습니다
4. 계란을 풀어 넣고 완성합니다

⏱️ 조리시간: 10분
💡 팁: 해물을 넣으면 더 시원한 맛""",

            "부대찌개": """📋 재료 (2인분)
주재료: 스팸 1/2캔, 소시지 4개, 라면사리 1개
양념: 고춧가루 1T, 고추장 1T, 다진마늘 1T

🍳 조리법
1. 재료를 팬에 보기 좋게 담습니다
2. 육수를 부어 끓입니다
3. 양념을 풀어 넣습니다
4. 라면사리를 넣고 3분 끓입니다

⏱️ 조리시간: 15분
💡 팁: 치즈를 올리면 더 고소해요""",

            "제육볶음": """📋 재료 (2인분)
주재료: 돼지고기 300g, 양파 1개, 대파 1대
양념: 고추장 2T, 고춧가루 1T, 간장 1T

🍳 조리법
1. 돼지고기를 양념에 재웁니다
2. 팬에 볶다가 양파를 넣습니다
3. 고기가 익으면 대파를 넣습니다
4. 참기름으로 마무리합니다

⏱️ 조리시간: 20분
💡 팁: 양념은 30분 전에 재워두세요"""
        }
        
        # 기본 레시피가 있으면 반환
        if dish_name in default_recipes:
            return default_recipes[dish_name]
        
        # 없으면 일반적인 안내
        return f"""📋 {dish_name} 기본 레시피

🍳 조리법
1. 재료를 준비합니다
2. 기본 양념을 만듭니다
3. 재료를 조리합니다
4. 간을 맞춰 완성합니다

💡 더 자세한 레시피는 검색해보세요!"""
    
    def _generate_quick_summary(self, dish_name: str, search_results: List[Dict]) -> str:
        """요리 요약 생성"""
        if search_results:
            return search_results[0]['snippet']
        return f"{dish_name}은(는) 한국의 대표적인 요리입니다."
    
    def _find_related_dishes(self, dish_name: str) -> List[str]:
        """관련 요리 찾기"""
        related_map = {
            "김치찌개": ["된장찌개", "부대찌개", "순두부찌개"],
            "된장찌개": ["김치찌개", "청국장찌개", "순두부찌개"],
            "불고기": ["제육볶음", "갈비찜", "불갈비"],
            "비빔밥": ["볶음밥", "김밥", "덮밥"],
            "파스타": ["리조또", "피자", "그라탕"],
            "볶음밥": ["비빔밥", "오므라이스", "덮밥"],
            "제육볶음": ["불고기", "돼지갈비", "두루치기"],
            "순두부찌개": ["김치찌개", "된장찌개", "부대찌개"],
            "부대찌개": ["김치찌개", "라면", "순두부찌개"]
        }
        
        return related_map.get(dish_name, ["김치찌개", "된장찌개", "볶음밥"])