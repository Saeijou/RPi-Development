#!/usr/bin/env python3

import subprocess
import time
import logging
import requests
import configparser
import os
import socket
import re
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import threading

# Read config
config = configparser.ConfigParser()
config.read(os.path.expanduser('~/Python/.config'))

# Setup logging
logging.basicConfig(filename=config['Paths']['log_file'], level=logging.INFO,
                    format='%(asctime)s:%(levelname)s:%(message)s')

# Zoho email settings
access_token = config['Zoho']['access_token']
refresh_token = config['Zoho']['refresh_token']
client_id = config['Zoho']['client_id']
client_secret = config['Zoho']['client_secret']
sender_email = config['Email']['sender_email']
receiver_email = config['Email']['receiver_email']

# Log file paths
main_log_file = config['Paths']['log_file']
bot_log_file = config['Paths']['bot_log_file']

def refresh_access_token():
    global access_token
    response = requests.post('https://accounts.zoho.com/oauth/v2/token', data={
        'grant_type': 'refresh_token',
        'client_id': client_id,
        'client_secret': client_secret,
        'refresh_token': refresh_token
    })
    if response.status_code == 200:
        access_token = response.json().get('access_token')
        logging.info("Access token refreshed successfully.")
        config['Zoho']['access_token'] = access_token
        with open(os.path.expanduser('~/Python/.config'), 'w') as configfile:
            config.write(configfile)
        return True
    else:
        logging.error(f"Failed to refresh access token: {response.content}")
        return False

def get_account_id():
    global access_token
    headers = {
        'Authorization': f'Zoho-oauthtoken {access_token}'
    }
    response = requests.get('https://mail.zoho.com/api/accounts', headers=headers)
    if response.status_code == 200:
        accounts = response.json().get('data')
        if accounts:
            return accounts[0].get('accountId')
        else:
            logging.error('No accounts found')
            return None
    elif response.status_code in [401, 404]:  # Unauthorized or Not Found
        if refresh_access_token():
            return get_account_id()  # Retry after refreshing
        else:
            return None
    else:
        logging.error(f"Failed to get accounts: {response.content}")
        return None

def send_email(subject, content):
    global access_token
    account_id = get_account_id()
    if not account_id:
        return

    headers = {
        'Authorization': f'Zoho-oauthtoken {access_token}',
        'Content-Type': 'application/json'
    }

    email_data = {
        'fromAddress': sender_email,
        'toAddress': receiver_email,
        'subject': subject,
        'content': content
    }

    response = requests.post(f'https://mail.zoho.com/api/accounts/{account_id}/messages', headers=headers, json=email_data)

    if response.status_code in [401, 404]:  # Unauthorized or Not Found
        if refresh_access_token():
            headers['Authorization'] = f'Zoho-oauthtoken {access_token}'
            response = requests.post(f'https://mail.zoho.com/api/accounts/{account_id}/messages', headers=headers, json=email_data)

    if response.status_code == 200:
        logging.info(f"Email sent successfully: {subject}")
    else:
        logging.error(f"Failed to send email: {response.content}")

def get_ups_data():
    try:
        output = subprocess.check_output(["upsc", "ups"]).decode()
        data = {}
        for line in output.split('\n'):
            if ':' in line:
                key, value = line.split(':', 1)
                data[key.strip()] = value.strip()
        return data
    except subprocess.CalledProcessError as e:
        logging.error(f"Error running upsc command: {e}")
        return None

def check_internet():
    hosts = ['google.com', '1.1.1.1']
    for host in hosts:
        try:
            socket.create_connection((host, 80), timeout=5)
        except OSError:
            pass
        else:
            return True
    return False

class LogFileHandler(FileSystemEventHandler):
    def __init__(self, log_file):
        self.log_file = log_file
        self.last_position = 0

    def on_modified(self, event):
        if event.src_path == self.log_file:
            self.check_for_errors()

    def check_for_errors(self):
        with open(self.log_file, 'r') as file:
            file.seek(self.last_position)
            new_lines = file.readlines()
            self.last_position = file.tell()

        for line in new_lines:
            if re.search(r'ERROR', line, re.IGNORECASE):
                log_name = 'Main' if self.log_file == main_log_file else 'Bot'
                send_email(f"{log_name} Log Error Alert", f"An error was detected in the {log_name} log file:\n\n{line}")

