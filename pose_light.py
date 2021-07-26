import tensorflow as tf
import numpy as np
from matplotlib import pyplot as plt
from matplotlib.collections import LineCollection
import matplotlib.patches as patches
from pprint import pprint

# import utils
import base64

# https://blog.tensorflow.org/2021/05/next-generation-pose-detection-with-movenet-and-tensorflowjs.html
# https://tfhub.dev/google/lite-model/movenet/singlepose/lightning/3
# https://github.com/tensorflow/tfjs-models/tree/master/pose-detection/src/movenet
# https://github.com/tensorflow/hub/tree/master/examples/colab
# https://colab.research.google.com/github/tensorflow/hub/blob/master/examples/colab/movenet.ipynb

# https://www.tensorflow.org/hub/tutorials/movenet

# Initialize the TFLite interpreter
interpreter = tf.lite.Interpreter( model_path="single_pose_lightning_v3.tflite" )
interpreter.allocate_tensors()

# https://raw.githubusercontent.com/tensorflow/hub/master/examples/colab/movenet.ipynb
def draw_prediction_on_image( image, keypoints_with_scores, crop_region=None, close_figure=False , output_image_height = None ):
	height, width, channel = image.shape
	aspect_ratio = float(width) / height
	fig, ax = plt.subplots(figsize=(12 * aspect_ratio, 12))
	# To remove the huge white borders
	fig.tight_layout(pad=0)
	ax.margins(0)
	ax.set_yticklabels([])
	ax.set_xticklabels([])
	plt.axis('off')
	im = ax.imshow(image)
	line_segments = LineCollection([], linewidths=(4), linestyle='solid')
	ax.add_collection(line_segments)
	# Turn off tick labels
	scat = ax.scatter([], [], s=60, color='#FF1493', zorder=3)
	(keypoint_locs, keypoint_edges, edge_colors) = _keypoints_and_edges_for_display( keypoints_with_scores , height , width )
	line_segments.set_segments( keypoint_edges )
	line_segments.set_color( edge_colors )
	if keypoint_edges.shape[0]:
		line_segments.set_segments(keypoint_edges)
		line_segments.set_color(edge_colors)
	if keypoint_locs.shape[0]:
		scat.set_offsets(keypoint_locs)
	if crop_region is not None:
		xmin = max(crop_region['x_min'] * width, 0.0)
		ymin = max(crop_region['y_min'] * height, 0.0)
		rec_width = min(crop_region['x_max'], 0.99) * width - xmin
		rec_height = min(crop_region['y_max'], 0.99) * height - ymin
		rect = patches.Rectangle( ( xmin , ymin ) , rec_width , rec_height , linewidth=1 ,edgecolor='b' ,facecolor='none' )
		ax.add_patch( rect )
	fig.canvas.draw()
	image_from_plot = np.frombuffer(fig.canvas.tostring_rgb(), dtype=np.uint8)
	image_from_plot = image_from_plot.reshape( fig.canvas.get_width_height()[::-1] + (3,) )
	plt.close(fig)
	if output_image_height is not None:
		output_image_width = int(output_image_height / height * width)
		image_from_plot = cv2.resize( image_from_plot, dsize=(output_image_width, output_image_height), interpolation=cv2.INTER_CUBIC)
	return image_from_plot

def movenet( input_image ):
	input_image = tf.cast( input_image , dtype=tf.float32 )
	input_details = interpreter.get_input_details()
	output_details = interpreter.get_output_details()
	interpreter.set_tensor( input_details[0]['index'] , input_image.numpy() )
	interpreter.invoke()
	keypoints_with_scores = interpreter.get_tensor( output_details[0]['index'] )
	return keypoints_with_scores


def run_inference( image_path ):
	image = tf.io.read_file( image_path )
	image = tf.compat.v1.image.decode_jpeg( image )
	input_image = tf.expand_dims( image , axis=0 )
	input_image = tf.image.resize_with_pad( input_image , 192 , 192 )
	keypoint_with_scores = movenet( input_image )
	print( keypoint_with_scores )
	display_image = tf.expand_dims( image , axis=0 )
	display_image = tf.cast( tf.image.resize_with_pad( display_image , 500 , 250 ) , dtype=tf.int32 )
	#output_overlay = draw_prediction_on_image( np.squeeze( display_image.numpy() , axis=0 ) , keypoint_with_scores )
	plt.figure( figsize = ( 5 , 5 ) )
	# plt.imshow( output_overlay )
	# plt.savefig( 'test.jpg' )
	# _ = plt.axis( 'off' )

