#!/bin/bash

# 0.) Use PyEnv to Install 3.7.3

/home/morphs/.pyenv/versions/3.7.3/bin/python3.7 -m venv venv
source ./venv/bin/activate
pip install ./wheels/numpy-1.19.5-cp37-cp37m-linux_armv7l.whl
pip install ./wheels/h5py-2.10.0-cp37-cp37m-linux_armv7l.whl
pip install ./wheels/grpcio-1.32.0-cp37-cp37m-linux_armv7l.whl
cat ./wheels/tensorflow-2.4.0-cp37-cp37m-linux_armv7l.whl.zip* > ./wheels/tensorflow.zip
unzip ./wheels/tensorflow.zip
mv ./tensorflow-2.4.0-cp37-cp37m-linux_armv7l.whl ./wheels/
rm ./wheels/tensorflow.zip
pip install ./wheels/tensorflow-2.4.0-cp37-cp37m-linux_armv7l.whl
pip install ./wheels/sanic-21.6.0-py3-none-any.whl
pip install ./wheels/uvloop-0.15.2-cp37-cp37m-linux_armv7l.whl
pip install ./wheels/httptools-0.2.0-cp37-cp37m-linux_armv7l.whl
pip install ./wheels/websockets-9.1-cp37-cp37m-linux_armv7l.whl
pip install ./wheels/sanic-21.6.0-py3-none-any.whl
pip install ./wheels/Pillow-8.2.0-cp37-cp37m-linux_armv7l.whl
pip install ./wheels/kiwisolver-1.3.1-cp37-cp37m-linux_armv7l.whl
pip install ./wheels/matplotlib-3.4.2-cp37-cp37m-linux_armv7l.whl
pip install ./wheels/numpy-1.21.0-cp37-cp37m-linux_armv7l.whl
pip install tensorflow_hub
pip install redis
pip install pytz