"""Главный файл - автоматически запускается при старте Pico."""

import time
import machine

from config import *
from wifi_manager import WiFiManager
from temperature_sensor import TemperatureSensor
from mqtt_publisher import MQTTPublisher


class PicoMonitor:
    def __init__(self):
        self.wifi = WiFiManager(WIFI_SSID, WIFI_PASSWORD)
        self.temperature = TemperatureSensor()
        self.mqtt = MQTTPublisher(MQTT_SERVER, MQTT_PORT, CLIENT_ID, MQTT_TOPIC)

    def setup(self) -> bool:
        if not self.wifi.connect():
            return False
        if not self.mqtt.connect():
            return False
        return True

    def run(self):
        while True:
            try:
                if not self.wifi.is_connected():
                    print("Reconnecting WiFi...")
                    if not self.wifi.connect():
                        time.sleep(10)
                        continue

                if not self.mqtt.client:
                    print("Reconnecting MQTT...")
                    if not self.mqtt.connect():
                        time.sleep(10)
                        continue

                temp = self.temperature.read()
                self.mqtt.publish({"temperature": temp})
                time.sleep(PUBLISH_INTERVAL)

            except Exception as e:
                print(f"Error: {e}")
                self.mqtt.disconnect()
                time.sleep(5)


try:
    monitor = PicoMonitor()
    if monitor.setup():
        print("System ready!")
        monitor.run()
    else:
        print("Init failed!")
except Exception as e:
    print(f"Critical error: {e}")
    time.sleep(10)
    machine.reset()
