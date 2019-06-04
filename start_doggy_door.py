#!/usr/bin/env python
import pigpio

# import threading
# from scripts.ble_device_poller import BLEDevicePoller

def lower_limit_callback(gpio, level, tick):
    print("Lower Limit Reached: %s, %s, %s" % (str(gpio), str(level), str(tick)) )

def upper_limit_callback(gpio, level, tick):
    print("Upper Limit Reached: %s, %s, %s" % (str(gpio), str(level), str(tick)) )

if __name__ == "__main__":
    import time, argparse

    # Setup commandline argument(s) structures
    ap = argparse.ArgumentParser(description='Pi Rotary Encoder')
    ap.add_argument("--upper", "-u", type=int, default=21, metavar='GPIO', help="Gpio responsible for setting motor direction")
    ap.add_argument("--lower", "-l", type=int, default=20, metavar='GPIO', help="Pin responsible for setting motor PWM signal")
    ap.add_argument("--sleep", "-t", type=int, default=300, metavar='PERIOD', help="How long you want the program to run (secs)")
    # Store parsed arguments into array of variables
    args = vars(ap.parse_args())

    # Extract stored arguments array into individual variables for later usage in script
    upLim = args["upper"]
    lowLim = args["lower"]
    dt = args["sleep"]

    pi = pigpio.pi()
    if not pi.connected:
        print("[ERROR] DoggyDoorMain() ---- Could not connect to Raspberry Pi!")
        exit()

    pi.set_mode(upLim, pigpio.INPUT)
    pi.set_mode(lowLim, pigpio.INPUT)
    pi.set_pull_up_down(upLim, pigpio.PUD_UP)
    pi.set_pull_up_down(lowLim, pigpio.PUD_UP)

    cb1 = pi.callback(upLim, pigpio.EITHER_EDGE, upper_limit_callback)
    cb2 = pi.callback(lowLim, pigpio.EITHER_EDGE, lower_limit_callback)
    time.sleep(dt)

    # pl = BLEDevicePoller(flag_hw_reset=True)
    # pl.add_device("BlueCharm","B0:91:22:F7:6D:55",'bluecharm')
    # pl.add_device("tkr","C3:CE:5E:26:AD:0A",'trackr')
    #
    # pl.start_btmon()
    # pl.update_thread = threading.Thread(target=pl.update_devices)
    # pl.motor_thread = threading.Thread(target=pl.motor_loop)
    # pl.update_thread.start()
    # pl.motor_thread.start()
    # pl.loop()
