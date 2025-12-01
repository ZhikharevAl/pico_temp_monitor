"""Сбор системных метрик Pico W"""

import machine
import gc
import time
import network
import ubinascii
import uos


class SystemMetrics:
    def __init__(self):
        self.temp_sensor = machine.ADC(4)
        self.vsys_pin = machine.ADC(29)
        self.start_time = time.time()
        self.wlan = network.WLAN(network.STA_IF)

        # Счётчики
        self.last_gc_time = time.time()
        self.gc_count = 0

        # Новые счетчики для дополнительных метрик
        self.mqtt_publish_success = 0
        self.mqtt_publish_failed = 0
        self.last_publish_time = time.time()
        self.max_temp = 0.0
        self.min_rssi = 0

    def get_temperature(self) -> float:
        """Температура процессора в °C."""
        reading = self.temp_sensor.read_u16() * 3.3 / 65535
        temperature = 27 - (reading - 0.706) / 0.001721
        temp = round(temperature, 2)

        # Отслеживаем максимальную температуру
        self.max_temp = max(self.max_temp, temp)
        return temp

    def get_memory_stats(self) -> dict:
        """Статистика памяти."""
        gc.collect()
        free_mem = gc.mem_free()
        allocated_mem = gc.mem_alloc()
        total_mem = free_mem + allocated_mem

        return {
            "memory_free_bytes": free_mem,
            "memory_allocated_bytes": allocated_mem,
            "memory_total_bytes": total_mem,
            "memory_usage_percent": round((allocated_mem / total_mem) * 100, 2),
            "memory_fragmentation": self.get_memory_fragmentation(),
        }

    def get_memory_fragmentation(self) -> float:
        """Оценка фрагментации памяти (0-100%)."""
        try:
            test_size = gc.mem_free() // 2
            test_block = bytearray(test_size)
            del test_block
            return 0.0
        except MemoryError:
            return round((1 - (test_size / gc.mem_free())) * 100, 2)
        except:
            return -1.0

    def get_vsys_voltage(self) -> float:
        """Напряжение системы Vsys."""
        reading = self.vsys_pin.read_u16()
        voltage = reading * (3.3 / 65535) * 3
        return round(voltage, 2)

    def get_cpu_frequency(self) -> int:
        """Частота CPU в Hz."""
        return machine.freq()

    def get_uptime(self) -> int:
        """Время работы в секундах."""
        return int(time.time() - self.start_time)

    def get_wifi_metrics(self, reconnect_count: int) -> dict:
        """Метрики WiFi соединения."""
        metrics = {
            "wifi_connected": 1 if self.wlan.isconnected() else 0,
            "wifi_status": self.wlan.status(),
            "wifi_reconnect_count": reconnect_count,
        }

        if self.wlan.isconnected():
            rssi = self.wlan.status("rssi")
            metrics["wifi_rssi_dbm"] = rssi

            # Отслеживаем минимальный (худший) RSSI
            if self.min_rssi == 0:
                self.min_rssi = rssi
            else:
                self.min_rssi = min(self.min_rssi, rssi)
            metrics["wifi_rssi_min_dbm"] = self.min_rssi

            # Качество сигнала в процентах
            signal_quality = max(0, min(100, 2 * (rssi + 100)))
            metrics["wifi_signal_quality_percent"] = round(signal_quality, 2)

            # Оценка стабильности (на основе качества сигнала)
            if signal_quality >= 80:
                metrics["wifi_link_quality"] = "excellent"
            elif signal_quality >= 60:
                metrics["wifi_link_quality"] = "good"
            elif signal_quality >= 40:
                metrics["wifi_link_quality"] = "fair"
            else:
                metrics["wifi_link_quality"] = "poor"

            # MAC и сетевая информация
            mac = ubinascii.hexlify(self.wlan.config("mac"), ":").decode()
            ifconfig = self.wlan.ifconfig()
            metrics["wifi_mac"] = mac
            metrics["wifi_ip"] = ifconfig[0]
            metrics["wifi_netmask"] = ifconfig[1]
            metrics["wifi_gateway"] = ifconfig[2]
            metrics["wifi_dns"] = ifconfig[3]

            # Канал WiFi
            try:
                channel = self.wlan.config("channel")
                metrics["wifi_channel"] = channel
            except:
                metrics["wifi_channel"] = -1

        else:
            metrics["wifi_rssi_dbm"] = -100
            metrics["wifi_signal_quality_percent"] = 0
            metrics["wifi_link_quality"] = "disconnected"
            metrics["wifi_mac"] = "disconnected"
            metrics["wifi_ip"] = "0.0.0.0"
            metrics["wifi_channel"] = -1

        return metrics

    def get_system_info(self) -> dict:
        """Информация о прошивке и ID устройства."""
        unique_id = ubinascii.hexlify(machine.unique_id()).decode()
        uname = uos.uname()

        return {
            "sys_unique_id": unique_id,
            "sys_version": uname.version,
            "sys_platform": uname.sysname,
            "sys_machine": uname.machine,
            "sys_release": uname.release,
        }

    def get_garbage_collector_stats(self) -> dict:
        """Статистика сборщика мусора."""
        current_time = time.time()
        time_since_last = current_time - self.last_gc_time

        self.gc_count += 1
        self.last_gc_time = current_time

        return {
            "gc_collections_total": self.gc_count,
            "gc_time_since_last": round(time_since_last, 2),
        }

    def get_power_metrics(self) -> dict:
        """Метрики питания и энергопотребления."""
        vsys = self.get_vsys_voltage()

        battery_percent = -1
        power_source = "unknown"

        if vsys > 4.5:
            power_source = "usb"
            battery_percent = 100
        elif vsys >= 3.3:
            power_source = "battery"
            battery_percent = round(((vsys - 3.3) / 0.9) * 100, 2)
        else:
            power_source = "critical"
            battery_percent = 0

        return {
            "vsys_voltage": vsys,
            "power_source": power_source,
            "battery_percent": max(0, min(100, battery_percent)),
        }

    def get_performance_metrics(self) -> dict:
        """Метрики производительности."""
        cpu_freq = self.get_cpu_frequency()

        if cpu_freq >= 250_000_000:
            cpu_mode = "performance"
        elif cpu_freq >= 125_000_000:
            cpu_mode = "normal"
        else:
            cpu_mode = "power_save"

        return {
            "cpu_frequency_hz": cpu_freq,
            "cpu_frequency_mhz": round(cpu_freq / 1_000_000, 2),
            "cpu_mode": cpu_mode,
            "cpu_temp_max_celsius": self.max_temp,
        }

    def get_mqtt_stats(self) -> dict:
        """Статистика MQTT публикаций."""
        current_time = time.time()
        publish_interval = current_time - self.last_publish_time

        total_publishes = self.mqtt_publish_success + self.mqtt_publish_failed
        success_rate = 0
        if total_publishes > 0:
            success_rate = round((self.mqtt_publish_success / total_publishes) * 100, 2)

        return {
            "mqtt_publish_success_total": self.mqtt_publish_success,
            "mqtt_publish_failed_total": self.mqtt_publish_failed,
            "mqtt_publish_total": total_publishes,
            "mqtt_publish_success_rate": success_rate,
            "mqtt_publish_interval_seconds": round(publish_interval, 2),
        }

    def record_mqtt_publish(self, success: bool):
        """Записать результат MQTT публикации."""
        if success:
            self.mqtt_publish_success += 1
        else:
            self.mqtt_publish_failed += 1
        self.last_publish_time = time.time()

    def get_health_status(self) -> dict:
        """Общий статус здоровья системы."""
        temp = self.get_temperature()
        mem_usage = (gc.mem_alloc() / (gc.mem_alloc() + gc.mem_free())) * 100

        # Определяем статус здоровья
        health_issues = []

        if temp > 70:
            health_issues.append("high_temperature")
        if mem_usage > 90:
            health_issues.append("high_memory_usage")
        if self.wlan.isconnected():
            rssi = self.wlan.status("rssi")
            if rssi < -80:
                health_issues.append("weak_wifi_signal")
        else:
            health_issues.append("wifi_disconnected")

        health_status = "healthy" if len(health_issues) == 0 else "warning"
        if temp > 75 or mem_usage > 95:
            health_status = "critical"

        return {
            "health_status": health_status,
            "health_issues_count": len(health_issues),
            "health_score": max(0, 100 - (len(health_issues) * 25)),
        }

    def get_all_metrics(self, reconnect_count: int, error_count: int = 0) -> dict:
        """Собрать все метрики."""
        metrics = {
            "temperature_celsius": self.get_temperature(),
            "uptime_seconds": self.get_uptime(),
            "error_count": error_count,
        }
        metrics.update(self.get_memory_stats())
        metrics.update(self.get_wifi_metrics(reconnect_count))
        metrics.update(self.get_system_info())
        metrics.update(self.get_garbage_collector_stats())
        metrics.update(self.get_power_metrics())
        metrics.update(self.get_performance_metrics())
        metrics.update(self.get_mqtt_stats())
        metrics.update(self.get_health_status())

        return metrics
