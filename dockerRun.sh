#!/bin/bash
APP_NAME="rpmt-frame-consumer"
sudo docker rm $APP_NAME || echo ""
IMAGE_NAME="xp6qhg9fmuolztbd2ixwdbtd1/raspi-motion-tracker-frame-consumer:arm32test"
id=$(sudo docker run -dit \
--name $APP_NAME \
-p 9379:9379 \
-v $(pwd)/config.json:/home/morphs/FRAME_CONSUMER/config.json:ro
$IMAGE_NAME config.json)
sudo docker logs -f $id


# -v ${PWD}/PythonVersion/built_wheels:/home/morphs/built_wheels \
# -v /tmp/.X11-unix:/tmp/.X11-unix \
# --device "/dev/video0:/dev/video0" \

# sudo docker exec -it 4ba44b079ac9 /bin/bash


# sudo docker run -it --rm  --entrypoint "/bin/bash" xp6qhg9fmuolztbd2ixwdbtd1/raspi-motion-tracker-frame-consumer:arm32