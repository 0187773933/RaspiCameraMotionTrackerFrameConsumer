import os
import sys
import signal
import base64
import binascii
import json
import redis
import datetime
import time
from pytz import timezone


# from datetime import datetime , timedelta , time
from time import localtime, strftime , sleep
SET_TIMEZONE = None


ON_CLOSE_HOOKS = []
NEEDED_ENVIRONMENT_KEYS = [
	"RPMA_SERVER_HOST" , "RPMA_SERVER_PORT" ,
	"RPMA_REDIS_HOST", "RPMA_REDIS_PORT" ,
	"RPMA_REDIS_DB" , "RPMA_REDIS_PREFIX" , "RPMA_REDIS_PASSWORD" ,
	"RPMA_MOST_RECENT_MOTION_EVENTS_TOTAL" , "RPMA_TIME_ZONE"
]
CONFIG = {}

def signal_handler( self , signal , frame ):
	global ON_CLOSE_HOOKS
	print( f"main.py closed , Signal = {str(signal)}" )
	for index , close_hook in enumerate( ON_CLOSE_HOOKS ):
		close_hook()
	sys.exit( 1 )

signal.signal( signal.SIGABRT , signal_handler )
signal.signal( signal.SIGFPE , signal_handler )
signal.signal( signal.SIGILL , signal_handler )
signal.signal( signal.SIGSEGV , signal_handler )
signal.signal( signal.SIGTERM , signal_handler )
signal.signal( signal.SIGINT , signal_handler )

def HookProgramClose( function_pointer ):
	ON_CLOSE_HOOKS.append( function_pointer )

def write_json( file_path , python_object ):
	with open( file_path , 'w', encoding='utf-8' ) as f:
		json.dump( python_object , f , ensure_ascii=False , indent=4 )

def read_json( file_path ):
	with open( file_path ) as f:
		return json.load( f )

# https://stackoverflow.com/questions/22210671/redis-python-setting-multiple-key-values-in-one-operation#22211254
def get_redis_connection():
	global CONFIG
	return redis.StrictRedis(
		host=CONFIG["redis"]["host"] ,
		port=CONFIG["redis"]["port"] ,
		db=CONFIG["redis"]["db"] ,
		password=CONFIG["redis"]["password"] ,
		decode_responses=True
		)

def redis_get_most_recent( redis , key , new_motion_event , total_motion_events ):
	most_recent = redis.get( key )
	if most_recent == None:
		most_recent = []
		most_recent.append( new_motion_event )
	else:
		# most_recent = str( most_recent , 'utf-8' )
		most_recent = json.loads( most_recent )
		most_recent.append( new_motion_event )
		if len( most_recent ) > total_motion_events:
			most_recent.pop( 0 )
	return most_recent

# https://stackoverflow.com/a/22211254
def ParseConfig():
	global NEEDED_ENVIRONMENT_KEYS
	global CONFIG
	global SET_TIMEZONE
	if len( sys.argv ) > 1:
		CONFIG = read_json( sys.argv[ 1 ] )
	else:
		for x in NEEDED_ENVIRONMENT_KEYS:
			if x not in os.environ:
				print( "config variables not set" )
				sys.exit( 1 )
		CONFIG = {
			"server": {
				"host": os.environ["RPMA_SERVER_HOST"] ,
				"port": os.environ["RPMA_SERVER_PORT"]
			} ,
			"redis": {
				"host": os.environ["RPMA_REDIS_HOST"] ,
				"port": os.environ["RPMA_REDIS_PORT"] ,
				"db": os.environ["RPMA_REDIS_DB"] ,
				"prefix": os.environ["RPMA_REDIS_PREFIX"] ,
				"password": os.environ["RPMA_REDIS_PASSWORD"]
			} ,
			"pose_estimation": {
				"minimum_average": os.environ["RPMA_POSE_ESTIMATION_MINIMUM_AVERAGE"]
			} ,
			"misc": {
				"most_recent_motion_events_total": os.environ("RPMA_MOST_RECENT_MOTION_EVENTS_TOTAL") , # for database
				"time_zone": os.environ("RPMA_TIME_ZONE")
			}
		}
		write_json( "config.json" , CONFIG )
	redis_client = get_redis_connection()
	redis_client.set( f'{CONFIG["redis"]["prefix"]}.CONFIG' , json.dumps( CONFIG ) )
	SET_TIME_ZONE = timezone( CONFIG["misc"]["time_zone"] )
	return CONFIG


def parse_go_time_stamp( time_stamp ):
	global SET_TIMEZONE
	time_object = datetime.datetime.strptime( time_stamp , "%d%b%Y === %H:%M:%S.%f" ).astimezone( SET_TIMEZONE )
	items = time_stamp.split( " === " )
	if len( items ) < 2:
		return False
	date = items[ 0 ]
	time = items[ 1 ]
	time_items = time.split( "." )
	milliseconds = time_items[ 1 ]
	time_items = time_items[ 0 ].split( ":" )
	hours = time_items[ 0 ]
	minutes = time_items[ 1 ]
	seconds = time_items[ 2 ]
	return {
		"date_time_object": time_object ,
		"date": date ,
		"hours": hours ,
		"minutes": minutes ,
		"seconds": seconds ,
		"milliseconds": milliseconds
	}



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