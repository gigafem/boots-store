-- Изменения структуры БД boots_store для модуля 3
-- Цена может включать сотые части и не может быть отрицательной
ALTER TABLE products MODIFY price DECIMAL(10, 2) DEFAULT NULL;
-- В photo хранится путь (имя файла в папке data) к загруженному изображению
ALTER TABLE products MODIFY photo VARCHAR(255) DEFAULT NULL;
ALTER TABLE products MODIFY description VARCHAR(500) DEFAULT NULL;
-- Ограничения на неотрицательные значения
ALTER TABLE products ADD CONSTRAINT chk_price CHECK (price >= 0);
ALTER TABLE products ADD CONSTRAINT chk_amount CHECK (amount_in_warehouse >= 0);
ALTER TABLE products ADD CONSTRAINT chk_discount CHECK (current_discount BETWEEN 0 AND 100);
