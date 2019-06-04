import os, sys, re, time
import subprocess as sp
import threading
import pprint
import signal

pp = pprint.PrettyPrinter(indent=4)

class BLEDevicePoller(object):
    def __init__(self, flag_hw_reset=False):
        if flag_hw_reset: self.restart_hardware()

        signal.signal(signal.SIGINT, self.signal_handler)
        self.btmon = None
        self.lescan = None
        self.prcs = []
        self.threads = []
        self.thread = None
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
        self.flag_exit_update = False

    def __del__(self):
        self.flag_exit_update = True

        # Stop any threads that may have been initialized
        self.thread.join()
        if len(self.threads) != 0:
            print("[INFO] Killing any initialized threads...")
            [th.join() for th in self.threads]

        # Kill the btmon service if it has been started
        if self.btmon is not None:
            print("[INFO] Killing 'btmon' and 'lescan' processes...")
            self.kill_btmon()
        # Kill any subprocesses if any exist
        if len(self.prcs) != 0:
            print("[INFO] Killing any initialized subprocesses...")
            [prc.kill() for prc in self.prcs]

    def signal_handler(self, signal, frame):
        print('You pressed Ctrl+C!')
        self.__del__()
        sys.exit(0)

    def add_device(self,name,baddr,type, verbose=True):
        tmpDev = {"name": str(name),
                  "addr": str(baddr),
                  "type": int(type),
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
        if self.thread is not None: self.thread.start()
        if len(self.threads) != 0:
            [thread.start() for thread in self.threads]
        print("[INFO] All threads started.")

    def stop_threads(self, verbose=True):
        if(verbose): print("[INFO] Stopping any initialized threads...")
        self.thread.join()
        if len(self.threads) != 0:
            [thread.join() for thread in self.threads]

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
                if self.flag_exit_update:
                    break
        else: print("[ERROR] 'btmon' service has not been started. Exiting 'update_devices()'.")
        print("[INFO] update_devices() --- Exited.")
        self.flag_exit_update = False

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
            # prevDevs = self.previous_devices

            # if lastSeen != curDevs[0]["times_seen"]:
            #     lastSeen = curDevs[0]["times_seen"]
            #     test_dt = time.time() - testT
            #     print("updated values of [%d] took %s secs" % (curDevs[0]["times_seen"],str(test_dt)))
            #     testT = time.time()

            # self.check_proximity(curDevs, prevDevs)
            # prevDevs = curDevs

            # Check for periodic event
            if self.dt >= check_period:
                self.last_time = time.time()
                self.nChecks+=1

                if prevDevs is None: prevDevs = [dict(d) for d in curDevs]


                self.check_proximity(curDevs,prevDevs)

                # if prevDev is None: prevDev = dict(curDev)
                # print(curDev["times_seen"],prevDev["times_seen"])
                # prevDev = dict(curDev)
                prevDevs = [dict(d) for d in curDevs]

                # if len(prevDevs) <= 0: prevDevs.append(dict(curDevs[0]))
                # else: prevDevs[0] = dict(curDevs[0])

                # curDevs = self.get_devices()
                # self.check_proximity(curDevs, prevDevs,verbose=False)
                # prevDev = curDev
                # self.check_proximity(self.get_devices())
                # self.previous_devices = curDevs
                # oldTest = newTest

            # Check for exit conditions
            if self.dt >= dt:
                print("[%.2f] Exiting loop." % now)
                self.nChecks = 0
                break
            # Pause
            time.sleep(0.0001)
            if self.flag_exit_update: break
        print("[INFO] loop() --- Loop exited. Initializing shut down...")
        self.flag_exit_update = True
        self.__del__()

    def check_proximity(self, curDevs,prevDevs, verbose=False):
        is_device_in_range = False
        nNearDevices = 0
        if len(prevDevs) <= 0: return is_device_in_range

        # if len(prevDevs) > 0:
        #     for i,pd in enumerate(prevDevs):
        #         if(verbose): print("Checking current devices with [%s]:" % (pd["addr"]) )
        #         for j,cd in enumerate(curDevs):
        #             if cd["addr"] == pd["addr"]:
        #                 print(cd["times_seen"],pd["times_seen"])


        for i in range(self.nDevices):
            # if verbose:
            #     print(curDevs[i])
            #     print(" ------------ ")
            #     print(prevDevs[i])
            #     print(" ============ ")

            if curDevs[i]["times_seen"] == prevDevs[i]["times_seen"]:
                if False: print("[INFO] check_proximity() ---- No new updates for device [%d], skipping...." % (i))
            else:
                print("Device [%s] detected with RSSI = %d" % (curDevs[i]["addr"],curDevs[i]["rssi"]))
                tmpVal = curDevs[i]["rssi"]
                # is_device_in_range = True
                if tmpVal >= -70:
                    is_device_in_range = True
                    nNearDevices+=1

        # tmpStr = str(dev["name"] + ": [nSeen=" + str(dev["times_seen"]) + ", RSSI=" + str(dev["rssi"])+", lastCount=" + str(dev["last_count"]) + "]")
        # print(tmpStr)

        if not is_device_in_range:
            if verbose: print("[INFO] check_proximity() ---- No Devices in range.")
        else: print("[INFO] check_proximity() ---- %d Devices found in range. BEGIN DOOR OPEN SEQUENCE." % (nNearDevices))
        return is_device_in_range

if __name__ == "__main__":
    pl = BLEDevicePoller(flag_hw_reset=True)
    pl.add_device("BlueCharm","B0:91:22:F7:6D:55",0)
    # pl.add_device("tkr","C3:CE:5E:26:AD:0A",1)

    pl.start_btmon()
    pl.thread = threading.Thread(target=pl.update_devices)
    pl.thread.start()
    pl.loop()
