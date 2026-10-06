from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Prefetch
from django.utils import timezone
from datetime import timedelta
from .models import (
    Order,
    OrderItem,
    OrderStatusHistory,
    Membership,
    Product,
    Customer,
    Table,
    Comanda,
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
def table_list(request):
    membership = get_object_or_404(
        Membership,
        user=request.user,
        is_active=True
    )

    if not has_role(membership, "OWNER", "MANAGER"):
        return redirect("/")

    tables = Table.objects.filter(
        business=membership.business
    ).order_by("number")

    return render(
        request,
        "core/table_list.html",
        {"tables": tables}
    )

@login_required
def table_create(request):
    membership = get_object_or_404(
        Membership,
        user=request.user,
        is_active=True
    )

    if not has_role(membership, "OWNER", "MANAGER"):
        return redirect("/")

    if request.method == "POST":
        number = request.POST.get("number", "").strip()

        if number:
            already_exists = Table.objects.filter(
                business=membership.business,
                number=number
            ).exists()

            if not already_exists:
                Table.objects.create(
                    business=membership.business,
                    number=number
                )
                return redirect("/mesas/")

    return render(
        request,
        "core/table_create.html"
    )

@login_required
def table_deactivate(request, table_id):
    membership = get_object_or_404(
        Membership,
        user=request.user,
        is_active=True
    )

    if not has_role(membership, "OWNER", "MANAGER"):
        return redirect("/")

    table = get_object_or_404(
        Table,
        id=table_id,
        business=membership.business
    )

    if request.method == "POST":
        table.is_active = False
        table.save(update_fields=["is_active"])

    return redirect("/mesas/")

@login_required
def table_activate(request, table_id):
    membership = get_object_or_404(
        Membership,
        user=request.user,
        is_active=True
    )

    if not has_role(membership, "OWNER", "MANAGER"):
        return redirect("/")

    table = get_object_or_404(
        Table,
        id=table_id,
        business=membership.business
    )

    if request.method == "POST":
        table.is_active = True
        table.save(update_fields=["is_active"])

    return redirect("/mesas/")


@login_required
def comanda_create(request, table_id):
    membership = get_object_or_404(
        Membership,
        user=request.user,
        is_active=True
    )

    if not has_role(membership, "OWNER", "MANAGER"):
        return redirect("/")

    table = get_object_or_404(
        Table,
        id=table_id,
        business=membership.business,
        is_active=True
    )

    if request.method == "POST":
        Comanda.objects.create(
            business=membership.business,
            table=table
        )

        return redirect("/comandas/")

    return render(
        request,
        "core/comanda_create.html",
        {"table": table}
    )



@login_required
def comanda_list(request):
    membership = get_object_or_404(
        Membership,
        user=request.user,
        is_active=True
    )

    if not has_role(membership, "OWNER", "MANAGER"):
        return redirect("/")

    comandas = Comanda.objects.filter(
        business=membership.business
    ).select_related("table").order_by("-opened_at")

    return render(
        request,
        "core/comanda_list.html",
        {"comandas": comandas}
    )    


@login_required
def comanda_detail(request, comanda_id):
    membership = get_object_or_404(
        Membership,
        user=request.user,
        is_active=True
    )

    if not has_role(membership, "OWNER", "MANAGER"):
        return redirect("/")

    comanda = get_object_or_404(
        Comanda.objects.select_related("table"),
        id=comanda_id,
        business=membership.business
    )

    pedidos = comanda.orders.prefetch_related(
        "orderitem_set__product"
    ).order_by("-created_at")

    produtos = Product.objects.filter(
    business=membership.business,
    is_active=True
    ).order_by("name")

    return render(
        request,
        "core/comanda_detail.html",
        {
         "comanda": comanda,
         "pedidos": pedidos,
        "produtos": produtos,
        }
    )


@login_required
def pedido_create(request, comanda_id):
    membership = get_object_or_404(
        Membership,
        user=request.user,
        is_active=True
    )

    if not has_role(membership, "OWNER", "MANAGER"):
        return redirect("/")

    comanda = get_object_or_404(
        Comanda,
        id=comanda_id,
        business=membership.business,
        status=Comanda.Status.OPEN
    )

    if request.method == "POST":
        customer, _ = Customer.objects.get_or_create(
            business=membership.business,
            name="Cliente de Mesa",
            defaults={
                "phone": "0000000000",
            }
        )

        Order.objects.create(
            business=membership.business,
            customer=customer,
            comanda=comanda,
            order_type=Order.OrderType.TABLE,
            payment_method=Order.PaymentMethod.PENDING,
            status=Order.Status.NEW,
            total_amount=0,
        )

        return redirect(
            "comanda_detail",
            comanda_id=comanda.id
        )

    return redirect(
        "comanda_detail",
        comanda_id=comanda.id
    )


@login_required
def pedido_item_create(request, comanda_id, pedido_id):
    membership = get_object_or_404(
        Membership,
        user=request.user,
        is_active=True
    )

    if not has_role(membership, "OWNER", "MANAGER"):
        return redirect("/")

    comanda = get_object_or_404(
        Comanda,
        id=comanda_id,
        business=membership.business,
        status=Comanda.Status.OPEN
    )

    pedido = get_object_or_404(
        Order,
        id=pedido_id,
        comanda=comanda,
        business=membership.business
    )

    if request.method == "POST":
        product_id = request.POST.get("product_id")
        quantity = request.POST.get("quantity")

        product = get_object_or_404(
            Product,
            id=product_id,
            business=membership.business,
            is_active=True
        )

        OrderItem.objects.create(
        order=pedido,
        product=product,
        quantity=quantity,
        unit_price=product.price,
    )

    pedido.calculate_total()

    return redirect(
        "comanda_detail",
        comanda_id=comanda.id
    )

    return redirect(
        "comanda_detail",
        comanda_id=comanda.id
    )
    
@login_required
def pedido_item_delete(request, comanda_id, pedido_id, item_id):
    membership = get_object_or_404(
        Membership,
        user=request.user,
        is_active=True
    )

    if not has_role(membership, "OWNER", "MANAGER"):
        return redirect("/")

    comanda = get_object_or_404(
        Comanda,
        id=comanda_id,
        business=membership.business,
        status=Comanda.Status.OPEN
    )

    pedido = get_object_or_404(
        Order,
        id=pedido_id,
        comanda=comanda,
        business=membership.business
    )

    item = get_object_or_404(
        OrderItem,
        id=item_id,
        order=pedido
    )

    if request.method == "POST":
        item.delete()

        pedido.calculate_total()

        return redirect(
            "comanda_detail",
            comanda_id=comanda.id
        )

    return redirect(
        "comanda_detail",
        comanda_id=comanda.id
    )

@login_required
def pedido_item_update(request, comanda_id, pedido_id, item_id):
    membership = get_object_or_404(
        Membership,
        user=request.user,
        is_active=True
    )

    if not has_role(membership, "OWNER", "MANAGER"):
        return redirect("/")

    comanda = get_object_or_404(
        Comanda,
        id=comanda_id,
        business=membership.business,
        status=Comanda.Status.OPEN
    )

    pedido = get_object_or_404(
        Order,
        id=pedido_id,
        comanda=comanda,
        business=membership.business
    )

    item = get_object_or_404(
        OrderItem,
        id=item_id,
        order=pedido
    )

    if request.method == "POST":
        quantity = request.POST.get("quantity")

        if not quantity or not quantity.isdigit():
            return redirect(
                "comanda_detail",
                comanda_id=comanda.id
            )

        quantity = int(quantity)

        if quantity < 1:
            return redirect(
                "comanda_detail",
                comanda_id=comanda.id
            )

        item.quantity = quantity
        item.save(update_fields=["quantity"])

        pedido.calculate_total()

        return redirect(
            "comanda_detail",
            comanda_id=comanda.id
        )

    return redirect(
        "comanda_detail",
        comanda_id=comanda.id
    )

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

    limite = timezone.now() - timedelta(hours=2)

    if request.method == "POST":
        if order.status != Order.Status.OUT_FOR_DELIVERY:
            return redirect("/")

        if order.out_for_delivery_at < limite:
            return render(
                request,
                "core/confirmation_expired.html",
                {"order": order}
            )


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