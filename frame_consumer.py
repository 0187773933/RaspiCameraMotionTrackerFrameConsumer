import os
import sys
import redis
import json
import time
from pprint import pprint
import datetime
from pytz import timezone

# import pose
import pose_light
import utils

from sanic import Sanic
from sanic.response import json as sanic_json
from sanic import response

class FrameConsumer:
	def __init__( self ):
		self.config = utils.read_json( sys.argv[ 1 ] )
		self.timezone = timezone( self.config["misc"]["time_zone"] )
		utils.setup_environment()
		utils.setup_signal_handlers( self.on_shutdown )
		self.redis = utils.setup_redis_connection( self.config["redis"] )
		self.twilio_client = utils.setup_twilio_client( self.config["twilio"] )
		self.time_windows = utils.setup_time_windows( self.redis , self.config )
	def on_shutdown( self , signal ):
		print( f"Frame Consumer Shutting Down === {str(signal)}" )
		sys.exit( 1 )

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
			print( e )
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
		print( f"Starting On === http://{self.config['server']['host']}:{self.config['server']['port']}" )
		self.server.run( host=self.config['server']['host'] , port=self.config['server']['port'] )

	def on_sms_finished( self , result ):
		print( "SMS Notification Callback()" )
		print( result )

	def on_voice_call_finished( self , result ):
		print( "Voice Notification Callback()" )
		print( result )

	def send_sms_notification( self , new_motion_event , key ):
		print( "=== SMS Alert ===" )
		seconds_since_last_notification = utils.get_now_time_difference( self.timezone , self.time_windows[key]["notifications"]["sms"]["last_notified_time"]["date_time_object"] )
		if seconds_since_last_notification < self.time_windows[key]["notifications"]["sms"]["cool_down"]:
			time_left = ( self.time_windows[key]["notifications"]["sms"]["cool_down"] - seconds_since_last_notification )
			print( f"Waiting [{time_left}] Seconds Until Cooldown is Over" )
			return
		else:
			over_time = ( seconds_since_last_notification - self.time_windows[key]["notifications"]["sms"]["cool_down"] )
			print( f"It's Been {seconds_since_last_notification} Seconds Since the Last Message , Which is {over_time} Seconds Past the Cooldown Time of {self.time_windows[key]['notifications']['sms']['cool_down']} Seconds" )
		self.time_windows[key]["notifications"]["sms"]["last_notified_time"]["date_time_object"] = datetime.datetime.now().astimezone( self.timezone )
		# self.redis.set( f"{config['redis']['prefix']}.TIME_WINDOWS.{self.time_windows[key]['id']}" , json.dumps( self.time_windows[key] ) )
		print( "Sending SMS Notification" )
		utils.run_in_background(
			utils.twilio_message ,
			self.twilio_client ,
			self.time_windows[key]["notifications"]["sms"]["from_number"] ,
			self.time_windows[key]["notifications"]["sms"]["to_number"] ,
			f'{self.time_windows[key]["notifications"]["sms"]["message_prefix"]} @@ {new_motion_event["date_time_string"]}' ,
			self.on_sms_finished
		)

	def send_voice_notification( self , now_motion_event , key ):
		print( "=== Voice Alert ===" )
		seconds_since_last_notification = utils.get_now_time_difference( self.timezone , self.time_windows[key]["notifications"]["voice"]["last_notified_time"]["date_time_object"] )
		if seconds_since_last_notification < self.time_windows[key]["notifications"]["voice"]["cool_down"]:
			time_left = ( self.time_windows[key]["notifications"]["voice"]["cool_down"] - seconds_since_last_notification )
			print( f"Waiting [{time_left}] Seconds Until Cooldown is Over" )
			return
		else:
			over_time = ( seconds_since_last_notification - self.time_windows[key]["notifications"]["voice"]["cool_down"] )
			print( f"It's Been {seconds_since_last_notification} Seconds Since the Last Message , Which is {over_time} Seconds Past the Cooldown Time of {self.time_windows[key]['notifications']['voice']['cool_down']} Seconds" )
		self.time_windows[key]["notifications"]["voice"]["last_notified_time"]["date_time_object"] = datetime.datetime.now().astimezone( self.timezone )
		# self.redis.set( f"{config['redis']['prefix']}.TIME_WINDOWS.{self.time_windows[key]['id']}" , json.dumps( self.time_windows[key] ) )
		print( "Sending Voice Call Notification" )
		utils.run_in_background(
			utils.twilio_voice_call ,
			self.twilio_client ,
			self.time_windows[key]["notifications"]["voice"]["from_number"] ,
			self.time_windows[key]["notifications"]["voice"]["to_number"] ,
			self.time_windows[key]["notifications"]["voice"]["callback_url"] ,
			self.on_voice_call_finished
		)

	def send_notifications( self , new_motion_event , key ):
		if "notifications" not in self.time_windows[key]:
			print( "No Notification Info Provided" )
			return
		# pprint( self.time_windows[key] )
		if "sms" in self.time_windows[key]["notifications"]:
			self.send_sms_notification( new_motion_event , key )
		if "voice" in self.time_windows[key]["notifications"]:
			self.send_voice_notification( new_motion_event , key )

	# Actual Logic
	async def decide( self , json_data ):

		new_motion_event = {
			"time_stamp": json_data["time_stamp"] ,
			"frame_buffer_b64_string": json_data['frame_buffer_b64_string'] ,
			"awake": False
		}

		# 1.) Run 'nets' on Image Buffer
		new_motion_event["pose_scores"] = await pose_light.process_opencv_frame( json_data )

		# 2.) Get 'Most Recent' Array of Motion Events
		most_recent_key = f'{self.config["redis"]["prefix"]}.MOTION_EVENTS.MOST_RECENT'
		most_recent = utils.redis_get_most_recent( self.redis , most_recent_key )
		most_recent.append( new_motion_event )

		# for index , item in enumerate( most_recent ):
		# 	print( f"{index} === {item['time_stamp']} === {item['pose_scores']['average_score']}" )

		# 3.) Calculate Time Differences Between 'Most Recent' Frame and Each 'Previous' Frame in the Saved List
		new_motion_event_time_object = utils.parse_go_time_stamp( self.timezone , json_data["time_stamp"] )
		new_motion_event["date_time_string"] = new_motion_event_time_object["date_time_string"]
		# time_objects = [ utils.parse_go_time_stamp( self.timezone , x['time_stamp'] ) for x in most_recent[0:-1] ]
		time_objects = [ utils.parse_go_time_stamp( self.timezone , x['time_stamp'] ) for x in most_recent ]
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
				print( f"Total Motion Events in the Previous {self.time_windows[key]['seconds']} Seconds : {motion_events} === Is GREATER than the defined maximum of {self.time_windows[key]['motion']['max_events']} events" )
				if pose_average >= self.time_windows[key]['pose']['minimum_moving_average']:
					print( f"Moving Pose Score Average : {pose_average} is GREATER than defined Minimum Moving Average of {self.time_windows[key]['pose']['minimum_moving_average']}" )
					new_motion_event["awake"] = True
					self.send_notifications( new_motion_event , key )
				else:
					print( f"Moving Pose Score Average : {pose_average} is LESS than defined Minimum Moving Average of {self.time_windows[key]['pose']['minimum_moving_average']}" )
			else:
				print( f"Total Motion Events in the Previous {self.time_windows[key]['seconds']} Seconds : {motion_events} === Is LESS than the defined maximum of {self.time_windows[key]['motion']['max_events']} events" )

		# 5.) Store Most Recent Array Back into DB
		if len( most_recent ) > self.config["misc"]["most_recent_motion_events_total"]:
			most_recent.pop( 0 )
		self.redis.set( most_recent_key , json.dumps( most_recent ) )
		return new_motion_event

	def Start( self ):
		self.start_server()