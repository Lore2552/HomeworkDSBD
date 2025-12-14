import json
import time
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from confluent_kafka import Consumer, KafkaError

# Gmail SMTP configurazione
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 465  # porta SSL
SMTP_USER = "ppp.paolapappalardo@gmail.com"
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD")  # password per app

def send_email(to_email, subject, body):
    try:
        # creazione mess
        msg = MIMEMultipart()
        msg['From'] = SMTP_USER
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        # connessione con ssl
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_USER, to_email, msg.as_string())

        print(f"Email inviata a {to_email}")

    except Exception as e:
        print(f"Failed to send email: {e}")

def main():
    print("Starting Alert Notifier System...")
    
    # sleep per kafka (dettagliare nella documentazione)
    time.sleep(20)

    consumer_config = {
        'bootstrap.servers': 'kafka:9092',
        'group.id': 'alert-notifier-group',
        'auto.offset.reset': 'earliest',
        'enable.auto.commit': False
    }

    consumer = Consumer(consumer_config)
    consumer.subscribe(['to-notifier'])

    print("Listening on to-notifier...")

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
                print(f"Received alert: {data}")
                
                email = data.get("email")
                airport = data.get("airport")
                condition = data.get("condition")
                
                if email and airport and condition:
                    subject = f"Flight Alert for {airport}"
                    body = (
                        f"Alert generated for airport: {airport}\n"
                        f"Condition triggered: {condition}"
                    )
                    send_email(email, subject, body)
                
                consumer.commit(asynchronous=False)
                
            except Exception as e:
                print(f"Error processing message: {e}")
    finally:
        consumer.close()

if __name__ == "__main__":
    main()