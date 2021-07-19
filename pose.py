
import time
import tensorflow as tf
import numpy as np
from matplotlib import pyplot as plt
from matplotlib.collections import LineCollection
import matplotlib.patches as patches
from pprint import pprint
import tensorflow_hub as hub

# Load the input image.
# image_path = '/home/morphs/DOCKER_IMAGES/RaspiMotionAlarm/PythonMotionFrameConsumer/dataset_original/awake/096.jpeg'
# image = tf.io.read_file(image_path)
# image = tf.compat.v1.image.decode_jpeg(image)
# image = tf.expand_dims(image, axis=0)
# # Resize and pad the image to keep the aspect ratio and fit the expected size.
# image = tf.cast(tf.image.resize_with_pad(image, 192, 192), dtype=tf.int32)

# # Download the model from TF Hub.
# model = hub.load("https://tfhub.dev/google/movenet/singlepose/lightning/3")
# movenet = model.signatures['serving_default']

# # Run model inference.
# outputs = movenet( image )
# # Output is a [1, 1, 17, 3] tensor.
# keypoints = outputs['output_0']


async def process_opencv_frame( json_data ):
	print( "sleeping for 5 seconds" )
	print( json_data )
	time.sleep( 5 )