#!/usr/bin/env python3

import os
import subprocess
import time
import smtplib
from email.mime.text import MIMEText
import logging
import socket
import configparser

logging.basicConfig(filename='/home/pi/Python/Scripts/script_runner.log', level=logging.INFO,
                    format='%(asctime)s:%(levelname)s:%(message)s')

logging.info("Starting script execution...")
time.sleep(30)

script_dir = "/home/pi/Python/Scripts"

# Read config
config = configparser.ConfigParser()
config.read('/home/pi/Python/.config')

# Get email settings from config
sender_email = config['Email']['sender_email']
receiver_email = config['Email']['receiver_email']
smtp_server = config['Email']['smtp_server']
smtp_port = int(config['Email']['smtp_port'])
smtp_username = config['Email']['smtp_username']
smtp_password = config['Email']['smtp_password']

successful_scripts = []
failed_scripts = []

if not os.path.isdir(script_dir):
    logging.error(f"Directory {script_dir} does not exist.")
else:
    for filename in os.listdir(script_dir):
        if filename.endswith(".py"):
            script_path = os.path.join(script_dir, filename)
            logging.info(f"Running script: {script_path}")

            try:
                process = subprocess.Popen(["python3", script_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                timeout = 30
                start_time = time.time()
                while time.time() - start_time < timeout:
                    return_code = process.poll()
                    if return_code is not None:
                        stdout, stderr = process.communicate()
                        if return_code == 0:
                            successful_scripts.append(script_path)
                        else:
                            logging.error(f"{script_path} encountered an error. Error: {stderr.decode()}")
                            failed_scripts.append(script_path)
                        break
                else:
                    successful_scripts.append(script_path)
            except Exception as e:
                logging.error(f"Error running {script_path}: {e}")
                failed_scripts.append(script_path)

report = []
if successful_scripts:
    report.append("Successfully Ran Scripts:")
    report.extend(successful_scripts)
if failed_scripts:
    report.append("\nFailed Scripts:")
    report.extend(failed_scripts)

if report:
    try:
        message = MIMEText("\n".join(report))
        message["Subject"] = "Script Execution Report"
        message["From"] = sender_email
        message["To"] = receiver_email
        
        socket.setdefaulttimeout(30)
        
        server = smtplib.SMTP(smtp_server, smtp_port, timeout=30)
        server.starttls()
        server.login(smtp_username, smtp_password)
        server.send_message(message)
        server.quit()
        logging.info("Email report sent successfully.")
    except Exception as e:
        logging.error(f"Failed to send email report: {str(e)}")
else:
    logging.info("No scripts were executed, no email report to send.")

logging.info("Script execution completed.")