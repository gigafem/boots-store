from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QMessageBox

from service.db_service import DBService
from view.products_window_ui import Ui_ProductsWindow

ROLE_ADMIN = "Администратор"
ROLE_MANAGER = "Менеджер"


class ProductsWindowService(QWidget, Ui_ProductsWindow):
    def __init__(self, user=None):
        super().__init__()
        self.setupUi(self)
        self.setWindowIcon(QIcon("data/Icon.png"))
        self.user = user
        self.product_form = None

        role_name = self.user.role_name if self.user else None
        self.is_admin = role_name == ROLE_ADMIN
        can_search = role_name in (ROLE_ADMIN, ROLE_MANAGER)

        # Поиск, сортировка и фильтрация доступны только менеджеру и администратору
        self.search_le.setVisible(can_search)
        self.sort_cb.setVisible(can_search)
        self.supplier_cb.setVisible(can_search)
        # Заказы доступны менеджеру и администратору
        self.orders_btn.setVisible(can_search)
        # Добавлять и редактировать товары может только администратор
        self.add_btn.setVisible(self.is_admin)

        self.fill_suppliers()

        self.products_list = DBService().get_products_info()
        # Если список товаров не пустой, он выводится в scrollArea
        if self.products_list:
            self.apply_filters()

        # Если пользователь авторизован, его имя отображается в правом верхнем углу окна
        if self.user:
            self.user_name_l.setText(f"{self.user.last_name} {self.user.first_name} {self.user.patronymic}")

        self.go_back_btn.clicked.connect(lambda: self.open_auth_window())
        # Поиск, сортировка и фильтр срабатывают сразу при изменении, без кнопки «Найти»
        self.search_le.textChanged.connect(lambda: self.apply_filters())
        self.sort_cb.currentIndexChanged.connect(lambda: self.apply_filters())
        self.supplier_cb.currentIndexChanged.connect(lambda: self.apply_filters())
        self.add_btn.clicked.connect(lambda: self.open_product_form())
        self.orders_btn.clicked.connect(lambda: self.open_orders_window())

    def fill_suppliers(self):
        self.supplier_cb.clear()
        # Первый элемент сбрасывает фильтр, у него нет id поставщика
        self.supplier_cb.addItem("Все поставщики", None)
        for id_supplier, name in DBService().get_reference_list("suppliers", "id_supplier"):
            self.supplier_cb.addItem(name, id_supplier)

    def apply_filters(self):
        """Совместно применяет фильтр по поставщику, поиск и выбранную сортировку."""
        products = list(self.products_list or [])

        id_supplier = self.supplier_cb.currentData()
        if id_supplier is not None:
            products = [product for product in products if product.id_supplier == id_supplier]

        search_words = self.search_le.text().lower().split()
        if search_words:
            # Каждое слово запроса должно найтись хотя бы в одном текстовом атрибуте товара,
            # поэтому можно искать сразу по нескольким атрибутам, например «kari ботинки»
            products = [product for product in products
                        if all(any(word in field for field in self.get_search_fields(product))
                               for word in search_words)]

        if self.sort_cb.currentIndex() == 1:
            products.sort(key=lambda product: product.amount_in_warehouse)
        elif self.sort_cb.currentIndex() == 2:
            products.sort(key=lambda product: product.amount_in_warehouse, reverse=True)

        self.display_products(products)

    def get_search_fields(self, product):
        fields = (product.type_name, product.article, product.description, product.producer_name,
                  product.supplier_name, product.category_name, product.unit_of_measurement)
        return [str(field).lower() for field in fields if field]

    def display_products(self, products_list):
        """Отображает список товаров в scrollArea. Если список уже отображается, то старый удаляется и отображается новый."""
        self.scrollWidget.deleteLater()

        self.scrollWidget = QWidget()

        self.products_layout = QVBoxLayout()
        self.scrollWidget.setLayout(self.products_layout)

        if not products_list:
            empty_l = QLabel("Товары не найдены. Измените условия поиска или выберите «Все поставщики».")
            empty_l.setFont(self.font)
            empty_l.setWordWrap(True)
            empty_l.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.products_layout.addWidget(empty_l)
            self.scrollArea.setWidget(self.scrollWidget)
            return

        for product in products_list:
            product_widget = QWidget()
            product_layout = QHBoxLayout()
            product_widget.setLayout(product_layout)
            self.products_layout.addWidget(product_widget)

            # Условия для выделения строки с товаром цветом: скидка больше 15% — зеленый, товара нет на складе — голубой
            if product.current_discount > 15:
                product_widget.setStyleSheet("""background-color: #2E8B57""")

            if product.amount_in_warehouse == 0:
                product_widget.setStyleSheet("""background-color: aqua""")

            # Условие для выделения цены, если скидка больше 0%
            if product.current_discount > 0:
                discounted_price = round(float(product.price) * (1 - product.current_discount / 100), 2)
                price_text = f"<s style='color:red'>{product.price}</s> {discounted_price:.2f}"
            else:
                price_text = str(product.price)

            product_photo_l = QLabel()
            product_photo_l.setFixedSize(200, 200)
            product_photo_l.setStyleSheet("border: 1px solid black")
            photo = product.photo.scaled(product_photo_l.size())
            product_photo_l.setPixmap(photo)
            product_layout.addWidget(product_photo_l)

            product_info_l = QLabel(f"{product.type_name} | {product.article}<br>"
                f"Описание товара: {product.description}<br>"
                f"Производитель: {product.producer_name}<br>"
                f"Поставщик: {product.supplier_name}<br>"
                f"Цена: {price_text}<br>"
                f"Единица измерения: {product.unit_of_measurement}<br>"
                f"Количество на складе: {product.amount_in_warehouse}")

            product_info_l.setFixedSize(300, 200)
            product_info_l.setFont(self.font)
            product_info_l.setWordWrap(True)
            product_info_l.setStyleSheet("border: 1px solid black")
            product_layout.addWidget(product_info_l)

            product_discount_l = QLabel(f"Действующая скидка:\n{product.current_discount}%")
            product_discount_l.setFont(self.font)
            product_discount_l.setWordWrap(True)
            product_discount_l.setStyleSheet("border: 1px solid black")
            product_discount_l.setAlignment(Qt.AlignmentFlag.AlignCenter)
            product_layout.addWidget(product_discount_l)

            if self.is_admin:
                product_widget.setCursor(Qt.CursorShape.PointingHandCursor)
                product_widget.setToolTip("Нажмите, чтобы отредактировать товар")
                # Клики по меткам внутри строки передаются строке, поэтому срабатывает нажатие в любом месте
                product_widget.mousePressEvent = lambda event, id_product=product.id: self.open_product_form(id_product)

        # Виджет помещается в scrollArea уже заполненным, иначе при обновлении открытого окна строки сжимаются
        self.scrollArea.setWidget(self.scrollWidget)

    def open_product_form(self, id_product=None):
        """Открывает форму добавления (id_product=None) или редактирования товара."""
        # Одновременно можно открыть только одну форму, чтобы случайно не изменить несколько товаров
        if self.product_form is not None and self.product_form.isVisible():
            self.product_form.activateWindow()
            QMessageBox.warning(self, "Форма товара уже открыта",
                                "Сейчас уже открыта форма добавления/редактирования товара.\n\n"
                                "Сохраните изменения или нажмите «Назад» в открытой форме, "
                                "а затем откройте другой товар.")
            return
        from service.product_form_service import ProductFormService
        self.product_form = ProductFormService(id_product)
        self.product_form.products_changed.connect(lambda: self.reload_products())
        self.product_form.show()

    def reload_products(self):
        """Обновляет список из БД после добавления, редактирования или удаления, сохраняя поиск, фильтр и сортировку."""
        self.products_list = DBService().get_products_info()
        self.apply_filters()

    def open_orders_window(self):
        """Переход к списку заказов."""
        from service.orders_window_service import OrdersWindowService
        self.window = OrdersWindowService(self.user)
        self.window.show()
        self.close()

    def open_auth_window(self):
        """Возврат на окно авторизации."""
        from service.auth_window_service import AuthWindowService
        self.window = AuthWindowService()
        self.window.show()
        self.close()

    def closeEvent(self, event):
        # Вместе с окном списка закрывается и открытая форма товара
        if self.product_form is not None:
            self.product_form.close()
        super().closeEvent(event)
