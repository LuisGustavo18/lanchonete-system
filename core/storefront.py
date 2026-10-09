import uuid
from decimal import Decimal

from django import forms
from django.db import transaction
from django.db.models import Prefetch
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .models import Address, Business, Category, Customer, Order, OrderItem, OrderStatusHistory, Product
from .customer_data import normalize_phone


class CheckoutForm(forms.Form):
    name = forms.CharField(label='Nome', max_length=150)
    phone = forms.RegexField(label='Telefone', regex=r'^\+?[\d\s().-]{8,20}$', max_length=20)
    order_type = forms.ChoiceField(label='Recebimento', choices=Order.OrderType.choices)
    payment_method = forms.ChoiceField(label='Pagamento', choices=Order.PaymentMethod.choices)
    cash_change_for = forms.DecimalField(label='Troco para (R$)', min_value=0, max_digits=10, decimal_places=2, required=False)
    street = forms.CharField(label='Rua', max_length=150, required=False)
    number = forms.CharField(label='Número', max_length=20, required=False)
    neighborhood = forms.CharField(label='Bairro', max_length=100, required=False)
    city = forms.CharField(label='Cidade', max_length=100, required=False)
    state = forms.RegexField(label='UF', regex=r'^[A-Za-z]{2}$', required=False)
    zip_code = forms.RegexField(label='CEP', regex=r'^\d{5}-?\d{3}$', required=False)
    complement = forms.CharField(label='Complemento', max_length=100, required=False)
    reference = forms.CharField(label='Referência', max_length=150, required=False)
    observation = forms.CharField(label='Observações', max_length=1000, required=False, widget=forms.Textarea)

    def __init__(self, *args, business=None, total=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.total = total
        if business is not None and not business.pix_key.strip():
            self.fields['payment_method'].choices = [(value, label) for value, label in Order.PaymentMethod.choices if value != Order.PaymentMethod.PIX]
        for name, field in self.fields.items():
            field.widget.attrs.update({'class': 'field', 'id': f'checkout-{name}'})
        self.fields['phone'].widget.attrs.update({'type': 'tel', 'autocomplete': 'tel'})
        self.fields['name'].widget.attrs['autocomplete'] = 'name'
        self.fields['observation'].widget.attrs['rows'] = 3
        self.fields['cash_change_for'].widget.attrs.update({'type': 'number', 'step': '0.01', 'min': '0', 'placeholder': 'Sem troco, deixe vazio'})

    def clean_name(self):
        return ' '.join(self.cleaned_data['name'].split())

    def clean_phone(self):
        phone = normalize_phone(self.cleaned_data['phone'])
        if len(phone) not in (12, 13) or not phone.startswith('55'):
            raise forms.ValidationError('Informe um telefone brasileiro com DDD (10 ou 11 dígitos).')
        return '+' + phone

    def clean(self):
        data = super().clean()
        if data.get('order_type') == Order.OrderType.DELIVERY:
            for name in ['street', 'number', 'neighborhood', 'city', 'state', 'zip_code']:
                if not data.get(name) and name not in self.errors:
                    self.add_error(name, 'Preencha este campo para entrega.')
        if data.get('state'):
            data['state'] = data['state'].upper()
        if data.get('payment_method') != 'DINHEIRO':
            data['cash_change_for'] = None
        elif data.get('cash_change_for') is not None and self.total is not None and data['cash_change_for'] < self.total:
            self.add_error('cash_change_for', 'O valor para troco deve ser igual ou maior que o total do pedido.')
        return data


def cart_key(business):
    return f'cart_{business.pk}'


def cart_context(request, business):
    cart = request.session.get(cart_key(business), {})
    products = list(Product.objects.filter(pk__in=cart.keys(), business=business).select_related('category'))
    existing = {str(product.pk) for product in products}
    if set(cart) != existing:
        cart = {key: entry for key, entry in cart.items() if key in existing}
        request.session[cart_key(business)] = cart
    items = []
    total = Decimal('0')
    valid = True
    for product in products:
        entry = cart[str(product.pk)]
        available = product.is_active and product.category.is_active and product.category.business_id == business.pk
        subtotal = product.price * entry['quantity']
        items.append({'product': product, **entry, 'subtotal': subtotal, 'available': available})
        total += subtotal
        valid = valid and available
    valid = valid and len(items) == len(cart)
    return {'business': business, 'cart_items': items, 'cart_total': total,
            'cart_count': sum(item['quantity'] for item in items), 'cart_valid': valid}


def menu(request, business_id=None):
    if business_id is None:
        business = Business.objects.filter(is_active=True).order_by('pk').first()
        if business is None:
            return render(request, 'storefront/unavailable.html')
        return redirect('menu', business_id=business.pk)
    business = get_object_or_404(Business, pk=business_id, is_active=True)
    categories = business.category_set.filter(is_active=True).prefetch_related(
        Prefetch('product_set', queryset=Product.objects.filter(business=business).order_by('name'))
    ).order_by('name')
    return render(request, 'storefront/menu.html', {**cart_context(request, business), 'categories': categories})


@require_POST
def cart_update(request, business_id, product_id):
    business = get_object_or_404(Business, pk=business_id, is_active=True)
    product = get_object_or_404(Product, pk=product_id, business=business)
    cart = request.session.get(cart_key(business), {}).copy()
    action = request.POST.get('action', 'add')
    key = str(product.pk)
    if action == 'remove':
        cart.pop(key, None)
    else:
        if not product.is_active or not product.category.is_active or product.category.business_id != business.pk:
            context = cart_context(request, business)
            context['cart_error'] = 'Este produto não está disponível. Remova-o do carrinho para continuar.'
            return render(request, 'storefront/cart.html', context)
        try:
            quantity = int(request.POST.get('quantity', '1'))
        except ValueError:
            return HttpResponseBadRequest('Quantidade inválida.')
        if action not in ['add', 'update'] or not 1 <= quantity <= 99:
            return HttpResponseBadRequest('Informe uma quantidade entre 1 e 99.')
        if action == 'add':
            quantity += cart.get(key, {}).get('quantity', 0)
        if quantity > 99:
            return HttpResponseBadRequest('Limite de 99 unidades por produto.')
        cart[key] = {'quantity': quantity, 'observation': request.POST.get('observation', cart.get(key, {}).get('observation', ''))[:500]}
    request.session[cart_key(business)] = cart
    request.session.pop(f'checkout_{business.pk}', None)
    if request.headers.get('HX-Request') == 'true':
        return render(request, 'storefront/cart.html', cart_context(request, business))
    return redirect('menu', business_id=business.pk)


def checkout(request, business_id):
    business = get_object_or_404(Business, pk=business_id, is_active=True)
    token_key = f'checkout_{business.pk}'
    token = request.session.get(token_key)
    if token is None:
        token = str(uuid.uuid4())
        request.session[token_key] = token
    if request.method == 'POST' and request.POST.get('token') != token:
        return HttpResponseBadRequest('Seu carrinho mudou. Volte ao cardápio e tente novamente.')
    previous = Order.objects.filter(checkout_token=token, business=business).first()
    if previous:
        return redirect('order_receipt', token=previous.confirmation_token)
    context = cart_context(request, business)
    delivery_fee = business.delivery_fee if request.POST.get('order_type') == 'DELIVERY' else Decimal('0')
    order_total = context['cart_total'] + delivery_fee
    form = CheckoutForm(request.POST if request.method == 'POST' else None,
                        business=business, total=order_total,
                        initial={'order_type': 'PICKUP', 'payment_method': 'PIX' if business.pix_key.strip() else 'DINHEIRO'})
    if request.method == 'POST' and form.is_valid():
        with transaction.atomic():
            # Recheck availability and prices inside the transaction.
            list(Product.objects.select_for_update().filter(business=business, pk__in=request.session.get(cart_key(business), {}).keys()))
            context = cart_context(request, business)
            order_total = context['cart_total'] + delivery_fee
            if context['cart_items'] and context['cart_valid']:
                data = form.cleaned_data
                if data.get('cash_change_for') is not None and data['cash_change_for'] < order_total:
                    form.add_error('cash_change_for', 'O valor para troco deve cobrir o total do pedido.')
                    return render(request, 'storefront/checkout.html', {**context, 'form': form, 'checkout_token': token, 'delivery_fee': business.delivery_fee, 'order_total': order_total})
                # Phone groups contacts, but does not verify identity. Do not update an existing profile.
                customer = Customer.objects.filter(business=business, normalized_phone=normalize_phone(data['phone']), name__iexact=data['name'], is_active=True).order_by('pk').first()
                customer_created = customer is None
                if customer_created:
                    customer = Customer.objects.create(business=business, name=data['name'], phone=data['phone'])
                address = None
                address_data = {}
                if data['order_type'] == 'DELIVERY':
                    address_data = {
                        name: data.get(name, '') for name in ['street', 'number', 'neighborhood', 'city', 'state', 'zip_code', 'complement', 'reference']
                    }
                    address = Address.objects.filter(customer=customer, **address_data).order_by('pk').first()
                    if address is None:
                        address = Address.objects.create(customer=customer, label='Entrega', **address_data)
                order, created = Order.objects.get_or_create(checkout_token=token, defaults={
                    'business': business, 'customer': customer, 'address': address,
                    'order_type': data['order_type'], 'payment_method': data['payment_method'],
                    'observation': data['observation'], 'total_amount': order_total, 'delivery_fee': delivery_fee,
                    'customer_name': data['name'], 'customer_phone': data['phone'], 'address_snapshot': address_data,
                    'cash_change_for': data.get('cash_change_for'),
                })
                if created:
                    OrderItem.objects.bulk_create([OrderItem(order=order, product=item['product'], quantity=item['quantity'],
                        unit_price=item['product'].price, observation=item['observation']) for item in context['cart_items']])
                    OrderStatusHistory.objects.create(order=order, status=order.status)
                elif customer_created:
                    customer.delete()
                request.session[cart_key(business)] = {}
                return redirect('order_receipt', token=order.confirmation_token)
        form.add_error(None, 'Seu carrinho está vazio ou contém produtos indisponíveis. Volte ao cardápio para revisar.')
    return render(request, 'storefront/checkout.html', {**context, 'form': form, 'checkout_token': token, 'delivery_fee': business.delivery_fee, 'order_total': order_total})


def order_receipt(request, token):
    order = get_object_or_404(Order.objects.select_related('business', 'address').prefetch_related('orderitem_set__product'), confirmation_token=token)
    return render(request, 'storefront/receipt.html', {'order': order, 'business': order.business})
