"""1024x600 PyQt6 execution dashboard shell for TestStandGUI.

This dashboard is designed for a 7-inch 1024x600 touchscreen.  It uses a
left-side navigation bar and a QStackedWidget so each page can stay readable.
The dashboard is still hardware-free and is driven by utils.telemetrySimulator
until the future gRPC/C++ runtime replaces the simulator.
"""

from __future__ import annotations

import json
import math
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from PyQt6.QtCore import QPointF, QRectF, Qt, QTimer
from PyQt6.QtGui import QColor, QFont, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from utils.storedDataPaths import getSavedTestsDir, getResultsDir
from utils.telemetrySimulator import TelemetrySimulator
from app.applicationState import ApplicationState


DARK_STYLE = """
QWidget {
    background-color: #071522;
    color: #E8F0F8;
    font-family: Segoe UI, Arial, sans-serif;
    font-size: 16px;
}
QFrame#panel {
    background-color: #0B1D2B;
    border: 1px solid #244055;
    border-radius: 6px;
}
QFrame#sideBar {
    background-color: #0A1B29;
    border-right: 1px solid #22384A;
}
QLabel#sideLogo {
    background-color: #1F497D;
    border: 1px solid #31506A;
    border-radius: 4px;
    padding: 4px;
}
QFrame#topBar, QFrame#bottomBar {
    background-color: #0A1B29;
    border: 1px solid #22384A;
}
QLabel#sectionTitle {
    color: #2BA7FF;
    font-weight: bold;
    font-size: 16px;
}
QLabel#largeValue {
    color: white;
    font-size: 30px;
    font-weight: 700;
}
QLabel#mediumValue {
    color: white;
    font-size: 22px;
    font-weight: 600;
}
QLabel#smallMuted {
    color: #A8B7C5;
    font-size: 17px;
}
QPushButton {
    background-color: #0D2638;
    border: 1px solid #31506A;
    border-radius: 5px;
    padding: 7px 8px;
    color: white;
    font-size: 16px;
}
QPushButton:hover { background-color: #14364E; }
QPushButton#navButton {
    border: none;
    background-color: transparent;
    padding: 8px 4px;
    text-align: left;
}
QPushButton#navSelected {
    background-color: #0E5BA3;
    border: 1px solid #1D75C4;
    border-radius: 6px;
    padding: 8px 4px;
    text-align: left;
}
QPushButton#runButton {
    background-color: #0D5F34;
    border: 1px solid #56C51F;
    font-weight: bold;
    font-size: 17px;
}
QPushButton#pauseButton {
    background-color: #F4A900;
    color: #101010;
    border: 1px solid #FFC145;
    font-weight: bold;
    font-size: 17px;
}
QPushButton#abortButton {
    background-color: #D93025;
    color: white;
    border: 1px solid #FF5548;
    font-weight: bold;
    font-size: 17px;
}
QPushButton#clearButton { background-color: #142C3E; color: #DDE7F0; }
QProgressBar {
    background-color: #132B3C;
    border: 1px solid #264359;
    border-radius: 4px;
    text-align: center;
    height: 14px;
}
QProgressBar::chunk { background-color: #2BA7FF; border-radius: 3px; }
QPlainTextEdit {
    background-color: #071522;
    border: none;
    color: #DDE7F0;
    font-family: Consolas, monospace;
    font-size: 17px;
}
"""

STATE_COLORS = {
    "IDLE": "#173044",
    "HOMING REQUIRED": "#2BA7FF",
    "HOMING": "#2BA7FF",
    "RUNNING": "#155E33",
    "PAUSED": "#F4A900",
    "COMPLETE": "#56C51F",
    "FAULT": "#D93025",
    "ABORTED": "#D93025",
}

ASSET_DIR = Path(__file__).resolve().parents[1] / "assets"
LOGO_PATH = ASSET_DIR / "C.J. Anderson - LOGO TEXT ONLY 250X100.png"


def _strip_leading_zero_time(value: str) -> str:
    """Return 12-hour time without a leading zero, e.g. 04:30 PM -> 4:30 PM."""
    return value[1:] if value.startswith("0") else value


def fmt_duration_words(seconds: Optional[float]) -> str:
    """Format duration as explicit operator-facing text, e.g. 4d 18hr 32min 14sec."""
    if seconds is None:
        return "--"
    seconds = max(0, int(seconds))
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, secs = divmod(rem, 60)
    return f"{days}d {hours:02d}hr {minutes:02d}min {secs:02d}sec"


def fmt_date(dt: Optional[datetime]) -> str:
    if dt is None:
        return "Pending"
    return dt.strftime("%b %d, %Y")


def fmt_time(dt: Optional[datetime]) -> str:
    if dt is None:
        return "Pending"
    return _strip_leading_zero_time(dt.strftime("%I:%M %p"))


def fmt_eta(dt: Optional[datetime]) -> str:
    if dt is None:
        return "--"
    return f"{_strip_leading_zero_time(dt.strftime('%I:%M %p'))} on {dt.strftime('%b %d, %Y')}"


def fmt_log_timestamp(dt: Optional[datetime]) -> str:
    if dt is None:
        dt = datetime.now()
    return f"{dt.strftime('%b %d, %Y')}  {_strip_leading_zero_time(dt.strftime('%I:%M:%S %p'))}"


def sanitize_name_for_id(name: str, max_len: int = 48) -> str:
    """Return a filesystem-friendly, readable suffix for a Run ID."""
    cleaned = re.sub(r'[<>:"/\\|?*]', "_", (name or "").strip())
    cleaned = re.sub(r"\s+", " ", cleaned).rstrip(" .")
    return cleaned[:max_len] if cleaned else "Unnamed Test"


def make_run_id(test_name: str, when: Optional[datetime] = None) -> str:
    """Create a human-readable unique Run ID that can also be used as a folder name."""
    when = when or datetime.now()
    return f"{when.strftime('%Y-%m-%d_%H-%M-%S')} - {sanitize_name_for_id(test_name)}"


def make_panel(title: str | None = None) -> tuple[QFrame, QVBoxLayout]:
    panel = QFrame()
    panel.setObjectName("panel")
    layout = QVBoxLayout(panel)
    layout.setContentsMargins(8, 6, 8, 6)
    layout.setSpacing(4)
    if title:
        label = QLabel(title)
        label.setObjectName("sectionTitle")
        layout.addWidget(label)
    return panel, layout


