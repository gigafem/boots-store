from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QWidget, QMessageBox

from service.db_service import DBService
from view.auth_window_ui import Ui_AuthorizationWindow


class AuthWindowService(QWidget, Ui_AuthorizationWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.setWindowIcon(QIcon("data/Icon.png"))

        self.auth_btn.clicked.connect(lambda: self.auth())
        self.guest_btn.clicked.connect(lambda: self.open_products_window())

    def auth(self):
        login = self.login_le.text().strip()
        password = self.password_le.text().strip()

        if not login or not password:
            return QMessageBox.warning(self, "Ошибка авторизации", "Все поля должны быть заполнены")

        user = DBService().get_user_info(login, password)
        if user:
            return self.open_products_window(user)
        return None

    def open_products_window(self, user=None):
        from service.products_window_service import ProductsWindowService
        self.window = ProductsWindowService(user)
        self.window.show()
        self.close()
