from django.utils import timezone
from datetime import timedelta
from django.utils import timezone
from datetime import timedelta
from .models import Order, OrderStatusHistory


def auto_complete_deliveries():
    limite = timezone.now() - timedelta(hours=2)

    pedidos = Order.objects.filter(
        status=Order.Status.OUT_FOR_DELIVERY,
        out_for_delivery_at__lte=limite
    )

    for order in pedidos:
        order.status = Order.Status.DELIVERED
        order.delivery_confirmed_by = "AUTOMATICO"

        order.save(
            update_fields=[
                "status",
                "delivery_confirmed_by"
            ]
        )
    OrderStatusHistory.objects.create(
    order=order,
    status=order.status,
    changed_by=None
)