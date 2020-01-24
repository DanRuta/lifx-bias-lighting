# https://github.com/mclarkk/lifxlan
from lifxlan import *

from PIL import ImageGrab, Image

import atexit
import colorsys
import argparse
import numpy as np
from threading import Timer
from datetime import datetime

bulb = None
bbox = None
timer = None

# For use with time-out
time_out = None
last_colour = {"r": 0, "g": 0, "b": 0, "time": datetime.utcnow(), "active": True, "counter": 0}
interval = 20
interval_default = 20


# Find the light bulb device, establish a connection, and turn it on
def get_light (name=None):
    num_lights = 1 # Faster discovery, when specified
    lan = LifxLAN(num_lights)

    if name is not None:
        bulb = lan.get_device_by_name(name)
    else:
        devices = None
        while devices is None or len(devices)==0:
            devices = lan.get_lights()
        bulb = devices[0]


    print(f'Selected {bulb.get_label()}')
    bulb.set_power("on")
    return bulb



# Update the light bulb with the screen mean colour
def update_light ():
    global bulb, bbox, timer, interval, interval_default, last_colour, time_out

    # Grab a screenshot from the selected region
    img = ImageGrab.grab(bbox=bbox)
    img.thumbnail(size=(64, 32), resample=Image.NEAREST)

    # Get the average colour of the selected pixels
    img = np.array(img)
    [r, g, b] = np.mean(img, axis=tuple(range(img.ndim-1)))

    # Convert the colour to the lifx colour system
    h, s, b = colorsys.rgb_to_hsv(r/255, g/255, b/255)
    # h, b, s = colorsys.rgb_to_hls(r/255, g/255, b/255)
    bulb.set_color([int(h*65535), s*65535, b*65535, 5750], duration=0, rapid=True)


    if time_out is not None:

        # Perform the time-out checks only once a second
        last_colour["counter"] += 1
        if last_colour["counter"] % interval==0:
            last_colour["counter"] = 0
            now = datetime.utcnow()
            if last_colour["r"]!=r or last_colour["g"]!=g or last_colour["b"]!=b:
                last_colour["r"] = r
                last_colour["g"] = g
                last_colour["b"] = b
                last_colour["time"] = now

                if last_colour["active"]==False:
                    last_colour["active"] = True
                    bulb.set_power("on")
                    interval = interval_default
            else:
                if (now-last_colour["time"]).seconds/60 > time_out:
                    last_colour["active"] = False
                    bulb.set_power("off")
                    interval = 1 # Check only once a second

    # Kick off another execution, after a very short delay
    timer = Timer(1/interval, update_light)
    timer.start()



# Safely exit the program, terminating the Timer
def exit_handler():
    if timer is not None:
        timer.cancel()
atexit.register(exit_handler)



if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument("--name", default=None, help="Bulb name")
    parser.add_argument("--t", default=None, type=int, help="How many minutes of inactivity to wait for, before turning off")
    args = parser.parse_args()

    time_out = args.t
    bulb = get_light(args.name)

    # Get an initial screen grab to get the screen size for bbox size init
    img = ImageGrab.grab()
    img = np.array(img)
    # (left_x, top_y, right_x, bottom_y)
    bbox = (img.shape[1]/20, img.shape[1]/10, img.shape[1]*0.9, img.shape[1]/2)
    bbox = (int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3]))
    print(f'bbox, {bbox}')

    # Kick off the screen fetcher
    update_light()