def process_image_file( image_path ):
	image = tf.io.read_file( image_path )
	image = tf.compat.v1.image.decode_jpeg( image )
	image = tf.expand_dims( image , axis=0 )
	# Resize and pad the image to keep the aspect ratio and fit the expected size.
	image = tf.image.resize_with_pad( image , 192 , 192 )
	# TF Lite format expects tensor type of float32.
	input_image = tf.cast( image , dtype=tf.float32 )
	input_details = interpreter.get_input_details()
	output_details = interpreter.get_output_details()
	interpreter.set_tensor( input_details[0]['index'] , input_image.numpy() )
	interpreter.invoke()
	pprint( type( output_details ) )
	# Output is a [1, 1, 17, 3] numpy array.
	keypoints_with_scores = interpreter.get_tensor( output_details[0]['index'] )
	print( keypoints_with_scores )

def OnMotionFrame( frame ):
	print( "here in on motion frame callback" )
	print( frame )


# process_image_file( '/home/morphs/DOCKER_IMAGES/RaspiMotionAlarm/PythonMotionFrameConsumer/dataset_original/awake/096.jpeg' )
# print( "\n" )
# process_image_file( '/home/morphs/DOCKER_IMAGES/RaspiMotionAlarm/PythonMotionFrameConsumer/dataset_original/asleep/019.jpeg' )
# run_inference( '/home/morphs/DOCKER_IMAGES/RaspiMotionAlarm/PythonMotionFrameConsumer/dataset_original/awake/324.jpeg' )

# https://storage.googleapis.com/movenet/MoveNet.SinglePose%20Model%20Card.pdf

async def process_opencv_frame( json_data ):
	try:
		# print( f"\nProcessing Frame --> SinglePoseLightningv3.tflite( {len( json_data['frame_buffer_b64_string'] )} )" )
		image_data = base64.b64decode( json_data['frame_buffer_b64_string'] )
		image = tf.image.decode_image( image_data , channels=3 )
		image = tf.expand_dims( image , axis=0 )
		image = tf.image.resize_with_pad( image , 192 , 192 )
		input_image = tf.cast( image , dtype=tf.float32 )
		input_details = interpreter.get_input_details()
		output_details = interpreter.get_output_details()
		interpreter.set_tensor( input_details[0]['index'] , input_image.numpy() )
		interpreter.invoke()
		keypoints_with_scores = interpreter.get_tensor( output_details[0]['index'] )
		keypoints_with_scores = keypoints_with_scores[0][0]
		scores = [ x[2] for x in keypoints_with_scores ]
		average_score = np.mean( scores )
		# print( f"Average Score = {average_score}" )
		return {
			"average_score": str( average_score ) ,
			"time_stamp": json_data["time_stamp"] ,
			"nose": {
				"name": "Nose" ,
				"score": str( scores[0] ) ,
			} ,
			"left_eye": {
				"name": "Left Eye" ,
				"score": str( scores[1] ) ,
			} ,
			"right_eye": {
				"name": "Right Eye" ,
				"score": str( scores[2] ) ,
			} ,
			"left_ear": {
				"name": "Left Ear" ,
				"score": str( scores[3] ) ,
			} ,
			"right_ear": {
				"name": "Right Ear" ,
				"score": str( scores[4] ) ,
			} ,
			"left_shoulder": {
				"name": "Left Shoulder" ,
				"score": str( scores[5] ) ,
			} ,
			"right_shoulder": {
				"name": "Right Shoulder" ,
				"score": str( scores[6] ) ,
			} ,
			"left_elbow": {
				"name": "Left Elbow" ,
				"score": str( scores[7] ) ,
			} ,
			"right_elbow": {
				"name": "Right Elbow" ,
				"score": str( scores[8] ) ,
			} ,
			"left_wrist": {
				"name": "Left Wrist" ,
				"score": str( scores[9] ) ,
			} ,
			"right_wrist": {
				"name": "Right Wrist" ,
				"score": str( scores[10] ) ,
			} ,
			"left_hip": {
				"name": "Left Hip" ,
				"score": str( scores[11] ) ,
			} ,
			"right_hip": {
				"name": "Right Hip" ,
				"score": str( scores[12] ) ,
			} ,
			"left_knee": {
				"name": "Left Knee" ,
				"score": str( scores[13] ) ,
			} ,
			"right_knee": {
				"name": "Right Knee" ,
				"score": str( scores[14] ) ,
			} ,
			"left_ankle": {
				"name": "Left Ankle" ,
				"score": str( scores[15] ) ,
			} ,
			"right_ankle": {
				"name": "Right Ankle" ,
				"score": str( scores[16] ) ,
			} ,
		}
	except Exception as e:
		print( e )
		return False