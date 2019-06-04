#!/usr/bin/env python
import pigpio

import threading
from ble_device_poller import BLEDevicePoller
from pi_motor_driver import PiMotorDriver
from pi_limit_switch import PiLimitSwitch
from pi_encoder import PiEncoder

class DoggyDoor(object):
    def __init__(self,pinPwm,pinGpio,pinEncA=None,pinEncB=None, pi=None):
        # Initialize pigpiod if not already done so
        if pi is None:
            pi = pigpio.pi()
            if not pi.connected:
                print("[ERROR] PiMotorDriver() ---- Could not connect to Raspberry Pi!")
                exit()
        self.pi = pi

        # Initialize everything else
        self.pwmPin = pinPwm
        self.dirPin = pinGpio
        self.pi.set_mode(pinPwm, pigpio.OUTPUT)
        self.pi.set_mode(pinGpio, pigpio.OUTPUT)

        self.encA = pinEncA
        self.encB = pinEncB

        self.MOTOR_DIRECTION_FORWARD = 1
        self.MOTOR_DIRECTION_BACKWARD = 0
        self.ENCODER_DIRECTION = -1

        signal.signal(signal.SIGINT, self.signal_handler)

    def __del__(self):
        # Shut down pigpiod LAST
        # self.pi.stop()
        print("[INFO] PiMotorDriver() ---- Deleting object...")

    def close(self):
        self.stop()
        self.__del__()

    def signal_handler(self, signal, frame):
        print('You pressed Ctrl+C!')
        self.__del__()
        sys.exit(0)

    def set_motor_direction(self,direction):
        self.pi.write(self.dirPin,direction)

    def flip_motor_direction(self,verbose=False):
        if verbose: print("[INFO] PiMotorDriver() --- Flipping motor direction...")
        self.MOTOR_DIRECTION_FORWARD = int(self.MOTOR_DIRECTION_FORWARD)
        self.MOTOR_DIRECTION_BACKWARD = int(self.MOTOR_DIRECTION_BACKWARD)
        self.ENCODER_DIRECTION = -1*self.ENCODER_DIRECTION

    def set_speed(self,speed_ratio):
        if(speed_ratio > 1.0): speed_ratio = 1.0
        elif(speed_ratio < -1.0): speed_ratio = -1.0

        if(speed_ratio > 0): self.set_motor_direction(self.MOTOR_DIRECTION_FORWARD)
        elif(speed_ratio < 0): self.set_motor_direction(self.MOTOR_DIRECTION_BACKWARD)
        else: self.stop()

        duty = int(math.fabs(speed_ratio) * 255)
        self.pi.set_PWM_dutycycle(self.pwmPin, duty)

    def stop(self,verbose=False):
        if verbose: print("[INFO] PiMotorDriver() --- Stopping motor...")
        self.pi.set_PWM_dutycycle(self.pwmPin, 0)

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
    ap.add_argument("--gpio", "-d", type=int, default=21, metavar='GPIO', help="Gpio responsible for setting motor direction")
    ap.add_argument("--pwm", "-p", type=int, default=20, metavar='GPIO', help="Pin responsible for setting motor PWM signal")
    ap.add_argument("--sleep", "-t", type=float, default=1.0, metavar='PERIOD', help="How long you want to drive the motor (secs)")
    ap.add_argument("--speed", "-s", type=float, default=0.0, metavar='SPEED', help="Speed you want to drive the motor (-1.0 < spd < 1.0)")
    # Store parsed arguments into array of variables
    args = vars(ap.parse_args())

    # Extract stored arguments array into individual variables for later usage in script
    dir = args["gpio"]
    pwm = args["pwm"]
    dt = args["sleep"]
    vel = args["speed"]

    pi = pigpio.pi()
    if not pi.connected:
        print("[ERROR] Could not connect to Raspberry Pi!")
        exit()
    motor = PiMotorDriver(pwm, dir,pi=pi)
    motor.set_speed(vel)
    time.sleep(dt)
    motor.stop()
    print("Successfully initialized 'PiMotorDriver' object")
    pi.stop()
