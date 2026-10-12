class Product:
    def __init__(self, id, article, id_type, type_name, unit_of_measurement, price,
                 id_supplier, supplier_name, id_producer, producer_name, id_category,
                 category_name, current_discount, amount_in_warehouse, description, photo):
        self.id = id
        self.article = article
        self.id_type = id_type
        self.type_name = type_name
        self.unit_of_measurement = unit_of_measurement
        self.price = price
        self.id_supplier = id_supplier
        self.supplier_name = supplier_name
        self.id_producer = id_producer
        self.producer_name = producer_name
        self.id_category = id_category
        self.category_name = category_name
        self.current_discount = current_discount
        self.amount_in_warehouse = amount_in_warehouse
        self.description = description
        self.photo = photo
