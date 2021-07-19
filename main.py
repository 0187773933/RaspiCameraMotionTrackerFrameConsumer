import os
import redis
import json
import time
from pprint import pprint

from sanic import Sanic
from sanic.response import json as sanic_json
from sanic import response

# import pose
import asleep_awake
import utils

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
CONFIG = {}

# https://github.com/huge-success/sanic/tree/master/examples
# https://github.com/huge-success/sanic/blob/master/examples/try_everything.py
# https://sanic.readthedocs.io/en/latest/sanic/blueprints.html
# https://sanic.readthedocs.io/en/stable/sanic/api/router.html

app = Sanic( name="Motion Alarm - Motion Frame Consumer Server" )

@app.get( "/" )
def hello( request ):
	return response.text( "You Found the Motion Alarm - Motion Frame Consumer!\n" )

@app.route( "/favicon.ico" )
async def favicon( request ):
    return await response.file( os.path.abspath( "favicon.ico" ) )

@app.post( "/process" )
async def process( request ):
	global CONFIG
	try:
		if request.json == None:
			return response.json( { "result": "failed" , "message": "no json received in request object" } )
		if "frame_buffer_b64_string" not in request.json:
			return response.json( { "result": "failed" , "message": "no 'frame_buffer_b64_string' key in request json" } )
		asleep_or_awake_decision = await asleep_awake.Decide( CONFIG , request.json )
		return response.json( { "result": "success" , "message": "successfully received and processed image" , "decision": asleep_or_awake_decision } )
	except Exception as e:
		print( e )
		return response.text( f"failed === {str(e)}" )

if __name__ == '__main__':
	CONFIG = utils.ParseConfig()
	print( f"Starting On === http://{CONFIG['server']['host']}:{CONFIG['server']['port']}" )
	app.run( host=CONFIG['server']['host'] , port=CONFIG['server']['port'] )