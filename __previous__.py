import numpy as np
import cv2
import requests
import sys
import os
import signal
import imutils
import json
import redis
import base64

from datetime import datetime , timedelta , time
from time import localtime, strftime , sleep
from pytz import timezone
eastern_tz = timezone( "US/Eastern" )

from twilio.rest import Client

redis_manager = False
redis_subscriber = False

videoPath = os.path.abspath( os.path.join( __file__ , ".." , ".." , "videos" ) )
framePathBase = os.path.abspath( os.path.join( __file__ , ".." , ".." , "client" ) )
frameLiveImagePath = os.path.abspath( os.path.join( framePathBase , "frame.jpeg" ) )
frameDeltaLiveImagePath = os.path.abspath( os.path.join( framePathBase , "frameDelta.jpeg" ) )
frameThreshLiveImagePath = os.path.abspath( os.path.join( framePathBase , "frameThresh.jpeg" ) )

personal_file_path = os.path.abspath( os.path.join( os.path.expanduser( "~" ) , ".config" , "personal" , "raspi_motion_alarm_rewrite.json" ) )
print( personal_file_path )
with open( personal_file_path , 'r' ) as f:
		Personal = json.load( f )
print( Personal )

#TwilioClient = Client( Personal[ 'twilio' ][ 'twilio_sid' ] , Personal[ 'twilio' ][ 'twilio_auth_token' ] )
ws = False

# ( 0 , 0 ) = TOP LEFT
# X = LEFT TO RIGHT
# Y = TOP TO BOTTOM
# [ y1:y2 , x1:x2 ]
# frame = frame[ 0:250 , 0:500 ]
DEFAULT_CLIPPING = { 'x': { '1': 0 , '2': 500 } , 'y': { '1': 0 , '2': 250 } }
DEFUALT_CONFIG = { 'frame_width': 500 , 'clipping': DEFAULT_CLIPPING , 'EMAIL_COOLOFF': 100 , 'MIN_MOTION_FRAMES': 2 , 'MIN_MOTION_SECONDS': 1 , 'MOTION_EVENTS_ACCEPTABLE': 4 , 'MAX_TIME_ACCEPTABLE': 45 , 'MAX_TIME_ACCEPTABLE_STAGE_2': 90 }
LOADED_CONFIG = DEFUALT_CONFIG

def make_folder( path ):
	try:
		print( "Trying to Make Folder Path --> " )
		print( path )
		os.makedirs( path )
	except OSError as exception:
		pass
		#if exception.errno != errno.EEXIST:
			#raise

def inside_message_time_window():
	# window_hours = [ 22 , 23 , 24 , 0 , 1 , 2 ]
	result = False
	now = datetime.now( eastern_tz )
	if now.hour > 21 or now.hour < 3:
		result = True
	express_publish( { "channel": "log" , "message": "Inside Alert Time Window === " + str( result ) } )
	return result

def inside_extra_alert_time_window():
	# ignore_hours = [ 22 , 23 , 24 , 0 , 1 ]
	result = False
	now = datetime.now( eastern_tz )
	if now.hour > 1 and now.hour < 10:
		result = True
	express_publish( { "channel": "log" , "message": "Inside Extra Alert Time Window === " + str( result ) } )
	return result

def express_publish( options ):
	options[ 'list_key_prefix' ] = "sleep.raspi.python." + options[ 'channel' ]
	try:
		print( options[ 'message' ] )
		response = requests.post( 'http://localhost:80/python-script' , data=options )
		#print( response.text )
	except Exception as e:
		print( e )

def redis_get_key_suffix():
	now = datetime.now( eastern_tz )
	return now.strftime( "%Y.%m.%d" )

