from kafka import KafkaConsumer, KafkaProducer
import json 
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import os

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("DB_NAME")
BATCH_SIZE = 5

mongo_client = AsyncIOMotorClient(MONGO_URI)
db = mongo_client[DB_NAME]

consumer = KafkaConsumer(
    "user_signups",
    bootstrap_servers = "localhost:9092",
    value_deserializer = lambda m: json.loads(m.decode("utf-8")),
    auto_offset_reset = "earliest",
    enable_auto_commit = False,
    group_id = "signup_consumers"
)

async def insert_batch(batch: list):
    try:
        await db.users.insert_many(batch)
        print(f"Inserted batch of {len(batch)} users")
        return True
    except Exception as e:
        print(f"Batch insert Failed : {e}")
        return False
    
async def run_consumer():
    batch = []
    print("Kafka consumer started, waiting for messages...")

    for message in consumer:
        user_data = message.value

        if "email" not in user_data:
            print(f"Skipping invalid message: {user_data}")
            continue

        print(f"Received: {user_data['email']}")
        batch.append(user_data)

        if len(batch) >= BATCH_SIZE:
            success = await insert_batch(batch)
            if success:
                consumer.commit()
                batch = []


asyncio.run(run_consumer())