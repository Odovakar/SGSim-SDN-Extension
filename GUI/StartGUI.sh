#!/bin/bash
cd /home/ubuntu/SGS/GUI
xterm -geometry 90x30-10+10 -T "DDOS Detection" -e "./DDOSDetection.sh" &
cd /home/ubuntu/SGS/GUI/PHPserver/
xterm  -geometry 90x30-560+10 -T "PHP Server" -e "php -S localhost:8000" &
