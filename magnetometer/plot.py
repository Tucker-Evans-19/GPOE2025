from asciiplot import asciiize, Color

import time
import board
import rm3100

i2c = board.I2C()
rm = rm3100.RM3100_I2C(i2c, i2c_address=0x21)

n = 10
xs = range(n)

all_Bx = [0] * n
all_By = [0] * n
all_Bz = [0] * n

#centerline = [0,1,2,3,4,5,6,7,8,9]

print(all_Bx, all_By, all_Bz)

i = 0

print('\n')

while True:
    try:
        rm.start_single_reading()
        time.sleep(rm.measurement_time) 
        reading = rm.get_next_reading()
        Bx, By, Bz = rm.convert_to_microteslas(reading) 
#        print(f'\r(Bx, By, Bz) = ({Bx:.3f}, {By:.3f}, {Bz:.3f}) µT') #, end='', flush=True)
        
        yindex = i % n
        #all_Bx[yindex] = Bx
        #all_By[yindex] = By
        all_Bz[yindex] = Bz 
        i += 1

        latest_graph = asciiize(
            #all_Bx,
            #all_By,
            all_Bz,
            #centerline,
            x_axis_tick_labels=xs,
            #sequence_colors=[Color.BLUE_VIOLET, Color.BLUE_VIOLET, Color.BLUE_VIOLET, Color.DEFAULT],
            #sequence_colors=[Color.DEFAULT],
            inter_points_margin=5,
            height=20,
            y_axis_tick_label_decimal_places=1,
            #background_color=Color.GREY_7,
            #title_color=Color.MEDIUM_PURPLE,
            #label_color=Color.MEDIUM_PURPLE,
            x_axis_description='Latest Measurement Index',
            y_axis_description='Field Strength',
            center_horizontally=False
        )
        
        print(latest_graph)
        print('\n')
        #print(latest_graph, end='', flush=True)


    except OSError as e:
        """ """

