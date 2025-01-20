# !/bin/bash

# check if a special file exists
if [ -f /home/gpoe/GPOE2025/RUN ]; then
    echo 'found RUN file; starting main control loop!'
    echo "Using config file:" $1
    cd /home/gpoe/GPOE2025
    rm RUN
    nohup python -u main.py -c $1 > run.log 2> run.err &
fi
