import os
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

import chromadb
from chromadb.config import Settings
from openai import OpenAI

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class UserVectorStore:
    """
    사용자별 데이터를 관리하는 Vector Database 클래스
    각 사용자의 인바디 데이터, 운동 선호도, 진행 상황 등을 저장
    """
    
    def __init__(self, 
                 collection_name: str = "user_personal_data",
                 persist_directory: str = "./user_chroma_db",
                 openai_api_key: Optional[str] = None):
        """
        UserVectorStore 초기화
        
        Args:
            collection_name: ChromaDB 컬렉션 이름
            persist_directory: 데이터베이스 저장 경로
            openai_api_key: OpenAI API 키
        """
        self.collection_name = collection_name
        self.persist_directory = persist_directory
        
        # OpenAI 클라이언트 설정
        self.openai_client = OpenAI(
            api_key=openai_api_key or os.getenv("OPENAI_API_KEY")
        )
        
        # ChromaDB 클라이언트 설정
        self.chroma_client = chromadb.PersistentClient(path=persist_directory)
        
        # 컬렉션 생성 또는 가져오기
        try:
            self.collection = self.chroma_client.get_collection(name=collection_name)
            logger.info(f"기존 사용자 데이터 컬렉션 '{collection_name}' 로드됨")
        except:
            self.collection = self.chroma_client.create_collection(
                name=collection_name,
                metadata={"description": "User personal fitness data"}
            )
            logger.info(f"새 사용자 데이터 컬렉션 '{collection_name}' 생성됨")
    
    def get_text_embedding(self, text: str, model: str = "text-embedding-3-small") -> List[float]:
        """텍스트 임베딩 생성"""
        try:
            response = self.openai_client.embeddings.create(
                input=text,
                model=model
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"임베딩 생성 실패: {e}")
            # 기본 임베딩 반환
            return [0.0] * 1536
    
    def format_inbody_data_for_vector(self, user_id: str, inbody_data: Dict[str, Any]) -> str:
        """인바디 데이터를 자연어로 변환"""
        formatted_text = f"""
        사용자 ID: {user_id}
        데이터 유형: 인바디 측정 결과
        
        신체 정보:
        - 성별: {inbody_data.get('gender', '미지정')}
        - 나이: {inbody_data.get('age', '미지정')}세
        - 신장: {inbody_data.get('height', '미지정')}cm
        - 체중: {inbody_data.get('weight', '미지정')}kg
        - 골격근량: {inbody_data.get('muscle_mass', '미측정')}kg
        - 체지방률: {inbody_data.get('body_fat', '미측정')}%
        - BMI: {inbody_data.get('bmi', '미계산')}
        - 기초대사율: {inbody_data.get('basal_metabolic_rate', '미계산')}kcal
        
        측정 일시: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}
        """
        return formatted_text.strip()
    
    def format_preferences_for_vector(self, user_id: str, preferences: Dict[str, Any]) -> str:
        """운동 선호도를 자연어로 변환"""
        formatted_text = f"""
        사용자 ID: {user_id}
        데이터 유형: 운동 선호도 및 목표
        
        운동 정보:
        - 운동 목표: {preferences.get('goal', '미지정')}
        - 경험 수준: {preferences.get('experience_level', '미지정')}
        - 부상 상태: {preferences.get('injury_status', '미지정')}
        - 운동 가능 시간: {preferences.get('available_time', '미지정')}
        
        기록 일시: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}
        """
        return formatted_text.strip()
    
    def add_user_inbody_data(self, user_id: str, inbody_data: Dict[str, Any]) -> bool:
        """사용자 인바디 데이터를 VectorDB에 추가"""
        try:
            # user_id 검증
            if not user_id or user_id == "None" or user_id == "null":
                logger.warning("유효하지 않은 user_id로 인바디 데이터 저장 건너뜀")
                return False
            
            # 자연어로 변환
            formatted_text = self.format_inbody_data_for_vector(str(user_id), inbody_data)
            
            # 임베딩 생성
            embedding = self.get_text_embedding(formatted_text)
            
            # 고유 ID 생성
            doc_id = f"inbody_{user_id}_{int(datetime.now().timestamp())}"
            
            # 메타데이터 준비 - 모든 값을 문자열로 변환
            metadata = {
                'user_id': str(user_id),
                'data_type': 'inbody',
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'gender': str(inbody_data.get('gender', '')),
                'age': str(inbody_data.get('age', '')),
                'bmi': str(inbody_data.get('bmi', ''))
            }
            
            # VectorDB에 저장
            self.collection.add(
                embeddings=[embedding],
                documents=[formatted_text],
                metadatas=[metadata],
                ids=[doc_id]
            )
            
            logger.info(f"사용자 {user_id}의 인바디 데이터가 VectorDB에 저장됨")
            return True
            
        except Exception as e:
            logger.error(f"인바디 데이터 저장 실패: {e}")
            return False
    
    def add_user_preferences(self, user_id: str, preferences: Dict[str, Any]) -> bool:
        """사용자 운동 선호도를 VectorDB에 추가"""
        try:
            # user_id 검증
            if not user_id or user_id == "None" or user_id == "null":
                logger.warning("유효하지 않은 user_id로 운동 선호도 저장 건너뜀")
                return False
            
            # 자연어로 변환
            formatted_text = self.format_preferences_for_vector(str(user_id), preferences)
            
            # 임베딩 생성
            embedding = self.get_text_embedding(formatted_text)
            
            # 고유 ID 생성
            doc_id = f"preferences_{user_id}_{int(datetime.now().timestamp())}"
            
            # 메타데이터 준비 - 모든 값을 문자열로 변환
            metadata = {
                'user_id': str(user_id),
                'data_type': 'preferences',
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'goal': str(preferences.get('goal', '')),
                'experience_level': str(preferences.get('experience_level', ''))
            }
            
            # VectorDB에 저장
            self.collection.add(
                embeddings=[embedding],
                documents=[formatted_text],
                metadatas=[metadata],
                ids=[doc_id]
            )
            
            logger.info(f"사용자 {user_id}의 운동 선호도가 VectorDB에 저장됨")
            return True
            
        except Exception as e:
            logger.error(f"운동 선호도 저장 실패: {e}")
            return False
    
    def get_user_context(self, user_id: str, query: str, n_results: int = 5) -> str:
        """사용자별 컨텍스트 검색"""
        try:
            # user_id 검증
            if not user_id or user_id == "None" or user_id == "null":
                logger.warning("유효하지 않은 user_id로 컨텍스트 검색 건너뜀")
                return ""
            
            # 쿼리 임베딩 생성
            query_embedding = self.get_text_embedding(query)
            
            # 사용자별 필터링 - user_id를 문자열로 변환하여 확실히 함
            where_filter = {"user_id": str(user_id)}
            
            # 검색 실행
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=where_filter
            )
            
            if not results['documents'] or not results['documents'][0]:
                logger.info(f"사용자 {user_id}에 대한 컨텍스트가 없습니다.")
                return ""
            
            # 컨텍스트 구성
            context_parts = []
            for doc in results['documents'][0]:
                context_parts.append(doc)
            
            logger.info(f"사용자 {user_id}에 대한 {len(context_parts)}개의 컨텍스트를 찾았습니다.")
            return '\n\n---\n\n'.join(context_parts)
            
        except Exception as e:
            logger.error(f"사용자 컨텍스트 검색 실패: {e}")
            return ""
    
    def get_user_latest_data(self, user_id: str, data_type: str = None) -> List[Dict[str, Any]]:
        """사용자의 최신 데이터 조회"""
        try:
            # user_id 검증
            if not user_id or user_id == "None" or user_id == "null":
                logger.warning("유효하지 않은 user_id로 데이터 조회 건너뜀")
                return []
            
            where_filter = {"user_id": str(user_id)}
            if data_type:
                where_filter["data_type"] = str(data_type)
            
            # 모든 데이터 조회 (최신순)
            results = self.collection.get(
                where=where_filter,
                include=["documents", "metadatas"]
            )
            
            if not results['documents']:
                logger.info(f"사용자 {user_id}에 대한 데이터가 없습니다.")
                return []
            
            # 메타데이터와 문서를 결합하여 반환
            combined_results = []
            for i, doc in enumerate(results['documents']):
                combined_results.append({
                    'document': doc,
                    'metadata': results['metadatas'][i]
                })
            
            # 타임스탬프 기준으로 정렬 (최신순)
            combined_results.sort(
                key=lambda x: x['metadata'].get('timestamp', ''),
                reverse=True
            )
            
            logger.info(f"사용자 {user_id}에 대한 {len(combined_results)}개의 데이터를 찾았습니다.")
            return combined_results
            
        except Exception as e:
            logger.error(f"사용자 데이터 조회 실패: {e}")
            return []
    
    def delete_user_data(self, user_id: str, data_type: str = None) -> bool:
        """사용자 데이터 삭제"""
        try:
            # user_id 검증
            if not user_id or user_id == "None" or user_id == "null":
                logger.warning("유효하지 않은 user_id로 데이터 삭제 건너뜀")
                return False
            
            where_filter = {"user_id": str(user_id)}
            if data_type:
                where_filter["data_type"] = str(data_type)
            
            # 삭제할 데이터 조회
            results = self.collection.get(
                where=where_filter,
                include=["documents", "metadatas"]
            )
            
            if not results['ids']:
                logger.info(f"삭제할 데이터가 없습니다: {user_id}")
                return True
            
            # 데이터 삭제
            self.collection.delete(
                where=where_filter
            )
            
            logger.info(f"사용자 {user_id}의 {data_type or '모든'} 데이터가 삭제됨")
            return True
            
        except Exception as e:
            logger.error(f"사용자 데이터 삭제 실패: {e}")
            return False
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """컬렉션 통계 정보 반환"""
        try:
            count = self.collection.count()
            return {
                'total_documents': count,
                'collection_name': self.collection_name
            }
        except Exception as e:
            logger.error(f"통계 정보 조회 실패: {e}")
            return {}
    
    def add_user_progress(self, user_id: str, progress_data: Dict[str, Any]) -> bool:
        """사용자 운동 진행 상황 추가"""
        try:
            # user_id 검증
            if not user_id or user_id == "None" or user_id == "null":
                logger.warning("유효하지 않은 user_id로 운동 진행 상황 저장 건너뜀")
                return False
            
            formatted_text = f"""
            사용자 ID: {user_id}
            데이터 유형: 운동 진행 상황
            
            진행 정보:
            - 완료한 운동: {progress_data.get('completed_exercises', [])}
            - 운동 일차: {progress_data.get('day', '미지정')}
            - 운동 날짜: {progress_data.get('date', '미지정')}
            - 총 운동 시간: {progress_data.get('total_time', '미지정')}분
            - 달성률: {progress_data.get('completion_rate', '미지정')}%
            
            기록 일시: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}
            """
            
            embedding = self.get_text_embedding(formatted_text)
            doc_id = f"progress_{user_id}_{int(datetime.now().timestamp())}"
            
            # 메타데이터 준비 - 모든 값을 문자열로 변환
            metadata = {
                'user_id': str(user_id),
                'data_type': 'progress',
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'day': str(progress_data.get('day', '')),
                'completion_rate': str(progress_data.get('completion_rate', ''))
            }
            
            self.collection.add(
                embeddings=[embedding],
                documents=[formatted_text],
                metadatas=[metadata],
                ids=[doc_id]
            )
            
            logger.info(f"사용자 {user_id}의 운동 진행 상황이 저장됨")
            return True
            
        except Exception as e:
            logger.error(f"운동 진행 상황 저장 실패: {e}")
            return False