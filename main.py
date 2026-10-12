import sys
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication
from service.auth_window_service import AuthWindowService


app = QApplication(sys.argv)
app.styleHints().setColorScheme(Qt.ColorScheme.Light)
window = AuthWindowService()
window.show()
sys.exit(app.exec())
