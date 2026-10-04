import uuid
from django.db import models
from django.contrib.auth.models import User



class Business(models.Model):
    name = models.CharField(max_length=150)
    phone = models.CharField(max_length=20)
    email = models.EmailField(blank=True)
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

class Table(models.Model):
    business = models.ForeignKey(
        Business,
        on_delete=models.CASCADE,
        related_name="tables",
    )
    number = models.CharField(max_length=20)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Mesa"
        verbose_name_plural = "Mesas"
        constraints = [
            models.UniqueConstraint(
                fields=["business", "number"],
                name="unique_table_number_per_business",
            ),
        ]

    def __str__(self):
        return f"Mesa {self.number}"


class Comanda(models.Model):

    class Status(models.TextChoices):
        OPEN = "ABERTA", "Aberta"
        CLOSED = "FECHADA", "Fechada"

    business = models.ForeignKey(
        Business,
        on_delete=models.CASCADE,
        related_name="comandas",
    )

    table = models.ForeignKey(
        Table,
        on_delete=models.PROTECT,
        related_name="comandas",
    )

    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.OPEN,
    )

    opened_at = models.DateTimeField(auto_now_add=True)
    closed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = "Comanda"
        verbose_name_plural = "Comandas"

    def __str__(self):
        return f"Comanda #{self.id} - Mesa {self.table.number}"

class Customer(models.Model):
    business = models.ForeignKey(Business, on_delete=models.CASCADE)
    name = models.CharField(max_length=150)
    phone = models.CharField(max_length=20)
    email = models.EmailField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Cliente"
        verbose_name_plural = "Clientes"

    def __str__(self):
        return self.name


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
        TABLE = "MESA", "Mesa"

    class PaymentMethod(models.TextChoices):
        PENDING = "PENDENTE", "Pendente"
        PIX = "PIX", "Pix"
        CASH = "DINHEIRO", "Dinheiro"
        CREDIT_CARD = "CARTAO_CREDITO", "Cartão de crédito"
        DEBIT_CARD = "CARTAO_DEBITO", "Cartão de débito"



    business = models.ForeignKey(Business, on_delete=models.CASCADE)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)

    comanda = models.ForeignKey(
    Comanda,
    on_delete=models.PROTECT,
    related_name="orders",
    null=True,
    blank=True,
)

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

    def calculate_total(self):
        total = sum(
            item.get_subtotal()
            for item in self.orderitem_set.all()
        )

        self.total_amount = total
        self.save(update_fields=["total_amount"])

        return total


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

    