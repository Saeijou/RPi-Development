import requests
from datetime import datetime
import smtplib
import time
import configparser
import os
from requests.exceptions import RequestException
from urllib3.exceptions import ProtocolError

# Read config
config = configparser.ConfigParser()
config.read(os.path.expanduser('~/Python/.config'))

my_email = config['Email']['sender_email']
password = config['Email']['smtp_password']
port = int(config['Email']['smtp_port'])

MY_LAT = 38.661750  # Your latitude
MY_LONG = -121.269265  # Your longitude

def get_iss_position(max_retries=3, retry_delay=5):
    for attempt in range(max_retries):
        try:
            response = requests.get(url="http://api.open-notify.org/iss-now.json", timeout=10)
            response.raise_for_status()
            data = response.json()
            return float(data["iss_position"]["latitude"]), float(data["iss_position"]["longitude"])
        except (RequestException, ProtocolError) as e:
            if attempt < max_retries - 1:
                print(f"Error fetching ISS position. Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                print(f"Failed to fetch ISS position after {max_retries} attempts. Error: {e}")
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
                print(f"Error fetching sun times. Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                print(f"Failed to fetch sun times after {max_retries} attempts. Error: {e}")
                return None, None

def iss_in_range(iss_latitude, iss_longitude):
    return abs(MY_LAT - iss_latitude) < 5 and abs(MY_LONG - iss_longitude) < 5

def is_dark(sunrise, sunset):
    time_now = datetime.now().hour
    return time_now <= sunrise or time_now >= sunset

def send_email():
    try:
        with smtplib.SMTP("smtp.gmail.com", port, timeout=30) as connection:
            connection.starttls()
            connection.login(user=my_email, password=password)
            connection.sendmail(
                from_addr=my_email,
                to_addrs=config['Email']['receiver_email'],
                msg="Subject:ISS IS ABOVE YOU!!\n\nLOOK UP!"
            )
        print("Email sent successfully")
    except Exception as e:
        print(f"Failed to send email. Error: {e}")

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