from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

load_dotenv

MONGODB_URL = os.getenv("MONGODB_URL")
DATABASE_NAME = "test"

client = None
db = None

async def get_database():
    """Get database instance"""
    client = AsyncIOMotorClient(MONGODB_URL)
    db = client[DATABASE_NAME]
    return db

async def connect_to_mongo():
    global client, db
    client = AsyncIOMotorClient(MONGODB_URL)
    db = client[DATABASE_NAME]
    print(f"Connected to MongoDB at {MONGODB_URL}")

async def close_mongo_connection():
    global client
    if client:
        client.close()
        print("Disconnected from MongoDB")