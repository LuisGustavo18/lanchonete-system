from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Prefetch
from django.utils import timezone
from .models import (
    Order,
    OrderItem,
    OrderStatusHistory,
    Membership,
    Product,
)


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
def product_list(request):
    membership = get_object_or_404(
        Membership,
        user=request.user,
        is_active=True
    )

    if not has_role(membership, "OWNER", "MANAGER"):
        return redirect("/")

    products = Product.objects.filter(
        business=membership.business
    ).select_related("category")

    return render(
        request,
        "core/product_list.html",
        {"products": products}
    )

@login_required
def product_create(request):
    membership = get_object_or_404(
        Membership,
        user=request.user,
        is_active=True
    )

    if not has_role(membership, "OWNER", "MANAGER"):
        return redirect("/")

    if request.method == "POST":
        name = request.POST.get("name")
        description = request.POST.get("description")
        price = request.POST.get("price")
        category_id = request.POST.get("category")

        Product.objects.create(
            business=membership.business,
            category_id=category_id,
            name=name,
            description=description,
            price=price,
        )

        return redirect("/produtos/")

    categories = membership.business.category_set.filter(
        is_active=True
    )

    return render(
        request,
        "core/product_create.html",
        {"categories": categories}
    )


@login_required
def product_update(request, product_id):
    membership = get_object_or_404(
        Membership,
        user=request.user,
        is_active=True
    )

    if not has_role(membership, "OWNER", "MANAGER"):
        return redirect("/")

    product = get_object_or_404(
        Product,
        id=product_id,
        business=membership.business
    )

    if request.method == "POST":
        product.name = request.POST.get("name")
        product.description = request.POST.get("description")

        price = request.POST.get("price").replace(",", ".")
        product.price = price

        product.category_id = request.POST.get("category")

        product.save()

        return redirect("/produtos/")

    categories = membership.business.category_set.filter(
        is_active=True
    )

    return render(
        request,
        "core/product_update.html",
        {
            "product": product,
            "categories": categories,
        }
    )

@login_required
def product_deactivate(request, product_id):
    membership = get_object_or_404(
        Membership,
        user=request.user,
        is_active=True
    )

    if not has_role(membership, "OWNER", "MANAGER"):
        return redirect("/")

    product = get_object_or_404(
        Product,
        id=product_id,
        business=membership.business
    )

    if request.method == "POST":
        product.is_active = False
        product.save()

    return redirect("/produtos/")

@login_required
def product_activate(request, product_id):
    membership = get_object_or_404(
        Membership,
        user=request.user,
        is_active=True
    )

    if not has_role(membership, "OWNER", "MANAGER"):
        return redirect("/")

    product = get_object_or_404(
        Product,
        id=product_id,
        business=membership.business
    )

    if request.method == "POST":
        product.is_active = True
        product.save()

    return redirect("/produtos/")


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

    new_orders = orders.filter(status="NOVO")

    accepted_orders = orders.filter(status="ACEITO")

    preparing_orders = orders.filter(status="EM_PREPARO")

    ready_orders = orders.filter(status="PRONTO")

    out_for_delivery_orders = orders.filter(
        status="SAIU_PARA_ENTREGA"
    )

    delivered_orders = orders.filter(status="ENTREGUE")

    return render(
        request,
        "core/home.html",
        {
            "new_orders": new_orders,
            "accepted_orders": accepted_orders,
            "preparing_orders": preparing_orders,
            "ready_orders": ready_orders,
            "out_for_delivery_orders": out_for_delivery_orders,
            "delivered_orders": delivered_orders,
        }
    )


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
    order.out_for_delivery_at = timezone.now()
    order.save(update_fields=["status", "out_for_delivery_at"])

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


def confirm_delivery(request, token):
    order = get_object_or_404(
        Order,
        confirmation_token=token
    )

    if request.method == "POST":
        if order.status == Order.Status.OUT_FOR_DELIVERY:
            order.status = Order.Status.DELIVERED
            order.delivery_confirmed_by = "CLIENTE"
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

        return redirect("/")

    return render(
        request,
        "core/confirm_delivery.html",
        {"order": order}
    )