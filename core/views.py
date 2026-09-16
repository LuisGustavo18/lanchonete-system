from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Prefetch
from .models import Order, OrderItem, OrderStatusHistory

@login_required
def home(request):
    orders = Order.objects.select_related("customer").prefetch_related(
        Prefetch(
            "orderitem_set",
            queryset=OrderItem.objects.select_related("product")
        ),
        "orderstatushistory_set"
    ).all()

    return render(request, "core/home.html", {"orders": orders})


@login_required
def accept_order(request, order_id):
    order = Order.objects.get(id=order_id)

    order.status = Order.Status.ACCEPTED
    order.save(update_fields=["status"])

    OrderStatusHistory.objects.create(
        order=order,
        status=order.status
    )

    return redirect("/")


@login_required
def start_preparing(request, order_id):
    order = Order.objects.get(id=order_id)

    order.status = Order.Status.PREPARING
    order.save(update_fields=["status"])

    OrderStatusHistory.objects.create(
        order=order,
        status=order.status
    )

    return redirect("/")


@login_required
def mark_ready(request, order_id):
    order = Order.objects.get(id=order_id)

    order.status = Order.Status.READY
    order.save(update_fields=["status"])

    OrderStatusHistory.objects.create(
        order=order,
        status=order.status
    )

    return redirect("/")


@login_required
def out_for_delivery(request, order_id):
    order = Order.objects.get(id=order_id)

    order.status = Order.Status.OUT_FOR_DELIVERY
    order.save(update_fields=["status"])

    OrderStatusHistory.objects.create(
        order=order,
        status=order.status
    )

    return redirect("/")


@login_required
def mark_delivered(request, order_id):
    order = Order.objects.get(id=order_id)

    order.status = Order.Status.DELIVERED
    order.save(update_fields=["status"])

    OrderStatusHistory.objects.create(
        order=order,
        status=order.status
    )

    return redirect("/")
