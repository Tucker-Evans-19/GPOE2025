from picamera2 import Picamera2
from datetime import datetime, timedelta
import numpy as np
import time
import argparse
import os
import json

# Setup and parse command line arguments
parser = argparse.ArgumentParser(prog="GPOE2025 All Sky Timelapse",
    description = "Takes exposures at a fixed interval for a timelapse, timestamps them, and stores them as numpy binary files")

parser.add_argument("-c", "--config", help="Name of JSON-formatted configuration file to use", type=str)

args = parser.parse_args()

# Load configuration file
with open(args.config, "rb") as file:
    config_dict = json.load(file)

# Create working directory
if capture_config["run_id"] == "iso_date"
    run_dir = 
    os.mkdir
else:
    np.save(capture_config["run_id"], array)

# Setup Camera
cam = Picamera2()
capture_config = cam.create_still_configuration(raw={}, display=None)

capture_config["controls"] = config_dict["camera_controls"]

cam.configure(capture_config)
cam.start()
time.sleep(2)

# Timelapse loop
for i in range(0, config_dict["num_frames"]):
    init_time = time.perf_counter()
    end_time = datetime.now() + timedelta(seconds=config_dict["capture_interval"])

    array = cam.capture_array("main")
    array = array[:, 250:-480, :]
    print(f"Captured Frame {i}")

    if capture_config["run_id"] == "iso_date"
        np.save(datetime.now().isoformat(), array)
    else:
        np.save(capture_config["run_id"], array)

    while datetime.now() < end_time:
        continue        
    
    print(f"Time elapsed: {time.perf_counter() - init_time}")