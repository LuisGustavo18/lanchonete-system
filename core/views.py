from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Prefetch, Q, Sum
from django.core.validators import MinValueValidator
from django.utils import timezone
from datetime import timedelta
from django.views.decorators.http import require_POST
from django import forms
from django.db import transaction
from django.http import HttpResponseBadRequest, HttpResponseForbidden
from .models import (
    Order,
    OrderItem,
    OrderStatusHistory,
    Membership,
    Product,
    PaymentEvent,
)


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'description', 'price', 'category']

    def __init__(self, *args, business, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category'].queryset = business.category_set.filter(
            Q(is_active=True) | Q(pk=self.instance.category_id)
        )
        self.fields['price'].validators.append(MinValueValidator(0))


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
    ).select_related("category").order_by('name')
    query = request.GET.get('q', '').strip()
    if query:
        products = products.filter(name__icontains=query)
    if request.GET.get('status') == 'active':
        products = products.filter(is_active=True)
    elif request.GET.get('status') == 'inactive':
        products = products.filter(is_active=False)

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

    form = ProductForm(request.POST if request.method == 'POST' else None, business=membership.business)
    if request.method == "POST" and form.is_valid():
        product = form.save(commit=False)
        product.business = membership.business
        product.save()
        return redirect("/produtos/")

    categories = form.fields['category'].queryset

    return render(
        request,
        "core/product_create.html",
        {"categories": categories, "form": form}
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

    form = ProductForm(request.POST if request.method == 'POST' else None, instance=product, business=membership.business)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("/produtos/")

    categories = form.fields['category'].queryset

    return render(
        request,
        "core/product_update.html",
        {
            "product": product,
            "categories": categories,
            "form": form,
        }
    )

@login_required
@require_POST
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

    if request.headers.get('HX-Request') == 'true':
        return product_list(request)
    return redirect("/produtos/")

@login_required
@require_POST
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

    if request.headers.get('HX-Request') == 'true':
        return product_list(request)
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
    ).select_related("customer", "address").prefetch_related(
        Prefetch(
            "orderitem_set",
            queryset=OrderItem.objects.select_related("product")
        ),
        "orderstatushistory_set",
        "payment_events__changed_by",
    )

    new_orders = orders.filter(status="NOVO")

    accepted_orders = orders.filter(status="ACEITO")

    preparing_orders = orders.filter(status="EM_PREPARO")

    ready_orders = orders.filter(status="PRONTO")

    out_for_delivery_orders = orders.filter(
        status="SAIU_PARA_ENTREGA"
    )

    delivered_orders = orders.filter(status="ENTREGUE")
    pending_payments = orders.filter(payment_status=Order.PaymentStatus.PENDING)

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
            "can_manage_payments": membership.role in ('OWNER', 'MANAGER'),
            "pending_payment_count": pending_payments.count(),
            "pending_payment_total": pending_payments.aggregate(total=Sum('total_amount'))['total'] or 0,
        }
    )


@login_required
@require_POST
def payment_update(request, order_id):
    membership = get_object_or_404(Membership, user=request.user, is_active=True)
    status = request.POST.get('status')
    note = request.POST.get('note', '').strip()
    if status not in Order.PaymentStatus.values or len(note) > 500:
        return HttpResponseBadRequest('Informe um status de pagamento válido e observação de até 500 caracteres.')
    if membership.role not in ('OWNER', 'MANAGER', 'STAFF'):
        return HttpResponseForbidden('Sem permissão para registrar pagamentos.')
    if status == Order.PaymentStatus.PENDING:
        if membership.role not in ('OWNER', 'MANAGER'):
            return HttpResponseForbidden('Somente dono ou gerente pode corrigir um recebimento.')
        if not note:
            return HttpResponseBadRequest('Informe o motivo da correção do pagamento.')
    with transaction.atomic():
        order = get_object_or_404(Order.objects.select_for_update(), pk=order_id, business=membership.business)
        if order.payment_status != status:
            order.payment_status = status
            order.paid_at = timezone.now() if status == Order.PaymentStatus.PAID else None
            order.save(update_fields=['payment_status', 'paid_at'])
            PaymentEvent.objects.create(order=order, status=status, amount=order.total_amount,
                                        changed_by=request.user, note=note)
    if request.headers.get('HX-Request') == 'true':
        return home(request)
    return redirect('/')


@login_required
@require_POST
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
@require_POST
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
@require_POST
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
@require_POST
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
@require_POST
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

    pickup_ready = order.order_type == Order.OrderType.PICKUP and order.status == Order.Status.READY
    if order.status != Order.Status.OUT_FOR_DELIVERY and not pickup_ready:
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
        if order.out_for_delivery_at is None or order.out_for_delivery_at < limite:
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

        return render(request, 'core/confirm_delivery.html', {'order': order})

    return render(
        request,
        "core/confirm_delivery.html",
        {"order": order}
    )
