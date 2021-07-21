#!/bin/bash
APP_NAME="rpmt-frame-consumer"
sudo docker run -dit \
--name $APP_NAME \
-p 9379:9379 \
$APP_NAME


# -v ${PWD}/PythonVersion/built_wheels:/home/morphs/built_wheels \
# -v /tmp/.X11-unix:/tmp/.X11-unix \
# --device "/dev/video0:/dev/video0" \

# sudo docker exec -it 4ba44b079ac9 /bin/bash