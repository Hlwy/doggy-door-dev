import threading
from scripts.ble_device_poller import BLEDevicePoller

if __name__ == "__main__":
    pl = BLEDevicePoller(flag_hw_reset=True)
    pl.add_device("BlueCharm","B0:91:22:F7:6D:55",'bluecharm')
    pl.add_device("tkr","C3:CE:5E:26:AD:0A",'trackr')

    pl.start_btmon()
    pl.update_thread = threading.Thread(target=pl.update_devices)
    pl.motor_thread = threading.Thread(target=pl.motor_loop)
    pl.update_thread.start()
    pl.motor_thread.start()
    pl.loop()
