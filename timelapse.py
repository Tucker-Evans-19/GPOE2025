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

# Create and enter working directory
if capture_config["run_id"] == "iso_date"
    run_dir = datetime.now().isoformat()[:9] # look for more elegant solution?
else:
    run_dir = capture_config["run_id"]

os.mkdir(run_dir)
os.chdir(run_dir)

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

    timestamp = datetime.now()
    image_arr = cam.capture_array("main")

    image_arr = image_arr[:, 250:-480, :] # Cuts off all black regions of image and reduces data size by ~18 %
    np.save(timestamp.replace(microsecond=0).isoformat(), image_arr)

    if datetime.now() >= end_time:
        print("WARNING: Execution of frame capture code exceeded specified capture interval. Consider reducing exposure time or increasing the invterval.")

    # Ensures spacing between frames is even regardless of code execution time above
    while datetime.now() < end_time:
        continue        
    
    print(f"Captured Frame {i}")
    print(f"Time elapsed: {time.perf_counter() - init_time}")

print("Timelapse Completed!")