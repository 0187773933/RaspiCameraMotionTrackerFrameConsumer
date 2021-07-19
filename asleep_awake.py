import pose_light
import json
import utils
from pprint import pprint
import pysnooper
# import pickle


async def Decide( config , json_data ):
	# 1.) Run 'nets' on Image Buffer
	pose_scores = await pose_light.process_opencv_frame( json_data )
	# 2.) Store New Motion Frame in 'Most Recent' Array of Motion Events
	#	Also , get the whole array of the most recent motion events so we can run heuristics
	# with pysnooper.snoop():
	new_motion_event = {
		"time_stamp": json_data["time_stamp"] ,
		"pose_scores": pose_scores ,
		"frame_buffer_b64_string": json_data['frame_buffer_b64_string']
	}
	redis = utils.get_redis_connection()
	most_recent_key = f'{config["redis"]["prefix"]}.MOTION_EVENTS.MOST_RECENT'
	most_recent = utils.redis_get_most_recent( redis , most_recent_key , new_motion_event , config["misc"]["most_recent_motion_events_total"] )

	# 3.) Make Time Decisions
	new_motion_event_time_object = utils.parse_go_time_stamp( json_data["time_stamp"] )
	time_objects = [ utils.parse_go_time_stamp( x['time_stamp'] ) for x in most_recent ]
	seconds_between_new_motion_event_and_previous_events = [ int( ( new_motion_event_time_object["date_time_object"] - x["date_time_object"] ).total_seconds() ) for x in time_objects ]
	# TO_FINISH

	# 4.) Use Time Decision and Pose Estimations to Classify as Asleep or Awake
	# TO_DO

	# 5.) Print Info
	for index , event in enumerate( most_recent ):
		ts = event['time_stamp']
		avg_score = event['pose_scores']['average_score']
		td = seconds_between_new_motion_event_and_previous_events[index]
		print( f"{index} === {ts} === Pose Average: {avg_score} === Time Difference: {td}" )

	# 6.) Store Most Recent Array Back into DB
	redis.set( most_recent_key , json.dumps( most_recent ) )
	# pprint( most_recent )
	return new_motion_event