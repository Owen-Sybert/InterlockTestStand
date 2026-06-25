"""Hardware-free telemetry simulator for the TestStand execution dashboard."""

from __future__ import annotations

import math
import random
import socket
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from PyQt6.QtCore import QObject, QTimer, pyqtSignal


@dataclass
class TelemetryPacket:
    state: str
    timestamp: str
    cycle: int
    total_cycles: int
    progress_percent: float
    elapsed_seconds: float
    remaining_seconds: Optional[float]
    cycle_time_avg_sec: Optional[float]
    make_and_carry_time_sec: Optional[float]
    estop_active: bool
    connected: bool
    paused: bool
    motor_torque_percent: List[float] = field(default_factory=list)
    motor_temperatures_c: List[float] = field(default_factory=list)
    load_cells_lbf: List[float] = field(default_factory=list)
    temperatures_c: List[float] = field(default_factory=list)
    active_faults: List[str] = field(default_factory=list)
    logging_enabled: bool = True
    log_level: str = "INFO"
    telemetry_frequency_hz: Optional[float] = 10.0
    recording_enabled: bool = True
    last_saved_timestamp: str = "--:--:--"
    disk_space_gb: float = 235.0
    disk_space_percent: float = 78.0
    wifi_connected: bool = False
    wifi_ssid: str = "Unknown"
    ip_address: str = ""
    signal_strength_percent: int = 0
    remote_dashboard_connected: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return self.__dict__.copy()


