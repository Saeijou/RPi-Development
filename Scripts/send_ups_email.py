import requests
import sys
import subprocess
import configparser
import os
import logging

# Read config
config = configparser.ConfigParser()
config.read(os.path.expanduser('~/Python/.config'))

# Logging setup
logging.basicConfig(filename=config['Paths']['log_file'], level=logging.INFO,
                    format='%(asctime)s:%(levelname)s:%(message)s')

# Zoho email settings
access_token = config['Zoho']['access_token']
refresh_token = config['Zoho']['refresh_token']
client_id = config['Zoho']['client_id']
client_secret = config['Zoho']['client_secret']
sender_email = config['Email']['sender_email']
receiver_email = config['Email']['receiver_email']

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
    else:
        logging.error(f"Failed to refresh access token: {response.content}")

def get_account_id():
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
    else:
        logging.error(f"Failed to get accounts: {response.content}")
        return None

def get_ups_status():
    try:
        result = subprocess.run(['upsc', 'ups'], capture_output=True, text=True)
        return result.stdout
    except Exception as e:
        return f"Error getting UPS status: {str(e)}"

def send_email(subject, body):
    ups_status = get_ups_status()
    full_body = f"{body}\n\nUPS Status:\n{ups_status}"

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
        'content': full_body
    }

    response = requests.post(f'https://mail.zoho.com/api/accounts/{account_id}/messages', headers=headers, json=email_data)

    if response.status_code == 401:  # Unauthorized, possibly due to expired access token
        logging.info("Access token expired, refreshing...")
        refresh_access_token()
        headers['Authorization'] = f'Zoho-oauthtoken {access_token}'
        response = requests.post(f'https://mail.zoho.com/api/accounts/{account_id}/messages', headers=headers, json=email_data)

    if response.status_code == 200:
        logging.info("Email sent successfully.")
    else:
        logging.error(f"Failed to send email: {response.content}")

if __name__ == "__main__":
    event = sys.argv[1]
    if event == "onbattery":
        send_email("UPS Power Alert", "Power outage detected. UPS is now on battery.")
    elif event == "online":
        send_email("UPS Power Alert", "Power has been restored. UPS is back on mains power.")