class GaugeWidget(QWidget):
    def __init__(self, title: str, unit: str = "%", max_value: float = 100.0, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.title = title
        self.unit = unit
        self.max_value = max_value
        self.value = 0.0
        self.setMinimumSize(92, 82)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def setValue(self, value: float) -> None:
        self.value = max(0.0, min(self.max_value, float(value)))
        self.update()

    def paintEvent(self, event):  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect().adjusted(4, 2, -4, -2)
        cx = rect.center().x()
        cy = rect.top() + 46
        radius = min(rect.width() / 2 - 8, 31)
        painter.setPen(QColor("#E8F0F8"))
        painter.setFont(QFont("Segoe UI", 7))
        painter.drawText(rect.left(), rect.top(), rect.width(), 14, Qt.AlignmentFlag.AlignCenter, self.title)
        arc_rect = int(cx - radius), int(cy - radius), int(radius * 2), int(radius * 2)
        start_angle = 210
        span_total = 240
        for color, start_frac, span_frac in [("#41C02D", 0.0, 0.55), ("#F6A800", 0.55, 0.25), ("#D93025", 0.80, 0.20)]:
            pen = QPen(QColor(color), 5)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
            painter.drawArc(*arc_rect, int((start_angle - span_total * start_frac) * 16), int(-span_total * span_frac * 16))
        angle = math.radians(start_angle - (self.value / self.max_value) * span_total)
        x2 = cx + radius * 0.72 * math.cos(angle)
        y2 = cy - radius * 0.72 * math.sin(angle)
        painter.setPen(QPen(QColor("#DDE7F0"), 2))
        painter.drawLine(int(cx), int(cy), int(x2), int(y2))
        painter.setBrush(QColor("#607D94"))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(int(cx - 3), int(cy - 3), 6, 6)
        painter.setPen(QColor("#C8D4DF"))
        painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        painter.drawText(rect.left(), int(cy + 22), rect.width(), 18, Qt.AlignmentFlag.AlignCenter, f"{self.value:.1f}{self.unit}")


class SparklineWidget(QWidget):
    def __init__(self, max_value: float | None = None, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.values: List[float] = []
        self.max_points = 120
        self.max_value = max_value
        self.setMinimumHeight(52)

    def addValue(self, value: float) -> None:
        self.values.append(float(value))
        self.values = self.values[-self.max_points:]
        self.update()

    def reset(self) -> None:
        self.values.clear()
        self.update()

    def paintEvent(self, event):  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect().adjusted(5, 5, -5, -5)
        painter.fillRect(self.rect(), QColor("#071522"))
        painter.setPen(QPen(QColor("#244055"), 1))
        for i in range(1, 4):
            y = rect.top() + rect.height() * i / 4
            painter.drawLine(rect.left(), int(y), rect.right(), int(y))
        if len(self.values) < 2:
            return
        if self.max_value is None:
            low, high = min(self.values), max(self.values)
        else:
            low, high = 0.0, self.max_value
        span = max(0.1, high - low)
        step = rect.width() / max(1, len(self.values) - 1)
        painter.setPen(QPen(QColor("#56C51F"), 2))
        last_x = rect.left()
        last_y = rect.bottom() - ((self.values[0] - low) / span) * rect.height()
        for i, value in enumerate(self.values[1:], start=1):
            x = rect.left() + i * step
            y = rect.bottom() - ((value - low) / span) * rect.height()
            painter.drawLine(int(last_x), int(last_y), int(x), int(y))
            last_x, last_y = x, y


class CameraViewWidget(QWidget):
    def __init__(self, camera_index: int = 1, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.camera_index = camera_index
        self.phase = 0.0
        self.setMinimumHeight(310)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._advance)
        self.timer.start(80)

    def setCamera(self, index: int) -> None:
        self.camera_index = index
        self.update()

    def _advance(self) -> None:
        self.phase += 0.08
        self.update()

    def paintEvent(self, event):  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor("#050D14"))
        r = self.rect().adjusted(12, 12, -12, -12)
        painter.setPen(QPen(QColor("#1E3B51"), 1))
        for x in range(r.left(), r.right(), 36):
            painter.drawLine(x, r.top(), x, r.bottom())
        for y in range(r.top(), r.bottom(), 36):
            painter.drawLine(r.left(), y, r.right(), y)
        painter.setPen(QColor("#A8B7C5"))
        painter.drawText(r.left() + 8, r.top() + 18, f"LIVE CAMERA {self.camera_index}")
        painter.drawText(r.right() - 95, r.top() + 18, datetime.now().strftime("%H:%M:%S"))

        cx, cy = r.center().x(), r.center().y() + 18
        bob = math.sin(self.phase) * 8
        painter.setBrush(QColor("#243F55"))
        painter.setPen(QPen(QColor("#7AA9C8"), 2))
        if self.camera_index == 1:
            painter.drawRoundedRect(QRectF(cx - 130, cy + 62, 260, 28), 7, 7)
            painter.setBrush(QColor("#566D7F"))
            painter.drawRoundedRect(QRectF(cx - 105, cy - 55 + bob, 210, 100), 10, 10)
            painter.setBrush(QColor("#91A9B9"))
            painter.drawEllipse(QPointF(cx - 62, cy + bob), 22, 22)
            painter.drawEllipse(QPointF(cx + 62, cy + bob), 22, 22)
            painter.setPen(QPen(QColor("#F6A800"), 4))
            painter.drawLine(int(cx - 95), int(cy - 72 + bob), int(cx + 95), int(cy - 72 + bob))
        else:
            painter.drawRoundedRect(QRectF(cx - 70, cy + 62, 140, 28), 7, 7)
            painter.setBrush(QColor("#566D7F"))
            painter.drawRoundedRect(QRectF(cx - 48, cy - 70 + bob, 96, 120), 10, 10)
            painter.setBrush(QColor("#91A9B9"))
            painter.drawEllipse(QPointF(cx, cy - 8 + bob), 30, 30)
            painter.setPen(QPen(QColor("#F6A800"), 4))
            painter.drawLine(int(cx - 38), int(cy - 88 + bob), int(cx + 38), int(cy - 88 + bob))


class ExecutionWindow(QWidget):

    # -------------------------------------------------------------------------
    # ApplicationState-backed properties
    #
    # ExecutionWindow remains the root controller, but durable application state
    # now lives in self.app_state. These properties preserve the existing
    # executionWindow.py API while moving ownership of state-like values into a
    # single object that can later be shared with gRPC clients, dialogs, result
    # recovery, and reports.
    # -------------------------------------------------------------------------

    @property
    def test_config(self) -> Dict[str, Any]:
        return self.app_state.loaded_profile or {}

    @test_config.setter
    def test_config(self, value: Dict[str, Any] | None) -> None:
        self.app_state.loaded_profile = value or {}

    @property
    def config_path(self) -> Optional[str]:
        return str(self.app_state.profile_path) if self.app_state.profile_path else None

    @config_path.setter
    def config_path(self, value: str | Path | None) -> None:
        self.app_state.profile_path = Path(value) if value else None

    @property
    def state(self) -> str:
        return self.app_state.machine_state

    @state.setter
    def state(self, value: str) -> None:
        self.app_state.machine_state = value or "IDLE"

    @property
    def loaded_for_run(self) -> bool:
        return self.app_state.loaded_for_run

    @loaded_for_run.setter
    def loaded_for_run(self, value: bool) -> None:
        self.app_state.loaded_for_run = bool(value)

    @property
    def test_start_datetime(self) -> Optional[datetime]:
        return self.app_state.test_start_datetime

    @test_start_datetime.setter
    def test_start_datetime(self, value: Optional[datetime]) -> None:
        self.app_state.test_start_datetime = value

    @property
    def test_end_datetime(self) -> Optional[datetime]:
        return self.app_state.test_end_datetime

    @test_end_datetime.setter
    def test_end_datetime(self, value: Optional[datetime]) -> None:
        self.app_state.test_end_datetime = value

    @property
    def estimated_complete_datetime(self) -> Optional[datetime]:
        return self.app_state.estimated_complete_datetime

    @estimated_complete_datetime.setter
    def estimated_complete_datetime(self, value: Optional[datetime]) -> None:
        self.app_state.estimated_complete_datetime = value

    @property
    def schedule_locked(self) -> bool:
        return self.app_state.schedule_locked

    @schedule_locked.setter
    def schedule_locked(self, value: bool) -> None:
        self.app_state.schedule_locked = bool(value)

    @property
    def _last_schedule_minute(self) -> Optional[str]:
        return self.app_state.last_schedule_minute

    @_last_schedule_minute.setter
    def _last_schedule_minute(self, value: Optional[str]) -> None:
        self.app_state.last_schedule_minute = value

    @property
    def run_id(self) -> Optional[str]:
        return self.app_state.run_id

    @run_id.setter
    def run_id(self, value: Optional[str]) -> None:
        self.app_state.run_id = value

    @property
    def results_dir(self) -> Optional[Path]:
        return self.app_state.results_dir

    @results_dir.setter
    def results_dir(self, value: str | Path | None) -> None:
        self.app_state.results_dir = Path(value) if value else None

    @property
    def machine_homed(self) -> bool:
        return self.app_state.machine_homed

    @machine_homed.setter
    def machine_homed(self, value: bool) -> None:
        self.app_state.machine_homed = bool(value)

    def __init__(self, test_config: Dict[str, Any] | None = None, config_path: str | None = None, parent_window: QWidget | None = None):
        super().__init__()
        self.app_state = ApplicationState()
        self.test_config = test_config or {}
        self.config_path = config_path
        self.parent_window = parent_window
        self.state = "IDLE"
        self.loaded_for_run = bool(test_config)
        self.test_start_datetime: Optional[datetime] = None
        self.test_end_datetime: Optional[datetime] = None
        self.estimated_complete_datetime: Optional[datetime] = None
        self.schedule_locked = False
        self._last_schedule_minute: Optional[str] = None
        self.run_id: Optional[str] = None
        self.results_dir: Optional[Path] = None
        self.machine_homed = False
        self.homingTimer: QTimer | None = None
        self.flash_on = True
        self.current_camera = 1
        self.torque_samples = [[] for _ in range(4)]
        self.torque_peaks = [(0.0, "--:--:--") for _ in range(4)]
        self.temp_peaks = [(0.0, "--:--:--") for _ in range(4)]
        self.internal_log: List[str] = []
        self.logConsoles: List[QPlainTextEdit] = []

        self.setWindowTitle("TestStand Execution Dashboard")
        self._configure_window_geometry()
        self.setStyleSheet(DARK_STYLE)

        self.simulator: TelemetrySimulator | None = None
        if self.test_config:
            self._create_simulator()

        self._build_ui()
        self._set_state(self.state)
        self._update_loaded_test_labels()

        self.flashTimer = QTimer(self)
        self.flashTimer.timeout.connect(self._flash_tick)
        self.flashTimer.start(500)

        self.clockTimer = QTimer(self)
        self.clockTimer.timeout.connect(self._update_clock)
        self.clockTimer.start(1000)
        self._update_clock()

        QTimer.singleShot(250, self._check_for_interrupted_test_on_startup)

    @classmethod
    def from_json_file(cls, file_path: str, parent_window: QWidget | None = None) -> "ExecutionWindow":
        """Create a dashboard window with a saved test profile loaded.

        This keeps JSON loading in the dashboard layer and gives
        parameterInput.py a simple, stable contract: return a file path.
        """
        with open(file_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        return cls(test_config=config, config_path=file_path, parent_window=parent_window)

    def load_profile_after_editor(self, file_path: str) -> None:
        """Load a profile that was just created or edited in parameterInput.py."""
        self._load_profile_from_file(file_path, source="Saved test profile")
        self._show_page(0)
        self.raise_()
        self.activateWindow()


    def _configure_window_geometry(self) -> None:
        """Size the dashboard for the target HMI display.

        On the Raspberry Pi 7-inch HMI, run fullscreen so the operator sees a
        dedicated appliance-style interface rather than a small desktop window.
        On development machines, fall back to the designed 1024x600 window if a
        smaller or unusual screen is detected.
        """
        screen = QApplication.primaryScreen()

        if screen is None:
            self.setFixedSize(1024, 600)
            return

        available = screen.availableGeometry()
        width = available.width()
        height = available.height()

        # Target display is 1024x600. If the current display is at least that
        # size, use true fullscreen. This also works if the Pi reports a larger
        # monitor during development.
        if width >= 1024 and height >= 600:
            self.setMinimumSize(1024, 600)
            self.showFullScreen()
        else:
            # Development fallback.
            self.setFixedSize(1024, 600)


    def _build_ui(self) -> None:
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        side = QFrame()
        side.setObjectName("sideBar")
        side.setFixedWidth(250)
        side_layout = QVBoxLayout(side)
        side_layout.setContentsMargins(8, 8, 8, 8)
        side_layout.setSpacing(8)

        self.sideLogoLabel = QLabel()
        self.sideLogoLabel.setObjectName("sideLogo")
        self.sideLogoLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.sideLogoLabel.setFixedSize(232, 82)
        if LOGO_PATH.exists():
            pixmap = QPixmap(str(LOGO_PATH))
            if not pixmap.isNull():
                self.sideLogoLabel.setPixmap(
                    pixmap.scaled(220, 72, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                )
        else:
            self.sideLogoLabel.setText("C.J. ANDERSON")
        side_layout.addWidget(self.sideLogoLabel)

        self.nav_buttons: Dict[str, QPushButton] = {}
        nav_items = [
            ("Operations", 0),
            ("Telemetry", 1),
            ("Trends", 2),
            ("Cameras", 3),
            ("Diagnostics", 4),
            ("Settings", 5),
        ]
        for label, index in nav_items:
            button = QPushButton(label)
            button.setObjectName("navButton")
            button.clicked.connect(lambda checked=False, i=index: self._show_page(i))
            side_layout.addWidget(button)
            self.nav_buttons[label] = button

        side_layout.addSpacing(8)
        self.primaryActionButton = QPushButton("PROGRAM TEST")
        self.primaryActionButton.setObjectName("runButton")
        self.primaryActionButton.clicked.connect(self._primary_action_clicked)
        side_layout.addWidget(self.primaryActionButton)

        self.pauseButton = QPushButton("PAUSE")
        self.pauseButton.setObjectName("pauseButton")
        self.pauseButton.clicked.connect(self._pause_or_resume)
        side_layout.addWidget(self.pauseButton)

        self.abortButton = QPushButton("ABORT")
        self.abortButton.setObjectName("abortButton")
        self.abortButton.clicked.connect(self._abort_test)
        side_layout.addWidget(self.abortButton)

        side_layout.addStretch(1)
        self.clockLabel = QLabel("TIME: --")
        self.clockLabel.setObjectName("smallMuted")
        side_layout.addWidget(self.clockLabel)

        root.addWidget(side)

        content = QVBoxLayout()
        content.setContentsMargins(8, 6, 8, 6)
        content.setSpacing(6)

        self.topBar = QFrame()
        self.topBar.setObjectName("topBar")
        top_layout = QHBoxLayout(self.topBar)
        top_layout.setContentsMargins(8, 4, 8, 4)
        top_layout.setSpacing(10)

        profile_box = QFrame()
        profile_box.setObjectName("panel")
        profile_layout = QVBoxLayout(profile_box)
        profile_layout.setContentsMargins(8, 4, 8, 4)
        profile_title = QLabel("TEST PROFILE")
        profile_title.setObjectName("smallMuted")
        self.testProfileTopLabel = QLabel("NONE YET SELECTED")
        self.testProfileTopLabel.setObjectName("largeValue")
        self.testProfileTopLabel.setWordWrap(True)
        profile_layout.addWidget(profile_title)
        profile_layout.addWidget(self.testProfileTopLabel)
        top_layout.addWidget(profile_box, 3)

        state_box = QFrame()
        state_box.setObjectName("panel")
        state_layout = QVBoxLayout(state_box)
        state_layout.setContentsMargins(8, 4, 8, 4)
        state_title = QLabel("MACHINE STATE")
        state_title.setObjectName("smallMuted")
        self.stateLabel = QLabel("IDLE")
        self.stateLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.stateLabel.setObjectName("mediumValue")
        state_layout.addWidget(state_title)
        state_layout.addWidget(self.stateLabel)
        top_layout.addWidget(state_box, 1)

        content.addWidget(self.topBar)

        self.stack = QStackedWidget()
        self.stack.addWidget(self._build_operations_page())
        self.stack.addWidget(self._build_telemetry_page())
        self.stack.addWidget(self._build_trends_page())
        self.stack.addWidget(self._build_cameras_page())
        self.stack.addWidget(self._build_diagnostics_page())
        self.stack.addWidget(self._build_settings_page())
        content.addWidget(self.stack, 1)

        self.bottomBar = QFrame()
        self.bottomBar.setObjectName("bottomBar")
        bottom_layout = QHBoxLayout(self.bottomBar)
        bottom_layout.setContentsMargins(8, 4, 8, 4)
        self.networkBottomLabel = QLabel("Internet: Unknown")
        self.networkBottomLabel.setObjectName("smallMuted")
        self.dataBottomLabel = QLabel("Recording: OFF | Last Saved: --")
        self.dataBottomLabel.setObjectName("smallMuted")
        self.fileBottomLabel = QLabel("File: None")
        self.fileBottomLabel.setObjectName("smallMuted")
        bottom_layout.addWidget(self.networkBottomLabel)
        bottom_layout.addWidget(self.dataBottomLabel)
        bottom_layout.addWidget(self.fileBottomLabel, 1)
        content.addWidget(self.bottomBar)

        root.addLayout(content, 1)
        self._show_page(0)

    def _build_operations_page(self) -> QWidget:
        page = QWidget()
        layout = QGridLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        progress_panel, pl = make_panel("OPERATIONS")
        self.progressBar = QProgressBar()
        self.progressBar.setRange(0, 100)
        self.progressLabel = QLabel("0.0%")
        self.progressLabel.setObjectName("largeValue")
        self.cycleLabel = QLabel("Cycle: -- / --")
        self.timeLeftLabel = QLabel("Time Left: --")
        self.elapsedLabel = QLabel("Elapsed: --")

        for label in [self.cycleLabel, self.timeLeftLabel, self.elapsedLabel]:
            label.setObjectName("mediumValue")
        pl.addWidget(self.progressLabel)
        pl.addWidget(self.progressBar)
        pl.addWidget(self.cycleLabel)
        pl.addWidget(self.timeLeftLabel)
        pl.addWidget(self.elapsedLabel)
        layout.addWidget(progress_panel, 0, 0)

        test_panel, tl = make_panel("RUN INFORMATION")
        self.testNameLabel = QLabel("Test Profile: None")
        self.dutLabel = QLabel("DUT Serial: --")
        self.paramsLabel = QLabel("Cycles: -- | Cycle Time: -- s")
        self.runIdTitleLabel = QLabel("RUN ID")
        self.runIdTitleLabel.setObjectName("sectionTitle")
        self.runIdLabel = QLabel("Pending")
        self.runIdLabel.setObjectName("mediumValue")
        self.runIdLabel.setWordWrap(True)
        self.testStartTitleLabel = QLabel("TEST START DATE")
        self.testStartTitleLabel.setObjectName("sectionTitle")
        self.testStartLabel = QLabel("Pending")
        self.testStartLabel.setObjectName("mediumValue")
        self.testStartLabel.setWordWrap(True)
        self.testEndTitleLabel = QLabel("EST. COMPLETE")
        self.testEndTitleLabel.setObjectName("sectionTitle")
        self.testEndLabel = QLabel("Pending")
        self.testEndLabel.setObjectName("mediumValue")
        self.testEndLabel.setWordWrap(True)
        for label in [self.testNameLabel, self.dutLabel, self.paramsLabel]:
            label.setWordWrap(True)
            label.setObjectName("mediumValue")
            tl.addWidget(label)
        tl.addSpacing(4)
        tl.addWidget(self.runIdTitleLabel)
        tl.addWidget(self.runIdLabel)
        tl.addSpacing(4)
        tl.addWidget(self.testStartTitleLabel)
        tl.addWidget(self.testStartLabel)
        tl.addSpacing(4)
        tl.addWidget(self.testEndTitleLabel)
        tl.addWidget(self.testEndLabel)
        self.testDetailsButton = QPushButton("Test Details...")
        self.testDetailsButton.setStyleSheet("font-size: 13px; padding: 3px 6px;")
        self.testDetailsButton.clicked.connect(self._show_test_details)
        tl.addWidget(self.testDetailsButton)
        layout.addWidget(test_panel, 0, 1)

        log_panel, logl = make_panel("EVENT LOG")
        clear_button = QPushButton("Clear Displayed Log")
        clear_button.setObjectName("clearButton")
        clear_button.clicked.connect(self._clear_displayed_log)
        self.operationsLogConsole = QPlainTextEdit()
        self.operationsLogConsole.setReadOnly(True)
        self.logConsoles.append(self.operationsLogConsole)
        logl.addWidget(clear_button)
        logl.addWidget(self.operationsLogConsole, 1)
        layout.addWidget(log_panel, 1, 0, 1, 2)

        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(1, 1)
        layout.setRowStretch(0, 0)
        layout.setRowStretch(1, 1)
        return page

    def _build_telemetry_page(self) -> QWidget:
        page = QWidget()
        layout = QGridLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self.torqueGauges: List[GaugeWidget] = []
        self.tempGauges: List[GaugeWidget] = []
        self.avgPeakLabels: List[QLabel] = []
        for i in range(4):
            panel, pl = make_panel(f"SERVO {i + 1}")
            torque = GaugeWidget("Torque", "%", 100)
            temp = GaugeWidget("Temp", "°C", 100)
            stats = QLabel("Avg: -- | Peak: -- @ --")
            stats.setObjectName("smallMuted")
            pl.addWidget(torque)
            pl.addWidget(stats)
            pl.addWidget(temp)
            self.torqueGauges.append(torque)
            self.tempGauges.append(temp)
            self.avgPeakLabels.append(stats)
            layout.addWidget(panel, 0, i)

        load_panel, ll = make_panel("LOAD CELLS")
        self.loadCellLabels = [QLabel("LC1: -- lbf"), QLabel("LC2: -- lbf")]
        for label in self.loadCellLabels:
            label.setObjectName("mediumValue")
            ll.addWidget(label)
        layout.addWidget(load_panel, 1, 0, 1, 2)

        temp_panel, tl = make_panel("AUX TEMPERATURES")
        self.auxTempLabels = [QLabel(f"T{i+1}: -- °C") for i in range(6)]
        aux_grid = QGridLayout()
        for i, label in enumerate(self.auxTempLabels):
            aux_grid.addWidget(label, i // 3, i % 3)
        tl.addLayout(aux_grid)
        layout.addWidget(temp_panel, 1, 2, 1, 2)
        return page

    def _build_trends_page(self) -> QWidget:
        page = QWidget()
        layout = QGridLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        self.trendWidgets: Dict[str, SparklineWidget] = {}
        for row, title in enumerate(["Servo Torque Trend", "Servo Temperature Trend", "Load Cell Trend", "Aux Temperature Trend"]):
            panel, pl = make_panel(title.upper())
            spark = SparklineWidget()
            self.trendWidgets[title] = spark
            pl.addWidget(spark)
            layout.addWidget(panel, row, 0)
        return page

    def _build_cameras_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        panel, pl = make_panel("CAMERAS")
        buttons = QHBoxLayout()
        cam1 = QPushButton("CAMERA 1")
        cam2 = QPushButton("CAMERA 2")
        cam1.clicked.connect(lambda: self._set_camera(1))
        cam2.clicked.connect(lambda: self._set_camera(2))
        buttons.addWidget(cam1)
        buttons.addWidget(cam2)
        buttons.addStretch(1)
        pl.addLayout(buttons)
        self.cameraView = CameraViewWidget(1)
        pl.addWidget(self.cameraView, 1)
        layout.addWidget(panel, 1)
        return page

    def _build_diagnostics_page(self) -> QWidget:
        page = QWidget()
        layout = QGridLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        fault_panel, fl = make_panel("ACTIVE FAULTS")
        self.faultLabel = QLabel("No active faults")
        self.faultLabel.setWordWrap(True)
        fl.addWidget(self.faultLabel)
        layout.addWidget(fault_panel, 0, 0)

        net_panel, nl = make_panel("NETWORK")
        self.internetLabel = QLabel("Internet: Unknown")
        self.ssidLabel = QLabel("SSID: --")
        self.ipLabel = QLabel("IP: --")
        self.signalLabel = QLabel("Signal: --")
        self.remoteLabel = QLabel("Remote Dashboard: Disconnected")
        for label in [self.internetLabel, self.ssidLabel, self.ipLabel, self.signalLabel, self.remoteLabel]:
            nl.addWidget(label)
        layout.addWidget(net_panel, 0, 1)

        log_panel, logl = make_panel("EVENT LOG")
        clear_button = QPushButton("Clear Displayed Log")
        clear_button.setObjectName("clearButton")
        clear_button.clicked.connect(self._clear_displayed_log)
        self.diagnosticsLogConsole = QPlainTextEdit()
        self.diagnosticsLogConsole.setReadOnly(True)
        self.logConsoles.append(self.diagnosticsLogConsole)
        logl.addWidget(clear_button)
        logl.addWidget(self.diagnosticsLogConsole, 1)
        layout.addWidget(log_panel, 1, 0, 1, 2)
        layout.setRowStretch(1, 1)
        return page

    def _build_settings_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        panel, pl = make_panel("SETTINGS / RUNTIME INFO")
        self.loggingLabel = QLabel("Logging: --")
        self.telemetryRateLabel = QLabel("Telemetry Rate: -- Hz")
        self.runtimeLabel = QLabel("Runtime Source: Local Telemetry Simulator")
        self.futureLabel = QLabel("Future: gRPC client will replace simulator without changing dashboard layout.")
        self.futureLabel.setWordWrap(True)
        for label in [self.loggingLabel, self.telemetryRateLabel, self.runtimeLabel, self.futureLabel]:
            pl.addWidget(label)
        pl.addStretch(1)
        layout.addWidget(panel, 1)
        return page

    def _show_test_details(self) -> None:
        """Show non-operational metadata without cluttering the Operations page."""
        if not self.test_config:
            QMessageBox.information(self, "Test Details", "Load a test profile first.")
            return

        meta = self.test_config.get("test_metadata", {})
        params = self.test_config.get("test_parameters", {})
        image_capture = self.test_config.get("image_capture", {})
        logging_cfg = self.test_config.get("logging", {})

        details = [
            "TEST DETAILS",
            "",
            f"Test Profile: {meta.get('test_name') or '--'}",
            f"Project: {meta.get('project_number') or '--'}",
            f"Operator: {meta.get('operator') or '--'}",
            f"DUT Serial: {meta.get('dut_serial_number') or '--'}",
            f"Profile UUID: {meta.get('test_id') or '--'}",
            f"JSON File: {Path(self.config_path).name if self.config_path else '--'}",
            f"Results Folder: {self.results_dir if self.results_dir else '--'}",
            "",
            "PARAMETERS",
            f"Number of Cycles: {params.get('number_of_cycles') or '--'}",
            f"Cycle Time: {params.get('cycle_time_sec') or '--'} sec",
            f"Make and Carry Time: {params.get('make_and_carry_time_sec') or '--'} sec",
            f"Motion Profile Version: {params.get('motion_profile_version') or '--'}",
            "",
            "IMAGE CAPTURE",
            f"Enabled: {image_capture.get('enabled')}",
            f"Frequency Cycles: {image_capture.get('frequency_cycles') or '--'}",
            "",
            "LOGGING",
            f"Enabled: {logging_cfg.get('enabled')}",
            f"Log Level: {logging_cfg.get('log_level') or '--'}",
            f"Telemetry Frequency: {logging_cfg.get('telemetry_frequency_hz') or '--'} Hz",
        ]

        notes = meta.get("notes")
        if notes:
            details.extend(["", "NOTES", str(notes)])

        QMessageBox.information(self, "Test Details", "\n".join(details))

    def _check_for_interrupted_test_on_startup(self) -> None:
        """Check the most recent Results folder for an incomplete prior run."""
        if self.loaded_for_run:
            return
        try:
            results_dir = Path(getResultsDir())
            if not results_dir.exists():
                return
            run_dirs = [p for p in results_dir.iterdir() if p.is_dir()]
            if not run_dirs:
                return
            latest = max(run_dirs, key=lambda p: p.stat().st_mtime)
            state_path = latest / "execution_state.json"
            manifest_path = latest / "run_manifest.json"
            profile_path = latest / "test_config.json"

            data = None
            source_path = None
            for candidate in (state_path, manifest_path):
                if candidate.exists():
                    with open(candidate, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    source_path = candidate
                    break
            if data is None:
                return

            status = str(data.get("status", data.get("result", ""))).upper()
            if status in ("COMPLETE", "COMPLETED", "ABORTED"):
                return

            if status == "FAULT":
                message = "Previous incomplete detected. Testing data shows the test had a fault upon test interruption. Load and review faulted test?"
            else:
                message = "Previous incomplete test detected. Load and resume?"

            reply = QMessageBox.question(
                self,
                "Previous Incomplete Test Detected",
                message,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

            config = data.get("test_config")
            config_file = profile_path if profile_path.exists() else None
            if config is None and config_file:
                with open(config_file, "r", encoding="utf-8") as f:
                    config = json.load(f)
            if config is None:
                QMessageBox.warning(self, "Resume Failed", f"No test_config could be found in {latest}.")
                return

            self._apply_loaded_config(config, str(config_file or source_path), f"Previous incomplete run loaded: {latest.name}")
            self.app_state.load_resume_state(
                run_id=latest.name,
                results_dir=latest,
                test_start=self._parse_optional_datetime(data.get("start_time") or data.get("test_start_time")),
                test_end=self._parse_optional_datetime(data.get("end_time") or data.get("test_end_time")),
                estimated_complete=self._parse_optional_datetime(data.get("estimated_complete_time")),
            )
            self._update_test_date_labels()
            if status == "FAULT":
                self._set_state("FAULT")
                self._append_log({"time": datetime.now().strftime("%H:%M:%S"), "level": "FAULT", "message": "Previous run was interrupted in FAULT state."})
            else:
                self._set_state("PAUSED")
                self._append_log({"time": datetime.now().strftime("%H:%M:%S"), "level": "WARN", "message": "Previous incomplete run loaded for resume review."})
        except Exception as exc:  # noqa: BLE001
            self._append_log({"time": datetime.now().strftime("%H:%M:%S"), "level": "WARN", "message": f"Startup recovery check failed: {exc}"})

    def _show_page(self, index: int) -> None:
        self.stack.setCurrentIndex(index)
        labels = list(self.nav_buttons.keys())
        for i, label in enumerate(labels):
            self.nav_buttons[label].setObjectName("navSelected" if i == index else "navButton")
            self.nav_buttons[label].style().unpolish(self.nav_buttons[label])
            self.nav_buttons[label].style().polish(self.nav_buttons[label])

    def _set_camera(self, index: int) -> None:
        self.current_camera = index
        if hasattr(self, "cameraView"):
            self.cameraView.setCamera(index)
        if hasattr(self, "opCameraView"):
            self.opCameraView.setCamera(index)

    def _create_simulator(self) -> None:
        self.simulator = TelemetrySimulator(self.test_config, interval_ms=250, parent=self)
        self.simulator.telemetry_updated.connect(self._update_from_telemetry)
        self.simulator.log_updated.connect(self._append_log)

    def _primary_action_clicked(self) -> None:
        if self.state in ("RUNNING", "PAUSED", "FAULT"):
            QMessageBox.information(self, "Unavailable", "Feature unavailable while test is running.")
            return
        if self.state == "HOMING":
            return

        if not self.loaded_for_run or self.state in ("COMPLETE", "ABORTED"):
            self._program_test_clicked()
            return

        if self.loaded_for_run and not self.machine_homed and self.state == "IDLE":
            self._start_homing_sequence()
            return

        if self.loaded_for_run and self.machine_homed and self.state == "IDLE":
            self._start_test()
            return

        self._program_test_clicked()

    def _program_test_clicked(self) -> None:
        if self.state in ("RUNNING", "PAUSED", "FAULT", "HOMING"):
            QMessageBox.information(self, "Unavailable", "Feature unavailable while test is running.")
            return
        if self.loaded_for_run and self.state not in ("COMPLETE", "ABORTED"):
            QMessageBox.information(
                self,
                "Profile Already Loaded",
                "A test profile is already loaded. Profile replacement is available after test completion.",
            )
            return

        msg = QMessageBox(self)
        msg.setWindowTitle("Program Test")
        msg.setText("Choose how to program the next test profile.")
        load_button = msg.addButton("Load Existing Profile", QMessageBox.ButtonRole.AcceptRole)
        create_button = msg.addButton("Create New Profile", QMessageBox.ButtonRole.ActionRole)
        modify_button = msg.addButton("Modify Existing Profile", QMessageBox.ButtonRole.ActionRole)
        resume_button = msg.addButton("Resume Previous Test", QMessageBox.ButtonRole.ActionRole)
        msg.addButton(QMessageBox.StandardButton.Cancel)
        msg.exec()

        clicked = msg.clickedButton()
        if clicked == load_button:
            self._load_existing_profile()
        elif clicked == create_button:
            self._create_new_profile()
        elif clicked == modify_button:
            self._modify_existing_profile()
        elif clicked == resume_button:
            self._resume_previous_test()

    def _load_existing_profile(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Test Profile JSON",
            str(getSavedTestsDir()),
            "JSON Files (*.json)",
        )
        if file_path:
            self._load_profile_from_file(file_path, source="Loaded test profile")

    def _resume_previous_test(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Previous Test Execution State",
            str(getResultsDir()),
            "JSON Files (*.json)",
        )
        if not file_path:
            return
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Resume Failed", f"Could not read selected resume file.\n\n{exc}")
            return

        # Future runtime result manifests may wrap the original profile under
        # test_config. For now, also accept a normal saved-test profile directly.
        config = data.get("test_config", data)
        self._apply_loaded_config(config, file_path, f"Resume file selected: {Path(file_path).name}")
        if "test_config" in data:
            self.app_state.load_resume_state(
                run_id=data.get("run_id") or Path(file_path).parent.name,
                results_dir=Path(file_path).parent,
                test_start=self._parse_optional_datetime(data.get("start_time") or data.get("test_start_time")),
                test_end=self._parse_optional_datetime(data.get("end_time") or data.get("test_end_time")),
                estimated_complete=self._parse_optional_datetime(data.get("estimated_complete_time")),
            )
            self._update_test_date_labels()

    def _modify_existing_profile(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Test Profile to Modify",
            str(getSavedTestsDir()),
            "JSON Files (*.json)",
        )
        if not file_path:
            return
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                config = json.load(f)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Failed to Load JSON", str(exc))
            return

        from ui.parameterInput import enduranceTestSetup

        self.parameterWindow = enduranceTestSetup(
            mode="edit",
            parent_window=self,
            initial_config=config,
            source_path=file_path,
        )
        self.parameterWindow.show()
        self.hide()

    def _create_new_profile(self) -> None:
        from ui.parameterInput import enduranceTestSetup

        self.parameterWindow = enduranceTestSetup(mode="create", parent_window=self)
        self.parameterWindow.show()
        self.hide()

    def _edit_test_profile(self) -> None:
        if not self.loaded_for_run:
            QMessageBox.information(self, "No Test Profile", "Load a test profile before editing.")
            return
        if self.state not in ("IDLE", "COMPLETE"):
            QMessageBox.information(self, "Unavailable", "Editing is available only before running or after completion.")
            return

        from ui.parameterInput import enduranceTestSetup

        self.parameterWindow = enduranceTestSetup(
            mode="edit",
            parent_window=self,
            initial_config=self.test_config,
            source_path=self.config_path,
        )
        self.parameterWindow.show()
        self.hide()

    def _load_profile_from_file(self, file_path: str, source: str = "Loaded test profile") -> None:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                config = json.load(f)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Failed to Load JSON", str(exc))
            return
        self._apply_loaded_config(config, file_path, f"{source}: {Path(file_path).name}")

    def _apply_loaded_config(self, config: Dict[str, Any], file_path: str, log_message: str) -> None:
        self.app_state.load_profile(config, file_path)
        self._reset_statistics()
        if self.simulator:
            self.simulator.stop()
            self.simulator.deleteLater()
        self._create_simulator()
        self._refresh_pending_run_schedule(force=True)
        self._update_loaded_test_labels()
        self._append_log({"time": datetime.now().strftime("%H:%M:%S"), "level": "INFO", "message": log_message})
        self._set_state("IDLE")

    def _start_homing_sequence(self) -> None:
        if not self.test_config:
            QMessageBox.warning(self, "No Test Selected", "Select a JSON test file before homing.")
            return
        self.machine_homed = False
        self._append_log({"time": datetime.now().strftime("%H:%M:%S"), "level": "INFO", "message": "Homing started."})
        self._set_state("HOMING")
        if self.homingTimer:
            self.homingTimer.stop()
            self.homingTimer.deleteLater()
        self.homingTimer = QTimer(self)
        self.homingTimer.setSingleShot(True)
        self.homingTimer.timeout.connect(self._homing_complete)
        self.homingTimer.start(3000)

    def _homing_complete(self) -> None:
        if self.state != "HOMING":
            return
        self.machine_homed = True
        self._append_log({"time": datetime.now().strftime("%H:%M:%S"), "level": "INFO", "message": "Homing complete. Machine is ready to run."})
        self._set_state("IDLE")

    def _start_test(self) -> None:
        if not self.test_config or not self.simulator:
            QMessageBox.warning(self, "No Test Selected", "Select a JSON test file before running.")
            return
        if not self.machine_homed:
            QMessageBox.warning(self, "Home Required", "Home the machine before running the selected test.")
            return
        self._reset_statistics()
        self.app_state.lock_schedule(datetime.now())

        meta = self.test_config.get("test_metadata", {})
        test_name = meta.get("test_name") or "Unnamed Test"
        self.run_id = make_run_id(test_name, self.test_start_datetime)

        total_seconds = self._estimate_total_test_seconds()
        self.estimated_complete_datetime = (
            self.test_start_datetime + timedelta(seconds=total_seconds)
            if total_seconds is not None
            else None
        )

        self._prepare_results_folder()
        self._update_test_date_labels()
        self.simulator.reset_for_new_test(self.test_config)
        self.simulator.start()
        self._append_log({"time": datetime.now().strftime("%H:%M:%S"), "level": "INFO", "message": "Test started."})
        self._set_state("RUNNING")

    def _pause_or_resume(self) -> None:
        if not self.simulator:
            return
        if self.state == "RUNNING":
            reply = QMessageBox.question(self, "Pause Test", "Pause the running test?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                self.simulator.pause()
                self._set_state("PAUSED")
        elif self.state in ("PAUSED", "FAULT"):
            reply = QMessageBox.question(self, "Resume Test", "Acknowledge and resume the test?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                self.simulator.resume()
                self._set_state("RUNNING")

    def _abort_test(self) -> None:
        if self.state not in ("RUNNING", "PAUSED", "FAULT", "HOMING"):
            return
        reply = QMessageBox.question(self, "Abort Test", "Abort the current operation?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            if self.homingTimer:
                self.homingTimer.stop()
            if self.simulator:
                self.simulator.abort()
            self._append_log({"time": datetime.now().strftime("%H:%M:%S"), "level": "WARN", "message": "Operation aborted by operator."})
            self._set_state("ABORTED")

    def _set_state(self, state: str) -> None:
        self.state = state
        if state in ("COMPLETE", "ABORTED") and self.test_end_datetime is None:
            self.app_state.mark_finished(datetime.now())
            if hasattr(self, "testEndLabel"):
                self._update_test_date_labels()
            self._write_execution_state(state)
        self.stateLabel.setText(state)

        if self.state == "HOMING":
            self.primaryActionButton.setText("HOMING")
        elif self.state in ("RUNNING", "PAUSED", "FAULT"):
            self.primaryActionButton.setText("TEST RUNNING")
        elif self.loaded_for_run and self.state == "IDLE" and not self.machine_homed:
            self.primaryActionButton.setText("HOME")
        elif self.loaded_for_run and self.state == "IDLE" and self.machine_homed:
            self.primaryActionButton.setText("PRESS TO RUN")
        else:
            self.primaryActionButton.setText("PROGRAM TEST")

        self.primaryActionButton.setEnabled(self.state != "HOMING")
        self.pauseButton.setEnabled(state in ("RUNNING", "PAUSED", "FAULT"))
        self.abortButton.setEnabled(state in ("RUNNING", "PAUSED", "FAULT", "HOMING"))
        if hasattr(self, "testDetailsButton"):
            self.testDetailsButton.setEnabled(self.loaded_for_run)
        if state in ("PAUSED", "FAULT"):
            self.pauseButton.setText("RESUME")
        else:
            self.pauseButton.setText("PAUSE")
        self._apply_state_style()

    def _apply_state_style(self) -> None:
        color = STATE_COLORS.get(self.state, "#173044")
        text_color = "#101010" if self.state == "PAUSED" else "white"
        self.stateLabel.setStyleSheet(
            f"background-color: {color}; color: {text_color}; border-radius: 5px; padding: 6px; font-weight: bold;"
        )

        # Top bar is informational and does not flash. Only actionable buttons flash.
        if self.state == "HOMING":
            # Solid blue while the machine is actively homing.
            self.primaryActionButton.setStyleSheet("background-color:#0E5BA3; border:1px solid #2BA7FF; color:white; font-weight:bold; font-size:17px;")
        elif self.loaded_for_run and self.state == "IDLE" and not self.machine_homed:
            # Flashing blue HOME button asks the operator to begin homing.
            if self.flash_on:
                self.primaryActionButton.setStyleSheet("background-color:#0E5BA3; border:1px solid #2BA7FF; color:white; font-weight:bold; font-size:17px;")
            else:
                self.primaryActionButton.setStyleSheet("background-color:#173044; border:1px solid #2BA7FF; color:#2BA7FF; font-weight:bold; font-size:17px;")
        elif self.loaded_for_run and self.state == "IDLE" and self.machine_homed:
            # Flashing green PRESS TO RUN button asks the operator to start the test.
            if self.flash_on:
                self.primaryActionButton.setStyleSheet("background-color:#0D5F34; border:1px solid #56C51F; font-weight:bold; font-size:17px;")
            else:
                self.primaryActionButton.setStyleSheet("background-color:#173044; border:1px solid #56C51F; color:#56C51F; font-weight:bold; font-size:17px;")
        elif self.state in ("RUNNING", "PAUSED", "FAULT"):
            self.primaryActionButton.setStyleSheet("background-color:#173044; border:1px solid #31506A; color:#A8B7C5; font-weight:bold; font-size:17px;")
        else:
            # PROGRAM TEST state.
            self.primaryActionButton.setStyleSheet("background-color:#0D5F34; border:1px solid #56C51F; font-weight:bold; font-size:17px;")

        if self.state in ("PAUSED", "FAULT"):
            if self.flash_on:
                self.pauseButton.setStyleSheet("background-color:#F4A900; color:#101010; border:1px solid #FFC145; font-weight:bold; font-size:15px;")
            else:
                self.pauseButton.setStyleSheet("background-color:#173044; color:#F4A900; border:1px solid #F4A900; font-weight:bold; font-size:15px;")
        else:
            self.pauseButton.setStyleSheet("")

    def _flash_tick(self) -> None:
        self.flash_on = not self.flash_on
        self._apply_state_style()

    def _update_clock(self) -> None:
        now = datetime.now()
        self.clockLabel.setText(f"TIME: {_strip_leading_zero_time(now.strftime('%I:%M:%S %p'))} on {fmt_date(now)}")
        self._refresh_pending_run_schedule(now=now)

    def _refresh_pending_run_schedule(self, now: Optional[datetime] = None, force: bool = False) -> None:
        """Preview the run timing after a profile is loaded but before PRESS TO RUN.

        The displayed Run ID, TEST START DATE, and EST. COMPLETE values are
        calculated immediately when a profile is loaded. They keep rolling forward
        once per minute until the operator presses PRESS TO RUN, at which point
        _start_test locks them to the actual run start.
        """
        if not self.loaded_for_run or not self.test_config or self.schedule_locked:
            return
        if self.state in ("RUNNING", "PAUSED", "FAULT", "COMPLETE", "ABORTED"):
            return

        now = now or datetime.now()
        minute_key = now.strftime("%Y-%m-%d_%H-%M")
        if not force and minute_key == self._last_schedule_minute:
            return

        preview_start = now.replace(second=0, microsecond=0)
        meta = self.test_config.get("test_metadata", {})
        test_name = meta.get("test_name") or "Unnamed Test"
        total_seconds = self._estimate_total_test_seconds()
        self.app_state.set_preview_schedule(
            preview_start=preview_start,
            run_id=make_run_id(test_name, preview_start),
            estimated_complete=(
                preview_start + timedelta(seconds=total_seconds)
                if total_seconds is not None
                else None
            ),
            minute_key=minute_key,
        )
        if hasattr(self, "runIdLabel"):
            self._update_test_date_labels()

    def _reset_statistics(self) -> None:
        self.torque_samples = [[] for _ in range(4)]
        self.torque_peaks = [(0.0, "--:--:--") for _ in range(4)]
        self.temp_peaks = [(0.0, "--:--:--") for _ in range(4)]
        for widget in getattr(self, "trendWidgets", {}).values():
            widget.reset()

    def _update_loaded_test_labels(self) -> None:
        meta = self.test_config.get("test_metadata", {}) if self.test_config else {}
        params = self.test_config.get("test_parameters", {}) if self.test_config else {}
        test_name = meta.get("test_name") or "NONE YET SELECTED"
        display_name = str(test_name).upper() if self.loaded_for_run else "NONE YET SELECTED"
        self.testProfileTopLabel.setText(display_name)
        self.testNameLabel.setText(f"Test Profile: {test_name if self.loaded_for_run else 'None'}")
        self.dutLabel.setText(f"DUT Serial: {meta.get('dut_serial_number') or '--'}")
        self.paramsLabel.setText(f"Cycles: {params.get('number_of_cycles') or '--'} | Cycle Time: {params.get('cycle_time_sec') or '--'} s")
        self.fileBottomLabel.setText(f"File: {Path(self.config_path).name if self.config_path else 'None'}")
        self._update_test_date_labels()

    def _update_test_date_labels(self) -> None:
        if hasattr(self, "runIdLabel"):
            self.runIdLabel.setText(self.run_id or "Pending")

        if self.test_start_datetime:
            self.testStartLabel.setText(
                f"{fmt_date(self.test_start_datetime)}  {fmt_time(self.test_start_datetime)}"
            )
        else:
            self.testStartLabel.setText("Pending")

        completion_dt = self.test_end_datetime or self.estimated_complete_datetime
        self.testEndTitleLabel.setText("COMPLETED" if self.test_end_datetime else "EST. COMPLETE")
        if completion_dt:
            self.testEndLabel.setText(
                f"{fmt_date(completion_dt)}  {fmt_time(completion_dt)}"
            )
        else:
            self.testEndLabel.setText("Pending")

    def _update_from_telemetry(self, packet: Dict[str, Any]) -> None:
        runtime_state = packet.get("state", self.state)
        if runtime_state in ("RUNNING", "PAUSED", "FAULT", "COMPLETE", "ABORTED") and runtime_state != self.state:
            self._set_state(runtime_state)

        progress = float(packet.get("progress_percent", 0.0))
        self.progressBar.setValue(int(progress))
        self.progressLabel.setText(f"{progress:.1f}%")
        self.cycleLabel.setText(f"Cycle: {packet.get('cycle', 0):,} / {packet.get('total_cycles', 0):,}")
        remaining_seconds = packet.get('remaining_seconds')
        self.timeLeftLabel.setText(f"Time Left: {fmt_duration_words(remaining_seconds)}")
        self.elapsedLabel.setText(f"Elapsed: {fmt_duration_words(packet.get('elapsed_seconds'))}")
        if self.state == "RUNNING" and self.test_end_datetime is None:
            self.estimated_complete_datetime = self._calculate_completion_datetime(remaining_seconds)
            self._update_test_date_labels()

        torques = packet.get("motor_torque_percent", [])
        temps = packet.get("motor_temperatures_c", [])
        now = packet.get("timestamp", datetime.now().strftime("%H:%M:%S"))
        for i in range(4):
            torque = float(torques[i]) if i < len(torques) else 0.0
            temp = float(temps[i]) if i < len(temps) else 0.0
            self.torqueGauges[i].setValue(torque)
            self.tempGauges[i].setValue(temp)
            self.torque_samples[i].append(torque)
            self.torque_samples[i] = self.torque_samples[i][-500:]
            if torque > self.torque_peaks[i][0]:
                self.torque_peaks[i] = (torque, now)
            if temp > self.temp_peaks[i][0]:
                self.temp_peaks[i] = (temp, now)
            avg = sum(self.torque_samples[i]) / len(self.torque_samples[i]) if self.torque_samples[i] else 0.0
            peak, peak_time = self.torque_peaks[i]
            temp_peak, temp_time = self.temp_peaks[i]
            self.avgPeakLabels[i].setText(f"Avg: {avg:.1f}% | Peak: {peak:.1f}% @ {peak_time}\nTemp Peak: {temp_peak:.1f}°C @ {temp_time}")

        load_cells = packet.get("load_cells_lbf", [])
        for i, label in enumerate(self.loadCellLabels):
            label.setText(f"LC{i + 1}: {load_cells[i]:.1f} lbf" if i < len(load_cells) else f"LC{i + 1}: -- lbf")

        aux_temps = packet.get("temperatures_c", [])
        for i, label in enumerate(self.auxTempLabels):
            label.setText(f"T{i + 1}: {aux_temps[i]:.1f} °C" if i < len(aux_temps) else f"T{i + 1}: -- °C")

        if torques:
            self.trendWidgets["Servo Torque Trend"].addValue(sum(torques) / len(torques))
        if temps:
            self.trendWidgets["Servo Temperature Trend"].addValue(sum(temps) / len(temps))
        if load_cells:
            self.trendWidgets["Load Cell Trend"].addValue(sum(load_cells) / len(load_cells))
        if aux_temps:
            self.trendWidgets["Aux Temperature Trend"].addValue(sum(aux_temps) / len(aux_temps))

        faults = packet.get("active_faults", [])
        self.faultLabel.setText("No active faults" if not faults else "\n".join(faults))
        self.internetLabel.setText(f"Internet: {'Connected' if packet.get('wifi_connected') else 'Disconnected'}")
        self.ssidLabel.setText(f"SSID: {packet.get('wifi_ssid') or '--'}")
        self.ipLabel.setText(f"IP: {packet.get('ip_address') or '--'}")
        self.signalLabel.setText(f"Signal: {packet.get('signal_strength_percent', 0)}%")
        self.remoteLabel.setText(f"Remote Dashboard: {'Connected' if packet.get('remote_dashboard_connected') else 'Disconnected'}")
        self.networkBottomLabel.setText(f"Internet: {'ON' if packet.get('wifi_connected') else 'OFF'} | IP: {packet.get('ip_address') or '--'}")
        rec = "ON" if packet.get("recording_enabled") else "OFF"
        last = packet.get("last_saved_timestamp") or "--"
        self.dataBottomLabel.setText(f"Recording: {rec} | Last Saved: {last}")
        self.loggingLabel.setText(f"Logging: {'Enabled' if packet.get('logging_enabled') else 'Disabled'} | Level: {packet.get('log_level')}")
        self.telemetryRateLabel.setText(f"Telemetry Rate: {packet.get('telemetry_frequency_hz') or '--'} Hz")

    def _calculate_completion_datetime(self, remaining_seconds: Any) -> Optional[datetime]:
        try:
            seconds = float(remaining_seconds)
        except (TypeError, ValueError):
            return None

        if seconds < 0:
            return None

        return datetime.now() + timedelta(seconds=seconds)

    def _estimate_total_test_seconds(self) -> Optional[float]:
        """Estimate run duration from the loaded profile before telemetry exists."""
        try:
            params = self.test_config.get("test_parameters", {})
            cycle_time = float(params.get("cycle_time_sec"))
            cycles = int(params.get("number_of_cycles"))
            return max(0.0, cycle_time * cycles)
        except (TypeError, ValueError):
            return None

    def _prepare_results_folder(self) -> None:
        """Create the run results folder and seed files for future resume/logging."""
        if not self.run_id:
            return
        try:
            self.results_dir = Path(getResultsDir()) / self.run_id
            self.results_dir.mkdir(parents=True, exist_ok=True)
            with open(self.results_dir / "test_config.json", "w", encoding="utf-8") as f:
                json.dump(self.test_config, f, indent=4)
            self._write_execution_state("RUNNING")
        except Exception as exc:  # noqa: BLE001
            self._append_log({"time": datetime.now().strftime("%H:%M:%S"), "level": "WARN", "message": f"Could not prepare results folder: {exc}"})

    def _write_execution_state(self, status: str) -> None:
        if not self.results_dir:
            return
        try:
            state = {
                "run_id": self.run_id,
                "status": status,
                "start_time": self.test_start_datetime.isoformat() if self.test_start_datetime else None,
                "estimated_complete_time": self.estimated_complete_datetime.isoformat() if self.estimated_complete_datetime else None,
                "end_time": self.test_end_datetime.isoformat() if self.test_end_datetime else None,
                "test_config": self.test_config,
                "last_update": datetime.now().isoformat(timespec="seconds"),
            }
            with open(self.results_dir / "execution_state.json", "w", encoding="utf-8") as f:
                json.dump(state, f, indent=4)
        except Exception as exc:  # noqa: BLE001
            self._append_log({"time": datetime.now().strftime("%H:%M:%S"), "level": "WARN", "message": f"Could not write execution_state.json: {exc}"})

    def _parse_optional_datetime(self, value: Any) -> Optional[datetime]:
        if not value:
            return None
        try:
            return datetime.fromisoformat(str(value).replace("Z", "+00:00")).replace(tzinfo=None)
        except ValueError:
            return None

    def _format_log_timestamp(self, value: Optional[str]) -> str:
        if not value:
            return fmt_log_timestamp(datetime.now())

        # Simulator/manual log entries may provide only HH:MM:SS. Prefix today's date
        # so the operator log always includes both date and time in the dashboard format.
        if len(value) == 8 and value.count(":") == 2:
            parsed = datetime.strptime(value, "%H:%M:%S")
            now = datetime.now()
            return fmt_log_timestamp(now.replace(hour=parsed.hour, minute=parsed.minute, second=parsed.second, microsecond=0))

        # Accept ISO-style timestamps when they appear in future runtime messages.
        try:
            return fmt_log_timestamp(datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None))
        except ValueError:
            return value

    def _append_log(self, entry: Dict[str, str]) -> None:
        timestamp = self._format_log_timestamp(entry.get("timestamp") or entry.get("time"))
        line = f"[{timestamp}] {entry.get('level', 'INFO')}: {entry.get('message', '')}"
        self.internal_log.append(line)
        for console in self.logConsoles:
            console.appendPlainText(line)

    def _clear_displayed_log(self) -> None:
        for console in self.logConsoles:
            console.clear()
        self.internal_log.append(
            f"[{fmt_log_timestamp(datetime.now())}] INFO: Displayed log cleared; internal log retained."
        )

    def closeEvent(self, event):  # noqa: N802
        if self.simulator:
            self.simulator.stop()
        event.accept()
