import requests
from datetime import datetime
import smtplib
import time
import configparser

# Read config
config = configparser.ConfigParser()
config.read('/home/pi/Python/.config')

my_email = config['Email']['sender_email']
password = config['Email']['smtp_password']
port = int(config['Email']['smtp_port'])

MY_LAT = 38.661750 # Your latitude
MY_LONG = -121.269265 # Your longitude

response = requests.get(url="http://api.open-notify.org/iss-now.json")
response.raise_for_status()
data = response.json()

iss_latitude = float(data["iss_position"]["latitude"])
iss_longitude = float(data["iss_position"]["longitude"])

#Your position is within +5 or -5 degrees of the ISS position.

parameters = {
    "lat": MY_LAT,
    "lng": MY_LONG,
    "formatted": 0,
}

response = requests.get("https://api.sunrise-sunset.org/json", params=parameters)
response.raise_for_status()
data = response.json()
sunrise = int(data["results"]["sunrise"].split("T")[1].split(":")[0])
sunset = int(data["results"]["sunset"].split("T")[1].split(":")[0])

time_now = datetime.now().hour


def iss_in_range():
    if abs(MY_LAT - iss_latitude) < 5 and abs(MY_LONG - iss_longitude)  < 5:
        return True
    else:
        return False

def is_dark():
    if time_now <= sunset or time_now >= sunset:
        return True
    else:
        return False

while True:
    if iss_in_range() and is_dark():
        with smtplib.SMTP("smtp.gmail.com", port) as connection:
            connection.starttls()
            connection.login(user=my_email, password=password)
            connection.sendmail(
                from_addr=my_email,
                to_addrs=config['Email']['receiver_email'],
                msg=f"Subject:ISS IS ABOVE YOU!!\n\n LOOK UP!"
            )
        time.sleep(60)
    else:
        time.sleep(60)



