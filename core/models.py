import uuid
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator



class Business(models.Model):
    name = models.CharField(max_length=150)
    phone = models.CharField(max_length=20)
    email = models.EmailField(blank=True)
    pix_key = models.CharField('Chave Pix', max_length=140, blank=True)
    pix_recipient = models.CharField('Nome do recebedor Pix', max_length=150, blank=True)
    delivery_fee = models.DecimalField('Taxa fixa de entrega', max_digits=8, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Lanchonete"
        verbose_name_plural = "Lanchonetes"

    def __str__(self):
        return self.name


class Membership(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    business = models.ForeignKey(Business, on_delete=models.CASCADE)

    class Role(models.TextChoices):
        OWNER = "OWNER", "Dono"
        MANAGER = "MANAGER", "Gerente"
        STAFF = "STAFF", "Funcionário"

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.STAFF,
    )

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.business.name} - {self.get_role_display()}"

    class Meta:
        verbose_name = "Membro"
        verbose_name_plural = "Membros"


class Category(models.Model):
    business = models.ForeignKey(Business, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Categoria"
        verbose_name_plural = "Categorias"

    def __str__(self):
        return self.name


class Product(models.Model):
    business = models.ForeignKey(Business, on_delete=models.CASCADE)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Produto"
        verbose_name_plural = "Produtos"

    def __str__(self):
        return self.name


class Customer(models.Model):
    business = models.ForeignKey(Business, on_delete=models.CASCADE)
    name = models.CharField(max_length=150)
    phone = models.CharField(max_length=20)
    normalized_phone = models.CharField(max_length=20, blank=True, db_index=True, editable=False)
    email = models.EmailField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Cliente"
        verbose_name_plural = "Clientes"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        from .customer_data import normalize_phone
        self.normalized_phone = normalize_phone(self.phone)
        if kwargs.get('update_fields') is not None and 'phone' in kwargs['update_fields']:
            kwargs['update_fields'] = set(kwargs['update_fields']) | {'normalized_phone'}
        super().save(*args, **kwargs)


class Address(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    label = models.CharField(max_length=50)
    street = models.CharField(max_length=150)
    number = models.CharField(max_length=20)
    complement = models.CharField(max_length=100, blank=True)
    neighborhood = models.CharField(max_length=100)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=2)
    zip_code = models.CharField(max_length=9)
    reference = models.CharField(max_length=150, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Endereço"
        verbose_name_plural = "Endereços"


class Order(models.Model):

    class Status(models.TextChoices):
        NEW = "NOVO", "Novo"
        ACCEPTED = "ACEITO", "Aceito"
        PREPARING = "EM_PREPARO", "Em preparo"
        READY = "PRONTO", "Pronto"
        OUT_FOR_DELIVERY = "SAIU_PARA_ENTREGA", "Saiu para entrega"
        DELIVERED = "ENTREGUE", "Entregue"

    confirmation_token = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False
    )

    out_for_delivery_at = models.DateTimeField(
        null=True,
        blank=True
    )

    delivery_confirmed_by = models.CharField(
        max_length=20,
        null=True,
        blank=True
    )
    class OrderType(models.TextChoices):
        DELIVERY = "DELIVERY", "Entrega"
        PICKUP = "PICKUP", "Retirada"

    class PaymentMethod(models.TextChoices):
        PIX = "PIX", "Pix"
        CASH = "DINHEIRO", "Dinheiro"
        CREDIT_CARD = "CARTAO_CREDITO", "Cartão de crédito"
        DEBIT_CARD = "CARTAO_DEBITO", "Cartão de débito"

    class PaymentStatus(models.TextChoices):
        PENDING = 'PENDENTE', 'Pagamento pendente'
        PAID = 'PAGO', 'Pagamento recebido'

    business = models.ForeignKey(Business, on_delete=models.CASCADE)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    address = models.ForeignKey(Address, on_delete=models.SET_NULL, null=True, blank=True)
    checkout_token = models.UUIDField(null=True, blank=True, unique=True, editable=False)
    customer_name = models.CharField(max_length=150, blank=True)
    customer_phone = models.CharField(max_length=20, blank=True)
    address_snapshot = models.JSONField(default=dict, blank=True)
    payment_status = models.CharField(max_length=20, choices=PaymentStatus.choices, default=PaymentStatus.PENDING)
    paid_at = models.DateTimeField(null=True, blank=True)
    cash_change_for = models.DecimalField('Troco para', max_digits=10, decimal_places=2, null=True, blank=True)
    delivery_fee = models.DecimalField('Taxa de entrega do pedido', max_digits=8, decimal_places=2, default=0, validators=[MinValueValidator(0)])

    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.NEW,
    )

    order_type = models.CharField(
        max_length=20,
        choices=OrderType.choices,
    )

    payment_method = models.CharField(
        max_length=20,
        choices=PaymentMethod.choices,
    )

    total_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
    )

    observation = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Pedido"
        verbose_name_plural = "Pedidos"

    def __str__(self):
        return f"Pedido #{self.id} - {self.customer.name}"

    def save(self, *args, **kwargs):
        if self._state.adding and self.customer_id:
            self.customer_name = self.customer_name or self.customer.name
            self.customer_phone = self.customer_phone or self.customer.phone
            if self.address_id and not self.address_snapshot:
                self.address_snapshot = {key: getattr(self.address, key) for key in (
                    'street', 'number', 'neighborhood', 'city', 'state', 'zip_code', 'complement', 'reference'
                )}
        super().save(*args, **kwargs)

    def calculate_total(self):
        total = sum(
            item.get_subtotal()
            for item in self.orderitem_set.all()
        )

        self.total_amount = total + self.delivery_fee
        self.save(update_fields=["total_amount"])

        return self.total_amount


class PaymentEvent(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='payment_events')
    status = models.CharField(max_length=20, choices=Order.PaymentStatus.choices)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    changed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    note = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at', 'pk']
        verbose_name = 'Registro de pagamento'
        verbose_name_plural = 'Registros de pagamento'


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )
    observation = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Item do pedido"
        verbose_name_plural = "Itens do pedido"

    def __str__(self):
        return f"{self.quantity}x {self.product.name}"

    def get_subtotal(self):
        return self.quantity * self.unit_price

    def set_price_from_product(self):
        self.unit_price = self.product.price


class OrderStatusHistory(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    status = models.CharField(
        max_length=30,
        choices=Order.Status.choices
    )
    changed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    observation = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Histórico de status"
        verbose_name_plural = "Histórico de status"

    def __str__(self):
        return f"Pedido #{self.order.id} - {self.status}"


    delivery_confirmed_by = models.CharField(
    max_length=20,
    null=True,
    blank=True
)
