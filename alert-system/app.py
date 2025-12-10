import json
import time
import os
from kafka import KafkaConsumer, KafkaProducer
from sqlalchemy import create_engine, text

# Database connection
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://user:password@postgres:5432/datadb")
engine = create_engine(DATABASE_URL)

def get_user_preferences(airport_code):
    # Query datadb for users interested in this airport with thresholds
    query = text("""
        SELECT user_email, high_value, low_value 
        FROM user_airports 
        WHERE airport_code = :code
    """)
    with engine.connect() as conn:
        result = conn.execute(query, {"code": airport_code})
        return result.fetchall()

def main():
    print("Starting Alert System...")
    
    # Wait for Kafka
    time.sleep(20) 

    consumer = KafkaConsumer(
        'to-alert-system',
        bootstrap_servers=['kafka:9092'],
        auto_offset_reset='earliest',
        enable_auto_commit=True,
        group_id='alert-system-group',
        value_deserializer=lambda x: json.loads(x.decode('utf-8'))
    )

    producer = KafkaProducer(
        bootstrap_servers=['kafka:9092'],
        value_serializer=lambda v: json.dumps(v).encode('utf-8')
    )

    print("Listening on to-alert-system...")

    for message in consumer:
        data = message.value
        print(f"Received message: {data}")
        
        if data.get("type") == "update_completed":
            airport_counts = data.get("airport_counts", {})
            
            for airport, count in airport_counts.items():
                preferences = get_user_preferences(airport)
                
                for pref in preferences:
                    email = pref[0]
                    high = pref[1]
                    low = pref[2]
                    
                    condition = None
                    if high is not None and count >= high:
                        condition = f"Flight count {count} >= High Threshold {high}"
                    elif low is not None and count <= low:
                        condition = f"Flight count {count} <= Low Threshold {low}"
                    
                    if condition:
                        alert_msg = {
                            "email": email,
                            "airport": airport,
                            "condition": condition,
                            "count": count
                        }
                        producer.send('to-notifier', alert_msg)
                        print(f"Alert sent for {email} regarding {airport}: {condition}")
                        
            producer.flush()

if __name__ == "__main__":
    main()
