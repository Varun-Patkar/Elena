import ctypes
import ctypes.wintypes
import subprocess
import sys
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path

from elena.runtime import default_data_dir

RUNTIME_URL = "http://127.0.0.1:8765"
HOTKEY_ID = 0xE1E
WM_HOTKEY = 0x0312
MOD_CONTROL = 0x0002
VK_F4 = 0x73
PM_REMOVE = 0x0001


def runtime_command() -> tuple[str, list[str]]:
    return sys.executable, ["-m", "elena.runtime"]


def runtime_is_ready(timeout: float = 0.3) -> bool:
    try:
        with urllib.request.urlopen(f"{RUNTIME_URL}/health", timeout=timeout) as response:
            return response.status == 200
    except (OSError, urllib.error.URLError):
        return False


def cleanup_managed_containers() -> None:
    try:
        result = subprocess.run(
            ["docker", "ps", "-aq", "--filter", "label=com.elena.managed=true"],
            capture_output=True,
            check=False,
            text=True,
            timeout=5,
        )
        container_ids = result.stdout.split()
        if container_ids:
            subprocess.run(
                ["docker", "rm", "-f", *container_ids],
                capture_output=True,
                check=False,
                timeout=15,
            )
    except (OSError, subprocess.SubprocessError):
        pass


def main() -> None:
    try:
        from PySide6.QtCore import QLockFile, QProcess, QTimer
        from PySide6.QtGui import QAction, QColor, QFont, QIcon, QPainter, QPixmap
        from PySide6.QtWidgets import QApplication, QMenu, QMessageBox, QSystemTrayIcon
    except ImportError as error:
        raise SystemExit(
            "The desktop shell is optional. Install it with: uv sync --extra desktop"
        ) from error

    class DesktopHost:
        def __init__(self, application: QApplication, lock: QLockFile) -> None:
            self.application = application
            self.lock = lock
            self.process = QProcess(application)
            self.process.finished.connect(self._runtime_finished)
            self.health_timer = QTimer(application)
            self.health_timer.setInterval(250)
            self.health_timer.timeout.connect(self._check_runtime)
            self.hotkey_timer = QTimer(application)
            self.hotkey_timer.setInterval(100)
            self.hotkey_timer.timeout.connect(self._check_hotkey)
            self.restart_attempts = 0
            self.stopping = False
            self.open_when_ready = True
            self.hotkey_registered = False
            self.tray = QSystemTrayIcon(self._create_icon(), application)
            self.tray.setToolTip("Elena is starting")
            self.tray.activated.connect(self._tray_activated)
            self.tray.setContextMenu(self._create_menu())
            self.tray.show()

        def _create_icon(self) -> QIcon:
            pixmap = QPixmap(64, 64)
            pixmap.fill(QColor("#1f282a"))
            painter = QPainter(pixmap)
            painter.setPen(QColor("#f2aa95"))
            painter.setFont(QFont("Georgia", 34, QFont.Weight.DemiBold))
            painter.drawText(pixmap.rect(), 0x84, "E")
            painter.end()
            return QIcon(pixmap)

        def _create_menu(self) -> QMenu:
            menu = QMenu()
            open_action = QAction("Open Elena", menu)
            open_action.triggered.connect(self.open_browser)
            close_action = QAction("Close Elena", menu)
            close_action.triggered.connect(self.shutdown)
            menu.addAction(open_action)
            menu.addSeparator()
            menu.addAction(close_action)
            return menu

        def start(self) -> None:
            self._register_hotkey()
            self._start_runtime()

        def _register_hotkey(self) -> None:
            if sys.platform != "win32":
                return
            self.hotkey_registered = bool(
                ctypes.windll.user32.RegisterHotKey(None, HOTKEY_ID, MOD_CONTROL, VK_F4)
            )
            if self.hotkey_registered:
                self.hotkey_timer.start()
            else:
                self.tray.showMessage(
                    "Elena hotkey unavailable",
                    "Ctrl+F4 is already in use. The tray menu remains available.",
                )

        def _check_hotkey(self) -> None:
            message = ctypes.wintypes.MSG()
            if ctypes.windll.user32.PeekMessageW(
                ctypes.byref(message), None, WM_HOTKEY, WM_HOTKEY, PM_REMOVE
            ) and message.wParam == HOTKEY_ID:
                self.open_browser()

        def _start_runtime(self) -> None:
            program, arguments = runtime_command()
            self.tray.setToolTip("Elena is starting")
            self.process.setProgram(program)
            self.process.setArguments(arguments)
            self.process.start()
            self.health_timer.start()

        def _check_runtime(self) -> None:
            if not runtime_is_ready():
                return
            self.health_timer.stop()
            self.restart_attempts = 0
            self.tray.setToolTip("Elena is ready - Ctrl+F4 to open")
            if self.open_when_ready:
                self.open_when_ready = False
                self.open_browser()

        def _runtime_finished(self) -> None:
            self.health_timer.stop()
            if self.stopping:
                return
            if self.restart_attempts >= 3:
                self.tray.setToolTip("Elena needs attention")
                self.tray.showMessage(
                    "Elena could not start",
                    "The runtime stopped repeatedly. Close Elena and run setup again.",
                )
                return
            delay = 1000 * (2**self.restart_attempts)
            self.restart_attempts += 1
            QTimer.singleShot(delay, self._start_runtime)

        def _tray_activated(self, reason: object) -> None:
            if reason == QSystemTrayIcon.ActivationReason.Trigger:
                self.open_browser()

        def open_browser(self) -> None:
            if runtime_is_ready():
                webbrowser.open_new_tab(RUNTIME_URL)
                return
            self.open_when_ready = True
            self.tray.showMessage("Elena is starting", "The browser will open when ready.")

        def shutdown(self) -> None:
            if self.stopping:
                return
            self.stopping = True
            self.health_timer.stop()
            self.hotkey_timer.stop()
            if self.hotkey_registered:
                ctypes.windll.user32.UnregisterHotKey(None, HOTKEY_ID)
            if self.process.state() != QProcess.ProcessState.NotRunning:
                self.process.terminate()
                if not self.process.waitForFinished(5000):
                    self.process.kill()
                    self.process.waitForFinished(1500)
            cleanup_managed_containers()
            self.tray.hide()
            self.lock.unlock()
            self.application.quit()

    application = QApplication(sys.argv)
    application.setApplicationName("Elena")
    application.setQuitOnLastWindowClosed(False)

    data_dir = Path(default_data_dir())
    data_dir.mkdir(parents=True, exist_ok=True)
    lock = QLockFile(str(data_dir / "desktop.lock"))
    lock.setStaleLockTime(0)
    if not lock.tryLock(100):
        if runtime_is_ready():
            webbrowser.open_new_tab(RUNTIME_URL)
        else:
            QMessageBox.information(None, "Elena is already running", "Elena is starting.")
        raise SystemExit(0)

    host = DesktopHost(application, lock)
    application.aboutToQuit.connect(host.shutdown)
    host.start()
    raise SystemExit(application.exec())


if __name__ == "__main__":
    main()