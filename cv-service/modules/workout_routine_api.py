# cv-service/modules/workout_routine_api.py - FIXED VERSION

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from bson import ObjectId
import os
from datetime import datetime
from typing import Union

router = APIRouter(prefix="/api/workout", tags=["workout"])

# MongoDB connection
MONGO_URL = os.getenv("MONGO_URL", "mongodb://root:example@192.168.0.199:27017/?authSource=admin")
MONGO_DB = os.getenv("MONGO_DB", "test")

class MongoDB:
    client: AsyncIOMotorClient = None
    db: AsyncIOMotorDatabase = None

mongodb = MongoDB()

async def get_database() -> AsyncIOMotorDatabase:
    return mongodb.db

# MongoDB connection lifecycle
async def connect_to_mongo():
    mongodb.client = AsyncIOMotorClient(MONGO_URL)
    mongodb.db = mongodb.client[MONGO_DB]
    print(f"Connected to MongoDB at {MONGO_URL}, DB: {mongodb.db.name}")

async def close_mongo_connection():
    if mongodb.client:
        mongodb.client.close()
        print("Disconnected from MongoDB")

# Data models
class WorkoutSet(BaseModel):
    id: int
    reps: Optional[int] = None
    weight: Optional[float] = None
    time: Optional[str] = None
    completed: bool = False

class Exercise(BaseModel):
    id: int
    name: str
    sets: List[WorkoutSet]

class Routine(BaseModel):
    day: int
    title: str
    exercises: List[Exercise]

class RoutineInDB(Routine):
    id: str = Field(alias="_id")
    
    class Config:
        populate_by_name = True

# Helper function to convert MongoDB document to dict
def routine_helper(routine) -> dict:
    return {
        "_id": str(routine["_id"]),
        "day": routine["day"],
        "title": routine["title"],
        "exercises": routine["exercises"]
    }

