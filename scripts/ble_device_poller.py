import os, sys, re, time
import subprocess as sp
import threading
import signal
import enum

class BeaconType(enum.Enum):
    trackr = -60
    bluecharm = -70
    tile = -50

class BLEDevicePoller(object):
    def __init__(self, flag_hw_reset=False):
        if flag_hw_reset: self.restart_hardware()

        signal.signal(signal.SIGINT, self.signal_handler)
        self.btmon = None
        self.lescan = None
        self.prcs = []
        self.threads = []
        self.update_thread = None
        self.motor_thread = None
        self.lock = threading.Lock()

        self.dt = 0
        self.nLoops = 0
        self.nChecks = 0
        self.nUpdates = 0
        self.nDevices = 0
        self.init_time = time.time()
        self.last_time = time.time()
        self.paired_devices = []
        self.found_devices = []
        self.previous_devices = []

        self.update_rate = 0.1
        self.flag_stop = False
        self.flag_open_door = False
        self.is_door_opening = False

    def __del__(self):
        self.flag_stop = True
        # Stop any threads that may have been initialized
        self.stop_threads()
        # Kill the btmon service if it has been started
        print("[INFO] Killing 'btmon' and 'lescan' processes...")
        self.kill_btmon()
        # Kill any subprocesses if any exist
        if len(self.prcs) != 0:
            print("[INFO] Killing any initialized subprocesses...")
            [prc.kill() for prc in self.prcs]

    def start(self):
        self.start_btmon()
        self.update_thread = threading.Thread(target=self.update_devices)
        self.update_thread.start()
        self.loop()

    def close(self):
        self.__del__()


    def signal_handler(self, signal, frame):
        print('You pressed Ctrl+C!')
        self.__del__()
        sys.exit(0)

    def add_device(self,name,baddr,beacon_type, verbose=True):
        try: devtype = BeaconType[str(beacon_type)]
        except:
            print("[INFO] add_device() ---- Invalid 'beacon_type' passed in, defaulting to BeaconType['bluecharm'].")
            devtype = BeaconType['bluecharm']
            pass
        tmpDev = {"name": str(name),
                  "addr": str(baddr),
                  "beacon_type": devtype,
                  "seen": 0.0,
                  "last_seen": 0.0,
                  "times_seen": 0,
                  "last_count": 0,
                  "rssi": 0
                }
        if verbose: print("Adding Device [%s] with address '%s' from list of known devices." % (name, baddr))
        self.paired_devices.append(tmpDev)
        self.nDevices+=1

    def remove_device(self, id):
        is_found = False
        for i,dev in enumerate(self.paired_devices):
            if id in dev.itervalues():
                print("Removing Device [%s] with address '%s' from list of known devices." % (dev["name"], dev["addr"]))
                is_found = True
                del self.paired_devices[i]
                self.nDevices-=1
                break
        if not is_found:
            print("[WARNING] Could not find a device with id = '%s' within list of known devices." % (id))

    def restart_hardware(self,verbose=True):
        if(verbose): print("[INFO] Turning off 'hci0' hardware interface...")
        try: sp.call("sudo hciconfig hci0 down".split(" "))
        except:
            print("[ERROR] Could not shut off 'hci0' hardware interface.")
            pass
        time.sleep(1.0)
        if(verbose): print("[INFO] Turning on 'hci0' hardware interface...")
        try: sp.call("sudo hciconfig hci0 up".split(" "))
        except:
            print("[ERROR] Could not turn on 'hci0' hardware interface.")
            pass
        print("[INFO] Finished resetting bluetooth hardware.")
        time.sleep(1.0)

    def start_btmon(self,verbose=True):
        if(verbose): print("[INFO] Starting 'btmon' process...")
        self.btmon = sp.Popen("sudo btmon".split(" "),stdout=sp.PIPE,stderr=sp.PIPE)
        if(verbose): print("[INFO] Starting 'lescan' process...")
        self.lescan = sp.Popen("sudo hcitool lescan --duplicates".split(" "),stdout=sp.PIPE,stderr=sp.PIPE)
        print("[INFO] Process 'btmon' and 'lescan' initialized.")

    def kill_btmon(self, verbose=True):
        if(verbose): print("[INFO] Killing 'btmon' process...")
        if self.btmon is not None: self.btmon.kill()
        try: sp.call(["sudo", "pkill", "-9", "-f", "btmon"])
        except: pass

        if(verbose): print("[INFO] Killing 'lescan' process...")
        if self.lescan is not None: self.lescan.kill()
        try: sp.call(["sudo", "pkill", "-9", "-f", "hcitool"])
        except: pass
        print("[INFO] Processes 'btmon' and 'lescan' terminated.")

    def start_threads(self,verbose=True):
        if(verbose): print("[INFO] Starting threads...")
        if self.update_thread is not None: self.update_thread.start()
        if self.motor_thread is not None: self.motor_thread.start()
        if len(self.threads) != 0:
            [thread.start() for thread in self.threads]
        print("[INFO] All threads started.")

    def stop_threads(self, verbose=True):
        if(verbose): print("[INFO] Stopping any initialized threads...")
        if self.update_thread is not None: self.update_thread.join()
        if self.motor_thread is not None: self.motor_thread.join()

        if len(self.threads) != 0:
            print("[INFO] Killing any initialized threads...")
            [th.join() for th in self.threads]

        print("[INFO] All threads stopped.")

    def search_time(self, line):
        tmpSearch = re.search("\[.*?\] (.*)", line)
        if tmpSearch: return float(tmpSearch.group(1))
        else: return None

    def search_device_name(self, line):
        tmpSearch = re.search("Name.*: (.*)", line)
        if tmpSearch: return tmpSearch.group(1)
        else: return None

    def search_rssi(self, line):
        tmpSearch = re.search("RSSI: (.*) dBm?", line)
        if tmpSearch: return int(tmpSearch.group(1))
        else: return None

    def update_devices(self):
        count = 0
        last_count = 0
        if self.btmon is not None:
            self.found_devices = list(self.paired_devices)
            for line in iter(self.btmon.stdout.readline, b''):
                count+=1
                self.lock.acquire()
                copyDevs = list(self.found_devices)
                for i,dev in enumerate(copyDevs):
                    if dev["addr"] in line.rstrip():
                        dev["times_seen"]+=1
                        dev["last_seen"]=dev["seen"]
                        dev["seen"] = time.time()
                        dev["last_count"] = count
                    tmpRssi = self.search_rssi(line.rstrip())
                    if tmpRssi and (count - dev["last_count"]) < 15:
                        dev["rssi"] = tmpRssi

                self.found_devices = copyDevs
                self.nUpdates+=1
                self.lock.release()
                time.sleep(0)
                if self.flag_stop:
                    break
        else: print("[ERROR] 'btmon' service has not been started. Exiting 'update_devices()'.")
        print("[INFO] update_devices() --- Exited.")

    def get_devices(self):
        self.lock.acquire()
        foundDevs = list(self.found_devices)
        self.lock.release()
        return foundDevs

    def loop(self, dt=30, check_period=0.5,verbose=True):
        self.last_time = time.time()
        lastSeen = []
        testT = time.time()
        prevDevs = None
        prevDev = None
        while 1:
            self.nLoops+=1
            now = time.time()
            self.dt = now - self.last_time
            curDevs = self.get_devices()

            # Check for periodic event
            if self.dt >= check_period:
                self.last_time = time.time()
                self.nChecks+=1
                if prevDevs is None: prevDevs = [dict(d) for d in curDevs]

                self.flag_open_door = self.check_proximity(curDevs,prevDevs)
                if verbose: print("[INFO] motor_loop() ---- Opening Door...")
                # Store Current found devices for next check sequence
                prevDevs = [dict(d) for d in curDevs]

            # Check for exit conditions
            if self.dt >= dt:
                print("[%.2f] Exiting loop." % now)
                self.nChecks = 0
                break
            # Pause
            time.sleep(0.0001)
            if self.flag_stop: break
        print("[INFO] loop() --- Loop exited. Initializing shut down...")
        self.flag_stop = True
        self.close()

    def check_proximity(self, curDevs,prevDevs, debug_readings=False,verbose=False):
        flag_open_door = False
        nNearDevices = 0
        readings = self.verify_device_readings(curDevs,prevDevs)

        for dev in readings:
            if not dev["has_active_readings"]:
                if verbose: print("[INFO] check_proximity() ---- No new updates for device [%s], skipping...." % (dev["addr"]))
            else:
                if debug_readings: print("[INFO] check_proximity() -------- Device [%s] detected with RSSI = %d. (Threshold = %d)" % (dev["addr"],dev["rssi"],dev["beacon_type"].value))

                if dev["rssi"] >= dev["beacon_type"].value:
                    flag_open_door = True
                    nNearDevices+=1

        if not flag_open_door:
            if verbose: print("[INFO] check_proximity() ---- No Devices in range.")
        else:
            if verbose: print("[INFO] check_proximity() ---- %d Devices found in range. BEGIN DOOR OPEN SEQUENCE." % (nNearDevices))
        return flag_open_door

    def verify_device_readings(self,current_devices,previous_devices,verbose=False):
        readings = []
        if len(current_devices) > 0:
            for cd in current_devices:
                is_matched = False
                is_fresh_reading = False
                if len(previous_devices) > 0:
                    if(verbose): print("[INFO] verify_device_readings() --- Checking current device [%s] for previous found devices:" % (cd["addr"]) )
                    for pd in previous_devices:
                        if cd["addr"] == pd["addr"]:
                            if(verbose): print("[INFO] verify_device_readings() ---- Current Device [%s] matched with a previous device reading." % (cd["addr"]))
                            is_matched = True
                            if cd["times_seen"] == pd["times_seen"]: is_fresh_reading = False
                            else: is_fresh_reading = True
                            cd["has_active_readings"] = is_fresh_reading
                            readings.append(cd)
                            # readings.append([cd["rssi"],is_fresh_reading])
                    if not is_matched:
                        if(verbose): print("[INFO] verify_device_readings() --- Current device [%s] has no previously found readings, therefore fresh readings." % (cd["addr"]))
                        cd["has_active_readings"] = True
                        readings.append(cd)
                        # readings.append([cd["rssi"],True])
                else:
                    if(verbose): print("[INFO] verify_device_readings() ---- No previous devices readings, therefore fresh readings.")
                    cd["has_active_readings"] = True
                    readings.append(cd)
                    # readings.append([cd["rssi"],True])
        else:
            print("[INFO] verify_device_readings() ---- No devices currently found.")
            return []

        if(verbose): print("[INFO] verify_device_readings() --- Verified %d device readings" % (len(readings)))
        return readings

if __name__ == "__main__":
    pl = BLEDevicePoller(flag_hw_reset=True)
    pl.add_device("BlueCharm","B0:91:22:F7:6D:55",'bluecharm')
    pl.add_device("tkr","C3:CE:5E:26:AD:0A",'trackr')

    pl.start()
