from pymongo import MongoClient
from datetime import datetime, timezone
from typing import List, Dict, Optional

# MongoDB 연결 설정
MONGO_URL = "mongodb://root:example@192.168.0.199:27017/?authSource=admin"
DB_NAME = "test"
COLLECTION_NAME = "routines_test"
USER_DATA_COLLECTION = "user_data"  # 사용자 데이터 컬렉션 추가

class DatabaseHandler:
    def __init__(self):
        self.client = MongoClient(MONGO_URL)
        self.db = self.client[DB_NAME]
        self.collection = self.db[COLLECTION_NAME]
        self.user_data_collection = self.db[USER_DATA_COLLECTION]

    def save_routine(self, routine_data: dict):
        try:
            # created_at이 없으면 추가
            if 'created_at' not in routine_data:
                routine_data['created_at'] = datetime.now(timezone.utc)
                
            result = self.collection.insert_one(routine_data)
            return str(result.inserted_id)
        except Exception as e:
            print(f"MongoDB 저장 실패: {e}")
            return None

    def get_routines_by_day(self, user_id: int, day: int):
        try:
            return self.collection.find_one({"user_id": user_id, "day": day})
        except Exception as e:
            print(f"MongoDB 조회 실패: {e}")
            return None
    
    def get_user_routines(self, user_id: str) -> List[Dict]:
        """사용자의 모든 운동 루틴 조회"""
        try:
            routines = list(self.collection.find({"user_id": user_id}).sort("day", 1))
            return routines
        except Exception as e:
            print(f"사용자 루틴 조회 실패: {e}")
            return []
    
    def has_user_routines(self, user_id: str) -> bool:
        """사용자가 기존 운동 루틴을 가지고 있는지 확인"""
        try:
            count = self.collection.count_documents({"user_id": user_id})
            return count > 0
        except Exception as e:
            print(f"사용자 루틴 존재 확인 실패: {e}")
            return False
    
    def delete_user_routines(self, user_id: str) -> bool:
        """사용자의 모든 운동 루틴 삭제"""
        try:
            result = self.collection.delete_many({"user_id": user_id})
            return result.deleted_count > 0
        except Exception as e:
            print(f"사용자 루틴 삭제 실패: {e}")
            return False
    
    def update_routine(self, routine_id: str, update_data: dict) -> bool:
        """특정 루틴 업데이트"""
        try:
            from bson import ObjectId
            update_data['updated_at'] = datetime.now(timezone.utc)
            result = self.collection.update_one(
                {"_id": ObjectId(routine_id)},
                {"$set": update_data}
            )
            return result.modified_count > 0
        except Exception as e:
            print(f"루틴 업데이트 실패: {e}")
            return False
    
    # 사용자 데이터 관련 메서드들
    def save_user_data(self, user_id: str, data_type: str, data: dict) -> Optional[str]:
        """사용자 데이터 저장 (인바디, 선호도 등)"""
        try:
            user_data = {
                'user_id': user_id,
                'data_type': data_type,  # 'inbody', 'preferences', 'progress' 등
                'data': data,
                'created_at': datetime.now(timezone.utc)
            }
            result = self.user_data_collection.insert_one(user_data)
            return str(result.inserted_id)
        except Exception as e:
            print(f"사용자 데이터 저장 실패: {e}")
            return None
    
    def get_user_data(self, user_id: str, data_type: str = None) -> List[Dict]:
        """사용자 데이터 조회"""
        try:
            query = {"user_id": user_id}
            if data_type:
                query["data_type"] = data_type
            
            data = list(self.user_data_collection.find(query).sort("created_at", -1))
            return data
        except Exception as e:
            print(f"사용자 데이터 조회 실패: {e}")
            return []
    
    def get_latest_user_data(self, user_id: str, data_type: str) -> Optional[Dict]:
        """최신 사용자 데이터 조회"""
        try:
            data = self.user_data_collection.find_one(
                {"user_id": user_id, "data_type": data_type},
                sort=[("created_at", -1)]
            )
            return data
        except Exception as e:
            print(f"최신 사용자 데이터 조회 실패: {e}")
            return None