class TelemetrySimulator(QObject):
    telemetry_updated = pyqtSignal(dict)
    log_updated = pyqtSignal(dict)

    def __init__(self, test_config: Dict[str, Any], interval_ms: int = 250, parent: QObject | None = None):
        super().__init__(parent)
        self.test_config = test_config or {}
        self.interval_ms = interval_ms
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self._network = self._get_basic_network_status()
        self.reset_for_new_test(self.test_config)

    def reset_for_new_test(self, test_config: Dict[str, Any] | None = None) -> None:
        if test_config is not None:
            self.test_config = test_config
        params = self.test_config.get("test_parameters", {})
        image_cfg = self.test_config.get("image_capture", {})
        logging_cfg = self.test_config.get("logging", {})
        self.total_cycles = int(params.get("number_of_cycles") or 1000000)
        self.cycle_time = float(params.get("cycle_time_sec") or 1.0)
        self.make_and_carry_time = params.get("make_and_carry_time_sec")
        self.image_frequency = image_cfg.get("frequency_cycles")
        self.logging_enabled = bool(logging_cfg.get("enabled", True))
        self.log_level = str(logging_cfg.get("log_level") or "INFO")
        self.telemetry_frequency_hz = logging_cfg.get("telemetry_frequency_hz") or 10.0
        self.start_time = time.monotonic()
        self.pause_started_at: Optional[float] = None
        self.total_paused_seconds = 0.0
        self.last_cycle = 0
        self.paused = False
        self.abort_requested = False
        self.completed = False
        self.faulted = False
        self.active_faults: List[str] = []
        self.last_saved_timestamp = "--:--:--"

    def start(self) -> None:
        if not self.timer.isActive():
            self.timer.start(self.interval_ms)
        self._emit_log("INFO", "Telemetry simulator started")

    def stop(self) -> None:
        if self.timer.isActive():
            self.timer.stop()
        self._emit_log("INFO", "Telemetry simulator stopped")

    def pause(self) -> None:
        if self.abort_requested or self.completed:
            return
        if not self.paused:
            self.paused = True
            self.pause_started_at = time.monotonic()
            self._emit_log("WARN", "Pause acknowledged")

    def resume(self) -> None:
        if self.abort_requested or self.completed:
            return
        if self.paused:
            if self.pause_started_at is not None:
                self.total_paused_seconds += time.monotonic() - self.pause_started_at
            self.pause_started_at = None
            self.paused = False
            self.faulted = False
            self.active_faults.clear()
            self._emit_log("INFO", "Resume acknowledged")

    def abort(self) -> None:
        self.abort_requested = True
        self.paused = False
        self._emit_log("ERROR", "Abort acknowledged")

    def trigger_fault(self, message: str = "Simulated fault condition") -> None:
        self.faulted = True
        self.paused = True
        self.pause_started_at = time.monotonic()
        self.active_faults = [message]
        self._emit_log("ERROR", f"FAULT: {message}")

    def _running_elapsed(self) -> float:
        elapsed = time.monotonic() - self.start_time - self.total_paused_seconds
        if self.paused and self.pause_started_at is not None:
            elapsed -= time.monotonic() - self.pause_started_at
        return max(0.0, elapsed)

    def _tick(self) -> None:
        elapsed = self._running_elapsed()
        if self.abort_requested:
            state = "ABORTED"
        elif self.faulted:
            state = "FAULT"
        elif self.paused:
            state = "PAUSED"
        elif self.completed:
            state = "COMPLETE"
        else:
            state = "RUNNING"
            self.last_cycle = min(self.total_cycles, int(elapsed / max(self.cycle_time, 0.01)))
            if self.last_cycle >= self.total_cycles and self.total_cycles > 0:
                self.completed = True
                state = "COMPLETE"
                self._emit_log("INFO", "Simulated test completed")

        progress = 0.0 if self.total_cycles <= 0 else min(100.0, (self.last_cycle / self.total_cycles) * 100.0)
        remaining_cycles = max(0, self.total_cycles - self.last_cycle)
        remaining = remaining_cycles * self.cycle_time if state not in ("ABORTED", "COMPLETE") else 0.0

        t = time.monotonic() - self.start_time
        motor_torque = [
            13.0 + 3.2 * math.sin(t * 0.80 + 0.0) + random.uniform(-0.7, 0.7),
            15.0 + 3.4 * math.sin(t * 0.70 + 1.2) + random.uniform(-0.7, 0.7),
            11.0 + 2.8 * math.sin(t * 0.60 + 2.0) + random.uniform(-0.7, 0.7),
            10.0 + 2.5 * math.sin(t * 0.50 + 3.0) + random.uniform(-0.7, 0.7),
        ]
        motor_temps = [
            38.0 + 4.0 * math.sin(t * 0.045 + i * 0.7) + random.uniform(-0.15, 0.15)
            for i in range(4)
        ]
        load_cells = [
            123.0 + 4.0 * math.sin(t * 0.40) + random.uniform(-1.0, 1.0),
            118.0 + 3.0 * math.sin(t * 0.37 + 1.0) + random.uniform(-1.0, 1.0),
        ]
        aux_temps = motor_temps + [
            31.0 + math.sin(t * 0.05 + 4.0) * 2.0,
            30.0 + math.sin(t * 0.05 + 5.0) * 2.0,
        ]

        if self.last_cycle > 0 and self.last_cycle % 25 == 0:
            self.last_saved_timestamp = datetime.now().strftime("%H:%M:%S")

        packet = TelemetryPacket(
            state=state,
            timestamp=datetime.now().strftime("%H:%M:%S"),
            cycle=self.last_cycle,
            total_cycles=self.total_cycles,
            progress_percent=progress,
            elapsed_seconds=elapsed,
            remaining_seconds=remaining,
            cycle_time_avg_sec=self.cycle_time,
            make_and_carry_time_sec=self.make_and_carry_time,
            estop_active=False,
            connected=True,
            paused=self.paused,
            motor_torque_percent=[round(max(0.0, x), 1) for x in motor_torque],
            motor_temperatures_c=[round(x, 1) for x in motor_temps],
            load_cells_lbf=[round(x, 1) for x in load_cells],
            temperatures_c=[round(x, 1) for x in aux_temps],
            active_faults=list(self.active_faults),
            logging_enabled=self.logging_enabled,
            log_level=self.log_level,
            telemetry_frequency_hz=self.telemetry_frequency_hz,
            recording_enabled=self.logging_enabled and state in ("RUNNING", "PAUSED", "FAULT"),
            last_saved_timestamp=self.last_saved_timestamp,
            wifi_connected=self._network["connected"],
            wifi_ssid=self._network["ssid"],
            ip_address=self._network["ip_address"],
            signal_strength_percent=self._network["signal_strength_percent"],
            remote_dashboard_connected=False,
        )
        self.telemetry_updated.emit(packet.to_dict())

    def _emit_log(self, level: str, message: str) -> None:
        self.log_updated.emit({"time": datetime.now().strftime("%H:%M:%S"), "level": level, "message": message})

    def _get_basic_network_status(self) -> Dict[str, Any]:
        ip = ""
        connected = False
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                ip = s.getsockname()[0]
                connected = bool(ip and not ip.startswith("127."))
        except OSError:
            try:
                ip = socket.gethostbyname(socket.gethostname())
                connected = bool(ip and not ip.startswith("127."))
            except OSError:
                ip = ""
        return {
            "connected": connected,
            "ssid": "Local Network" if connected else "Disconnected",
            "ip_address": ip,
            "signal_strength_percent": 86 if connected else 0,
        }
