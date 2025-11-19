"""Управление WiFi подключением."""

import time
import network


class WiFiManager:
    def __init__(self, ssid: str, password: str):
        self.ssid = ssid
        self.password = password
        self.wlan = network.WLAN(network.STA_IF)

    def connect(self) -> bool:
        print(f"Connecting to WiFi '{self.ssid}'...")
        self.wlan.active(True)
        self.wlan.connect(self.ssid, self.password)

        max_wait = 15
        while max_wait > 0:
            if self.wlan.status() < 0 or self.wlan.status() >= 3:
                break
            max_wait -= 1
            print("Waiting for connection...")
            time.sleep(1)

        if self.wlan.status() != 3:
            print("WiFi connection failed")
            return False

        print(f"Connected! IP: {self.wlan.ifconfig()[0]}")
        return True

    def is_connected(self) -> bool:
        return self.wlan.status() == 3
