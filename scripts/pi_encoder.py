#!/usr/bin/env python
import pigpio
import os, sys, time, signal
import math

class PiEncoder(object):
    levelA = 0
    levelB = 0
    dt = 0.01
    lastGpio = None
    position = 0
    def __init__(self,pinEncA,pinEncB, debounce=50, pi=None):
        # Initialize pigpiod if not already done so
        if pi is None:
            pi = pigpio.pi()
            if not pi.connected:
                print("[ERROR] PiMotorDriver() ---- Could not connect to Raspberry Pi!")
                exit()
        self.pi = pi

        # Initialize everything else
        self.encA = pinEncA
        self.encB = pinEncB
        self.pi.set_mode(pinEncA, pigpio.INPUT)
        self.pi.set_mode(pinEncB, pigpio.INPUT)
        self.pi.set_pull_up_down(pinEncA, pigpio.PUD_UP)
        self.pi.set_pull_up_down(pinEncB, pigpio.PUD_UP)
        # self.pi.set_glitch_filter(pinEncA, debounce)
        # self.pi.set_glitch_filter(pinEncB, debounce)

        self.cbA = self.pi.callback(pinEncA, pigpio.EITHER_EDGE, self.pulse_cb)
        self.cbB = self.pi.callback(pinEncB, pigpio.EITHER_EDGE, self.pulse_cb)

    def __del__(self):
        print("[INFO] PiEncoder() ---- Deleting object...")
        self.cbA.cancel()
        self.cbB.cancel()
        # Shut down pigpiod LAST
        # self.pi.stop()
    def close(self):
        self.__del__()

    def callback(self,step):
        self.position+=step
        print("[INFO] PiEncoder --- Position: %d" % self.position)

    def signal_handler(self, signal, frame):
        print('You pressed Ctrl+C!')
        self.__del__()
        sys.exit(0)

    def pulse_cb(self, gpio, level, tick):
        if gpio == self.encA: self.levelA = level
        else: self.levelB = level

        # Handle debounce
        if gpio != self.lastGpio:
            self.lastGpio = gpio

            if gpio == self.encA and level == 1:
                if self.levelB == 1: self.callback(1)
            elif gpio == self.encB and level == 1:
                if self.levelA == 1: self.callback(-1)

if __name__ == "__main__":
    import time, argparse

    # Setup commandline argument(s) structures
    ap = argparse.ArgumentParser(description='Pi Rotary Encoder')
    ap.add_argument("--pinA", "-a", type=int, default=18, metavar='GPIO', help="Encoder A pin")
    ap.add_argument("--pinB", "-b", type=int, default=23, metavar='GPIO', help="Encoder B pin")
    ap.add_argument("--sleep", "-t", type=int, default=300, metavar='PERIOD', help="How long you want program to run (secs)")
    # Store parsed arguments into array of variables
    args = vars(ap.parse_args())

    # Extract stored arguments array into individual variables for later usage in script
    pinA = args["pinA"]
    pinB = args["pinB"]
    dt = args["sleep"]

    if pi is None:
        pi = pigpio.pi()
        if not pi.connected:
            print("[ERROR] Could not connect to Raspberry Pi!")
            exit()
    enc = PiEncoder(pinA, pinB,pi=pi)
    time.sleep(dt)
    enc.close()
    pi.stop()
