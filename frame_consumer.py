import os
import sys
import redis
import json
import time
from pprint import pprint
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

	def send_notification( self , new_motion_event , time_window ):
		# TODO Add Cooloff Support
		print( "Sending Notification" )
		if "notifications" not in time_window:
			print( "No Notification Info Provided" )
			return
		if "sms" in time_window["notifications"]:
			utils.twilio_message(
				self.twilio_client ,
				time_window["notifications"]["sms"]["from_number"] ,
				time_window["notifications"]["sms"]["to_number"] ,
				f'{time_window["notifications"]["sms"]["message_prefix"]} @@ {new_motion_event["date_time_string"]}' ,
			)

	# Actual Logic
	async def decide( self , json_data ):
		# 1.) Run 'nets' on Image Buffer
		pose_scores = await pose_light.process_opencv_frame( json_data )

		# 2.) Get 'Most Recent' Array of Motion Events
		new_motion_event = {
			"time_stamp": json_data["time_stamp"] ,
			"pose_scores": pose_scores ,
			"frame_buffer_b64_string": json_data['frame_buffer_b64_string'] ,
			"awake": False
		}
		most_recent_key = f'{self.config["redis"]["prefix"]}.MOTION_EVENTS.MOST_RECENT'
		most_recent = utils.redis_get_most_recent( self.redis , most_recent_key )

		# 3.) Calculate Time Differences Between 'Most Recent' Frame and Each 'Previous' Frame in the Saved List
		new_motion_event_time_object = utils.parse_go_time_stamp( self.timezone , json_data["time_stamp"] )
		new_motion_event["date_time_string"] = new_motion_event_time_object["date_time_string"]
		time_objects = [ utils.parse_go_time_stamp( self.timezone , x['time_stamp'] ) for x in most_recent ]
		seconds_between_new_motion_event_and_previous_events = [ int( ( new_motion_event_time_object["date_time_object"] - x["date_time_object"] ).total_seconds() ) for x in time_objects ]

		# 4.) Tally Total Motion Events in Each Configed Time Window
		# AND Compute Moving Average of Average Pose Scores in Each Configed Time Window
		# ONLY IF , Total Events Surpases Maximum , then check if the moving average pose score is greater than Minimum Defined Moving Average
		# THEN , Send Notification
		time_windows = self.config["time_windows"]
		for time_window_index , time_window in enumerate( time_windows ):
			motion_events = 0
			# pose_sum = 0.0
			pose_sums = [ float( x["pose_scores"]["average_score"] ) for x in most_recent[ ( -1 * time_window["pose"]["total_events_to_pull_from"] ): ] ]
			pose_sum = sum( pose_sums )
			for index , time_difference in enumerate( seconds_between_new_motion_event_and_previous_events ):
				if time_difference < time_window["seconds"]:
					motion_events += 1
					# pose_sum += float( most_recent[index]["pose_scores"]["average_score"] )
			# pose_average = ( pose_sum / float( len( most_recent ) ) )
			pose_average = ( pose_sum / float( time_window["pose"]["total_events_to_pull_from"] ) )
			if motion_events > time_window['motion']['max_events']:
				print( f"Total Motion Events in the Previous {time_window['seconds']} Seconds : {motion_events} === Is GREATER than the defined maximum of {time_window['motion']['max_events']} events" )
				if pose_average > time_window['pose']['minimum_moving_average']:
					print( f"Moving Pose Score Average : {pose_average} is GREATER than defined Minimum Moving Average of {time_window['pose']['minimum_moving_average']}" )
					new_motion_event["awake"] = True
					self.send_notification( new_motion_event , time_window )
				else:
					print( f"Moving Pose Score Average : {pose_average} is LESS than defined Minimum Moving Average of {time_window['pose']['minimum_moving_average']}" )
			else:
				print( f"Total Motion Events in the Previous {time_window['seconds']} Seconds : {motion_events} === Is LESS than the defined maximum of {time_window['motion']['max_events']} events" )

		# 6.) Store Most Recent Array Back into DB
		most_recent.append( new_motion_event )
		if len( most_recent ) > self.config["misc"]["most_recent_motion_events_total"]:
			most_recent.pop( 0 )
		self.redis.set( most_recent_key , json.dumps( most_recent ) )
		# pprint( most_recent )
		return new_motion_event

	def Start( self ):
		self.start_server()
