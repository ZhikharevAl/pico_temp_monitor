import time

import network

WIFI_SSID = ""
WIFI_PASSWORD = ""

wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect(WIFI_SSID, WIFI_PASSWORD)

print("Connecting...")
while not wlan.isconnected() and wlan.status() >= 0:
    time.sleep(1)

if wlan.isconnected():
    print("Wi-Fi Connected! IP:", wlan.ifconfig()[0])

    import mip

    mip.install("umqtt.simple")
    print("Installation complete!")
else:
    print("Failed to connect to Wi-Fi.")
