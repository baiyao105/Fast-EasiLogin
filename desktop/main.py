import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from RinUI import RinUIWindow


def main() -> int:
    app = QApplication(sys.argv)
    base_dir = Path(__file__).resolve().parent
    qml_path = base_dir / "view" / "main.qml"
    window = RinUIWindow(str(qml_path))
    window.setProperty("title", f"Seewo FastLogin")
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
