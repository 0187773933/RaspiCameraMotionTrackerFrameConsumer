import pose_light
import json
import utils
from pprint import pprint
import pysnooper
# import pickle


async def Decide( config , json_data ):
	# 1.) Run 'nets' on Image Buffer
	pose_scores = await pose_light.process_opencv_frame( json_data )

	# 2.) Get 'Most Recent' Array of Motion Events
	# with pysnooper.snoop():
	new_motion_event = {
		"time_stamp": json_data["time_stamp"] ,
		"pose_scores": pose_scores ,
		"frame_buffer_b64_string": json_data['frame_buffer_b64_string'] ,
		"awake": False
	}
	redis = utils.get_redis_connection()
	most_recent_key = f'{config["redis"]["prefix"]}.MOTION_EVENTS.MOST_RECENT'
	# most_recent = utils.redis_get_most_recent( redis , most_recent_key , new_motion_event , config["misc"]["most_recent_motion_events_total"] )
	most_recent = utils.redis_get_most_recent( redis , most_recent_key )

	# 3.) Calculate Time Differences Between 'Most Recent' Frame and Each 'Previous' Frame in the Saved List
	new_motion_event_time_object = utils.parse_go_time_stamp( json_data["time_stamp"] )
	time_objects = [ utils.parse_go_time_stamp( x['time_stamp'] ) for x in most_recent ]
	seconds_between_new_motion_event_and_previous_events = [ int( ( new_motion_event_time_object["date_time_object"] - x["date_time_object"] ).total_seconds() ) for x in time_objects ]

	# 4.) Iterate Through Each Configed Time Window and Check if Total Events Surpases Maximum
	# ONLY IF , Total Events Surpases Maximum , then check if average pose score is greater than Minimum Defined Average
	for time_window_index , time_window in enumerate( config["time_windows"] ):
		total_events_in_time_window = 0
		for index , time_difference in enumerate( seconds_between_new_motion_event_and_previous_events ):
			if time_difference < time_window["seconds"]:
				total_events_in_time_window += 1
		if total_events_in_time_window > time_window["max_events"]:
			print( f"Total Events in the Previous {time_window['seconds']} Seconds : {total_events_in_time_window} === Is GREATER than the defined maximum of {time_window['max_events']} events" )
			if float( new_motion_event["pose_scores"]["average_score"] ) > config["pose_estimation"]["minimum_average"]:
				print( f"Average Pose Score : {new_motion_event['pose_scores']['average_score']} is GREATER than defined Minimum Average of {config['pose_estimation']['minimum_average']}" )
				print( "SHOULD Send Notification" )
				new_motion_event["awake"] = True
			else:
				print( f"Average Pose Score : {new_motion_event['pose_scores']['average_score']} is LESS than defined Minimum Average of {config['pose_estimation']['minimum_average']}" )
				print( "NOT Sending Notification" )
		else:
			print( f"Total Events in the Previous {time_window['seconds']} Seconds : {total_events_in_time_window} === Is LESS than the defined maximum of {time_window['max_events']} events" )

	# 5.) Print Info
	# for index , event in enumerate( most_recent ):
	# 	ts = event['time_stamp']
	# 	avg_score = event['pose_scores']['average_score']
	# 	td = seconds_between_new_motion_event_and_previous_events[index]
	# 	print( f"{index} === {ts} === Pose Average: {avg_score} === Time Difference: {td}" )

	# 6.) Store Most Recent Array Back into DB
	most_recent.append( new_motion_event )
	if len( most_recent ) > config["misc"]["most_recent_motion_events_total"]:
		most_recent.pop( 0 )
	redis.set( most_recent_key , json.dumps( most_recent ) )
	# pprint( most_recent )
	return new_motion_event