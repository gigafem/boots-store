import pymysql
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtWidgets import QMessageBox

from data.order import Order
from data.product import Product
from data.user import User


class DBService:
    def __init__(self):
        self.conn = None
        try:
            self.conn = pymysql.connect(host="127.0.1.30", user="root", password="", db="boots_store")
        except Exception as e:
            QMessageBox.warning(None, "Ошибка подключения к БД", f"Ошибка: {e}")

    def get_user_info(self, login, password):
        """Возвращает объект User по логину и паролю, или None при неправильных данных."""
        if not self.conn:
            return None
        try:
            with self.conn.cursor() as cur:
                cur.execute("""select u.id_user, u.last_name, u.first_name, u.patronymic, u.id_role, r.name from users u
                            join users_roles r on r.id_role = u.id_role
                            where u.login = %s and u.password = %s""", (str(login), str(password)))
                result = cur.fetchall()
                if result:
                    return User(*result[0])
                else:
                    QMessageBox.warning(None, "Ошибка авторизации", "Неверный логин или пароль")
                    return None
        except Exception as e:
            QMessageBox.warning(None, "Ошибка получения данных", f"Ошибка: {e}")
            return None

    def get_products_info(self):
        """Возвращает список объектов Product из БД. Если фото отсутствует — используется картинка-заглушка."""
        if not self.conn:
            return None
        try:
            with self.conn.cursor() as cur:
                cur.execute("""select p.id_product, p.article, p.id_type, t.name, p.unit_of_measurment, p.price,
                 p.id_supplier, s.name, p.id_producer, pr.name, p.id_category,
                 c.name, p.current_discount, p.amount_in_warehouse, p.description, p.photo from products p
                            join product_type t on t.id_type = p.id_type
                            join suppliers s on s.id_supplier = p.id_supplier
                            join producers pr on pr.id_producer = p.id_producer
                            join product_category c on c.id_category = p.id_category""")
                result = cur.fetchall()

                products_list = []
                if result:
                    for product in result:
                        if product[15]:
                            photo_img = QImage(f"data/{product[15]}")
                        else:
                            photo_img = QImage(f"data/picture.png")
                        photo_pixmap = QPixmap.fromImage(photo_img)

                        products_list.append(Product(*product[:15], photo_pixmap))
                    return products_list
                else:
                    QMessageBox.warning(None, "Ошибка получения данных", "Товары не найдены")
                    return None
        except Exception as e:
            QMessageBox.warning(None, "Ошибка получения данных", f"Ошибка: {e}")
            return None

    def get_reference_list(self, table, id_column):
        """Возвращает список (id, название) из справочной таблицы для выпадающих списков."""
        if not self.conn:
            return []
        try:
            with self.conn.cursor() as cur:
                # Имена таблицы и столбца задаются только в коде программы, а не пользователем
                cur.execute(f"select {id_column}, name from {table} order by name")
                return list(cur.fetchall())
        except Exception as e:
            QMessageBox.critical(None, "Ошибка базы данных",
                                 f"Не удалось загрузить справочник «{table}».\nОшибка: {e}")
            return []

    def get_product(self, id_product):
        """Возвращает словарь с данными товара для формы редактирования, или None."""
        if not self.conn:
            return None
        try:
            with self.conn.cursor(pymysql.cursors.DictCursor) as cur:
                cur.execute("""select id_product, article, id_type, unit_of_measurment, price, id_supplier,
                            id_producer, id_category, current_discount, amount_in_warehouse, description, photo
                            from products where id_product = %s""", (id_product,))
                product = cur.fetchone()
                if not product:
                    QMessageBox.warning(None, "Товар не найден",
                                        f"Товар с ID {id_product} не найден. Возможно, он уже удален.\n"
                                        "Список товаров будет обновлен.")
                return product
        except Exception as e:
            QMessageBox.critical(None, "Ошибка базы данных", f"Не удалось загрузить данные товара.\nОшибка: {e}")
            return None

    def article_exists(self, article, exclude_id=None):
        """Проверяет, есть ли в БД другой товар с таким же артикулом."""
        if not self.conn:
            return None
        try:
            with self.conn.cursor() as cur:
                cur.execute("select count(*) from products where article = %s and id_product <> %s",
                            (article, exclude_id or 0))
                return cur.fetchone()[0] > 0
        except Exception as e:
            QMessageBox.critical(None, "Ошибка базы данных", f"Не удалось проверить артикул.\nОшибка: {e}")
            return None

    def add_product(self, data):
        """Добавляет товар. ID вычисляется как максимальный ID в БД + 1."""
        if not self.conn:
            return False
        try:
            with self.conn.cursor() as cur:
                cur.execute("select coalesce(max(id_product), 0) + 1 from products")
                new_id = cur.fetchone()[0]
                cur.execute("""insert into products (id_product, article, id_type, unit_of_measurment, price,
                            id_supplier, id_producer, id_category, current_discount, amount_in_warehouse,
                            description, photo)
                            values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                            (new_id, data["article"], data["id_type"], data["unit"], data["price"],
                             data["id_supplier"], data["id_producer"], data["id_category"], data["discount"],
                             data["amount"], data["description"], data["photo"]))
            self.conn.commit()
            return True
        except Exception as e:
            self.conn.rollback()
            QMessageBox.critical(None, "Ошибка базы данных",
                                 f"Товар не был добавлен. Проверьте введенные данные и повторите попытку.\nОшибка: {e}")
            return False

    def update_product(self, id_product, data):
        """Сохраняет изменения существующего товара."""
        if not self.conn:
            return False
        try:
            with self.conn.cursor() as cur:
                cur.execute("""update products set article = %s, id_type = %s, unit_of_measurment = %s, price = %s,
                            id_supplier = %s, id_producer = %s, id_category = %s, current_discount = %s,
                            amount_in_warehouse = %s, description = %s, photo = %s
                            where id_product = %s""",
                            (data["article"], data["id_type"], data["unit"], data["price"], data["id_supplier"],
                             data["id_producer"], data["id_category"], data["discount"], data["amount"],
                             data["description"], data["photo"], id_product))
            self.conn.commit()
            return True
        except Exception as e:
            self.conn.rollback()
            QMessageBox.critical(None, "Ошибка базы данных",
                                 f"Изменения не были сохранены. Проверьте введенные данные и повторите попытку.\nОшибка: {e}")
            return False

    def product_in_orders(self, id_product):
        """Проверяет, присутствует ли товар хотя бы в одном заказе."""
        if not self.conn:
            return None
        try:
            with self.conn.cursor() as cur:
                cur.execute("select count(*) from products_in_orders where id_product = %s", (id_product,))
                return cur.fetchone()[0] > 0
        except Exception as e:
            QMessageBox.critical(None, "Ошибка базы данных", f"Не удалось проверить заказы товара.\nОшибка: {e}")
            return None

    def delete_product(self, id_product):
        """Удаляет товар из БД."""
        if not self.conn:
            return False
        try:
            with self.conn.cursor() as cur:
                cur.execute("delete from products where id_product = %s", (id_product,))
            self.conn.commit()
            return True
        except Exception as e:
            self.conn.rollback()
            QMessageBox.critical(None, "Ошибка базы данных", f"Товар не был удален.\nОшибка: {e}")
            return False

    def get_orders_info(self):
        """Возвращает список объектов Order. Артикул заказа собирается из товаров заказа: «артикул, количество, ...»."""
        if not self.conn:
            return None
        try:
            with self.conn.cursor() as cur:
                cur.execute("""select o.id_order,
                            group_concat(concat(p.article, ', ', pio.amount_product)
                                         order by pio.id_procudt_in_order separator ', '),
                            o.id_status, s.name, o.id_pick_up_point,
                            concat_ws(', ', pp.index_address, pp.city, pp.street, pp.house),
                            o.date_order, o.date_delivery, o.code, o.id_client from orders o
                            left join order_status s on s.id_status = o.id_status
                            left join pick_up_points pp on pp.id_point = o.id_pick_up_point
                            left join products_in_orders pio on pio.id_order = o.id_order
                            left join products p on p.id_product = pio.id_product
                            group by o.id_order
                            order by o.id_order""")
                return [Order(*order) for order in cur.fetchall()]
        except Exception as e:
            QMessageBox.critical(None, "Ошибка базы данных", f"Не удалось загрузить список заказов.\nОшибка: {e}")
            return None

    def get_pick_up_points(self):
        """Возвращает список (id, адрес) пунктов выдачи."""
        if not self.conn:
            return []
        try:
            with self.conn.cursor() as cur:
                cur.execute("""select id_point, concat_ws(', ', index_address, city, street, house)
                            from pick_up_points order by city, street, house""")
                return list(cur.fetchall())
        except Exception as e:
            QMessageBox.critical(None, "Ошибка базы данных", f"Не удалось загрузить пункты выдачи.\nОшибка: {e}")
            return []

    def get_product_ids_by_articles(self, articles):
        """Возвращает словарь {артикул: id товара} для найденных в БД артикулов."""
        if not self.conn or not articles:
            return {}
        try:
            with self.conn.cursor() as cur:
                placeholders = ", ".join(["%s"] * len(articles))
                cur.execute(f"select article, id_product from products where article in ({placeholders})",
                            list(articles))
                return {article.upper(): id_product for article, id_product in cur.fetchall()}
        except Exception as e:
            QMessageBox.critical(None, "Ошибка базы данных", f"Не удалось проверить артикулы товаров.\nОшибка: {e}")
            return None

    def save_order_items(self, cur, id_order, items):
        """Перезаписывает состав заказа: items — список (id товара, количество)."""
        cur.execute("delete from products_in_orders where id_order = %s", (id_order,))
        for id_product, amount in items:
            cur.execute("insert into products_in_orders (id_order, id_product, amount_product) values (%s, %s, %s)",
                        (id_order, id_product, amount))

    def add_order(self, data, items):
        """Добавляет заказ. Номер и код получения вычисляются как максимальные значения в БД + 1."""
        if not self.conn:
            return False
        try:
            with self.conn.cursor() as cur:
                cur.execute("select coalesce(max(id_order), 0) + 1, coalesce(max(code), 900) + 1 from orders")
                new_id, new_code = cur.fetchone()
                cur.execute("""insert into orders (id_order, date_order, date_delivery, id_pick_up_point, code, id_status)
                            values (%s, %s, %s, %s, %s, %s)""",
                            (new_id, data["date_order"], data["date_delivery"], data["id_pick_up_point"],
                             new_code, data["id_status"]))
                self.save_order_items(cur, new_id, items)
            self.conn.commit()
            return True
        except Exception as e:
            self.conn.rollback()
            QMessageBox.critical(None, "Ошибка базы данных",
                                 f"Заказ не был добавлен. Проверьте введенные данные и повторите попытку.\nОшибка: {e}")
            return False

    def update_order(self, id_order, data, items):
        """Сохраняет изменения заказа вместе с его составом."""
        if not self.conn:
            return False
        try:
            with self.conn.cursor() as cur:
                cur.execute("""update orders set date_order = %s, date_delivery = %s, id_pick_up_point = %s,
                            id_status = %s where id_order = %s""",
                            (data["date_order"], data["date_delivery"], data["id_pick_up_point"],
                             data["id_status"], id_order))
                self.save_order_items(cur, id_order, items)
            self.conn.commit()
            return True
        except Exception as e:
            self.conn.rollback()
            QMessageBox.critical(None, "Ошибка базы данных",
                                 f"Изменения заказа не были сохранены. Повторите попытку.\nОшибка: {e}")
            return False

    def delete_order(self, id_order):
        """Удаляет заказ вместе с его составом."""
        if not self.conn:
            return False
        try:
            with self.conn.cursor() as cur:
                # Состав удаляется первым, иначе в products_in_orders останутся строки без заказа
                cur.execute("delete from products_in_orders where id_order = %s", (id_order,))
                cur.execute("delete from orders where id_order = %s", (id_order,))
            self.conn.commit()
            return True
        except Exception as e:
            self.conn.rollback()
            QMessageBox.critical(None, "Ошибка базы данных", f"Заказ не был удален.\nОшибка: {e}")
            return False