def setup_log_monitoring():
    main_handler = LogFileHandler(main_log_file)
    bot_handler = LogFileHandler(bot_log_file)

    observer = Observer()
    observer.schedule(main_handler, path=os.path.dirname(main_log_file), recursive=False)
    observer.schedule(bot_handler, path=os.path.dirname(bot_log_file), recursive=False)
    observer.start()

    return observer, main_handler, bot_handler

def continuous_error_check(main_handler, bot_handler):
    while True:
        main_handler.check_for_errors()
        bot_handler.check_for_errors()
        time.sleep(60)  # Check for errors every minute

def monitor_power_and_internet():
    power_out = False
    internet_out = False
    battery_low_alert_sent = False
    power_out_start = None
    internet_out_start = None
    last_known_power_status = True
    last_known_internet_status = True

    while True:
        ups_data = get_ups_data()
        internet_status = check_internet()

        if ups_data is not None:
            input_voltage = float(ups_data.get('input.voltage', '0'))
            battery_charge = float(ups_data.get('battery.charge', '100'))

            current_power_status = input_voltage > 0

            # Check for power status change
            if current_power_status != last_known_power_status:
                if not current_power_status:  # Power just went out
                    power_out = True
                    power_out_start = time.time()
                    logging.info("Power outage detected")
                    if internet_status:  # If internet is still up, send email
                        send_email("Power Outage Alert", "Power is out. Input voltage has dropped to 0.")
                else:  # Power just came back
                    power_out = False
                    power_outage_duration = time.time() - power_out_start
                    logging.info(f"Power restored after {power_outage_duration:.2f} seconds")
                    if internet_status:  # If internet is up, send email
                        send_email("Power Restored", f"Power has been restored after {power_outage_duration:.2f} seconds")
                    power_out_start = None
                    battery_low_alert_sent = False
                last_known_power_status = current_power_status

            # Check for low battery during power outage
            if power_out and battery_charge < 40 and not battery_low_alert_sent and internet_status:
                send_email("UPS Battery Low", f"UPS battery charge is below 40%. Current charge: {battery_charge}%")
                battery_low_alert_sent = True

        # Check for internet status change
        if internet_status != last_known_internet_status:
            if not internet_status:  # Internet just went out
                internet_out = True
                internet_out_start = time.time()
                logging.info("Internet outage detected")
            else:  # Internet just came back
                internet_out = False
                internet_outage_duration = time.time() - internet_out_start
                logging.info(f"Internet restored after {internet_outage_duration:.2f} seconds")
                if not power_out:
                    send_email("Internet Restored", f"Internet has been restored after {internet_outage_duration:.2f} seconds")
                else:
                    send_email("Internet Restored, Power Still Out", 
                               f"Internet connection has been restored after {internet_outage_duration:.2f} seconds, but power is still out.")
                internet_out_start = None
            last_known_internet_status = internet_status

        # If both power and internet just came back, send a combined status email
        if not power_out and not internet_out and power_out_start is None and internet_out_start is None \
           and (not last_known_power_status or not last_known_internet_status):
            subject = "Status Update: Power and Internet"
            content = "Both power and internet have been restored.\n"
            if not last_known_power_status:
                content += f"Power outage duration: {(time.time() - power_out_start):.2f} seconds\n"
            if not last_known_internet_status:
                content += f"Internet outage duration: {(time.time() - internet_out_start):.2f} seconds"
            send_email(subject, content)

        time.sleep(60)  # Wait for 1 minute before next check

if __name__ == "__main__":
    logging.info("Starting power, internet, and log monitoring script")
    try:
        log_observer, main_handler, bot_handler = setup_log_monitoring()
        
        # Start the continuous error checking in a separate thread
        error_check_thread = threading.Thread(target=continuous_error_check, args=(main_handler, bot_handler))
        error_check_thread.daemon = True
        error_check_thread.start()

        monitor_power_and_internet()
    except Exception as e:
        logging.error(f"Unexpected error in monitoring script: {e}")
    finally:
        log_observer.stop()
        log_observer.join()