def redis_publish( options ):
	pass
	# global redis_manager
	# global redis_subscriber
	# options[ 'list_key_prefix' ] = "sleep.raspi.python." + options[ 'channel' ]
	# json_string = json.dumps( options )
	# print( options[ 'message' ] )
	# max_retries_outer = 5
	# for i in range( max_retries_outer - 1 ):
	# 	try:
	# 		# https://stackoverflow.com/a/24773545
	# 		max_retries_inner = 5
	# 		for j in range( max_retries_inner - 1 ):
	# 			try:
	# 				redis_manager.publish( "python-script-controller" , json_string )
	# 				return True
	# 			except Exception as error:
	# 				sleep( 3 )
	# 				redis_connect()
	# 	except Exception as e:
	# 		print( "Couldn't Publish Message to REDIS" )
	# 		sleep( 3 )
	# 		redis_connect()


def calculate_text_position_from_clipping():
	pass

def add_text_to_image():
	# https://www.meccanismocomplesso.org/en/opencv-python-drawing-shapes-and-text-on-images/
	# https://www.life2coding.com/how-to-put-text-on-image-using-opencv-in-python/
	# https://stackoverflow.com/questions/16615662/how-to-write-text-on-a-image-in-windows-using-python-opencv2
	cv2.putText(image,"Hello World!!!", (x,y), cv2.FONT_HERSHEY_SIMPLEX, 2, 255)

def update_loaded_config( config ):
	if 'EMAIL_COOLOFF' in config:
		LOADED_CONFIG[ 'EMAIL_COOLOFF' ] = config[ 'EMAIL_COOLOFF' ]
	if 'MIN_MOTION_SECONDS' in config:
		LOADED_CONFIG[ 'MIN_MOTION_SECONDS' ] = config[ 'MIN_MOTION_SECONDS' ]
	if 'MOTION_EVENTS_ACCEPTABLE' in config:
		LOADED_CONFIG[ 'MOTION_EVENTS_ACCEPTABLE' ] = config[ 'MOTION_EVENTS_ACCEPTABLE' ]
	if 'MAX_TIME_ACCEPTABLE' in config:
		LOADED_CONFIG[ 'MAX_TIME_ACCEPTABLE' ] = config[ 'MAX_TIME_ACCEPTABLE' ]
	if 'MAX_TIME_ACCEPTABLE_STAGE_2' in config:
		LOADED_CONFIG[ 'MAX_TIME_ACCEPTABLE_STAGE_2' ] = config[ 'MAX_TIME_ACCEPTABLE_STAGE_2' ]
	if 'clipping' in config:
		print( config[ 'clipping' ] )
		if 'reset' in config[ 'clipping' ]:
			if config[ 'clipping' ][ 'reset' ] == True or config[ 'clipping' ][ 'reset' ] == "true" or config[ 'clipping' ][ 'reset' ] == "True":
				LOADED_CONFIG[ 'clipping' ] = DEFAULT_CLIPPING
				#express_publish( { "channel": "log" , "message": "LOADED_CONFIG == DEFAULT_CLIPPING" } )
			return
		if 'x' in config[ 'clipping' ]:
			if '1' in config[ 'clipping' ][ 'x' ]:
				LOADED_CONFIG[ 'clipping' ][ 'x' ][ '1' ] = config[ 'clipping' ][ 'x' ][ '1' ]
				express_publish( { "channel": "log" , "message": "LOADED_CONFIG[ 'clipping' ][ 'x' ][ '1' ] == " + str( config[ 'clipping' ][ 'x' ][ '1' ] ) } )

			if '2' in config[ 'clipping' ][ 'x' ]:
				LOADED_CONFIG[ 'clipping' ][ 'x' ][ '2' ] = config[ 'clipping' ][ 'x' ][ '2' ]
				express_publish( { "channel": "log" , "message": "LOADED_CONFIG[ 'clipping' ][ 'x' ][ '2' ] == " + str( config[ 'clipping' ][ 'x' ][ '2' ] ) } )
		if 'y' in config[ 'clipping' ]:
			if '1' in config[ 'clipping' ][ 'y' ]:
				LOADED_CONFIG[ 'clipping' ][ 'y' ][ '1' ] = config[ 'clipping' ][ 'y' ][ '1' ]
				express_publish( { "channel": "log" , "message": "LOADED_CONFIG[ 'clipping' ][ 'y' ][ '1' ] == " + str( config[ 'clipping' ][ 'y' ][ '1' ] ) } )

			if '2' in config[ 'clipping' ][ 'y' ]:
				LOADED_CONFIG[ 'clipping' ][ 'y' ][ '2' ] = config[ 'clipping' ][ 'y' ][ '2' ]
				express_publish( { "channel": "log" , "message": "LOADED_CONFIG[ 'clipping' ][ 'y' ][ '2' ] == " + str( config[ 'clipping' ][ 'y' ][ '2' ] ) } )

