import json
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from kafka import KafkaConsumer

# Gmail SMTP Configuration
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 465  # SSL port
SMTP_USER = "ppp.paolapappalardo@gmail.com"
SMTP_PASSWORD = "zklb yavk fqfm wnqf"  # password per app

def send_email(to_email, subject, body):
    try:
        # Create message
        msg = MIMEMultipart()
        msg['From'] = SMTP_USER
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        # Connect with SSL
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_USER, to_email, msg.as_string())

        print(f"Email inviata a {to_email}")

    except Exception as e:
        print(f"Failed to send email: {e}")

def main():
    print("Starting Alert Notifier System...")
    
    # Wait for Kafka
    time.sleep(20)

    consumer = KafkaConsumer(
        'to-notifier',
        bootstrap_servers=['kafka:9092'],
        auto_offset_reset='earliest',
        enable_auto_commit=True,
        group_id='alert-notifier-group',
        value_deserializer=lambda x: json.loads(x.decode('utf-8'))
    )

    print("Listening on to-notifier...")

    for message in consumer:
        data = message.value
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

if __name__ == "__main__":
    main()