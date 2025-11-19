"""MQTT публикация данных."""

import ujson
from umqtt.simple import MQTTClient


class MQTTPublisher:
    def __init__(self, server: str, port: int, client_id: str, topic: bytes):
        self.server = server
        self.port = port
        self.client_id = client_id
        self.topic = topic
        self.client = None

    def connect(self) -> bool:
        print(f"Connecting to MQTT at {self.server}:{self.port}...")
        try:
            self.client = MQTTClient(self.client_id, self.server, port=self.port)
            self.client.connect()
            print("MQTT connected!")
            return True
        except Exception as e:
            print(f"MQTT connection failed: {e}")
            self.client = None
            return False

    def publish(self, data: dict) -> bool:
        if not self.client:
            return False

        try:
            payload = ujson.dumps(data)
            self.client.publish(self.topic, payload)
            print(f"Published: {payload}")
            return True
        except Exception as e:
            print(f"Publish error: {e}")
            self.disconnect()
            return False

    def disconnect(self):
        if self.client:
            try:
                self.client.disconnect()
            except:
                pass
            self.client = None
