#!/usr/bin/env python
import pigpio

import threading
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

def open_door(motor, speed,encoder,switches,encoder_limit=2945.0):
    motor.set_speed(speed)
    while 1:
        flag_stop_motor = False
        pos = encoder.get_current_position()
        print("[INFO] open_door() --- Position: %d" % pos)
        if(pos >= encoder_limit):
            flag_stop_motor = True
            print("[INFO] open_door() --- Encoder Max Position Reached Stopping Motor...")
            break
        for sw in switches:
            if sw.is_pressed:
                flag_stop_motor = True

        if flag_stop_motor:
            break

    motor.stop()

def close_door(motor, speed,encoder,switches,encoder_limit=2945.0):
    motor.set_speed(speed)
    while 1:
        flag_stop_motor = False
        pos = encoder.get_current_position()
        print("[INFO] close_door() --- Position: %d" % pos)
        if(pos <= encoder_limit):
            flag_stop_motor = True
            print("[INFO] close_door() --- Encoder Min Position Reached Stopping Motor...")
            break
        for sw in switches:
            if sw.is_pressed:
                flag_stop_motor = True

        if flag_stop_motor:
            break

    motor.stop()

if __name__ == "__main__":
    import time, argparse

    # Setup commandline argument(s) structures
    ap = argparse.ArgumentParser(description='Doggy Door Main')
    ap.add_argument("--upper", "-u", type=int, default=12, metavar='GPIO', help="Gpio responsible for setting motor direction")
    ap.add_argument("--lower", "-l", type=int, default=16, metavar='GPIO', help="Pin responsible for setting motor PWM signal")
    ap.add_argument("--pinA", "-a", type=int, default=18, metavar='GPIO', help="Encoder A pin")
    ap.add_argument("--pinB", "-b", type=int, default=23, metavar='GPIO', help="Encoder B pin")
    ap.add_argument("--gpio", "-d", type=int, default=21, metavar='GPIO', help="Gpio responsible for setting motor direction")
    ap.add_argument("--pwm", "-p", type=int, default=20, metavar='GPIO', help="Pin responsible for setting motor PWM signal")
    ap.add_argument("--speed", "-s", type=float, default=0.1, metavar='SPEED', help="Speed you want to drive the motor (-1.0 < spd < 1.0)")
    ap.add_argument("--limit", "-L", type=float, default=2945.0, metavar='ENC_POS', help="Encoder reading at max door open position.")
    ap.add_argument("--sleep", "-t", type=int, default=300, metavar='PERIOD', help="How long you want the program to run (secs)")
    ap.add_argument("--verbose","-v", action="store_true", help="increase output verbosity")
    # Store parsed arguments into array of variables
    args = vars(ap.parse_args())
    # Extract stored arguments array into individual variables for later usage in script
    upLim = args["upper"];           lowLim = args["lower"]
    pinA = args["pinA"];             pinB = args["pinB"]
    dir = args["gpio"];              pwm = args["pwm"]
    vel = args["speed"];             dt = args["sleep"]
    encLim = args["limit"]
    verbose = args["verbose"]

    pi = pigpio.pi()
    if not pi.connected:
        print("[ERROR] DoggyDoorMain() ---- Could not connect to Raspberry Pi!")
        exit()

    # Initialize Objects
    motor = PiMotorDriver(pwm, dir,pi=pi)
    enc = PiEncoder(pinA, pinB,pi=pi)
    upSwitch = PiLimitSwitch(upLim,"Upper Switch",pi=pi, verbose=True)
    lowSwitch = PiLimitSwitch(lowLim,"Lower Switch",pi=pi, verbose=True)

    pl = BLEDevicePoller(flag_hw_reset=True,debug_rssi=verbose)
    pl.add_device("BlueCharm","B0:91:22:F7:6D:55",'bluecharm')
    pl.add_device("tkr","C3:CE:5E:26:AD:0A",'trackr')
    update_thread = threading.Thread(target=pl.start)
    update_thread.start()

    # self.motor_thread = threading.Thread(target=self.motor_loop)
    # self.motor_thread.start()

    if not lowSwitch.check():
        print("[INFO] DoggyDoor not closed, closing door...")
        close_door(motor,-1.0*vel,enc,[lowSwitch],encoder_limit=-1.0*encLim)
        encOffset = enc.get_current_position()
    else:
        print("[INFO] DoggyDoor already closed.")
        encOffset = 0.0

    print("[INFO] DoggyDoor() --- Beginning Main loop...")
    while 1:
        if pl.are_devices_nearby():
            print("[%.2f] Devices in range..." % time.time())
            # motor.set_speed(vel)
            open_door(motor,vel,enc,[upSwitch],encoder_limit=encLim+encOffset)
            while 1:
                flags = []
                for i in range(5):
                    flags.append(pl.are_devices_nearby())
                    time.sleep(0.1)
                print("[DEBUG] Nearby Device Check = %s" % (str(flags)) )
                if True in flags:
                    print("Keeping door open (devices nearby).....")
                print("Keeping door open (devices nearby).....")
            print("No devices nearby, closing door...")
            close_door(motor,-1.0*vel,enc,[lowSwitch],encoder_limit=(-1.0*encLim)+encOffset)
        # if upSwitch.is_pressed:
        #     motor.stop()
        #     break
        # if lowSwitch.is_pressed:
        #     motor.stop()
        #     break
        time.sleep(0.1)

    print("Switch pressed, Stopping...")
    motor.stop()
    pl.terminate()
    update_thread.join()
    enc.close()
    motor.stop()
    upSwitch.close()
    lowSwitch.close()
    pl.close()
