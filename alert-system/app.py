import json
import time
import os
from confluent_kafka import Consumer, Producer, KafkaError
from sqlalchemy import create_engine, text

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://user:password@postgres:5432/datadb")
engine = create_engine(DATABASE_URL)

def get_user_preferences(airport_code):
    
    query = text("""
        SELECT user_email, high_value, low_value 
        FROM user_airports 
        WHERE airport_code = :code
    """)
    with engine.connect() as conn:
        result = conn.execute(query, {"code": airport_code})
        return result.fetchall()

def delivery_report(err, msg):
    """Callback to verify production"""
    if err:
        print(f"Failed to produce to {msg.topic()}: {err}")
    else:
        print(f"Alert sent to {msg.topic()} at offset {msg.offset()}")

def main():
    print("Starting Alert System...")
    
    # sleep per kafka (dettagliare nella documentazione)
    time.sleep(20) 

    consumer_config = {
        'bootstrap.servers': 'kafka:9092',
        'group.id': 'alert-system-group',
        'auto.offset.reset': 'earliest',
        'enable.auto.commit': False
    }

    producer_config = {
        'bootstrap.servers': 'kafka:9092',
        'acks': 'all',
        'retries': 5,
        'batch.size': 32768,
        'linger.ms': 20
    }

    consumer = Consumer(consumer_config)
    producer = Producer(producer_config)

    consumer.subscribe(['to-alert-system'])
    print("Listening on to-alert-system...")

    try:
        while True:
            msg = consumer.poll(1.0)

            if msg is None:
                continue
            
            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    continue
                else:
                    print(f"Consumer error: {msg.error()}")
                    continue

            try:
                data = json.loads(msg.value().decode('utf-8'))
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
                                producer.produce(
                                    'to-notifier', 
                                    json.dumps(alert_msg).encode('utf-8'),
                                    callback=delivery_report
                                )
                                producer.poll(0)
                                print(f"Alert queued for {email} regarding {airport}: {condition}")
                    
                    producer.flush()
                    consumer.commit(asynchronous=False)
                    
            except Exception as e:
                print(f"Error processing message: {e}")

    except KeyboardInterrupt:
        print("Interrupted by user")
    finally:
        consumer.close()

if __name__ == "__main__":
    main()