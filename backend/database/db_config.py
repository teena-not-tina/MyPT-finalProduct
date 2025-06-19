from pymongo import MongoClient
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional
from bson import ObjectId
import threading
import time
import logging

logger = logging.getLogger(__name__)

# MongoDB 연결 설정
MONGO_URL = "mongodb://root:example@192.168.0.199:27017/?authSource=admin"
DB_NAME = "test"
COLLECTION_NAME = "routines"
USER_DATA_COLLECTION = "user_data"
TEMP_ROUTINES_COLLECTION = "temp_routines"

class DatabaseHandler:
    def __init__(self):
        self.client = MongoClient(MONGO_URL)
        self.db = self.client[DB_NAME]
        self.collection = self.db[COLLECTION_NAME]
        self.user_data_collection = self.db[USER_DATA_COLLECTION]
        self.temp_routines_collection = self.db[TEMP_ROUTINES_COLLECTION]
        self.restoration_schedule = {}  # 복원 스케줄 관리
        
        # 백그라운드 복원 스레드 시작
        self._start_restoration_thread()

    def _convert_objectid(self, data):
        """ObjectId를 문자열로 변환하는 헬퍼 함수"""
        if isinstance(data, list):
            return [self._convert_objectid(item) for item in data]
        elif isinstance(data, dict):
            result = {}
            for key, value in data.items():
                if isinstance(value, ObjectId):
                    result[key] = str(value)
                elif isinstance(value, (dict, list)):
                    result[key] = self._convert_objectid(value)
                else:
                    result[key] = value
            return result
        elif isinstance(data, ObjectId):
            return str(data)
        else:
            return data

    
    def save_routine(self, routine_data: dict):
        """루틴 저장 with 상세한 오류 처리"""
        try:
            # 필수 필드 검증
            required_fields = ['user_id', 'day', 'title', 'exercises']
            for field in required_fields:
                if field not in routine_data:
                    print(f"❌ 필수 필드 누락: {field}")
                    return None
            
            # user_id 타입 검증 및 변환
            if isinstance(routine_data['user_id'], str):
                try:
                    routine_data['user_id'] = int(routine_data['user_id'])
                except ValueError:
                    print(f"❌ user_id 변환 실패: {routine_data['user_id']}")
                    return None
            
            # created_at이 없으면 추가
            if 'created_at' not in routine_data:
                routine_data['created_at'] = datetime.now(timezone.utc)
            
            # 데이터 유효성 추가 검증
            if not isinstance(routine_data['exercises'], list) or len(routine_data['exercises']) == 0:
                print("❌ exercises 필드가 비어있거나 잘못된 형식")
                return None
                
            print(f"✅ 루틴 저장 시도: user_id={routine_data['user_id']}, day={routine_data['day']}")
            
            result = self.collection.insert_one(routine_data)
            
            if result.acknowledged:
                print(f"✅ 루틴 저장 성공: {result.inserted_id}")
                return str(result.inserted_id)
            else:
                print("❌ MongoDB 저장 실패: acknowledged=False")
                return None
                
        except Exception as e:
            print(f"❌ MongoDB 저장 중 예외 발생: {e}")
            import traceback
            traceback.print_exc()
            return None

    def get_routines_by_day(self, user_id: int, day: int):
        try:
            result = self.collection.find_one({"user_id": user_id, "day": day})
            return self._convert_objectid(result) if result else None
        except Exception as e:
            print(f"MongoDB 조회 실패: {e}")
            return None
    
    def get_user_routines(self, user_id: str) -> List[Dict]:
        """사용자의 모든 운동 루틴 조회"""
        try:
            # user_id를 정수로 변환하여 검색
            try:
                user_id_int = int(user_id)
            except (ValueError, TypeError):
                user_id_int = user_id  # 변환 실패 시 원본 사용
            
            routines = list(self.collection.find({"user_id": user_id_int}).sort("day", 1))
            return self._convert_objectid(routines)
        except Exception as e:
            print(f"사용자 루틴 조회 실패: {e}")
            return []
    
    def has_user_routines(self, user_id: str) -> bool:
        """사용자가 기존 운동 루틴을 가지고 있는지 확인"""
        try:
            # user_id를 정수로 변환하여 검색
            try:
                user_id_int = int(user_id)
            except (ValueError, TypeError):
                user_id_int = user_id  # 변환 실패 시 원본 사용
                
            count = self.collection.count_documents({"user_id": user_id_int})
            return count > 0
        except Exception as e:
            print(f"사용자 루틴 존재 확인 실패: {e}")
            return False
    
    def delete_user_routines(self, user_id: str) -> bool:
        """사용자의 모든 운동 루틴 삭제"""
        try:
            # user_id를 정수로 변환하여 삭제
            try:
                user_id_int = int(user_id)
            except (ValueError, TypeError):
                user_id_int = user_id  # 변환 실패 시 원본 사용
                
            result = self.collection.delete_many({"user_id": user_id_int})
            return result.deleted_count > 0
        except Exception as e:
            print(f"사용자 루틴 삭제 실패: {e}")
            return False

    # 🔥 NEW: 특정 일차 루틴만 삭제하는 메서드 추가
    def delete_specific_day_routine(self, user_id: str, day: int) -> bool:
        """사용자의 특정 일차 운동 루틴만 삭제"""
        try:
            # user_id를 정수로 변환하여 삭제
            try:
                user_id_int = int(user_id)
            except (ValueError, TypeError):
                user_id_int = user_id
                
            result = self.collection.delete_many({
                "user_id": user_id_int,
                "day": day
            })
            
            print(f"사용자 {user_id}의 {day}일차 루틴 삭제: {result.deleted_count}개")
            return result.deleted_count > 0
        except Exception as e:
            print(f"특정 일차 루틴 삭제 실패: {e}")
            return False

    # 🔥 NEW: 여러 일차 루틴을 일괄 삭제하는 메서드 추가
    def delete_multiple_days_routines(self, user_id: str, days: List[int]) -> bool:
        """사용자의 여러 일차 운동 루틴을 일괄 삭제"""
        try:
            try:
                user_id_int = int(user_id)
            except (ValueError, TypeError):
                user_id_int = user_id
                
            result = self.collection.delete_many({
                "user_id": user_id_int,
                "day": {"$in": days}
            })
            
            print(f"사용자 {user_id}의 {days} 일차 루틴 삭제: {result.deleted_count}개")
            return result.deleted_count > 0
        except Exception as e:
            print(f"여러 일차 루틴 삭제 실패: {e}")
            return False
    
    def update_routine(self, routine_id: str, update_data: dict) -> bool:
        """특정 루틴 업데이트"""
        try:
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
            return self._convert_objectid(data)
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
            return self._convert_objectid(data) if data else None
        except Exception as e:
            print(f"최신 사용자 데이터 조회 실패: {e}")
            return None

    # 🔥 NEW: 개선된 임시 루틴 저장 기능들 (백업 타입 구분)
    def backup_user_routines_to_temp(self, user_id: str, routines: List[Dict], backup_type: str = "general") -> bool:
        """사용자 루틴을 임시 컬렉션에 백업 (백업 타입 구분)"""
        try:
            user_id_int = int(user_id) if isinstance(user_id, str) else user_id
            
            # 기존 동일 타입 백업 삭제
            self.temp_routines_collection.delete_many({
                "user_id": user_id_int,
                "backup_type": backup_type
            })
            
            # 새로운 백업 저장
            backup_data = {
                "user_id": user_id_int,
                "backup_type": backup_type,  # 🔥 NEW: 백업 타입 추가
                "original_routines": self._convert_objectid(routines),
                "backup_time": datetime.now(timezone.utc),
                "status": "active"
            }
            
            result = self.temp_routines_collection.insert_one(backup_data)
            print(f"사용자 {user_id} 루틴 백업 완료 ({backup_type}): {result.inserted_id}")
            return True
            
        except Exception as e:
            print(f"루틴 백업 실패: {e}")
            return False

    def restore_user_routines_from_temp(self, user_id: str, backup_type: str = None) -> bool:
        """임시 컬렉션에서 사용자 루틴 완전 복원 - 데이터 형식 보장"""
        try:
            user_id_int = int(user_id) if isinstance(user_id, str) else user_id
            
            # 백업된 루틴 찾기 (최신 백업 우선)
            query = {"user_id": user_id_int, "status": "active"}
            if backup_type:
                query["backup_type"] = backup_type
            
            backup = self.temp_routines_collection.find_one(
                query,
                sort=[("backup_time", -1)]  # 최신 백업 우선
            )
            
            if not backup:
                print(f"사용자 {user_id}의 백업 루틴을 찾을 수 없습니다. (타입: {backup_type})")
                return False
            
            original_routines = backup["original_routines"]
            
            # 🔥 현재 루틴 완전 삭제
            self.delete_user_routines(user_id)
            
            # 🔥 원래 루틴 완전 복원 (데이터 형식 그대로 유지)
            restored_count = 0
            for routine in original_routines:
                # _id 제거 (새로 생성되도록)
                if '_id' in routine:
                    del routine['_id']
                
                # user_id 보장
                routine['user_id'] = user_id_int
                
                # 원본 데이터 형식 그대로 저장
                saved_id = self.save_routine(routine)
                if saved_id:
                    restored_count += 1
            
            if restored_count > 0:
                # 백업 상태를 'restored'로 변경
                self.temp_routines_collection.update_one(
                    {"_id": backup["_id"]},
                    {"$set": {"status": "restored", "restored_time": datetime.now(timezone.utc)}}
                )
                
                print(f"사용자 {user_id} 루틴 완전 복원 완료: {restored_count}일차 (타입: {backup.get('backup_type', 'general')})")
                
                # 🔥 복원 완료 후 temp에서 삭제
                self.temp_routines_collection.delete_one({"_id": backup["_id"]})
                print(f"사용자 {user_id}의 백업 루틴을 temp에서 삭제했습니다.")
                
                return True
            else:
                print(f"사용자 {user_id} 루틴 복원 실패: 저장된 루틴 없음")
                return False
            
        except Exception as e:
            print(f"루틴 복원 실패: {e}")
            return False

    # 🔥 NEW: 백업 타입별 백업 존재 여부 확인
    def has_backup_routine(self, user_id: str, backup_type: str = None) -> bool:
        """사용자가 백업된 루틴을 가지고 있는지 확인"""
        try:
            user_id_int = int(user_id) if isinstance(user_id, str) else user_id
            
            query = {"user_id": user_id_int, "status": "active"}
            if backup_type:
                query["backup_type"] = backup_type
            
            count = self.temp_routines_collection.count_documents(query)
            return count > 0
        except Exception as e:
            print(f"백업 루틴 존재 확인 실패: {e}")
            return False

    # 🔥 NEW: 백업 타입별 백업 정보 조회
    def get_backup_info(self, user_id: str, backup_type: str = None) -> Optional[Dict]:
        """백업 정보 조회"""
        try:
            user_id_int = int(user_id) if isinstance(user_id, str) else user_id
            
            query = {"user_id": user_id_int, "status": "active"}
            if backup_type:
                query["backup_type"] = backup_type
            
            backup = self.temp_routines_collection.find_one(
                query,
                sort=[("backup_time", -1)]
            )
            
            return self._convert_objectid(backup) if backup else None
        except Exception as e:
            print(f"백업 정보 조회 실패: {e}")
            return None

    def schedule_routine_restoration(self, user_id: str, hours_delay: float):
        """루틴 자동 복원 스케줄링 - 분 단위 지원"""
        try:
            user_id_int = int(user_id) if isinstance(user_id, str) else user_id
            restoration_time = datetime.now(timezone.utc) + timedelta(hours=hours_delay)
            
            # 스케줄에 추가
            self.restoration_schedule[user_id_int] = restoration_time
            
            # 분 단위로 표시
            if hours_delay < 1:
                time_display = f"{int(hours_delay * 60)}분"
            else:
                time_display = f"{hours_delay}시간"
            
            print(f"사용자 {user_id} 루틴 복원이 {time_display} 후 ({restoration_time})에 스케줄되었습니다.")
            
        except Exception as e:
            print(f"복원 스케줄링 실패: {e}")

    def _start_restoration_thread(self):
        """백그라운드 복원 스레드 시작 - 정확한 시간 체크"""
        def restoration_worker():
            while True:
                try:
                    current_time = datetime.now(timezone.utc)
                    
                    # 복원할 사용자들 찾기
                    users_to_restore = []
                    for user_id, scheduled_time in self.restoration_schedule.items():
                        if current_time >= scheduled_time:
                            users_to_restore.append(user_id)
                    
                    # 복원 실행
                    for user_id in users_to_restore:
                        try:
                            # 🔥 원본 루틴을 temp에서 routines로 완전 복원
                            success = self.restore_user_routines_from_temp(str(user_id), backup_type="daily_modification")
                            if success:
                                print(f"자동 복원 완료: 사용자 {user_id}")
                            else:
                                print(f"자동 복원 실패: 사용자 {user_id}")
                        except Exception as e:
                            print(f"사용자 {user_id} 자동 복원 중 오류: {e}")
                        finally:
                            # 스케줄에서 제거
                            del self.restoration_schedule[user_id]
                    
                    # 🔥 10초마다 체크 (더 정확한 타이밍)
                    time.sleep(10)
                    
                except Exception as e:
                    print(f"복원 스레드 오류: {e}")
                    time.sleep(10)
        
        # 데몬 스레드로 시작
        restoration_thread = threading.Thread(target=restoration_worker, daemon=True)
        restoration_thread.start()
        print("루틴 자동 복원 스레드가 시작되었습니다.")

    def cleanup_old_temp_routines(self, days_old: int = 7):
        """오래된 임시 루틴 정리"""
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_old)
            
            result = self.temp_routines_collection.delete_many({
                "backup_time": {"$lt": cutoff_date}
            })
            
            print(f"{result.deleted_count}개의 오래된 임시 루틴을 정리했습니다.")
            
        except Exception as e:
            print(f"임시 루틴 정리 실패: {e}")

    def get_user_temp_routine_status(self, user_id: str) -> Dict:
        """사용자의 임시 루틴 상태 조회"""
        try:
            user_id_int = int(user_id) if isinstance(user_id, str) else user_id
            
            backup = self.temp_routines_collection.find_one(
                {"user_id": user_id_int, "status": "active"}
            )
            
            if backup:
                scheduled_restoration = self.restoration_schedule.get(user_id_int)
                return {
                    "has_temp_routine": True,
                    "backup_time": backup["backup_time"],
                    "backup_type": backup.get("backup_type", "general"),
                    "scheduled_restoration": scheduled_restoration,
                    "status": "active"
                }
            else:
                return {
                    "has_temp_routine": False,
                    "status": "none"
                }
                
        except Exception as e:
            print(f"임시 루틴 상태 조회 실패: {e}")
            return {"has_temp_routine": False, "status": "error"}

    # 🔥 NEW: 백업 타입별 전체 백업 현황 조회 (관리용)
    def get_all_backup_status(self) -> Dict:
        """모든 사용자의 백업 현황 조회 (관리용)"""
        try:
            pipeline = [
                {"$match": {"status": "active"}},
                {"$group": {
                    "_id": "$backup_type",
                    "count": {"$sum": 1},
                    "users": {"$addToSet": "$user_id"}
                }}
            ]
            
            backup_stats = list(self.temp_routines_collection.aggregate(pipeline))
            
            result = {
                "total_active_backups": 0,
                "backup_types": {},
                "scheduled_restorations": len(self.restoration_schedule)
            }
            
            for stat in backup_stats:
                backup_type = stat["_id"] or "general"
                result["backup_types"][backup_type] = {
                    "count": stat["count"],
                    "users": stat["users"]
                }
                result["total_active_backups"] += stat["count"]
            
            return result
            
        except Exception as e:
            print(f"백업 현황 조회 실패: {e}")
            return {
                "total_active_backups": 0,
                "backup_types": {},
                "scheduled_restorations": 0,
                "error": str(e)
            }
            
    def has_backup_routine(self, user_id: str, backup_type: str = None) -> bool:
        """사용자가 백업된 루틴을 가지고 있는지 확인 (기존 메서드 강화)"""
        try:
            user_id_int = int(user_id) if isinstance(user_id, str) else user_id
            
            query = {"user_id": user_id_int, "status": "active"}
            if backup_type:
                query["backup_type"] = backup_type
            
            count = self.temp_routines_collection.count_documents(query)
            
            if count > 0:
                logger.info(f"🔍 사용자 {user_id}의 활성 백업 루틴 {count}개 발견")
            
            return count > 0
        except Exception as e:
            logger.error(f"백업 루틴 존재 확인 실패: {e}")
            return False

    def get_backup_info(self, user_id: str, backup_type: str = None) -> Optional[Dict]:
        """백업 정보 조회 (기존 메서드 강화)"""
        try:
            user_id_int = int(user_id) if isinstance(user_id, str) else user_id
            
            query = {"user_id": user_id_int, "status": "active"}
            if backup_type:
                query["backup_type"] = backup_type
            
            backup = self.temp_routines_collection.find_one(
                query,
                sort=[("backup_time", -1)]  # 최신 백업 우선
            )
            
            if backup:
                logger.info(f"📋 사용자 {user_id}의 백업 정보 조회 성공: 타입={backup.get('backup_type')}, 루틴수={len(backup.get('original_routines', []))}")
            
            return self._convert_objectid(backup) if backup else None
        except Exception as e:
            logger.error(f"백업 정보 조회 실패: {e}")
            return None