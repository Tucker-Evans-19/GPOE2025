from asciiplot import asciiize, Color

import time
import board
import rm3100

i2c = board.I2C()
rm = rm3100.RM3100_I2C(i2c, i2c_address=0x21)

xs = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
ys = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]

while True:
    i = 0

    try:
        rm.start_single_reading()
        time.sleep(rm.measurement_time) 
        reading = rm.get_next_reading()
        Bx, By, Bz = rm.convert_to_microteslas(reading) 
        #print(f'\r(Bx, By, Bz) = ({Bx:.3f}, {By:.3f}, {Bz:.3f}) µT', end='', flush=True)

        ys[i % len(ys)] = Bx 

        latest_graph = asciiize(
            xs,
            [7, 8, 3, 17, 19, 18, 5, 2, 20],

            sequence_colors=[Color.RED, Color.BLUE_VIOLET],
            inter_points_margin=5,
            height=20,
            #background_color=Color.GREY_7,
            title='Random Sequences',
            title_color=Color.MEDIUM_PURPLE,
            label_color=Color.MEDIUM_PURPLE,
            x_axis_description='time',
            y_axis_description='Bx',
            center_horizontally=True
        )

        print(latest_graph, end='', flush=True)

        i += 1


    except OSError as e:
        """ """

