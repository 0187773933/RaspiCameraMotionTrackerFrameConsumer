#!/bin/bash
APP_NAME="rpmt-frame-consumer"
sudo docker rm $APP_NAME -f || echo "failed to remove existing ssh server"
sudo docker build -t $APP_NAME .