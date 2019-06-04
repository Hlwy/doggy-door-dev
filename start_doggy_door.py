#!/usr/bin/env python
import pigpio

# import threading
from scripts.ble_device_poller import BLEDevicePoller
from scripts.pi_motor_driver import PiMotorDriver
from scripts.pi_limit_switch import PiLimitSwitch
from scripts.pi_encoder import PiEncoder

def motor_loop(self):
    while 1:
        if self.flag_open_door:
            if not self.is_door_opening:
                print("[INFO] motor_loop() ---- Opening Door...")
            else: print("[INFO] motor_loop() ---- Keeping Door Open...")
            self.is_door_opening = True
            # motor control function here
            time.sleep(5.0)
        else:
            if self.is_door_opening:
                print("[INFO] motor_loop() ---- Closing Door...")
            self.is_door_opening = False
            # motor control function here
        if self.flag_stop: break
    print("[INFO] motor_loop() --- Exited.")


if __name__ == "__main__":
    import time, argparse

    # Setup commandline argument(s) structures
    ap = argparse.ArgumentParser(description='Pi Rotary Encoder')
    ap.add_argument("--upper", "-u", type=int, default=21, metavar='GPIO', help="Gpio responsible for setting motor direction")
    ap.add_argument("--lower", "-l", type=int, default=20, metavar='GPIO', help="Pin responsible for setting motor PWM signal")
    ap.add_argument("--pinA", "-a", type=int, default=18, metavar='GPIO', help="Encoder A pin")
    ap.add_argument("--pinB", "-b", type=int, default=23, metavar='GPIO', help="Encoder B pin")
    ap.add_argument("--gpio", "-d", type=int, default=21, metavar='GPIO', help="Gpio responsible for setting motor direction")
    ap.add_argument("--pwm", "-p", type=int, default=20, metavar='GPIO', help="Pin responsible for setting motor PWM signal")
    ap.add_argument("--speed", "-s", type=float, default=0.0, metavar='SPEED', help="Speed you want to drive the motor (-1.0 < spd < 1.0)")
    ap.add_argument("--sleep", "-t", type=int, default=300, metavar='PERIOD', help="How long you want the program to run (secs)")
    # Store parsed arguments into array of variables
    args = vars(ap.parse_args())

    # Extract stored arguments array into individual variables for later usage in script
    upLim = args["upper"]
    lowLim = args["lower"]
    pinA = args["pinA"]
    pinB = args["pinB"]
    dt = args["sleep"]
    dir = args["gpio"]
    pwm = args["pwm"]
    vel = args["speed"]

    pi = pigpio.pi()
    if not pi.connected:
        print("[ERROR] DoggyDoorMain() ---- Could not connect to Raspberry Pi!")
        exit()

    # Initialize Objects
    motor = PiMotorDriver(pwm, dir,pi=pi)
    enc = PiEncoder(pinA, pinB,pi=pi)
    upSwitch = PiLimitSwitch(upLim,"Upper Switch",pi=pi, verbose=True)
    lowSwitch = PiLimitSwitch(lowLim,"Lower Switch",pi=pi, verbose=True)

    pl = BLEDevicePoller(flag_hw_reset=True)
    pl.add_device("BlueCharm","B0:91:22:F7:6D:55",'bluecharm')
    pl.add_device("tkr","C3:CE:5E:26:AD:0A",'trackr')
    pl.start()

    # self.motor_thread = threading.Thread(target=self.motor_loop)
    # self.motor_thread.start()

    while 1:
        print(pl.flag_open_door)
        if upSwitch.is_pressed:
            break
        if lowSwitch.is_pressed:
            break
    print("Switch pressed, Stopping...")
    pl.flag_stop = True
    enc.close()
    motor.stop()
    upSwitch.close()
    lowSwitch.close()
    pl.close()

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
