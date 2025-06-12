from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
import os
import requests
import json
import time
import base64
import threading
from pymongo import MongoClient
from datetime import datetime, timezone, timedelta

MONGO_URI = "mongodb://root:example@192.168.0.199:27017/?authSource=admin"
DB_NAME = "test"

router = APIRouter()

def delete_food_data(user_id):
    try:
        time.sleep(60)
        client = MongoClient(MONGO_URI)
        db = client[DB_NAME]
        collection = db.user_image
        result = collection.update_one(
            {'user_id': user_id},
            {'$unset': {'food': 1}}
        )
        if result.modified_count > 0:
            print(f"MongoDB: food 데이터 삭제 완료 (user_id: {user_id})")
    except Exception as e:
        print(f"MongoDB 삭제 오류: {str(e)}")
    finally:
        client.close()

def save_food_image(user_id, image_base64, previous_image=None):
    try:
        client = MongoClient(MONGO_URI)
        db = client[DB_NAME]
        collection = db.user_image
        current_time = datetime.now(timezone.utc)
        update_data = {
            'food': {
                'image_data': image_base64,
                'created_at': current_time,
                'updated_at': current_time,
                'expires_at': current_time + timedelta(seconds=60)
            }
        }
        if previous_image:
            update_data['food']['previous_image'] = previous_image
        result = collection.update_one(
            {'user_id': user_id},
            {'$set': update_data},
            upsert=True
        )
        print(f"MongoDB: 이미지 {'업데이트' if result.matched_count else '저장'} 완료 (user_id: {user_id}, 60초 후 삭제 예정)")
        delete_thread = threading.Thread(
            target=delete_food_data,
            args=(user_id,)
        )
        delete_thread.daemon = True
        delete_thread.start()
        return True
    except Exception as e:
        print(f"MongoDB 저장 오류: {str(e)}")
        return False
    finally:
        client.close()

def generate_image_from_comfyui(prompt, user_id):
    try:
        COMFYUI_API_URL = os.getenv('COMFYUI_API_URL', 'http://127.0.0.1:8188')
        start_time = time.time()
        comfyui_output = os.path.abspath(r"C:\Users\702-17\Documents\ComfyUI\output")
        print(f"이미지 생성 시작 - 프롬프트: {prompt}")
        workflow_path = os.path.join(os.path.dirname(__file__), 'workflows', 'my_comfyui_workflow.json')
        with open(workflow_path, 'r', encoding='utf-8') as f:
            workflow = json.load(f)
        food_prompt = f"""
            (masterpiece:1.2), (best quality:1.2), ultra detailed,
            cute SD chibi character made of {prompt}, 
            {prompt} as main theme, {prompt}-shaped body parts,
            melted {prompt} texture skin, {prompt} details,
            food mascot character, appetizing and kawaii,
            anime style, big head small body,
            professional food photo lighting
        """
        negative_prompt = """
            ugly, deformed, disfigured, mutated, blurry,
            bad anatomy, incorrect proportions, 
            low quality, worst quality, 
            text, watermark, signature, copyright,
            extra limbs, missing limbs, floating limbs,
            malformed hands, duplicate bodies, multiple characters,
            poorly drawn face, bad perspective,
            oversaturated, overexposed
        """
        workflow["2"]["inputs"]["text"] = food_prompt.strip().replace('\n', ' ')
        workflow["3"]["inputs"]["text"] = negative_prompt.strip().replace('\n', ' ')
        workflow["5"]["inputs"].update({
            "seed": int(time.time()) % 1000000000,
            "steps": 30,
            "cfg": 8.5,
            "sampler_name": "euler_ancestral",
            "scheduler": "karras",
            "denoise": 0.45
        })
        print(f"[사용된 프롬프트]: {food_prompt.strip()}")
        print(f"[사용된 네거티브 프롬프트]: {negative_prompt.strip()}")
        response = requests.post(f"{COMFYUI_API_URL}/prompt", json={"prompt": workflow})
        if not response.ok:
            raise Exception(f"ComfyUI API 오류: {response.status_code}")
        prompt_id = response.json()['prompt_id']
        print(f"프롬프트 전송 완료. ID: {prompt_id}")
        max_attempts = 300
        for attempt in range(max_attempts):
            try:
                response = requests.get(f"{COMFYUI_API_URL}/history/{prompt_id}")
                if not response.ok:
                    print(f"History API 응답 오류: {response.status_code}")
                    time.sleep(1)
                    continue
                history = response.json()
                if prompt_id in history and 'outputs' in history[prompt_id]:
                    try:
                        client = MongoClient(MONGO_URI)
                        db = client[DB_NAME]
                        collection = db.user_image
                        user_doc = collection.find_one({'user_id': user_id})
                        previous_image = None
                        if user_doc and 'food' in user_doc:
                            previous_image = user_doc['food']['image_data']
                            print(f"기존 이미지 데이터 찾음 (user_id: {user_id})")
                    except Exception as db_error:
                        print(f"MongoDB 조회 오류: {str(db_error)}")
                    finally:
                        client.close()
                    output_files = os.listdir(comfyui_output)
                    if output_files:
                        latest_file = max([f for f in output_files if f.endswith('.png')],
                                        key=lambda x: os.path.getctime(os.path.join(comfyui_output, x)))
                        with open(os.path.join(comfyui_output, latest_file), 'rb') as image_file:
                            new_image_base64 = base64.b64encode(image_file.read()).decode('utf-8')
                            if save_food_image(user_id, new_image_base64, previous_image):
                                elapsed_time = time.time() - start_time
                                print(f"이미지 생성 및 저장 완료! 소요 시간: {elapsed_time:.1f}초")
                                return new_image_base64
            except Exception as e:
                print(f"이미지 처리 중 오류: {str(e)}")
            print(f"이미지 생성 대기 중... {attempt+1}/{max_attempts}초")
            time.sleep(1)
        raise Exception("이미지 생성 시간 초과")
    except Exception as e:
        print(f"전체 프로세스 오류: {str(e)}")
        raise e

class FoodRequest(BaseModel):
    food: str
    # user_id: int

@router.post("/generate-food")
async def generate_food(request: Request):
    try:
        data = await request.json()
        food = data.get("food")
        # 세션 또는 쿠키에서 user_id 추출 (여기서는 예시로 sessionStorage에서 프론트가 헤더로 user_id를 보낸다고 가정)
        user_id = request.headers.get("user-id")
        if not user_id:
            raise HTTPException(status_code=400, detail="user_id가 필요합니다.")
        user_id = int(user_id)
        print(f"API 요청 받음: {food}, user_id: {user_id}")
        image_base64 = generate_image_from_comfyui(food, user_id)
        return {"image_base64": image_base64}
    except Exception as e:
        print(f"API 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def health_check():
    return {"status": "ok", "message": "Food Generator API is running"}

# @router.post("/generate-food")
# async def generate_food(request: FoodRequest):
#     try:
#         food = request.food
#         user_id = request.user_id
#         print(f"API 요청 받음: {food}, user_id: {user_id}")
#         image_base64 = generate_image_from_comfyui(food, user_id)
#         return {"image_base64": image_base64}
#     except Exception as e:
#         print(f"API 오류: {str(e)}")
#         raise HTTPException(status_code=500, detail=str(e))

# @router.get("/health")
# async def health_check():
#     return {"status": "ok", "message": "Food Generator API is running"}