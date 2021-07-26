#!/bin/bash
TIME_STAMP=$(date +"%Y.%m.%d")
redis-cli -n 1 -p 6379 -a asdfasdfasdf --no-auth-warning \
lrange "RPMA.LOG.$TIME_STAMP" 0 -1