import os
import sys
import signal
import redis
import json
import time
import math
from pprint import pprint
import datetime
from pytz import timezone
import hashlib
import threading

# import pose
import pose_light
# import utils

from sanic import Sanic
from sanic.response import json as sanic_json
from sanic import response

from twilio.rest import Client

class FrameConsumer:
	def __init__( self ):
		self.config = self.read_json( sys.argv[ 1 ] )
		self.setup_environment()
		self.setup_signal_handlers()
		self.setup_redis_connection()
		self.setup_twilio_client()
		self.setup_time_windows()

	def on_shutdown( self , signal ):
		self.log( f"Frame Consumer Shutting Down === {str(signal)}" )
		sys.exit( 1 )

	def get_common_time_string( self ):
		now = datetime.datetime.now().astimezone( self.timezone )
		milliseconds = round( now.microsecond / 1000 )
		milliseconds = str( milliseconds ).zfill( 3 )
		now_string = now.strftime( "%d%b%Y === %H:%M:%S" ).upper()
		return f"{now_string}.{milliseconds}"

	def log( self , message ):
		time_string_prefix = self.get_common_time_string()
		log_message = f"{time_string_prefix} === {message}"
		self.redis.rpush( self.log_key , log_message )
		print( log_message )

	def read_json( self , file_path ):
		with open( file_path ) as f:
			return json.load( f )

	def setup_environment( self ):
		self.timezone = timezone( self.config["misc"]["time_zone"] )
		self.most_recent_key = f'{self.config["redis"]["prefix"]}.MOTION_EVENTS.MOST_RECENT'
		now = datetime.datetime.now().astimezone( self.timezone )
		day = now.strftime( "%d" ).zfill( 2 )
		month = now.strftime( "%m" ).zfill( 2 )
		year = now.strftime( "%Y" )
		self.log_key = f'{self.config["redis"]["prefix"]}.LOG.{year}.{month}.{day}'
		os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

	def setup_signal_handlers( self ):
		signal.signal( signal.SIGABRT , self.on_shutdown )
		signal.signal( signal.SIGFPE , self.on_shutdown )
		signal.signal( signal.SIGILL , self.on_shutdown )
		signal.signal( signal.SIGSEGV , self.on_shutdown )
		signal.signal( signal.SIGTERM , self.on_shutdown )
		signal.signal( signal.SIGINT , self.on_shutdown )

	def setup_redis_connection( self ):
		self.redis = None
		self.redis = redis.StrictRedis(
			host=self.config["redis"]["host"] ,
			port=self.config["redis"]["port"] ,
			db=self.config["redis"]["db"] ,
			password=self.config["redis"]["password"] ,
			decode_responses=True
		)

	def setup_twilio_client( self ):
		self.twilio_client = None
		self.twilio_client = Client( self.config["twilio"]["sid"] , self.config["twilio"]["auth_token"] )

	def setup_time_windows( self ):
		self.time_windows = {}
		time_zone = timezone( self.config["misc"]["time_zone"] )
		now = datetime.datetime.now().astimezone( time_zone )
		now = now - datetime.timedelta( hours=0 , minutes=0 , seconds=180 )
		for index , time_window in enumerate( self.config["time_windows"] ):
			time_window["id"] = hashlib.sha256( json.dumps( time_window ).encode( 'utf-8' ) ).hexdigest()
			if "notifications" in time_window:
				if "sms" in time_window["notifications"]:
					time_window["notifications"]["sms"]["last_notified_time"] = {}
					time_window["notifications"]["sms"]["last_notified_time"]["date_time_object"] = now
				if "voice" in time_window["notifications"]:
					time_window["notifications"]["voice"]["last_notified_time"] = {}
					time_window["notifications"]["voice"]["last_notified_time"]["date_time_object"] = now
			self.time_windows[time_window["id"]] = time_window
			# redis_client.set( f"{config['redis']['prefix']}.TIME_WINDOWS.{time_window['id']}" , json.dumps( time_window ) )

	def run_in_background( self , function_pointer , *args , **kwargs ):
		t = threading.Thread( target=function_pointer , args=args , kwargs=kwargs , daemon=True )
		t.start()

	def get_now_time_difference( self , start_date_time_object ):
		now = datetime.datetime.now().astimezone( self.timezone )
		return math.floor( ( now - start_date_time_object ).total_seconds() )

	# Server Stuff
	async def route_home( self , request ):
		return response.text( "You Found the Motion Alarm - Motion Frame Consumer!\n" )
	async def route_process( self , request ):
		try:
			if request.json == None:
				return response.json( { "result": "failed" , "message": "no json received in request object" } )
			if "frame_buffer_b64_string" not in request.json:
				return response.json( { "result": "failed" , "message": "no 'frame_buffer_b64_string' key in request json" } )
			asleep_or_awake_decision = await self.decide( request.json )
			return response.json( { "result": "success" , "message": "successfully received and processed image" , "decision": asleep_or_awake_decision } )
		except Exception as e:
			self.log( e )
			return response.text( f"failed === {str(e)}" )
	def init_server( self ):
		self.server = Sanic( name="Motion Alarm - Motion Frame Consumer Server" )
		self.server.add_route( self.route_home , "/" , methods=[ "GET" ] )
		self.server.static( "/favicon.ico" , os.path.abspath( "favicon.ico" ) )
		self.server.static( "/apple-touch-icon.png" , os.path.abspath( "apple-touch-icon.png" ) )
		self.server.static( "/apple-touch-icon-precomposed.png" , os.path.abspath( "apple-touch-icon.png" ) )
		self.server.add_route( self.route_process , "/process" , methods=[ "POST" ] )
	def start_server( self ):
		self.init_server()
		self.log( f"Frame Consumer ONLINE === http://{self.config['server']['host']}:{self.config['server']['port']}" )
		self.server.run( host=self.config['server']['host'] , port=self.config['server']['port'] )

	def on_sms_finished( self , result ):
		self.log( "SMS Notification Callback()" )
		self.log( result )

	def on_voice_call_finished( self , result ):
		self.log( "Voice Notification Callback()" )
		self.log( result )

	def twilio_message( self , from_number , to_number , message ):
		try:
			start_time = time.time()
			result = self.twilio_client.messages.create(
				to_number ,
				from_=from_number ,
				body=message ,
			)
			result = result.fetch()
			completed_duration = False
			for i in range( 10 ):
				time.sleep( 1 )
				result = result.fetch()
				if result.status == "delivered":
					completed_duration = int( time.time() - start_time )
					break
			self.on_sms_finished( { "result": result.status , "completed_duration": completed_duration } )
			return
		except Exception as e:
			print ( e )

	def twilio_voice_call( self , from_number , to_number , server_callback_endpoint ):
		try:
			start_time = time.time()
			new_call = self.twilio_client.calls.create(
				from_=from_number ,
				to=to_number ,
				url=server_callback_endpoint ,
				method="POST"
			)
			answered = False
			completed = False
			answer_duration = None
			completed_duration = None
			for i in range( 30 ):
				time.sleep( 1 )
				new_call = new_call.update()
				status = new_call.status
				self.log( status )
				if status == "in-progress":
					answered = True
					answer_duration = int( time.time() - start_time )
				if status == "completed":
					completed = True
					completed_duration = int( time.time() - start_time )
					break
			self.on_voice_call_finished( { "answered": answered , "completed": completed , "answer_duration": answer_duration , "completed_duration": completed_duration } )
			return
		except Exception as e:
			print( e )
			callback_function( "failed to make twilio call" )

	def send_sms_notification( self , new_motion_event , key ):
		self.log( "=== SMS Alert ===" )
		seconds_since_last_notification = self.get_now_time_difference( self.time_windows[key]["notifications"]["sms"]["last_notified_time"]["date_time_object"] )
		if seconds_since_last_notification < self.time_windows[key]["notifications"]["sms"]["cool_down"]:
			time_left = ( self.time_windows[key]["notifications"]["sms"]["cool_down"] - seconds_since_last_notification )
			self.log( f"Waiting [{time_left}] Seconds Until Cooldown is Over" )
			return
		else:
			over_time = ( seconds_since_last_notification - self.time_windows[key]["notifications"]["sms"]["cool_down"] )
			self.log( f"It's Been {seconds_since_last_notification} Seconds Since the Last Message , Which is {over_time} Seconds Past the Cooldown Time of {self.time_windows[key]['notifications']['sms']['cool_down']} Seconds" )
		self.time_windows[key]["notifications"]["sms"]["last_notified_time"]["date_time_object"] = datetime.datetime.now().astimezone( self.timezone )
		# self.redis.set( f"{config['redis']['prefix']}.TIME_WINDOWS.{self.time_windows[key]['id']}" , json.dumps( self.time_windows[key] ) )
		self.log( "Sending SMS Notification" )
		self.run_in_background(
			self.twilio_message ,
			self.time_windows[key]["notifications"]["sms"]["from_number"] ,
			self.time_windows[key]["notifications"]["sms"]["to_number"] ,
			f'{self.time_windows[key]["notifications"]["sms"]["message_prefix"]} @@ {new_motion_event["date_time_string"]}' ,
		)

	def send_voice_notification( self , now_motion_event , key ):
		self.log( "=== Voice Alert ===" )
		seconds_since_last_notification = self.get_now_time_difference( self.time_windows[key]["notifications"]["voice"]["last_notified_time"]["date_time_object"] )
		if seconds_since_last_notification < self.time_windows[key]["notifications"]["voice"]["cool_down"]:
			time_left = ( self.time_windows[key]["notifications"]["voice"]["cool_down"] - seconds_since_last_notification )
			self.log( f"Waiting [{time_left}] Seconds Until Cooldown is Over" )
			return
		else:
			over_time = ( seconds_since_last_notification - self.time_windows[key]["notifications"]["voice"]["cool_down"] )
			self.log( f"It's Been {seconds_since_last_notification} Seconds Since the Last Message , Which is {over_time} Seconds Past the Cooldown Time of {self.time_windows[key]['notifications']['voice']['cool_down']} Seconds" )
		self.time_windows[key]["notifications"]["voice"]["last_notified_time"]["date_time_object"] = datetime.datetime.now().astimezone( self.timezone )
		# self.redis.set( f"{config['redis']['prefix']}.TIME_WINDOWS.{self.time_windows[key]['id']}" , json.dumps( self.time_windows[key] ) )
		self.log( "Sending Voice Call Notification" )
		self.run_in_background(
			self.twilio_voice_call ,
			self.time_windows[key]["notifications"]["voice"]["from_number"] ,
			self.time_windows[key]["notifications"]["voice"]["to_number"] ,
			self.time_windows[key]["notifications"]["voice"]["callback_url"] ,
		)

	def send_notifications( self , new_motion_event , key ):
		if "notifications" not in self.time_windows[key]:
			self.log( "No Notification Info Provided" )
			return
		# pself.log( self.time_windows[key] )
		if "sms" in self.time_windows[key]["notifications"]:
			self.send_sms_notification( new_motion_event , key )
		if "voice" in self.time_windows[key]["notifications"]:
			self.send_voice_notification( new_motion_event , key )

	def redis_get_most_recent( self ):
		most_recent = self.redis.get( self.most_recent_key )
		if most_recent == None:
			most_recent = []
		else:
			most_recent = json.loads( most_recent )
		return most_recent

	def parse_go_time_stamp( self , time_stamp ):
		time_object = datetime.datetime.strptime( time_stamp , "%d%b%Y === %H:%M:%S.%f" ).astimezone( self.timezone )
		items = time_stamp.split( " === " )
		if len( items ) < 2:
			return False
		date = items[ 0 ]
		x_time = items[ 1 ]
		time_items = x_time.split( "." )
		milliseconds = time_items[ 1 ]
		time_items = time_items[ 0 ].split( ":" )
		hours = time_items[ 0 ]
		minutes = time_items[ 1 ]
		seconds = time_items[ 2 ]
		return {
			"date_time_object": time_object ,
			"date_time_string": f"{date} === {hours}:{minutes}:{seconds}.{milliseconds}" ,
			"date": date ,
			"hours": hours ,
			"minutes": minutes ,
			"seconds": seconds ,
			"milliseconds": milliseconds ,
		}


	# Actual Logic
	async def decide( self , json_data ):

		new_motion_event = {
			"time_stamp": json_data["time_stamp"] ,
			"frame_buffer_b64_string": json_data['frame_buffer_b64_string'] ,
			"awake": False
		}

		# 1.) Run 'nets' on Image Buffer
		print( "" )
		self.log( f"Processing Frame --> SinglePoseLightningv3.tflite( {len( json_data['frame_buffer_b64_string'] )} )" )
		new_motion_event["pose_scores"] = await pose_light.process_opencv_frame( json_data )

		# 2.) Get 'Most Recent' Array of Motion Events

		most_recent = self.redis_get_most_recent()
		most_recent.append( new_motion_event )

		# for index , item in enumerate( most_recent ):
		# 	self.log( f"{index} === {item['time_stamp']} === {item['pose_scores']['average_score']}" )

		# 3.) Calculate Time Differences Between 'Most Recent' Frame and Each 'Previous' Frame in the Saved List
		new_motion_event_time_object = self.parse_go_time_stamp( json_data["time_stamp"] )
		new_motion_event["date_time_string"] = new_motion_event_time_object["date_time_string"]
		# time_objects = [ utils.parse_go_time_stamp( self.timezone , x['time_stamp'] ) for x in most_recent[0:-1] ]
		time_objects = [ self.parse_go_time_stamp( x['time_stamp'] ) for x in most_recent ]
		seconds_between_new_motion_event_and_previous_events = [ int( ( new_motion_event_time_object["date_time_object"] - x["date_time_object"] ).total_seconds() ) for x in time_objects ]

		# 4.) Tally Total Motion Events in Each Configed Time Window
		# AND Compute Moving Average of Average Pose Scores in Each Configed Time Window
		# ONLY IF , Total Events Surpases Maximum , then check if the moving average pose score is greater than Minimum Defined Moving Average
		# THEN , Send Notification
		for index , key in enumerate( self.time_windows ):
			motion_events = 0
			# pose_sum = 0.0
			pose_sums = [ float( x["pose_scores"]["average_score"] ) for x in most_recent[ ( -1 * self.time_windows[key]["pose"]["total_events_to_pull_from"] ): ] ]
			pose_sum = sum( pose_sums )
			for index , time_difference in enumerate( seconds_between_new_motion_event_and_previous_events ):
				if time_difference < self.time_windows[key]["seconds"]:
					motion_events += 1
					# pose_sum += float( most_recent[index]["pose_scores"]["average_score"] )
			# pose_average = ( pose_sum / float( len( most_recent ) ) )
			pose_average = ( pose_sum / float( self.time_windows[key]["pose"]["total_events_to_pull_from"] ) )
			if motion_events > self.time_windows[key]['motion']['max_events']:
				self.log( f"Total Motion Events in the Previous {self.time_windows[key]['seconds']} Seconds : {motion_events} === Is GREATER than the defined maximum of {self.time_windows[key]['motion']['max_events']} events" )
				if pose_average >= self.time_windows[key]['pose']['minimum_moving_average']:
					self.log( f"Moving Pose Score Average : {pose_average} is GREATER than defined Minimum Moving Average of {self.time_windows[key]['pose']['minimum_moving_average']}" )
					new_motion_event["awake"] = True
					self.send_notifications( new_motion_event , key )
				else:
					self.log( f"Moving Pose Score Average : {pose_average} is LESS than defined Minimum Moving Average of {self.time_windows[key]['pose']['minimum_moving_average']}" )
			else:
				self.log( f"Total Motion Events in the Previous {self.time_windows[key]['seconds']} Seconds : {motion_events} === Is LESS than the defined maximum of {self.time_windows[key]['motion']['max_events']} events" )

		# 5.) Store Most Recent Array Back into DB
		if len( most_recent ) > self.config["misc"]["most_recent_motion_events_total"]:
			most_recent.pop( 0 )
		self.redis.set( self.most_recent_key , json.dumps( most_recent ) )
		return new_motion_event

	def Start( self ):
		self.start_server()