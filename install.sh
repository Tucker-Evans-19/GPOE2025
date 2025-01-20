#!/bin/bash

echo -e '===== running update & upgrade ===== \n\n'

#sudo apt-get update
#sudo apt-get upgrade

echo -e '\n\n ===== installing picamera2 ===== \n\n'

sudo apt-get install -y python3-picamera2 --no-install-recommends

echo -e '\n\n ===== setup virtual enviroment ===== \n\n'

cd /home/gpoe
if [ ! -e '.venv/pyvenv.cfg' ]; then
    python -m venv .venv
else
    echo 'virtual environment already exists'
fi

source .venv/bin/activate

echo -e '\n\n ===== install h5py & numpy ===== \n\n'

sudo apt-get install python3-h5py
sudo apt-get install python3-numpy

echo -e '\n\n ===== setup virtual environment pyvenv.cfg ===== \n\n'

sudo cat <<EOF >.venv/pyvenv.cfg
home = /usr/bin
include-system-site-packages = true
version = 3.11.2
executable = /usr/bin/python3.11
command = /usr/bin/python -m venv /home/gpoe/.venv
EOF

echo -e '\n\n ===== install remaining python requirements ===== \n\n'

pip install -r /home/gpoe/GPOE2025/requirements.txt

echo -e '\n\n ===== sync system clock to rtc ===== \n\n'
sudo hwclock --hctosys

echo 'done!'
