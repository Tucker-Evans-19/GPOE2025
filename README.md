# GPOE2025
repository for all things aurora: camera software, analysis scripts &amp; documentation

Feel free to commit everything to do with the project in the software realm!

## timelapse.py

This is an inital attempt at a customizable script for making timelapses with a Raspberry Pi HQ camera (Or Arducam brand, both with IMX477 sensors). To launch the script, call it from the command line as follows:

```
python3 timelapse.py -c timelapse_config.json
```

The `-c` (or `--config`) command line argument must be provided. The JSON file passed in contains all relevant parameters to define the timelapse. Currently the following parameters are implemented:

| Parameter Name | Description                |
| -------------- | -------------------------- |
| `num_frames`   | Numer of frames to capture |
| `capture_interval` | Time between frame captures |
| `run_id` | Name of the timelapse. Used for directory where image files are stored. If set to `"iso_date"`, uses the current ISO 8601-formatted date |
| `camera_controls` | A dictionary containing settings for the camera like exposure time and sensor gain. This dictionary is defined by the `Picamera2` library. |

The only dependencies for this script which aren't built-in Python libraries are `Picamera2` and `Numpy` both of which are installed by default on Raspberry Pi OS, so no package installation should be necessary.


## miscellany
- Don't install `h5py` like `pip install h5py`. This will throw an error like:
```
ImportError: libhdf5_serial.so.103: cannot open shared object file: No such file or directory
```
Instead, do:
`sudo apt-get install python3-h5py`

Similarly, for `numpy` (which should already be installed to use picamera, I think), don't install it with pip, but `sudo apt-get install python3-numpy`

Finally, since this won't be immediately reflected in the virtualenv needed to us the RM3100 libraries, make sure the config file, `.venv/pyvenv.cfg`, looks like:

```
home = /usr/bin
include-system-site-packages = true
version = 3.11.2
executable = /usr/bin/python3.11
command = /usr/bin/python3 -m venv /home/gpoe2025/GPOE2025/.venv
```

so that it will use the packages installed for the system-wide site-packages via `apt-get`.


- check I2C devices:
      - run `i2cdetect -y 1`, you should see something like:
  
      ```
           0  1  2  3  4  5  6  7  8  9  a  b  c  d  e  f
      00:                         -- -- -- -- -- -- -- -- 
      10: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- 
      20: -- 21 -- -- -- -- -- -- -- -- -- -- -- -- -- -- 
      30: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- 
      40: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- 
      50: 50 51 52 53 54 55 56 57 -- -- -- -- -- -- -- -- 
      60: -- -- -- -- -- -- -- -- UU -- -- -- -- -- -- -- 
      70: -- -- -- -- -- -- -- --    
      ```
  - `UU` indicates the clock is being used as a hardware clokc
  - `21` is the magnetometer (sometimes it's also `20`, `23`... we need to get this set to a fixed value
  - `50 - 57` might be the camera-- currently unknown

# running the main code
First, change into the code directory:
`cd ~/GPOE2025`

Check that your terminal displays the following after doing that:
`(.venv) gpoe2025@birkeland:~/GPOE2025`
(the name after the `@` will be different on different devices).

If, in particular, you don't see `(.venv)` at the beginning, make sure to activate the virtual environment like:
`source /home/gpoe2025/GPOE2025/.venv/bin/activate`

Finally, run the main loop like:
`nohup python -u main.py > run.log 2> run.err &`
(I recommend changing `run` in the naming of the log and error files to something more unique, like the current date).

# Updating the devices (16 Nov 2024)
1. `ssh gpoe@{animal}.local`
2. Check that the terminal displays `(.venv)` at the beginning of the line, which indicates the virtual environment is active, like:
   
`(.venv) gpoe2025@birkeland:~/GPOE2025`

If not, add the following line to `~/.bashrc`:

`source /home/gpoe/GPOE2025/.venv/bin/activate`

Then, run `source ~/.bashrc`.

4. `cd ~/GPOE2025`
   
5. Pull the latest version of the code;
   
```
git fetch origin
git checkout integrated-loop
git pull origin integrated-loop
```

If you get a warning & it doesn't let you pull, stash your changes like so:

```
git add .
git stash
```
And then repeat.

6. Finally, we modify how the pi tries to mount the usb drive on boot.

Replace the last line of `/etc/fstab` with:

`/dev/sda1 /media/usb_drive            vfat    rw,umask=000`

Note, you need to do this with superuser privileges, so open the file like

`sudo nano /etc/fstab`

and use password `aurora`.

7. Finally, reboot the device and test the code, like:

`sudo reboot`

`cd ~/GPOE2025`

`python main.py`

You should see in `/media/usb_drive` a new folder with the current date; in there, open up `xx-measurements.txt`, and verify that there are non-zero temperature & timestamp values being recorded!

# Running the code (16 Nov 2024)

```
cd ~/GPOE2025
nohup python -u main.py > run.log 2> run.err &
```
