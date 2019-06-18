#!/usr/bin/env python
import pigpio, time

class PiLimitSwitch(object):
    is_pressed = False
    def __init__(self,pin, name="Lower Limit Switch",pi=None, verbose=False):
        self.name = name
        self.verbose = verbose
        self.pin = pin
        # Initialize pigpiod if not already done so
        if pi is None:
            pi = pigpio.pi()
            if not pi.connected:
                print("[ERROR] PiLimitSwitch() ---- Could not connect to Raspberry Pi!")
                exit()
        self.pi = pi

        # Initialize everything else
        self.pi.set_mode(pin, pigpio.INPUT)
        self.pi.set_pull_up_down(pin, pigpio.PUD_UP)
        self.pi.set_glitch_filter(pin, 50)

        self.cb_down = pi.callback(pin, pigpio.FALLING_EDGE, self.callback_pressed)
        self.cb_up = pi.callback(pin, pigpio.RISING_EDGE, self.callback_depressed)

    def __del__(self):
        print("[INFO] PiLimitSwitch() ---- Deleting object '%s'..." % self.name)
        self.cb_up.cancel()
        self.cb_down.cancel()

    def close(self):
        self.__del__()

    def callback_pressed(self,gpio, level, tick):
        if self.verbose: print("[%.2f] Limit Switch '%s' on pin '%d' activated." % (time.time(),self.name,gpio) )
        self.is_pressed = True

    def callback_depressed(self,gpio, level, tick):
        if self.verbose: print("[%.2f] Limit Switch '%s' on pin '%d' de-activated." % (time.time(),self.name,gpio) )
        self.is_pressed = False

    def check(self):
        level = self.pi.read(self.pin)
        print("[INFO] PiLimitSwitch::check() ---- GPIO [%d] Level = %d" % (self.pin,level))

if __name__ == "__main__":
    import time, argparse
    count = 0
    # Setup commandline argument(s) structures
    ap = argparse.ArgumentParser(description='Pi Limit Switch')
    ap.add_argument("--pin", "-p", type=int, default=20, metavar='GPIO', help="Pin attached to switch")
    ap.add_argument("--name", "-n", type=str, default="Default Limit Switch", metavar='NAME', help="Identifier for switch")
    ap.add_argument("--sleep", "-t", type=int, default=300, metavar='PERIOD', help="How long you want program to run (secs)")
    # Store parsed arguments into array of variables
    args = vars(ap.parse_args())

    # Extract stored arguments array into individual variables for later usage in script
    pin = args["pin"]
    name = args["name"]
    dt = args["sleep"]

    pi = pigpio.pi()
    if not pi.connected:
        print("[ERROR] Could not connect to Raspberry Pi!")
        exit()
    switch = PiLimitSwitch(pin, name,pi=pi)
    while 1:
        switch.check()
        time.sleep(0.1)
        count+=1
        if count >= 10:
            break
    time.sleep(dt)
    switch.close()
    pi.stop()
