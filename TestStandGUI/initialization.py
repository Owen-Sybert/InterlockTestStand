import sys
from PyQt6.QtWidgets import QApplication
from ui.executionWindow import ExecutionWindow


def main():
    app = QApplication(sys.argv)
    window = ExecutionWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
