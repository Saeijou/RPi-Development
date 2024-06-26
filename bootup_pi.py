#!/usr/bin/env python3

import os
import subprocess
import time
import logging
import requests
import configparser

# Read config
config = configparser.ConfigParser()
config.read(os.path.expanduser('~/Python/.config'))

logging.basicConfig(filename=config['Paths']['log_file'], level=logging.INFO,
                    format='%(asctime)s:%(levelname)s:%(message)s')

logging.info("Starting script execution...")
time.sleep(30)

script_dir = config['Paths']['scripts_folder']

# Get Zoho email settings from config
access_token = config['Zoho']['access_token']
refresh_token = config['Zoho']['refresh_token']
client_id = config['Zoho']['client_id']
client_secret = config['Zoho']['client_secret']
sender_email = config['Email']['sender_email']
receiver_email = config['Email']['receiver_email']

successful_scripts = []
failed_scripts = []

if not os.path.isdir(script_dir):
    logging.error(f"Directory {script_dir} does not exist.")
else:
    for filename in os.listdir(script_dir):
        if filename.endswith(".py"):
            script_path = os.path.join(script_dir, filename)

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
    for script in successful_scripts:
        report.append(f"  - {script}")
        logging.info(f"Successfully ran script: {script}")
    report.append("")  # Add an empty line

if failed_scripts:
    report.append("Failed Scripts:")
    for script in failed_scripts:
        report.append(f"  - {script}")
    report.append("")  # Add an empty line
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
        # Update the config file with the new access token
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

def send_email(report):
    global access_token
    account_id = get_account_id()
    if not account_id:
        return

    headers = {
        'Authorization': f'Zoho-oauthtoken {access_token}',
        'Content-Type': 'application/json'
    }

    # Join the report lines with proper line breaks
    email_content = '\n'.join(report)

    email_data = {
        'fromAddress': sender_email,
        'toAddress': receiver_email,
        'subject': 'Script Execution Report',
        'content': email_content
    }

    response = requests.post(f'https://mail.zoho.com/api/accounts/{account_id}/messages', headers=headers, json=email_data)

    if response.status_code in [401, 404]:  # Unauthorized or Not Found
        if refresh_access_token():
            headers['Authorization'] = f'Zoho-oauthtoken {access_token}'
            response = requests.post(f'https://mail.zoho.com/api/accounts/{account_id}/messages', headers=headers, json=email_data)

    if response.status_code == 200:
        logging.info("Email report sent successfully.")
    else:
        logging.error(f"Failed to send email: {response.content}")

if report:
    try:
        send_email(report)
    except Exception as e:
        logging.error(f"Failed to send email report: {str(e)}")
else:
    logging.info("No scripts were executed, no email report to send.")

logging.info("Script execution completed.")