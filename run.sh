# !/bin/bash

# check if a special file exists
if [ -f /home/gpoe2025/RUN ]; then
    echo 'found RUN file; starting main control loop!'
    cd /home/gpoe2025/GPOE2025
    nohup python -u main.py > run.log 2> run.err &
fi