def redis_publish_image_set( frame , frameThreshold , frameDelta ):
	frame_retval , frame_buffer = cv2.imencode( '.jpg' , frame )
	frame_base64 = base64.b64encode( frame_buffer )
	thresh_retval , thresh_buffer = cv2.imencode( '.jpg' , frameThreshold )
	thresh_base64 = base64.b64encode( thresh_buffer )
	delta_retval , delta_buffer = cv2.imencode( '.jpg' , frameDelta )
	delta_base64 = base64.b64encode( delta_buffer )
	# redis_manager.publish( "python-script-controller" , json.dumps({
	# 	"channel": "new_frame" , "data64": frame_base64
	# }))
	# redis_manager.publish( "python-script-controller" , json.dumps({
	# 	"channel": "new_threshold" , "data64": thresh_base64
	# }))
	# redis_manager.publish( "python-script-controller" , json.dumps({
	# 	"channel": "new_delta" , "data64": delta_base64
	# }))

def redis_on_message( message ):
	try:
		message = json.loads( message )
		print( message )
		if 'command' in message:
			if message[ 'command' ] == "update_loaded_config":
				if 'config' in message:
					update_loaded_config( message.config )
	except Exception as e:
		pring( e )
		print( "Failed To Parse Redis Message" )

def twilio_message( number , message ):
	try:
		TwilioClient = Client( "ACd4e1f0a8e96f2d48e7b6c1027d833279" , "4eda43216375b68e3c5062176ecde1e6" )
		message = TwilioClient.messages.create( number ,
			body=message ,
			from_=Personal[ 'twilio' ][ 'fromSMSNumber' ] ,
		)
		express_publish( { "channel": "log" , "message": "Sent SMS to: " + str( number ) } )

	except Exception as e:
		print ( e )
		express_publish( { "channel": "errors" , "message": "failed to send sms: " + "Error = " + str( e ) } )

def twilio_call( number ):
	try:
		TwilioClient = Client( "ACd4e1f0a8e96f2d48e7b6c1027d833279" , "4eda43216375b68e3c5062176ecde1e6" )
		new_call = TwilioClient.calls.create( url=Personal[ 'twilio' ][ 'twilio_response_server_url' ] , to=Personal[ 'twilio' ][ 'toSMSExtraNumber' ] , from_=Personal[ 'twilio' ][ 'fromSMSNumber' ] , method="POST" )
	except Exception as e:
		print( e )
		print( "failed to make twilio call" )
		express_publish( { "channel": "errors" , "message": "Failed to Make Twilio Call to: " + str( number ) +  " Error = " + str( e ) } )

def broadcast_error( message ):
	#print( message )
	express_publish( { "channel": "errors" , "message": message } )

def broadcast_log( message ):
	#print( message )
	express_publish( { "channel": "events" , "message": message } )

def broadcast_record( message ):
	if inside_message_time_window() == True:
		twilio_message( Personal[ 'twilio' ][ 'toSMSNumber' ] , message )
	else:
		if inside_extra_alert_time_window() == True:
			twilio_message( Personal[ 'twilio' ][ 'toSMSExtraNumber' ] , message )
	express_publish( { "channel": "records" , "message": message } )

def broadcast_extra_record( message ):
	twilio_message( Personal[ 'twilio' ][ 'toSMSExtraNumber' ] , message )
	express_publish( { "channel": "log" , "message": "Sending SMS to ExtraNumber === " + message } )


