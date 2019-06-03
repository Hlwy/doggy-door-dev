import os, sys, re, time
import subprocess as sp
import threading
import pprint

pp = pprint.PrettyPrinter(indent=4)

class BLEDevicePoller(object):
    def __init__(self,auto_start_btmon=False):
        self.btmon = None
        self.lescan = None
        self.prcs = []
        self.threads = []
        self.lock = threading.Lock()


        self.dt = 0
        self.nLoops = 0
        self.nChecks = 0
        self.nUpdates = 0
        self.init_time = time.time()
        self.last_time = time.time()
        self.paired_devices = []

        self.flag_update_exit = False
        if auto_start_btmon: self.start_btmon()

    def __del__(self):
        # Kill the btmon service if it has been started
        if self.btmon is not None:
            print("[INFO] Killing 'btmon' service...")
            self.kill_btmon()
        # Kill any subprocesses if any exist
        if len(self.prcs) != 0:
            print("[INFO] Killing any initialized subprocesses...")
            [prc.kill() for prc in self.prcs]
        # Stop any threads that may have been initialized
        if len(self.threads) != 0:
            print("[INFO] Killing any initialized threads...")
            [th.join() for th in self.threads]

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

    def remove_device(self, id):
        is_found = False
        for i,dev in enumerate(self.paired_devices):
            if id in dev.itervalues():
                print("Removing Device [%s] with address '%s' from list of known devices." % (dev["name"], dev["addr"]))
                is_found = True
                del self.paired_devices[i]
                break
        if not is_found:
            print("[WARNING] Could not find a device with id = '%s' within list of known devices." % (id))

    def start_btmon(self,verbose=True):
        if(verbose): print("[INFO] Starting 'btmon' process...")
        self.btmon = sp.Popen("sudo btmon".split(" "),stdout=sp.PIPE,stderr=sp.PIPE)
        if(verbose): print("[INFO] Starting 'lescan' process...")
        self.lescan = sp.Popen("sudo hcitool lescan --duplicates".split(" "),stdout=sp.PIPE,stderr=sp.PIPE)
        print("[INFO] Process 'btmon' and 'lescan' initialized.")

    def kill_btmon(self, verbose=True):
        if(verbose): print("[INFO] Killing 'btmon' process...")
        if self.btmon is not None: self.btmon.kill()
        if self.lescan is not None: self.lescan.kill()

        try: sp.call(["sudo", "pkill", "-9", "-f", "btmon"])
        except: pass
        try: sp.call(["sudo", "pkill", "-9", "-f", "hcitool"])
        except: pass
        print("[INFO] Process 'btmon' terminated.")

    def start_thread(self, verbose=True):
        if(verbose): print("[INFO] Starting 'btmon' thread...")
        self.thread.start()
        print("[INFO] 'btmon' thread started.")

    def stop_thread(self, verbose=True):
        if(verbose): print("[INFO] Killing 'btmon' thread...")
        self.thread.join()
        print("[INFO] 'btmon' thread stopped.")

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

    def update_devices(self,verbose=True):
        count = 0
        last_count = 0
        if self.btmon is not None:
            for line in iter(self.btmon.stdout.readline, b''):
                self.device_update_exited = False
                count+=1
                dispStr = ""
                for i,dev in enumerate(self.paired_devices):
                    if dev["addr"] in line.rstrip():
                        dev["times_seen"]+=1
                        dev["last_seen"]=dev["seen"]
                        dev["seen"] = time.time()
                        dev["last_count"] = count
                    tmpRssi = self.search_rssi(line.rstrip())
                    if tmpRssi and (count - dev["last_count"]) < 15:
                        dev["rssi"] = tmpRssi

                    # tmpStr = str(dev["name"] + ": [Seen=" + str(dev["times_seen"]) + ", RSSI=" + str(dev["rssi"])+"] --------- ")
                    tmpStr = str(pp.pprint(dev))
                    dispStr = dispStr + tmpStr
                print(dispStr)
                print("==================")
                self.nUpdates+=1
                if self.flag_update_exit:
                    break
        else: print("[ERROR] 'btmon' service has not been started. Exiting 'update_devices()'.")
        print("[INFO] update_devices() --- Exited.")
        self.flag_update_exit = False

    def loop(self, dt=30, check_period=10.0):
        self.last_time = time.time()
        while 1:
            self.nLoops+=1
            now = time.time()
            self.dt = now - self.last_time

            # Do something
            # try: print(self.data[-1])
            # except: pass

            # Check for periodic event
            if self.dt >= check_period:
                self.last_time = time.time()
                self.nChecks+=1
                # print("[%.2f] Periodic Function..." % dt)

            # Check for exit conditions
            if self.dt >= dt:
                print("[%.2f] Exiting loop." % now)
                self.nChecks = 0
                break
            # Pause
            time.sleep(0.5)


if __name__ == "__main__":
    pl = BLEDevicePoller()
    pl.add_device("BlueCharm","B0:91:22:F7:6D:55",0)

    pl.start_btmon()
    pl.update_devices()
