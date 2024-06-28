#!/bin/bash
source /home/pi/Python/myenv/bin/activate
python /home/pi/Python/bootup_pi.py
deactivate

#add to crontab -e
#@reboot /home/pi/Python/run_bot.sh >> /home/pi/Python/bot_cron.log 2>&1