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
    PaymentEvent,
)

admin.site.register(Business)
admin.site.register(Membership)
admin.site.register(Category)
admin.site.register(Product)
admin.site.register(Customer)
admin.site.register(Address)
@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'business', 'customer', 'status', 'payment_method', 'payment_status', 'total_amount')
    list_filter = ('business', 'status', 'payment_status', 'payment_method')
    search_fields = ('customer_name', 'customer_phone', 'customer__name')
    readonly_fields = ('payment_status', 'paid_at', 'checkout_token', 'customer_name', 'customer_phone', 'address_snapshot')

    def get_readonly_fields(self, request, obj=None):
        fields = super().get_readonly_fields(request, obj)
        if obj and obj.payment_status == Order.PaymentStatus.PAID:
            return fields + ('total_amount', 'payment_method', 'cash_change_for', 'delivery_fee')
        return fields


@admin.register(PaymentEvent)
class PaymentEventAdmin(admin.ModelAdmin):
    list_display = ('order', 'status', 'amount', 'changed_by', 'created_at')
    readonly_fields = ('order', 'status', 'amount', 'changed_by', 'note', 'created_at')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
admin.site.register(OrderItem)
admin.site.register(OrderStatusHistory)
