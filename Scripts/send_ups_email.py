import smtplib
from email.mime.text import MIMEText
import sys
import subprocess
import configparser
import os

# Read config
config = configparser.ConfigParser()
config.read(os.path.expanduser('~/Python/.config'))

# Get email settings from config
sender_email = config['Email']['sender_email']
receiver_email = config['Email']['receiver_email']
smtp_server = config['Email']['smtp_server']
smtp_port = int(config['Email']['smtp_port'])
smtp_username = config['Email']['smtp_username']
smtp_password = config['Email']['smtp_password']

def get_ups_status():
    try:
        result = subprocess.run(['upsc', 'ups'], capture_output=True, text=True)
        return result.stdout
    except Exception as e:
        return f"Error getting UPS status: {str(e)}"

def send_email(subject, body):
    ups_status = get_ups_status()
    full_body = f"{body}\n\nUPS Status:\n{ups_status}"
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = sender_email
    msg['To'] = receiver_email

    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.starttls()
        server.login(smtp_username, smtp_password)
        server.send_message(msg)

if __name__ == "__main__":
    event = sys.argv[1]
    if event == "onbattery":
        send_email("UPS Power Alert", "Power outage detected. UPS is now on battery.")
    elif event == "online":
        send_email("UPS Power Alert", "Power has been restored. UPS is back on mains power.")