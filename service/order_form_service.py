from PyQt6.QtCore import QDate, pyqtSignal
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QWidget, QMessageBox

from service.db_service import DBService
from view.order_form_ui import Ui_OrderFormWindow


class OrderFormService(QWidget, Ui_OrderFormWindow):
    """Форма добавления (order=None) и редактирования заказа. Доступна только администратору."""
    orders_changed = pyqtSignal()

    def __init__(self, order=None):
        super().__init__()
        self.setupUi(self)
        self.setWindowIcon(QIcon("data/Icon.png"))
        self.order = order

        self.fill_combo_boxes()

        if self.order is None:
            self.setWindowTitle("Добавление заказа")
            self.id_l.hide()
            self.id_le.hide()
            self.delete_btn.hide()
            self.date_order_de.setDate(QDate.currentDate())
            self.date_delivery_de.setDate(QDate.currentDate())
        else:
            self.setWindowTitle("Редактирование заказа")
            self.fill_fields()

        self.save_btn.clicked.connect(lambda: self.save_order())
        self.delete_btn.clicked.connect(lambda: self.delete_order())
        self.back_btn.clicked.connect(lambda: self.close())

    def fill_combo_boxes(self):
        db = DBService()
        for id_status, name in db.get_reference_list("order_status", "id_status"):
            self.status_cb.addItem(name, id_status)
        for id_point, address in db.get_pick_up_points():
            self.pick_up_point_cb.addItem(address, id_point)

    def fill_fields(self):
        self.id_le.setText(str(self.order.id))
        self.articles_le.setText(self.order.articles or "")
        self.status_cb.setCurrentIndex(self.status_cb.findData(self.order.id_status))
        self.pick_up_point_cb.setCurrentIndex(self.pick_up_point_cb.findData(self.order.id_pick_up_point))
        if self.order.date_order:
            self.date_order_de.setDate(QDate(self.order.date_order))
        if self.order.date_delivery:
            self.date_delivery_de.setDate(QDate(self.order.date_delivery))

    def parse_articles(self, errors):
        """Разбирает строку «артикул, количество, ...» в список (id товара, количество)."""
        parts = [part.strip() for part in self.articles_le.text().split(",") if part.strip()]
        if not parts:
            errors.append("Укажите артикул заказа: артикул товара и количество через запятую, "
                          "например «A112T4, 2».")
            return []
        if len(parts) % 2 != 0:
            errors.append("После каждого артикула через запятую укажите количество, например «A112T4, 2, F635R4, 1».")
            return []

        amounts = {}
        for article, amount in zip(parts[::2], parts[1::2]):
            article = article.upper()
            if not amount.isdigit() or int(amount) == 0:
                errors.append(f"Количество товара «{article}» должно быть целым числом больше нуля.")
            elif article in amounts:
                errors.append(f"Артикул «{article}» указан несколько раз. Укажите его один раз с общим количеством.")
            else:
                amounts[article] = int(amount)

        product_ids = DBService().get_product_ids_by_articles(amounts.keys())
        if product_ids is None:
            return []
        unknown = [article for article in amounts if article not in product_ids]
        if unknown:
            errors.append(f"Товары с артикулами {', '.join(unknown)} не найдены. Проверьте артикулы в списке товаров.")
        return [(product_ids[article], amount) for article, amount in amounts.items() if article in product_ids]

    def save_order(self):
        errors = []
        items = self.parse_articles(errors)
        if self.status_cb.currentData() is None:
            errors.append("Выберите статус заказа.")
        if self.pick_up_point_cb.currentData() is None:
            errors.append("Выберите адрес пункта выдачи.")
        if self.date_delivery_de.date() < self.date_order_de.date():
            errors.append("Дата выдачи не может быть раньше даты заказа.")
        if errors:
            QMessageBox.warning(self, "Ошибка заполнения формы",
                                "Заказ не сохранен. Исправьте ошибки:\n\n" + "\n".join(f"• {e}" for e in errors))
            return

        data = {"id_status": self.status_cb.currentData(),
                "id_pick_up_point": self.pick_up_point_cb.currentData(),
                "date_order": self.date_order_de.date().toPyDate(),
                "date_delivery": self.date_delivery_de.date().toPyDate()}

        db = DBService()
        if self.order is None:
            if not db.add_order(data, items):
                return
            QMessageBox.information(self, "Добавление заказа", "Заказ успешно добавлен.")
        else:
            if not db.update_order(self.order.id, data, items):
                return
            QMessageBox.information(self, "Редактирование заказа", f"Изменения заказа № {self.order.id} сохранены.")
        self.orders_changed.emit()
        self.close()

    def delete_order(self):
        answer = QMessageBox.question(self, "Подтверждение удаления",
                                      f"Вы действительно хотите удалить заказ № {self.order.id}?\n\n"
                                      "Заказ будет удален вместе с составом. Это действие нельзя отменить.",
                                      QMessageBox.StandardButton.Да | QMessageBox.StandardButton.No,
                                      QMessageBox.StandardButton.Нет)
        if answer != QMessageBox.StandardButton.Да:
            return
        if DBService().delete_order(self.order.id):
            QMessageBox.information(self, "Удаление заказа", f"Заказ № {self.order.id} удален.")
            self.orders_changed.emit()
            self.close()
