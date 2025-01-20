# !/bin/bash

# check if a special file exists
source /home/gpoe/.venv/bin/activate
echo $(which python) > /home/gpoe/python.log
python -u /home/gpoe/GPOE2025/main.py -c $1 > /home/gpoe/script.log
