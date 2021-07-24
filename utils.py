import os
import sys
import math
import signal
import base64
import binascii
import hashlib
import json
import redis
import datetime
import time
from pytz import timezone

# import multiprocessing
# import concurrent.futures
import threading

# from datetime import datetime , timedelta , time
# from time import localtime, strftime , sleep , time

from twilio.rest import Client

def write_json( file_path , python_object ):
	with open( file_path , 'w', encoding='utf-8' ) as f:
		json.dump( python_object , f , ensure_ascii=False , indent=4 )

def read_json( file_path ):
	with open( file_path ) as f:
		return json.load( f )

def setup_signal_handlers( signal_handler ):
	signal.signal( signal.SIGABRT , signal_handler )
	signal.signal( signal.SIGFPE , signal_handler )
	signal.signal( signal.SIGILL , signal_handler )
	signal.signal( signal.SIGSEGV , signal_handler )
	signal.signal( signal.SIGTERM , signal_handler )
	signal.signal( signal.SIGINT , signal_handler )

def setup_environment():
	os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

# https://stackoverflow.com/questions/22210671/redis-python-setting-multiple-key-values-in-one-operation#22211254
def setup_redis_connection( config ):
	return redis.StrictRedis(
		host=config["host"] ,
		port=config["port"] ,
		db=config["db"] ,
		password=config["password"] ,
		decode_responses=True
		)

def setup_twilio_client( config ):
	return Client( config["sid"] , config["auth_token"] )

def redis_get_most_recent( redis , key ):
	most_recent = redis.get( key )
	if most_recent == None:
		most_recent = []
	else:
		most_recent = json.loads( most_recent )
	return most_recent

def parse_go_time_stamp( time_zone , time_stamp ):
	time_object = datetime.datetime.strptime( time_stamp , "%d%b%Y === %H:%M:%S.%f" ).astimezone( time_zone )
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


def twilio_message( twilio_client , from_number , to_number , message ):
	try:
		print( "here in twilio_message" )
		print( from_number , to_number , message )
		result = twilio_client.messages.create(
			to_number ,
			from_=from_number ,
			body=message ,
		)
		return result
	except Exception as e:
		print ( e )

def twilio_voice_call( twilio_client , from_number , to_number , server_callback_endpoint , callback_function ):
	try:
		print( "here in twilio_voice_call" )
		print( from_number , to_number , server_callback_endpoint )
		# start_time = time.time()
		# new_call = twilio_client.calls.create(
		# 	from_=from_number ,
		# 	to=to_number ,
		# 	url=server_callback_endpoint ,
		# 	method="POST"
		# )
		# answered = False
		# completed = False
		# answer_duration = None
		# completed_duration = None
		# for i in range( 30 ):
		# 	time.sleep( 1 )
		# 	new_call = new_call.update()
		# 	status = new_call.status
		# 	print( status )
		# 	if status == "in-progress":
		# 		answered = True
		# 		answer_duration = int( time.time() - start_time )
		# 	if status == "completed":
		# 		completed = True
		# 		completed_duration = int( time.time() - start_time )
		# 		break
		# callback_function( { "answered": answered , "completed": completed , "answer_duration": answer_duration , "completed_duration": answer_duration } )
		callback_function( { "answered": True , "completed": True , "answer_duration": 3 , "completed_duration": 3 } )
	except Exception as e:
		print( e )
		callback_function( "failed to make twilio call" )

def run_in_background( function_pointer , *args , **kwargs ):
	# cpu_count = multiprocessing.cpu_count()
	# pool = concurrent.futures.ThreadPoolExecutor( max_workers=cpu_count )
	# pool._max_workers = cpu_count
	# pool._adjust_thread_count()
	# function_pointer = pool.submit( function_pointer , *args , **kwargs )
	# function_pointer.add_done_callback( callback_function_pointer )
	# executor.submit( lambda: executor.submit(func, arg).result(timeout=50))
	# with concurrent.futures.ThreadPoolExecutor() as executor:
	# 	print( "background task starting" )
	# 	# result = executor.submit( lambda: executor.submit( function_pointer , *args , **kwargs ).result( timeout=33 ) )
	# 	result = executor.submit( function_pointer , *args , **kwargs ).result( timeout=33 )
	# 	print( "background task finished" )
	# 	callback_function_pointer( result )

	# https://docs.python.org/3/library/threading.html#threading.Thread
	t = threading.Thread( target=function_pointer , args=args , kwargs=kwargs , daemon=True )
	t.start()

def get_now_time_int( time_zone ):
	now = datetime.datetime.now().astimezone( time_zone )
	return int( now.strftime( "%d%m%Y%H%M%S%f" ) )


def get_now_time_difference( time_zone , start_date_time_object ):
	now = datetime.datetime.now().astimezone( time_zone )
	# >>> start = datetime.datetime.strptime( str( int( datetime.datetime.now().astimezone( time_zone ).strftime( "%d%m%Y%H%M%S%f" ) ) ) , "%d%m%Y%H%M%S%f" ).astimezone( time_zone )
	# >>> now = datetime.datetime.now().astimezone( time_zone )
	return math.floor( ( now - start_date_time_object ).total_seconds() )

def setup_time_windows( redis_client , config ):
	results = {}
	time_zone = timezone( config["misc"]["time_zone"] )
	now = datetime.datetime.now().astimezone( time_zone )
	print( "Setting all Last Notification Times To : " )
	print( now )
	for index , time_window in enumerate( config["time_windows"] ):
		time_window["id"] = hashlib.sha256( json.dumps( time_window ).encode( 'utf-8' ) ).hexdigest()
		if "notifications" in time_window:
			if "sms" in time_window["notifications"]:
				time_window["notifications"]["sms"]["last_notified_time"] = {}
				time_window["notifications"]["sms"]["last_notified_time"]["date_time_object"] = now
			if "voice" in time_window["notifications"]:
				time_window["notifications"]["voice"]["last_notified_time"] = {}
				time_window["notifications"]["voice"]["last_notified_time"]["date_time_object"] = now
		results[time_window["id"]] = time_window
		# redis_client.set( f"{config['redis']['prefix']}.TIME_WINDOWS.{time_window['id']}" , json.dumps( time_window ) )
	return results

# def base64_decode( base64_message ):
# 	try:
# 		base64_bytes = base64_message.encode( 'utf-8' )
# 		message_bytes = base64.b64decode(base64_bytes)
# 		message = message_bytes.decode( 'utf-8' )
# 		return message
# 	except Exception as e:
# 		print( e )
# 		return False


# def base64_decode( base64_message ):
# 	try:
# 		base64_bytes = base64_message.encode( 'utf-8' )
# 		message_bytes = base64.b64decode(base64_bytes)
# 		message = message_bytes.decode( 'utf-8' )
# 		return message
# 	except binascii.Error as e: # Remove Base64 Image Header : 'data:image/png;base64,'
# 		parts = base64_message.split( "," )
# 		parts.pop( 0 )
# 		base64_message = ''.join( parts )
# 		base64_decoded_image = base64.b64decode( str( base64_message ) )
# 		return base64_decoded_image
# 	except Exception as e:
# 		print( e )
# 		return False