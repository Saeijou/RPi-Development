import requests
from datetime import datetime
import time
import configparser
import os
import logging
from requests.exceptions import RequestException
from urllib3.exceptions import ProtocolError

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

MY_LAT = 38.661750  # Your latitude
MY_LONG = -121.269265  # Your longitude

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

def send_email():
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
        'subject': 'ISS IS ABOVE YOU!!',
        'content': 'LOOK UP!'
    }

    response = requests.post(f'https://mail.zoho.com/api/accounts/{account_id}/messages', headers=headers, json=email_data)

    if response.status_code in [401, 404]:  # Unauthorized or Not Found
        if refresh_access_token():
            headers['Authorization'] = f'Zoho-oauthtoken {access_token}'
            response = requests.post(f'https://mail.zoho.com/api/accounts/{account_id}/messages', headers=headers, json=email_data)

    if response.status_code == 200:
        logging.info("Email sent successfully.")
    else:
        logging.error(f"Failed to send email: {response.content}")

def get_iss_position(max_retries=3, retry_delay=5):
    for attempt in range(max_retries):
        try:
            response = requests.get(url="http://api.open-notify.org/iss-now.json", timeout=10)
            response.raise_for_status()
            data = response.json()
            return float(data["iss_position"]["latitude"]), float(data["iss_position"]["longitude"])
        except (RequestException, ProtocolError) as e:
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
            else:
                logging.error(f"Failed to fetch ISS position after {max_retries} attempts. Error: {e}")
                return None, None

def get_sun_times(max_retries=3, retry_delay=5):
    parameters = {
        "lat": MY_LAT,
        "lng": MY_LONG,
        "formatted": 0,
    }
    for attempt in range(max_retries):
        try:
            response = requests.get("https://api.sunrise-sunset.org/json", params=parameters, timeout=10)
            response.raise_for_status()
            data = response.json()
            sunrise = int(data["results"]["sunrise"].split("T")[1].split(":")[0])
            sunset = int(data["results"]["sunset"].split("T")[1].split(":")[0])
            return sunrise, sunset
        except (RequestException, ProtocolError) as e:
            if attempt < max_retries - 1:
                logging.warning(f"Error fetching sun times. Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                logging.error(f"Failed to fetch sun times after {max_retries} attempts. Error: {e}")
                return None, None

def iss_in_range(iss_latitude, iss_longitude):
    return abs(MY_LAT - iss_latitude) < 5 and abs(MY_LONG - iss_longitude) < 5

def is_dark(sunrise, sunset):
    time_now = datetime.now().hour
    return time_now <= sunrise or time_now >= sunset

def main():
    while True:
        iss_latitude, iss_longitude = get_iss_position()
        if iss_latitude is None or iss_longitude is None:
            time.sleep(60)
            continue

        sunrise, sunset = get_sun_times()
        if sunrise is None or sunset is None:
            time.sleep(60)
            continue

        if iss_in_range(iss_latitude, iss_longitude) and is_dark(sunrise, sunset):
            send_email()

        time.sleep(60)

if __name__ == "__main__":
    main()