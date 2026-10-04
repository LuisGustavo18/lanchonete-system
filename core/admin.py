from django.contrib import admin

from .models import (
    Business,
    Membership,
    Category,
    Product,
    Customer,
    Address,
    Order,
    OrderItem,
    OrderStatusHistory,
    Table,
    Comanda,
)

admin.site.register(Business)
admin.site.register(Membership)
admin.site.register(Category)
admin.site.register(Product)
admin.site.register(Customer)
admin.site.register(Address)
admin.site.register(Order)
admin.site.register(OrderItem)
admin.site.register(OrderStatusHistory)
admin.site.register(Table)
admin.site.register(Comanda)