	for time_window_index , time_window in enumerate( config["time_windows"] ):
		total_motion_events_in_time_window = 0
		for index , time_difference in enumerate( seconds_between_new_motion_event_and_previous_events ):
			if time_difference < time_window["seconds"]:
				total_motion_events_in_time_window += 1
		if total_motion_events_in_time_window > time_window["motion"]["max_events"]:
			print( f"Total Motion Events in the Previous {time_window['seconds']} Seconds : {total_motion_events_in_time_window} === Is GREATER than the defined maximum of {time_window['motion']['max_events']} events" )
			if float( new_motion_event["pose_scores"]["average_score"] ) > config["pose_estimation"]["minimum_average"]:
				print( f"Average Pose Score : {new_motion_event['pose_scores']['average_score']} is GREATER than defined Minimum Average of {config['pose_estimation']['minimum_average']}" )
				print( "SHOULD Send Notification" )
				new_motion_event["awake"] = True
			else:
				print( f"Average Pose Score : {new_motion_event['pose_scores']['average_score']} is LESS than defined Minimum Average of {config['pose_estimation']['minimum_average']}" )
				print( "NOT Sending Notification" )
		else:
			print( f"Total Motion Events in the Previous {time_window['seconds']} Seconds : {total_motion_events_in_time_window} === Is LESS than the defined maximum of {time_window['motion']['max_events']} events" )
