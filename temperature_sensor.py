"""Работа с температурным датчиком."""

import machine


class TemperatureSensor:
    def __init__(self):
        self.sensor = machine.ADC(4)

    def read(self) -> float:
        reading = self.sensor.read_u16() * 3.3 / 65535
        temperature = 27 - (reading - 0.706) / 0.001721
        return round(temperature, 2)
