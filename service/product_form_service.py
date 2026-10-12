import os
import time

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QIcon, QImage, QPixmap
from PyQt6.QtWidgets import QWidget, QMessageBox, QFileDialog

from service.db_service import DBService
from view.product_form_ui import Ui_ProductFormWindow

PHOTO_DIR = "data"
PLACEHOLDER_PHOTO = "data/picture.png"
MAX_PHOTO_WIDTH = 300
MAX_PHOTO_HEIGHT = 200


class ProductFormService(QWidget, Ui_ProductFormWindow):
    """Форма добавления (id_product=None) и редактирования товара. Доступна только администратору."""
    products_changed = pyqtSignal()

    def __init__(self, id_product=None):
        super().__init__()
        self.setupUi(self)
        self.setWindowIcon(QIcon("data/Icon.png"))
        self.id_product = id_product
        self.old_photo = None
        self.new_photo_path = None

        self.fill_combo_boxes()

        if self.id_product is None:
            self.setWindowTitle("Добавление товара")
            self.id_l.hide()
            self.id_le.hide()
            self.delete_btn.hide()
            self.set_photo(PLACEHOLDER_PHOTO)
        else:
            self.setWindowTitle("Редактирование товара")
            self.load_product()

        self.choose_photo_btn.clicked.connect(lambda: self.choose_photo())
        self.save_btn.clicked.connect(lambda: self.save_product())
        self.delete_btn.clicked.connect(lambda: self.delete_product())
        self.back_btn.clicked.connect(lambda: self.close())

    def fill_combo_boxes(self):
        """Заполняет выпадающие списки значениями из справочников БД."""
        db = DBService()
        combo_sources = ((self.type_cb, "product_type", "id_type"),
                         (self.category_cb, "product_category", "id_category"),
                         (self.producer_cb, "producers", "id_producer"),
                         (self.supplier_cb, "suppliers", "id_supplier"))
        for combo, table, id_column in combo_sources:
            combo.clear()
            for item_id, name in db.get_reference_list(table, id_column):
                combo.addItem(name, item_id)

    def load_product(self):
        """Подгружает в поля формы актуальные данные товара из БД."""
        product = DBService().get_product(self.id_product)
        if not product:
            self.products_changed.emit()
            self.save_btn.setEnabled(False)
            self.delete_btn.setEnabled(False)
            return

        self.id_le.setText(str(product["id_product"]))
        self.article_le.setText(product["article"] or "")
        self.description_te.setPlainText(product["description"] or "")
        self.unit_le.setText(product["unit_of_measurment"] or "")
        self.price_sb.setValue(float(product["price"] or 0))
        self.amount_sb.setValue(product["amount_in_warehouse"] or 0)
        self.discount_sb.setValue(product["current_discount"] or 0)
        self.type_cb.setCurrentIndex(self.type_cb.findData(product["id_type"]))
        self.category_cb.setCurrentIndex(self.category_cb.findData(product["id_category"]))
        self.producer_cb.setCurrentIndex(self.producer_cb.findData(product["id_producer"]))
        self.supplier_cb.setCurrentIndex(self.supplier_cb.findData(product["id_supplier"]))

        self.old_photo = product["photo"]
        if self.old_photo and os.path.isfile(os.path.join(PHOTO_DIR, self.old_photo)):
            self.set_photo(os.path.join(PHOTO_DIR, self.old_photo))
        else:
            self.set_photo(PLACEHOLDER_PHOTO)

    def set_photo(self, path):
        pixmap = QPixmap(path)
        self.photo_l.setPixmap(pixmap.scaled(self.photo_l.size(), Qt.AspectRatioMode.KeepAspectRatio,
                                             Qt.TransformationMode.SmoothTransformation))

    def choose_photo(self):
        """Выбор нового фото. Файл копируется в папку data только при сохранении товара."""
        path, _ = QFileDialog.getOpenFileName(self, "Выбор фото товара", "", "Изображения (*.png *.jpg *.jpeg)")
        if not path:
            return
        if QImage(path).isNull():
            QMessageBox.warning(self, "Ошибка загрузки фото",
                                f"Не удалось открыть файл:\n{path}\n\n"
                                "Выберите изображение в формате PNG или JPG.")
            return
        self.new_photo_path = path
        self.set_photo(path)

    def get_form_data(self):
        return {"article": self.article_le.text().strip(),
                "id_type": self.type_cb.currentData(),
                "id_category": self.category_cb.currentData(),
                "description": self.description_te.toPlainText().strip(),
                "id_producer": self.producer_cb.currentData(),
                "id_supplier": self.supplier_cb.currentData(),
                "price": round(self.price_sb.value(), 2),
                "unit": self.unit_le.text().strip(),
                "amount": self.amount_sb.value(),
                "discount": self.discount_sb.value(),
                "photo": self.old_photo}

    def validate(self, data):
        """Возвращает список ошибок заполнения формы (пустой список — ошибок нет)."""
        errors = []
        if not data["article"]:
            errors.append("Укажите артикул товара.")
        if data["id_type"] is None:
            errors.append("Выберите наименование товара.")
        if data["id_category"] is None:
            errors.append("Выберите категорию товара.")
        if not data["description"]:
            errors.append("Заполните описание товара.")
        elif len(data["description"]) > 500:
            errors.append("Описание не может быть длиннее 500 символов.")
        if data["id_producer"] is None:
            errors.append("Выберите производителя.")
        if data["id_supplier"] is None:
            errors.append("Выберите поставщика.")
        if data["price"] < 0:
            errors.append("Цена не может быть отрицательной.")
        if not data["unit"]:
            errors.append("Укажите единицу измерения (например, «шт.»).")
        if data["amount"] < 0:
            errors.append("Количество на складе не может быть отрицательным.")
        if data["article"] and DBService().article_exists(data["article"], self.id_product):
            errors.append(f"Товар с артикулом «{data['article']}» уже существует. Укажите другой артикул.")
        return errors

    def save_photo_file(self):
        """Сохраняет выбранное фото в папку data (не больше 300×200) и возвращает имя файла."""
        image = QImage(self.new_photo_path)
        if image.width() > MAX_PHOTO_WIDTH or image.height() > MAX_PHOTO_HEIGHT:
            image = image.scaled(MAX_PHOTO_WIDTH, MAX_PHOTO_HEIGHT, Qt.AspectRatioMode.KeepAspectRatio,
                                 Qt.TransformationMode.SmoothTransformation)
        file_name = f"product_{int(time.time() * 1000)}.jpg"
        if not image.save(os.path.join(PHOTO_DIR, file_name), "JPG"):
            QMessageBox.critical(self, "Ошибка сохранения фото",
                                 "Не удалось сохранить фото в папку data. Проверьте права доступа к папке "
                                 "приложения и повторите попытку.")
            return None
        return file_name

    def remove_photo_file(self, file_name):
        path = os.path.join(PHOTO_DIR, file_name)
        if file_name in ("picture.png", "Icon.png") or not os.path.isfile(path):
            return
        try:
            os.remove(path)
        except OSError as e:
            QMessageBox.warning(self, "Удаление фото", f"Старое фото не удалось удалить: {path}\nОшибка: {e}")

    def save_product(self):
        data = self.get_form_data()
        errors = self.validate(data)
        if errors:
            QMessageBox.warning(self, "Ошибка заполнения формы",
                                "Товар не сохранен. Исправьте ошибки:\n\n" + "\n".join(f"• {e}" for e in errors))
            return

        if self.new_photo_path:
            data["photo"] = self.save_photo_file()
            if data["photo"] is None:
                return

        db = DBService()
        if self.id_product is None:
            is_saved = db.add_product(data)
        else:
            is_saved = db.update_product(self.id_product, data)

        if not is_saved:
            if self.new_photo_path:
                self.remove_photo_file(data["photo"])
            return

        if self.new_photo_path and self.old_photo:
            self.remove_photo_file(self.old_photo)

        if self.id_product is None:
            QMessageBox.information(self, "Добавление товара", f"Товар «{data['article']}» успешно добавлен.")
        else:
            QMessageBox.information(self, "Редактирование товара", f"Изменения товара «{data['article']}» сохранены.")
        self.products_changed.emit()
        self.close()

    def delete_product(self):
        db = DBService()
        in_orders = db.product_in_orders(self.id_product)
        if in_orders is None:
            return
        article = self.article_le.text()
        if in_orders:
            QMessageBox.warning(self, "Удаление невозможно",
                                f"Товар «{article}» присутствует в заказах, поэтому его нельзя удалить.\n\n"
                                "Удалить можно только товар, которого нет ни в одном заказе.")
            return

        answer = QMessageBox.question(self, "Подтверждение удаления",
                                      f"Вы действительно хотите удалить товар «{article}»?\n\n"
                                      "Это действие нельзя отменить.",
                                      QMessageBox.StandardButton.Да | QMessageBox.StandardButton.No,
                                      QMessageBox.StandardButton.No)
        if answer != QMessageBox.StandardButton.Да:
            return

        if db.delete_product(self.id_product):
            if self.old_photo:
                self.remove_photo_file(self.old_photo)
            QMessageBox.information(self, "Удаление товара", f"Товар «{article}» удален.")
            self.products_changed.emit()
            self.close()