def redis_connect():
	pass
	# global redis_manager
	# global redis_subscriber
	# try:
	# 	redis_manager = redis.Redis( host='localhost' , port=6379 , db=1 )
	# 	print( redis_manager )
	# 	redis_subscriber = redis_manager.pubsub()
	# 	redis_subscriber.subscribe( **{ 'python-script-update' : redis_on_message } )
	# except Exception as e:
	# 	print( e )
	# 	print( "Failed to connect to REDIS" )
	# 	sys.exit( 0 )


def signal_handler( signal , frame ):
	message_string = "motion_simple_rewrite_fixed.py closed , Signal = " + str( signal )
	print( message_string )
	broadcast_error( message_string )
	sys.exit( 0 )

signal.signal( signal.SIGABRT , signal_handler )
signal.signal( signal.SIGFPE , signal_handler )
signal.signal( signal.SIGILL , signal_handler )
signal.signal( signal.SIGSEGV , signal_handler )
signal.signal( signal.SIGTERM , signal_handler )
signal.signal( signal.SIGINT , signal_handler )

class TenvisVideo():

	def __init__( self ):

		broadcast_log( "python --> motion_simple_rewrite_fixed.py --> init()" )

		self.write_thread = None

		self.EVENT_TOTAL = -1
		self.EVENT_POOL = []
		self.ExtraAlertPool = [ datetime.now( eastern_tz ) - timedelta( minutes=59 ) ] * 8

		self.total_motion = 0
		self.video_index = 0
		self.last_email_time = None
		self.last_saved_actual_sleep_image_set_time = datetime.now( eastern_tz )

		if 'opencv' in Personal:
			update_loaded_config( Personal[ 'opencv' ] )

		print ( "MIN_MOTION_SECONDS === " + str( LOADED_CONFIG[ 'MIN_MOTION_SECONDS' ] ) )
		print ( "MOTION_EVENTS_ACCEPTABLE === " + str( LOADED_CONFIG[ 'MOTION_EVENTS_ACCEPTABLE' ] ) )
		print ( "MAX_TIME_ACCEPTABLE === " + str( LOADED_CONFIG[ 'MAX_TIME_ACCEPTABLE' ] ) )
		print ( "MAX_TIME_ACCEPTABLE_STAGE_2 === " + str( LOADED_CONFIG[ 'MAX_TIME_ACCEPTABLE_STAGE_2' ] ) )

		# Start
		express_publish( { "channel": "log" , "message": "Starting" } )
		self.w_Capture = cv2.VideoCapture( 0 )
		self.motionTracking()

	def cleanup( self ):
		self.w_Capture.release()
		cv2.destroyAllWindows()
		broadcast_log( "motion_simple_rewrite_fixed.py --> cleanup()" )
		ws.close()

	def simulate_motion( self ):
		self.total_motion = LOADED_CONFIG[ 'MOTION_EVENTS_ACCEPTABLE' ] + 1
		now = datetime.now( eastern_tz )
		self.EVENT_POOL = []
		self.EVENT_POOL = [
			now - timedelta( minutes=10 ) ,
			now - timedelta( minutes=9 ) ,
			now - timedelta( minutes=8 ) ,
			now - timedelta( minutes=7 ) ,
			now - timedelta( minutes=6 ) ,
			now - timedelta( minutes=4 ) ,
			now - timedelta( minutes=5 ) ,
			now - timedelta( seconds=60 ) ,
			now - timedelta( seconds=40 ) ,
			now - timedelta( seconds=30 ) ,
			now - timedelta( seconds=3 ) ,
			now
		]

	def motionTracking( self ):

		avg = None
		firstFrame = None

		min_area = 500
		delta_thresh = 5

		motionCounter = 0

		#self.simulate_motion()

		while( self.w_Capture.isOpened() ):

			( grabbed , frame ) = self.w_Capture.read()

			if not grabbed:
				broadcast_error( "Can't Connect to PI Camera" )
				sleep( 1 )
				break

			frame = imutils.resize( frame , width = 500 )
			frame = frame[ LOADED_CONFIG[ 'clipping' ][ 'y' ][ '1' ]:LOADED_CONFIG[ 'clipping' ][ 'y' ][ '2' ] , LOADED_CONFIG[ 'clipping' ][ 'x' ][ '1' ]:LOADED_CONFIG[ 'clipping' ][ 'x' ][ '2' ] ]

			# https://stackoverflow.com/questions/39622281/capture-one-frame-from-a-video-file-after-every-10-seconds
			cv2.imwrite( frameLiveImagePath , frame )
			# print( frameLiveImagePath )
			# print( str( len( frame ) ) )
			sleep( .1 )

			# Tell Server to Save Image Set for Image Classifier of Actual Sleeping.
			sleep_now_time = datetime.now( eastern_tz )
			seconds_difference = int( ( self.last_saved_actual_sleep_image_set_time - sleep_now_time ).total_seconds() )
			if  seconds_difference > 60:
				self.last_saved_actual_sleep_image_set_time = sleep_now_time
				express_publish({
					"channel": "commands" ,
					"command": "publish_new_image_set_for_sleep" ,
					"message": "new image set ready for image classifier" ,
				})

			if self.last_email_time is not None:
				wNow = datetime.now( eastern_tz )
				self.elapsedTimeFromLastEmail = int( ( wNow - self.last_email_time ).total_seconds() )
				if self.elapsedTimeFromLastEmail < LOADED_CONFIG[ 'EMAIL_COOLOFF' ]:
					#print "sleeping"
					pass
				else:
					broadcast_log( "done sleeping" )
					self.last_email_time = None
					#self.simulate_motion()
				continue

			gray = cv2.cvtColor( frame , cv2.COLOR_BGR2GRAY )
			gray = cv2.GaussianBlur( gray , ( 21 , 21 ) , 0 )

			if firstFrame is None:
				firstFrame = gray
				continue

			if avg is None:
				avg = gray.copy().astype( "float" )
				continue

			cv2.accumulateWeighted( gray , avg , 0.5 )
			frameDelta = cv2.absdiff( gray , cv2.convertScaleAbs(avg) )

			frameThreshold = cv2.threshold( frameDelta , delta_thresh , 255 , cv2.THRESH_BINARY )[ 1 ]
			frameThreshold = cv2.dilate( frameThreshold , None , iterations=2 )

			# Search for Movment
			( cnts , _ ) = cv2.findContours( frameThreshold.copy() , cv2.RETR_EXTERNAL , cv2.CHAIN_APPROX_SIMPLE )
			for c in cnts:
				if cv2.contourArea( c ) < min_area:
					motionCounter = 0 # ???
					continue
				motionCounter += 1

			# If Movement Is Greater than frameThreshold , create motion record
			if motionCounter >= LOADED_CONFIG[ 'MIN_MOTION_FRAMES' ]:
				wNow = datetime.now( eastern_tz )
				broadcast_log( "Motion Counter === ( " + str( motionCounter ) + " >= " + str( LOADED_CONFIG[ 'MIN_MOTION_FRAMES' ] ) + " ) === Minimum Motion Frames" )
				#print "setting new motion record"

				# Check if this is "fresh" in a series of new motion records
				if len( self.EVENT_POOL ) > 1:
					wElapsedTime_x = int( ( self.EVENT_POOL[ -1 ] - self.EVENT_POOL[ -2 ] ).total_seconds() )
					if wElapsedTime_x > ( LOADED_CONFIG[ 'MAX_TIME_ACCEPTABLE_STAGE_2' ] * 2 ):
						broadcast_log( "Not Fresh , Elapsed Time Between Last 2 Events === ( " + str( wElapsedTime_x ) + " > " + str( LOADED_CONFIG[ 'MAX_TIME_ACCEPTABLE_STAGE_2' ] ) + " ) === Max Time Acceptable - Stage 2" )
						self.EVENT_POOL = []
						self.total_motion = 0
						# continue ????

				# Once We Get 10 Events that the Number of Motion Frames is > MIN_MOTION_FRAMES ,
				# THEN , actually record it as a 'True' event
				self.EVENT_POOL.append( wNow )
				if len( self.EVENT_POOL ) > 10:
					self.EVENT_POOL.pop( 0 )
				motionCounter = 0
				self.total_motion += 1

			# Once Total Motion Events Reach frameThreshold , create alert if timing conditions are met
			if self.total_motion >= LOADED_CONFIG[ 'MOTION_EVENTS_ACCEPTABLE' ]:
				broadcast_log( "Total Motion === ( " + str( self.total_motion ) + " >= " + str( LOADED_CONFIG[ 'MOTION_EVENTS_ACCEPTABLE' ] ) + " ) === Motion Events Acceptable" )
				self.total_motion = 0
				cv2.imwrite( frameThreshLiveImagePath , frameThreshold )
				cv2.imwrite( frameDeltaLiveImagePath , frameDelta )
				EVENT_POOL_STRINGS = map( lambda x: x.strftime( "%Y-%m-%d %H:%M:%S" ) , self.EVENT_POOL )
				EXTRA_ALERT_POOL_STRINGS = map( lambda x: x.strftime( "%Y-%m-%d %H:%M:%S" ) , self.ExtraAlertPool )
				express_publish({
					"channel": "commands" , "command": "publish_new_image_set" , "message": "new image set ready" , "event_pool": json.dumps( EVENT_POOL_STRINGS ) , "extra_alert_pool": json.dumps( EXTRA_ALERT_POOL_STRINGS )
				})

				# Evaluate Custom Timeing Conditions
				wNeedToAlert = False

				# Condition 1.) Check Elapsed Time Between Last 2 Motion Events
				wElapsedTime_1 = int( ( self.EVENT_POOL[ -1 ] - self.EVENT_POOL[ 0 ] ).total_seconds() )
				if wElapsedTime_1 <= LOADED_CONFIG[ 'MAX_TIME_ACCEPTABLE' ]:
					broadcast_log( "( Stage-1-Check ) === PASSED === Elapsed Time Between Previous 2 Events === ( " + str( wElapsedTime_1 ) + " <= " + str( LOADED_CONFIG[ 'MAX_TIME_ACCEPTABLE' ] ) + " ) === Max Time Acceptable" )
					wNeedToAlert = True

				# Condition 2.) Check if there are multiple events in a greater window
				elif len( self.EVENT_POOL ) >= 3:
					broadcast_log( "( Stage-1-Check ) === FAILED === Elapsed Time Between Previous 2 Events === ( " + str( wElapsedTime_1 ) + " > " + str( LOADED_CONFIG[ 'MAX_TIME_ACCEPTABLE' ] ) + " ) === Max Time Acceptable" )
					wElapsedTime_2 = int( ( self.EVENT_POOL[ -1 ] - self.EVENT_POOL[ -3 ] ).total_seconds() )
					if wElapsedTime_2 <= LOADED_CONFIG[ 'MAX_TIME_ACCEPTABLE_STAGE_2' ]:
						broadcast_log( "( Stage-2-Check ) === PASSED === Elapsed Time Between the First and Last Event in the Pool === ( " + str( wElapsedTime_2 ) + " <= " + str( LOADED_CONFIG[ 'MAX_TIME_ACCEPTABLE_STAGE_2' ] ) + " ) === Max Time Acceptable - Stage 2" )
						wNeedToAlert = True
					else:
						broadcast_log( "( Stage-2-Check ) === FAILED === Elapsed Time Between the First and Last Event in the Pool === ( " + str( wElapsedTime_2 ) + " > " + str( LOADED_CONFIG[ 'MAX_TIME_ACCEPTABLE_STAGE_2' ] ) + " ) === Max Time Acceptable - Stage 2" )

				if wNeedToAlert == True:
					#print "ALERT !!!!"
					wNowString = self.EVENT_POOL[ -1 ].strftime( "%Y-%m-%d %H:%M:%S" )
					wTimeMsg = "Motion @@ " + wNowString
					broadcast_record( wTimeMsg )
					EVENT_POOL_STRINGS = map( lambda x: x.strftime( "%Y-%m-%d %H:%M:%S" ) , self.EVENT_POOL )
					EXTRA_ALERT_POOL_STRINGS = map( lambda x: x.strftime( "%Y-%m-%d %H:%M:%S" ) , self.ExtraAlertPool )
					express_publish({
						"channel": "event_pools" , "message": "Saving Instance of Event Pools" , "event_pool": json.dumps( EVENT_POOL_STRINGS ) , "extra_alert_pool": json.dumps( EXTRA_ALERT_POOL_STRINGS )
					})
					self.last_email_time = self.EVENT_POOL[ -1 ]
					self.EVENT_POOL = []

					self.WRITING_EVENT_FRAMES = True
					self.FRAME_EVENT_COUNT = 0
					self.EVENT_TOTAL += 1

					if inside_extra_alert_time_window() == False:
						continue
					# In a Cycle of 8 last_email_time's , Count the Number of Times Per 10 minute Interval
					try:
						self.ExtraAlertPool.insert( 0 , self.last_email_time )
						self.ExtraAlertPool.pop()
						num_records_in_10_minutes = 0
						num_records_in_20_minutes = 0
						num_records_in_30_minutes = 0
						for i , record in enumerate( self.ExtraAlertPool ):
							time_diff = int( ( self.last_email_time - record ).total_seconds() )
							if time_diff < 1800:
								num_records_in_30_minutes = num_records_in_30_minutes + 1
							if time_diff < 1200:
								num_records_in_20_minutes = num_records_in_20_minutes + 1
							if time_diff < 600:
								num_records_in_10_minutes = num_records_in_10_minutes + 1
						# print( num_records_in_10_minutes )
						# print( num_records_in_20_minutes )
						# print( num_records_in_30_minutes )
						if num_records_in_10_minutes >= 2:
							wS1 = str( num_records_in_10_minutes ) + " Records in 10 Minutes"
							broadcast_extra_record( wS1 )
							broadcast_log( "( Stage-3-Check ) === PASSED === Number of Records in 10 Minutes === ( " + str( num_records_in_10_minutes ) + " >= 2 ) === Max Records in 10 Minutes" )
							if num_records_in_10_minutes >= 3:
								twilio_call( Personal[ 'twilio' ][ 'toSMSExtraNumber' ] )
						if num_records_in_20_minutes >= 3:
							twilio_call( Personal[ 'twilio' ][ 'toSMSExtraNumber' ] )
							broadcast_log( "( Stage-4-Check ) === PASSED === Number of Records in 20 Minutes === ( " + str( num_records_in_20_minutes ) + " >= 3 ) === Max Records in 20 Minutes" )
							self.ExtraAlertPool = [ datetime.now( eastern_tz ) - timedelta( minutes=59 ) ] * 8
						if num_records_in_30_minutes >= 7:
							#self.ExtraAlertPool = [ datetime.now( eastern_tz ) - timedelta( minutes=59 ) ] * 8
							#voice_call_dad()
							pass
						if num_records_in_30_minutes >= 9:
							#self.ExtraAlertPool = [ datetime.now( eastern_tz ) - timedelta( minutes=59 ) ] * 8
							#voice_call_house()
							pass

					except Exception as e:
						print( "failed to process extra events que" )
						broadcast_error( "failed to process extra events que" )
						broadcast_error( e )


			# cv2.imwrite( frameThreshLiveImagePath , frameThreshold )
			# cv2.imwrite( frameDeltaLiveImagePath , frameDelta )

			#cv2.imshow( "frame" , frame )
			#cv2.imshow( "frameThreshold" , frameThreshold )
			#cv2.imshow( "Frame Delta" , frameDelta )
			#if cv2.waitKey( 1 ) & 0xFF == ord( "q" ):
				#break

		self.cleanup()

redis_connect()
TenvisVideo()