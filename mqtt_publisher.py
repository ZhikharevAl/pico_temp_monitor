"""MQTT публикация данных."""

import ujson
import time
from umqtt.simple import MQTTClient


class MQTTPublisher:
    def __init__(self, server: str, port: int, client_id: str, topic: bytes):
        self.server = server
        self.port = port
        self.client_id = client_id
        self.topic = topic
        self.client = None

    def connect(self) -> bool:
        """Подключение к MQTT брокеру с повторными попытками."""
        print(f"Connecting to MQTT at {self.server}:{self.port}...")

        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                # Создаём клиента с увеличенным keepalive
                self.client = MQTTClient(
                    self.client_id,
                    self.server,
                    port=self.port,
                    keepalive=60,  # Увеличиваем keepalive до 60 секунд
                )

                # Пытаемся подключиться
                self.client.connect(clean_session=True)
                print("MQTT connected!")
                return True

            except OSError as e:
                print(f"MQTT connection attempt {attempt + 1}/{max_attempts} failed: {e}")
                self.client = None

                if attempt < max_attempts - 1:
                    # Ждём перед следующей попыткой
                    wait_time = (attempt + 1) * 2  # 2, 4, 6 секунд
                    print(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)

            except Exception as e:
                print(f"Unexpected error during MQTT connection: {e}")
                self.client = None
                return False

        print("MQTT connection failed after all attempts")
        return False

    def publish(self, data: dict) -> bool:
        """Публикация данных в MQTT."""
        if not self.client:
            print("No MQTT client available")
            return False

        try:
            payload = ujson.dumps(data)
            self.client.publish(self.topic, payload)
            print(f"Published: {payload}")
            return True

        except OSError as e:
            print(f"Publish error (network): {e}")
            self.disconnect()
            return False

        except Exception as e:
            print(f"Publish error: {e}")
            self.disconnect()
            return False

    def disconnect(self):
        """Отключение от MQTT брокера."""
        if self.client:
            try:
                self.client.disconnect()
                print("MQTT disconnected")
            except:
                pass
            self.client = None

    def is_connected(self) -> bool:
        """Проверка наличия активного подключения."""
        return self.client is not None
