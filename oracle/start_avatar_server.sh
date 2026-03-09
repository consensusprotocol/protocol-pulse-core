#!/bin/bash
cd ~/protocol_pulse/oracle
source ~/.bashrc
export CUDA_VISIBLE_DEVICES=1
gunicorn -w 2 -k gevent --timeout 300 --bind 0.0.0.0:8200 avatar_server:app 2>&1 | tee ~/protocol_pulse/logs/avatar_server.log
