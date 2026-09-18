from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Prefetch
from .models import Order, OrderItem, OrderStatusHistory, Membership


def has_role(membership, *roles):
    return membership.role in roles


@login_required
def manage_products(request):
    membership = get_object_or_404(
        Membership,
        user=request.user,
        is_active=True
    )

    if not has_role(membership, "OWNER", "MANAGER"):
        return redirect("/")

    return render(request, "core/manage_products.html")


@login_required
def home(request):
    membership = get_object_or_404(
        Membership,
        user=request.user,
        is_active=True
    )

    orders = Order.objects.filter(
        business=membership.business
    ).select_related("customer").prefetch_related(
        Prefetch(
            "orderitem_set",
            queryset=OrderItem.objects.select_related("product")
        ),
        "orderstatushistory_set"
    )

    return render(request, "core/home.html", {"orders": orders})


@login_required
def accept_order(request, order_id):
    membership = get_object_or_404(
    Membership,
    user=request.user,
    is_active=True
)

    order = get_object_or_404(
    Order,
    id=order_id,
    business=membership.business
)

    if order.status != Order.Status.NEW:
        return redirect("/")

    order.status = Order.Status.ACCEPTED
    order.save(update_fields=["status"])

    OrderStatusHistory.objects.create(
        order=order,
        status=order.status,
        changed_by=request.user
    )

    return redirect("/")


@login_required
def start_preparing(request, order_id):
    membership = get_object_or_404(
        Membership,
        user=request.user,
        is_active=True
    )

    order = get_object_or_404(
        Order,
        id=order_id,
        business=membership.business
    )

    if order.status != Order.Status.ACCEPTED:
        return redirect("/")

    order.status = Order.Status.PREPARING
    order.save(update_fields=["status"])

    OrderStatusHistory.objects.create(
        order=order,
        status=order.status,
        changed_by=request.user
    )

    return redirect("/")


@login_required
def mark_ready(request, order_id):
    membership = get_object_or_404(
        Membership,
        user=request.user,
        is_active=True
    )

    order = get_object_or_404(
        Order,
        id=order_id,
        business=membership.business
    )

    if order.status != Order.Status.PREPARING:
        return redirect("/")

    order.status = Order.Status.READY
    order.save(update_fields=["status"])

    OrderStatusHistory.objects.create(
        order=order,
        status=order.status,
        changed_by=request.user
    )

    return redirect("/")


@login_required
def out_for_delivery(request, order_id):
    membership = get_object_or_404(
        Membership,
        user=request.user,
        is_active=True
    )

    order = get_object_or_404(
        Order,
        id=order_id,
        business=membership.business
    )

    if order.status != Order.Status.READY:
        return redirect("/")

    order.status = Order.Status.OUT_FOR_DELIVERY
    order.save(update_fields=["status"])

    OrderStatusHistory.objects.create(
        order=order,
        status=order.status,
        changed_by=request.user
    )

    return redirect("/")


@login_required
def mark_delivered(request, order_id):
    membership = get_object_or_404(
        Membership,
        user=request.user,
        is_active=True
    )

    order = get_object_or_404(
        Order,
        id=order_id,
        business=membership.business
    )

    if order.status != Order.Status.OUT_FOR_DELIVERY:
        return redirect("/")

    order.status = Order.Status.DELIVERED
    order.save(update_fields=["status"])

    OrderStatusHistory.objects.create(
        order=order,
        status=order.status,
        changed_by=request.user
    )

    return redirect("/")