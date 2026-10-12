class Order:
    def __init__(self, id, articles, id_status, status_name, id_pick_up_point, address,
                 date_order, date_delivery, code, id_client):
        self.id = id
        self.articles = articles
        self.id_status = id_status
        self.status_name = status_name
        self.id_pick_up_point = id_pick_up_point
        self.address = address
        self.date_order = date_order
        self.date_delivery = date_delivery
        self.code = code
        self.id_client = id_client
