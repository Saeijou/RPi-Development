import requests
from datetime import datetime, timedelta
import time
import configparser
import os
import logging
from requests.exceptions import RequestException

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

# Weather API settings
WEATHER_API_KEY = config['Weather']['api_key']
LATITUDE = 38.6513  # Fair Oaks, CA latitude
LONGITUDE = -121.2711  # Fair Oaks, CA longitude

def refresh_access_token():
    global access_token
    try:
        response = requests.post('https://accounts.zoho.com/oauth/v2/token', data={
            'grant_type': 'refresh_token',
            'client_id': client_id,
            'client_secret': client_secret,
            'refresh_token': refresh_token
        })
        response.raise_for_status()
        access_token = response.json().get('access_token')
        logging.info("Access token refreshed successfully.")
        config['Zoho']['access_token'] = access_token
        with open(os.path.expanduser('~/Python/.config'), 'w') as configfile:
            config.write(configfile)
        return True
    except RequestException as e:
        logging.error(f"Failed to refresh access token: {e}")
        return False

def get_account_id():
    global access_token
    headers = {'Authorization': f'Zoho-oauthtoken {access_token}'}
    try:
        response = requests.get('https://mail.zoho.com/api/accounts', headers=headers)
        response.raise_for_status()
        accounts = response.json().get('data')
        if accounts:
            return accounts[0].get('accountId')
        else:
            logging.error('No accounts found')
            return None
    except RequestException as e:
        if response.status_code in [401, 404]:
            if refresh_access_token():
                return get_account_id()
            else:
                return None
        logging.error(f"Failed to get accounts: {e}")
        return None

def send_email(aqi):
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
        'subject': 'Air Quality Alert for Fair Oaks, CA',
        'content': f'The current Air Quality Index (AQI) in Fair Oaks, CA is {aqi}, which is considered unhealthy. Please take necessary precautions.'
    }

    try:
        response = requests.post(f'https://mail.zoho.com/api/accounts/{account_id}/messages', headers=headers, json=email_data)
        response.raise_for_status()
        logging.info("Air quality alert email sent successfully.")
    except RequestException as e:
        if response.status_code in [401, 404]:
            if refresh_access_token():
                send_email(aqi)
            else:
                logging.error(f"Failed to send email: {e}")
        else:
            logging.error(f"Failed to send email: {e}")

def get_air_quality():
    url = f"http://api.openweathermap.org/data/2.5/air_pollution?lat={LATITUDE}&lon={LONGITUDE}&appid={WEATHER_API_KEY}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        return data['list'][0]['main']['aqi'] * 20  # Convert to AQI scale (0-500)
    except RequestException as e:
        logging.error(f"Error fetching air quality data: {e}")
        return None

def main():
    last_alert_time = None
    while True:
        if not last_alert_time or datetime.now() - last_alert_time > timedelta(hours=12):
            aqi = get_air_quality()
            if aqi is not None and aqi > 100:  # AQI > 100 is considered unhealthy
                send_email(aqi)
                last_alert_time = datetime.now()
                logging.info(f"Alert sent. AQI: {aqi}")
            else:
                logging.info(f"Current AQI: {aqi}")
        
        time.sleep(3600)  # Sleep for 1 hour

if __name__ == "__main__":
    main()