# Test endpoint to check database connection
@router.get("/test-connection")
async def test_connection(db: AsyncIOMotorDatabase = Depends(get_database)):
    """Test MongoDB connection and return collection stats"""
    try:
        # Get collection names
        collections = await db.list_collection_names()
        
        # Count documents in routines collection
        count = await db.routines.count_documents({})
        
        # Get a sample routine
        sample = await db.routines.find_one()
        
        return {
            "status": "connected",
            "database": db.name,
            "collections": collections,
            "routines_count": count,
            "sample_routine": routine_helper(sample) if sample else None
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

# API Endpoints
@router.get("/routines")
async def get_all_routines(
    user_id: int = Query(...),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    user_id_str = str(user_id)
    routines = []
    # Add .sort("day", 1) to ensure routines are ordered by day ascending
    async for routine in db.routines.find(
        {"user_id": {"$in": [user_id, user_id_str, int(user_id_str) if user_id_str.isdigit() else None]}}
    ).sort("day", 1):
        routines.append(routine_helper(routine))
    return routines

# 특정 날짜 루틴 조회 (user_id 기준)
@router.get("/routines/{day}")
async def get_routine_by_day(
    day: int,
    user_id: int = Query(...),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    routine = await db.routines.find_one({"day": day, "user_id": user_id})
    if not routine:
        raise HTTPException(status_code=404, detail=f"Routine for day {day} not found")
    return routine_helper(routine)

# FIXED: Separate endpoints for different operations
@router.put("/routines/{day}/exercises/{exercise_id}/sets/{set_id}")
async def update_set(
    day: int, 
    exercise_id: int, 
    set_id: int, 
    update_data: Dict,
    user_id: int = Query(...),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Update a specific set with new data"""
    # Find the routine
    routine = await db.routines.find_one({"day": day, "user_id": user_id})
    if not routine:
        raise HTTPException(status_code=404, detail=f"Routine for day {day} not found")
    
    # Update the specific set
    updated = False
    for exercise in routine["exercises"]:
        if exercise["id"] == exercise_id:
            for set_item in exercise["sets"]:
                if set_item["id"] == set_id:
                    # Update the set data
                    for key, value in update_data.items():
                        if key in set_item or key in ["reps", "weight", "time", "completed"]:
                            set_item[key] = value
                    updated = True
                    break
            if updated:
                break
    
    if not updated:
        raise HTTPException(status_code=404, detail=f"Exercise {exercise_id} or Set {set_id} not found")
    
    # Save the updated routine
    await db.routines.update_one(
        {"day": day, "user_id": user_id},
        {"$set": {"exercises": routine["exercises"]}}
    )
    
    return {"message": "Set updated successfully"}

@router.post("/routines/{day}/exercises/{exercise_id}/complete-set/{set_id}")
async def toggle_set_completion(
    day: int, 
    exercise_id: int, 
    set_id: int,
    user_id: int = Query(...),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Toggle set completion status"""
    routine = await db.routines.find_one({"day": day, "user_id": user_id})
    if not routine:
        raise HTTPException(status_code=404, detail=f"Routine for day {day} not found")
    
    toggled = False
    current_status = None
    for exercise in routine["exercises"]:
        if exercise["id"] == exercise_id:
            for set_item in exercise["sets"]:
                if set_item["id"] == set_id:
                    set_item["completed"] = not set_item.get("completed", False)
                    current_status = set_item["completed"]
                    toggled = True
                    break
            if toggled:
                break
    
    if not toggled:
        raise HTTPException(status_code=404, detail=f"Exercise {exercise_id} or Set {set_id} not found")
    
    # Save the updated routine
    result = await db.routines.update_one(
        {"day": day, "user_id": user_id},
        {"$set": {"exercises": routine["exercises"]}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=500, detail="Failed to update routine in database")
    
    return {
        "message": "Set completion toggled successfully", 
        "completed": current_status,
        "set_id": set_id,
        "exercise_id": exercise_id
    }

@router.post("/routines/{day}/exercises/{exercise_id}/sets")
async def add_set(
    day: int, 
    exercise_id: int,
    user_id: int = Query(...),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Add a new set to an exercise"""
    routine = await db.routines.find_one({"day": day, "user_id": user_id})
    if not routine:
        raise HTTPException(status_code=404, detail=f"Routine for day {day} not found")
    
    new_set = None
    for exercise in routine["exercises"]:
        if exercise["id"] == exercise_id:
            # Create new set based on the last set
            if exercise["sets"]:
                last_set = exercise["sets"][-1]
                new_set = last_set.copy()
                new_set["id"] = max(s["id"] for s in exercise["sets"]) + 1
                new_set["completed"] = False
            else:
                # Default set if no existing sets
                new_set = {"id": 1, "reps": 10, "weight": 0, "completed": False}
            
            exercise["sets"].append(new_set)
            break
    
    if not new_set:
        raise HTTPException(status_code=404, detail=f"Exercise {exercise_id} not found")
    
    # Save the updated routine
    await db.routines.update_one(
        {"day": day, "user_id": user_id},
        {"$set": {"exercises": routine["exercises"]}}
    )
    
    return {"message": "Set added successfully", "set": new_set}

@router.delete("/routines/{day}/exercises/{exercise_id}/sets/{set_id}")
async def delete_set(
    day: int, 
    exercise_id: int, 
    set_id: int,
    user_id: int = Query(...),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Delete a specific set"""
    routine = await db.routines.find_one({"day": day, "user_id": user_id})
    if not routine:
        raise HTTPException(status_code=404, detail=f"Routine for day {day} not found")
    
    updated = False
    for exercise in routine["exercises"]:
        if exercise["id"] == exercise_id:
            original_length = len(exercise["sets"])
            exercise["sets"] = [s for s in exercise["sets"] if s["id"] != set_id]
            if len(exercise["sets"]) < original_length:
                updated = True
            break
    
    if not updated:
        raise HTTPException(status_code=404, detail=f"Exercise {exercise_id} or Set {set_id} not found")
    
    # Save the updated routine
    await db.routines.update_one(
        {"day": day, "user_id": user_id},
        {"$set": {"exercises": routine["exercises"]}}
    )
    
    return {"message": "Set deleted successfully"}

@router.delete("/routines/{day}/exercises/{exercise_id}")
async def delete_exercise(
    day: int, 
    exercise_id: int,
    user_id: int = Query(...),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Delete an exercise from a routine"""
    routine = await db.routines.find_one({"day": day, "user_id": user_id})
    if not routine:
        raise HTTPException(status_code=404, detail=f"Routine for day {day} not found")
    
    original_length = len(routine["exercises"])
    routine["exercises"] = [e for e in routine["exercises"] if e["id"] != exercise_id]
    
    if len(routine["exercises"]) == original_length:
        raise HTTPException(status_code=404, detail=f"Exercise {exercise_id} not found")
    
    # Save the updated routine
    await db.routines.update_one(
        {"day": day, "user_id": user_id},
        {"$set": {"exercises": routine["exercises"]}}
    )
    
    return {"message": "Exercise deleted successfully"}

@router.post("/routines/camera/analyze")
async def trigger_posture_analysis(request_data: Dict):
    """Trigger posture analysis (placeholder)"""
    exercise_name = request_data.get("exercise_name")
    return {
        "message": f"Analysis triggered for {exercise_name}",
        "status": "ready",
        "websocket_url": "ws://localhost:8001/api/workout/ws/analyze"
    }

# 유저별 루틴 조회
@router.get("/routines/user/{user_id}")
async def get_user_routines(
    user_id: int,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    routines = []
    async for routine in db.routines.find({"user_id": user_id}):
        routines.append(routine_helper(routine))
    return routines

# 유저별 기본 루틴 복사
@router.post("/routines/user/{user_id}/copy-default")
async def copy_default_routines_for_user(
    user_id: int,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    existing = await db.routines.find_one({"user_id": user_id})
    if existing:
        raise HTTPException(status_code=400, detail="User already has routines")
    default_routines = []
    async for routine in db.routines.find({"user_id": {"$exists": False}}):
        routine_copy = routine.copy()
        routine_copy.pop("_id", None)
        routine_copy["user_id"] = user_id
        routine_copy["created_at"] = datetime.utcnow()
        default_routines.append(routine_copy)
    if default_routines:
        result = await db.routines.insert_many(default_routines)
        return {"message": f"Created {len(result.inserted_ids)} routines for user {user_id}"}
    else:
        raise HTTPException(status_code=404, detail="No default routines found")

# 루틴 리셋 (user_id 기준)
@router.post("/routines/user/{user_id}/reset")
async def reset_user_routines(
    user_id: int,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    await db.routines.update_many(
        {"user_id": user_id},
        {"$set": {"exercises.$[].sets.$[].completed": False}}
    )
    return {"message": "User routines reset"}

# 루틴 완료시, 유저 progress, level 업데이트
@router.post("/routines/{day}/complete")
async def complete_routine(
    day: int,
    user_id: int = Query(...),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    # 1. 모든 세트가 완료되었는지 확인
    routine = await db.routines.find_one({"day": day, "user_id": user_id})
    if not routine:
        raise HTTPException(status_code=404, detail="Routine not found")

    all_completed = all(
        set_item.get("completed", False)
        for exercise in routine["exercises"]
        for set_item in exercise["sets"]
    )
    if not all_completed:
        raise HTTPException(status_code=400, detail="Not all sets are completed")

    # 2. users 컬렉션에서 user_id로 progress, level 업데이트
    user = await db.users.find_one({"user_id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    progress = user.get("progress", 0)
    level = user.get("level", 1)

    # level 7 이상이면 더 이상 증가하지 않음, 안내 메시지 반환
    if level >= 7:
        await db.users.update_one(
            {"user_id": user_id},
            {"$set": {"progress": 0, "level": 7}}
        )
        return {
            "message": "최고 레벨에 도달했습니다! 이후 기능은 곧 추가될 예정입니다.",
            "progress": 4,
            "level": 7,
            "alert": True
        }

    if progress >= 4:
        # 4번째 루틴 완료 시 progress 0, level +1
        new_progress = 0
        new_level = level + 1
    else:
        new_progress = progress + 1
        new_level = level

    await db.users.update_one(
        {"user_id": user_id},
        {"$set": {"progress": new_progress, "level": new_level}}
    )

    return {
        "message": "Routine completed, progress updated",
        "progress": new_progress,
        "level": new_level
    }