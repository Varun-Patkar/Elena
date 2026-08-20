import sys
import urllib.error
import urllib.request
from pathlib import Path

from elena.runtime import default_data_dir

RUNTIME_URL = "http://127.0.0.1:8765"


def runtime_command() -> tuple[str, list[str]]:
    return sys.executable, ["-m", "elena.runtime"]


def runtime_is_ready(timeout: float = 0.3) -> bool:
    try:
        with urllib.request.urlopen(
            f"{RUNTIME_URL}/health", timeout=timeout
        ) as response:
            return response.status == 200
    except (OSError, urllib.error.URLError):
        return False


def main() -> None:
    try:
        from PySide6.QtCore import QLockFile, QProcess, QTimer, QUrl
        from PySide6.QtGui import QAction, QColor, QFont, QIcon, QPainter, QPixmap
        from PySide6.QtWebEngineWidgets import QWebEngineView
        from PySide6.QtWidgets import (
            QApplication,
            QMainWindow,
            QMenu,
            QMessageBox,
            QSystemTrayIcon,
        )
    except ImportError as error:
        raise SystemExit(
            "The desktop shell is optional. Install it with: uv sync --extra desktop"
        ) from error

    class ElenaWindow(QMainWindow):
        def __init__(self) -> None:
            super().__init__()
            self.allow_close = False
            self.setWindowTitle("Elena")
            self.resize(1180, 780)
            self.setMinimumSize(820, 600)
            self.web_view = QWebEngineView(self)
            self.web_view.setHtml(
                "<body style='font-family: sans-serif; padding: 40px'>Preparing Elena...</body>"
            )
            self.setCentralWidget(self.web_view)

        def closeEvent(self, event: object) -> None:
            if self.allow_close:
                super().closeEvent(event)
                return
            self.hide()
            event.ignore()

    class DesktopHost:
        def __init__(self, application: QApplication, lock: QLockFile) -> None:
            self.application = application
            self.lock = lock
            self.window = ElenaWindow()
            self.process = QProcess(application)
            self.process.finished.connect(self._runtime_finished)
            self.health_timer = QTimer(application)
            self.health_timer.setInterval(250)
            self.health_timer.timeout.connect(self._check_runtime)
            self.restart_attempts = 0
            self.stopping = False
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
            open_action.triggered.connect(self.show)
            restart_action = QAction("Restart runtime", menu)
            restart_action.triggered.connect(self.restart_runtime)
            exit_action = QAction("Exit completely", menu)
            exit_action.triggered.connect(self.shutdown)
            menu.addAction(open_action)
            menu.addAction(restart_action)
            menu.addSeparator()
            menu.addAction(exit_action)
            return menu

        def start(self) -> None:
            self._start_runtime()
            self.window.show()

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
            self.tray.setToolTip("Elena is ready")
            self.window.web_view.setUrl(QUrl(RUNTIME_URL))

        def _runtime_finished(self) -> None:
            self.health_timer.stop()
            if self.stopping:
                return
            if self.restart_attempts >= 3:
                self.tray.setToolTip("Elena needs attention")
                QMessageBox.critical(
                    self.window,
                    "Elena could not start",
                    "The runtime stopped repeatedly. Open the runtime logs before trying again.",
                )
                return
            delay = 1000 * (2**self.restart_attempts)
            self.restart_attempts += 1
            QTimer.singleShot(delay, self._start_runtime)

        def _tray_activated(self, reason: object) -> None:
            if reason == QSystemTrayIcon.ActivationReason.Trigger:
                self.show()

        def show(self) -> None:
            self.window.show()
            self.window.raise_()
            self.window.activateWindow()

        def restart_runtime(self) -> None:
            self.health_timer.stop()
            if self.process.state() != QProcess.ProcessState.NotRunning:
                self.process.terminate()
                if not self.process.waitForFinished(3000):
                    self.process.kill()
                    self.process.waitForFinished(1000)
            self.restart_attempts = 0
            self._start_runtime()

        def shutdown(self) -> None:
            if self.stopping:
                return
            self.stopping = True
            self.health_timer.stop()
            if self.process.state() != QProcess.ProcessState.NotRunning:
                self.process.terminate()
                if not self.process.waitForFinished(5000):
                    self.process.kill()
                    self.process.waitForFinished(1500)
            self.window.allow_close = True
            self.window.close()
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
        QMessageBox.information(
            None, "Elena is already running", "Use the tray icon to open Elena."
        )
        raise SystemExit(0)

    host = DesktopHost(application, lock)
    application.aboutToQuit.connect(host.shutdown)
    host.start()
    raise SystemExit(application.exec())


if __name__ == "__main__":
    main()
