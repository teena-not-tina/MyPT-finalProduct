from pymongo import MongoClient
from datetime import datetime, timezone

# MongoDB 연결 설정
MONGO_URL = "mongodb://root:example@192.168.0.199:27017/?authSource=admin"
DB_NAME = "test"
COLLECTION_NAME = "routines"

class DatabaseHandler:
    def __init__(self):
        self.client = MongoClient(MONGO_URL)
        self.db = self.client[DB_NAME]
        self.collection = self.db[COLLECTION_NAME]

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