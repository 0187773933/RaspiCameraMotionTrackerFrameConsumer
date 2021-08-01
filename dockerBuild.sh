#!/bin/bash
# APP_NAME="rpmt-frame-consumer"
APP_NAME="xp6qhg9fmuolztbd2ixwdbtd1/raspi-motion-tracker-frame-consumer:arm32test"
# sudo docker rm $APP_NAME -f || echo "failed to remove existing ssh server"
sudo docker build --squash -t $APP_NAME .