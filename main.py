"""Главный файл - автоматически запускается при старте Pico."""

import time
from config import (
    CLIENT_ID,
    MQTT_PORT,
    MQTT_SERVER,
    MQTT_TOPIC,
    PUBLISH_INTERVAL,
    WIFI_PASSWORD,
    WIFI_SSID,
)
import machine

from wifi_manager import WiFiManager
from system_metrics import SystemMetrics
from mqtt_publisher import MQTTPublisher


class PicoMonitor:
    def __init__(self):
        self.wifi = WiFiManager(WIFI_SSID, WIFI_PASSWORD)
        self.metrics = SystemMetrics()
        self.metrics.wlan = self.wifi.wlan
        self.mqtt = MQTTPublisher(MQTT_SERVER, MQTT_PORT, CLIENT_ID, MQTT_TOPIC)
        self.reconnect_count = 0
        self.error_count = 0

    def setup(self) -> bool:
        """Инициализация системы."""
        print("\n=== System Initialization ===")

        # Подключение WiFi
        if not self.wifi.connect():
            print("ERROR: WiFi initialization failed")
            return False

        # Ждём стабилизации сети
        print("Waiting for network stability...")
        time.sleep(3)

        # Подключение MQTT
        if not self.mqtt.connect():
            print("ERROR: MQTT initialization failed")
            return False

        print("=== System Ready ===\n")
        return True

    def run(self):
        """Основной цикл работы."""
        print("Starting main loop...")

        while True:
            try:
                # Проверка WiFi подключения
                if not self.wifi.is_connected():
                    print("\n[!] WiFi disconnected, reconnecting...")
                    if not self.wifi.connect():
                        print("WiFi reconnection failed, waiting 10s...")
                        time.sleep(10)
                        continue
                    self.reconnect_count += 1

                    # После переподключения WiFi нужно восстановить MQTT
                    time.sleep(2)
                    if not self.mqtt.connect():
                        print("MQTT reconnection after WiFi failed")
                        time.sleep(5)
                        continue

                # Проверка MQTT подключения
                if not self.mqtt.is_connected():
                    print("\n[!] MQTT disconnected, reconnecting...")
                    if not self.mqtt.connect():
                        print("MQTT reconnection failed, waiting 10s...")
                        time.sleep(10)
                        continue

                # Сбор и публикация метрик
                metrics = self.metrics.get_all_metrics(self.reconnect_count)

                # Добавляем счётчик ошибок в метрики
                metrics["error_count"] = self.error_count

                print(f"\n--- Metrics at {time.time()} ---")
                print(f"Temp: {metrics.get('temperature_celsius')}°C")
                print(f"Memory: {metrics.get('memory_usage_percent')}%")
                print(f"WiFi RSSI: {metrics.get('wifi_rssi_dbm')} dBm")
                print(f"Uptime: {metrics.get('uptime_seconds')}s")

                # Публикация
                if self.mqtt.publish(metrics):
                    self.error_count = 0  # Сброс счётчика при успехе
                else:
                    self.error_count += 1
                    print(f"Publish failed (error count: {self.error_count})")

                    # Если много ошибок подряд - переподключаемся
                    if self.error_count >= 3:
                        print("Too many errors, forcing reconnection...")
                        self.mqtt.disconnect()
                        time.sleep(5)
                        continue

                # Ожидание перед следующей итерацией
                time.sleep(PUBLISH_INTERVAL)

            except MemoryError as e:
                print(f"\n[!] Memory Error: {e}")
                import gc

                gc.collect()
                print(f"Memory freed, retrying...")
                time.sleep(5)

            except Exception as e:
                print(f"\n[!] Unexpected Error: {e}")
                self.error_count += 1
                self.mqtt.disconnect()
                time.sleep(5)


def main():
    """Точка входа."""
    try:
        print("\n" + "=" * 50)
        print("Raspberry Pi Pico W Monitoring System")
        print("=" * 50)

        monitor = PicoMonitor()

        if monitor.setup():
            monitor.run()
        else:
            print("\n[FATAL] Initialization failed!")
            print("Please check:")
            print("  1. WiFi credentials in config.py")
            print("  2. MQTT broker is running")
            print("  3. Network connectivity")
            print("\nRebooting in 30 seconds...")
            time.sleep(30)
            machine.reset()

    except KeyboardInterrupt:
        print("\n\n[*] Stopped by user")

    except Exception as e:
        print(f"\n[CRITICAL ERROR] {e}")
        print("Rebooting in 10 seconds...")
        time.sleep(10)
        machine.reset()


# Запуск
if __name__ == "__main__":
    main()
