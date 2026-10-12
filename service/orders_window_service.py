from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QMessageBox

from service.db_service import DBService
from view.orders_window_ui import Ui_OrdersWindow

ROLE_ADMIN = "Администратор"


class OrdersWindowService(QWidget, Ui_OrdersWindow):
    """Окно списка заказов. Просмотр — менеджер и администратор, изменение — только администратор."""
    def __init__(self, user):
        super().__init__()
        self.setupUi(self)
        self.setWindowIcon(QIcon("data/Icon.png"))
        self.user = user
        self.order_form = None
        self.is_admin = self.user.role_name == ROLE_ADMIN

        self.user_name_l.setText(f"{self.user.last_name} {self.user.first_name} {self.user.patronymic}")
        self.add_order_btn.setVisible(self.is_admin)

        self.reload_orders()

        self.go_back_btn.clicked.connect(lambda: self.open_products_window())
        self.add_order_btn.clicked.connect(lambda: self.open_order_form())

    def reload_orders(self):
        self.orders_list = DBService().get_orders_info()
        self.display_orders(self.orders_list or [])

    def display_orders(self, orders_list):
        """Отображает заказы в scrollArea по макету: информация о заказе слева, дата доставки справа."""
        self.scrollWidget.deleteLater()
        self.scrollWidget = QWidget()
        self.orders_layout = QVBoxLayout()
        self.orders_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.scrollWidget.setLayout(self.orders_layout)

        if not orders_list:
            empty_l = QLabel("Заказов пока нет.")
            empty_l.setFont(self.font)
            empty_l.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.orders_layout.addWidget(empty_l)

        for order in orders_list:
            order_frame = QFrame()
            order_frame.setObjectName("order_frame")
            order_frame.setStyleSheet("#order_frame {border: 1px solid black}")
            order_layout = QHBoxLayout()
            order_frame.setLayout(order_layout)
            self.orders_layout.addWidget(order_frame)

            date_order = order.date_order.strftime("%d.%m.%Y") if order.date_order else "не указана"
            date_delivery = order.date_delivery.strftime("%d.%m.%Y") if order.date_delivery else "не указана"

            order_info_l = QLabel(f"<b>Артикул заказа: {order.articles or 'нет товаров'}</b><br>"
                f"Статус заказа: {order.status_name or 'не указан'}<br>"
                f"Адрес пункта выдачи: {order.address or 'не указан'}<br>"
                f"Дата заказа: {date_order}")
            order_info_l.setFont(self.font)
            order_info_l.setWordWrap(True)
            order_info_l.setStyleSheet("border: 1px solid black; padding: 5px")
            order_layout.addWidget(order_info_l, 1)

            delivery_l = QLabel(f"Дата доставки:\n{date_delivery}")
            delivery_l.setFont(self.font)
            delivery_l.setFixedWidth(150)
            delivery_l.setAlignment(Qt.AlignmentFlag.AlignCenter)
            delivery_l.setStyleSheet("border: 2px solid black")
            order_layout.addWidget(delivery_l)

            if self.is_admin:
                order_frame.setCursor(Qt.CursorShape.PointingHandCursor)
                order_frame.setToolTip("Нажмите, чтобы отредактировать заказ")
                order_frame.mousePressEvent = lambda event, selected=order: self.open_order_form(selected)

        self.scrollArea.setWidget(self.scrollWidget)

    def open_order_form(self, order=None):
        """Открывает форму добавления (order=None) или редактирования заказа."""
        if self.order_form is not None and self.order_form.isVisible():
            self.order_form.activateWindow()
            QMessageBox.warning(self, "Форма заказа уже открыта",
                                "Сейчас уже открыта форма добавления/редактирования заказа.\n\n"
                                "Сохраните изменения или нажмите «Назад» в открытой форме, "
                                "а затем откройте другой заказ.")
            return
        from service.order_form_service import OrderFormService
        self.order_form = OrderFormService(order)
        self.order_form.orders_changed.connect(lambda: self.reload_orders())
        self.order_form.show()

    def open_products_window(self):
        """Возврат к списку товаров."""
        from service.products_window_service import ProductsWindowService
        self.window = ProductsWindowService(self.user)
        self.window.show()
        self.close()

    def closeEvent(self, event):
        if self.order_form is not None:
            self.order_form.close()
        super().closeEvent(event)
