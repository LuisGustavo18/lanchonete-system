from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from .models import Business, Category, Customer, Order, Product


class StorefrontTests(TestCase):
    def setUp(self):
        self.business = Business.objects.create(name='Lanchonete teste', phone='11999999999', pix_key='loja@example.com', pix_recipient='Loja Teste')
        self.category = Category.objects.create(business=self.business, name='Lanches')
        self.product = Product.objects.create(business=self.business, category=self.category,
                                              name='X-salada', description='Pão e salada', price=Decimal('18.50'))
        self.menu = reverse('menu', args=[self.business.pk])
        self.cart = reverse('cart_update', args=[self.business.pk, self.product.pk])
        self.checkout = reverse('checkout', args=[self.business.pk])

    def add_item(self):
        response = self.client.post(self.cart, {'action': 'add', 'quantity': '2', 'observation': 'Sem cebola'}, HTTP_HX_REQUEST='true')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '37,00')

    def checkout_data(self):
        response = self.client.get(self.checkout)
        self.assertEqual(response.status_code, 200)
        return {'token': response.context['checkout_token'], 'name': 'Cliente teste', 'phone': '11999999999',
                'order_type': 'PICKUP', 'payment_method': 'PIX', 'observation': 'Retiro no balcão'}

    def test_menu_cart_update_and_remove(self):
        response = self.client.get(self.menu)
        self.assertContains(response, 'X-salada')
        self.assertContains(response, '18,50')
        self.add_item()
        response = self.client.post(self.cart, {'action': 'update', 'quantity': 3, 'observation': 'Bem passado'}, HTTP_HX_REQUEST='true')
        self.assertContains(response, '55,50')
        self.assertContains(response, 'Bem passado')
        response = self.client.post(self.cart, {'action': 'remove'}, HTTP_HX_REQUEST='true')
        self.assertContains(response, 'Escolha um produto')
        self.assertEqual(self.client.post(self.cart, {'quantity': '-1'}).status_code, 400)

    def test_pickup_order_and_duplicate_submission(self):
        self.add_item()
        data = self.checkout_data()
        response = self.client.post(self.checkout, data, follow=True)
        self.assertContains(response, 'Pedido recebido')
        order = Order.objects.get()
        self.assertEqual(order.total_amount, Decimal('37.00'))
        self.assertEqual(order.status, 'NOVO')
        self.assertIsNone(order.address)
        self.assertEqual(order.orderitem_set.get().observation, 'Sem cebola')
        self.assertEqual(order.orderitem_set.get().quantity, 2)
        self.assertEqual(order.orderstatushistory_set.count(), 1)
        self.client.post(self.checkout, data)
        self.assertEqual(Order.objects.count(), 1)
        self.assertEqual(Customer.objects.count(), 1)

    def test_delivery_requires_and_saves_address(self):
        self.add_item()
        data = self.checkout_data()
        data['order_type'] = 'DELIVERY'
        response = self.client.post(self.checkout, data)
        self.assertContains(response, 'Preencha este campo para entrega')
        self.assertEqual(Order.objects.count(), 0)
        data.update(street='Rua Central', number='42', neighborhood='Centro', city='São Paulo', state='sp', zip_code='01001-000')
        response = self.client.post(self.checkout, data, follow=True)
        self.assertContains(response, 'Rua Central')
        order = Order.objects.get()
        self.assertEqual(order.address.state, 'SP')
        self.assertEqual(order.address.customer, order.customer)

    def test_unavailable_cross_business_and_price_tampering(self):
        other = Business.objects.create(name='Outra', phone='')
        product = Product.objects.create(business=other, category=Category.objects.create(business=other, name='Outra'), name='Outro', price=10)
        url = reverse('cart_update', args=[self.business.pk, product.pk])
        self.assertEqual(self.client.post(url, {}).status_code, 404)
        self.add_item()
        data = self.checkout_data()
        self.product.is_active = False
        self.product.save()
        self.assertContains(self.client.get(self.menu), 'Indisponível')
        self.client.post(self.checkout, data)
        self.assertFalse(Order.objects.exists())
        self.product.is_active = True
        self.product.save()
        data['total_amount'] = '0.01'
        self.client.post(self.checkout, data)
        self.assertEqual(Order.objects.get().total_amount, Decimal('37.00'))

    def test_empty_cart_and_changed_cart_token(self):
        data = self.checkout_data()
        self.client.post(self.checkout, data)
        self.assertFalse(Order.objects.exists())
        self.add_item()
        self.assertEqual(self.client.post(self.checkout, data).status_code, 400)
