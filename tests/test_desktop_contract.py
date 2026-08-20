import sys

from elena.desktop import RUNTIME_URL, runtime_command


def test_desktop_starts_runtime_with_current_interpreter() -> None:
    program, arguments = runtime_command()

    assert program == sys.executable
    assert arguments == ["-m", "elena.runtime"]
    assert RUNTIME_URL == "http://127.0.0.1:8765"