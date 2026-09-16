from django.contrib import admin
from .models import Business, Category, Product, Customer, Address, Order, OrderItem

admin.site.register(Business)
admin.site.register(Category)
admin.site.register(Product)
admin.site.register(Customer)
admin.site.register(Address)
admin.site.register(Order)
admin.site.register(OrderItem)