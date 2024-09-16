import os
import glob
import time
#import matplotlib.pyplot as plt

os.system('modprobe w1-gpio')
os.system('modprobe w1-therm')
 
base_dir = '/sys/bus/w1/devices/'
device_folder = glob.glob(base_dir + '28*')[0]
device_file = device_folder + '/w1_slave'
 
def read_temp_raw():
    f = open(device_file, 'r')
    lines = f.readlines()
    f.close()
    return lines


def read_temp():
    lines = read_temp_raw()
    while lines[0].strip()[-3:] != 'YES':
        # time.sleep(0.2)
        lines = read_temp_raw()
    equals_pos = lines[1].find('t=')
    if equals_pos != -1:
        temp_string = lines[1][equals_pos+2:]
        temp_c = float(temp_string) / 1000.0
        return temp_c

# put counts and temps into text file


def get_temp(cadence=0.5, runtime=70, outfile='temperature.txt'):
    t_init = time.time()
    outfile = open(outfile, 'w')
    # plt.axis([t_init, t_init+runtime, 10,40])
    while True:
        temp = read_temp()
        print(temp)
        outfile.write(str(time.time()-t_init)+' '+str(temp)+'\n')
        # time.sleep(cadence)
        if time.time() > t_init + runtime:
            outfile.close()
            break

# plt.axis([0,10,0,10])
# for i in range(10):
#     plt.scatter(i,i)
#     plt.pause(0.5)

get_temp()
