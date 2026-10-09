from decimal import Decimal
from django.contrib.auth.models import User
from django.test import TestCase
from .models import Business, Membership, Category, Product, Customer, Order


class FrontendFlowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('tester', password='test-password')
        self.business = Business.objects.create(name='Teste', phone='')
        Membership.objects.create(user=self.user, business=self.business, role='OWNER')
        self.category = Category.objects.create(business=self.business, name='Lanches')
        self.product = Product.objects.create(business=self.business, category=self.category,
                                              name='X-salada', price=Decimal('18.50'))
        self.customer = Customer.objects.create(business=self.business, name='Cliente', phone='')
        self.client.force_login(self.user)

    def test_pages_and_product_filters(self):
        for path in ['/', '/produtos/', '/produtos/novo/', '/produtos/gerenciar/',
                     f'/produtos/{self.product.pk}/editar/']:
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, 'core/css/app.css')
        response = self.client.get('/produtos/', {'q': 'salada'}, HTTP_HX_REQUEST='true')
        self.assertContains(response, 'X-salada')
        self.assertNotContains(self.client.get('/produtos/', {'q': 'ausente'}), 'X-salada')
        response = self.client.post(f'/produtos/{self.product.pk}/inativar/?status=active',
                                    HTTP_HX_REQUEST='true')
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'X-salada')
        self.product.refresh_from_db()
        self.assertFalse(self.product.is_active)

    def test_product_form_validation_and_save(self):
        data = {'name': 'Novo lanche', 'description': 'Pao e queijo', 'price': '22.90',
                'category': self.category.pk}
        response = self.client.post('/produtos/novo/', data)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Product.objects.filter(name='Novo lanche', price='22.90').exists())
        data['price'] = '-1'
        response = self.client.post('/produtos/novo/', data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'role="alert"')
        other = Business.objects.create(name='Outra', phone='')
        category = Category.objects.create(business=other, name='Outra categoria')
        data.update(price='20.00', category=category.pk)
        self.assertEqual(self.client.post('/produtos/novo/', data).status_code, 200)
        self.assertEqual(Product.objects.filter(name='Novo lanche').count(), 1)

    def test_order_progression_and_get_protection(self):
        order = Order.objects.create(business=self.business, customer=self.customer,
                                     order_type='DELIVERY', payment_method='PIX')
        actions = [('aceitar', 'ACEITO'), ('preparar', 'EM_PREPARO'), ('pronto', 'PRONTO'),
                   ('entrega', 'SAIU_PARA_ENTREGA'), ('entregue', 'ENTREGUE')]
        self.assertEqual(self.client.get(f'/pedido/{order.pk}/aceitar/').status_code, 405)
        for action, status in actions:
            response = self.client.post(f'/pedido/{order.pk}/{action}/', HTTP_HX_REQUEST='true', follow=True)
            self.assertContains(response, 'id="order-board"')
            order.refresh_from_db()
            self.assertEqual(order.status, status)
        self.assertEqual(order.orderstatushistory_set.count(), 5)
        pickup = Order.objects.create(business=self.business, customer=self.customer,
                                      order_type='PICKUP', payment_method='PIX', status='PRONTO')
        self.client.post(f'/pedido/{pickup.pk}/entregue/')
        pickup.refresh_from_db()
        self.assertEqual(pickup.status, 'ENTREGUE')

    def test_login_and_public_confirmation(self):
        order = Order.objects.create(business=self.business, customer=self.customer,
                                     order_type='DELIVERY', payment_method='PIX',
                                     status='SAIU_PARA_ENTREGA')
        from django.utils import timezone
        order.out_for_delivery_at = timezone.now()
        order.save()
        self.client.logout()
        self.assertEqual(self.client.get('/').status_code, 302)
        self.assertContains(self.client.get('/accounts/login/'), 'autocomplete="current-password"')
        response = self.client.post(f'/seu-pedido/confirmar/{order.confirmation_token}/')
        self.assertContains(response, 'Recebimento confirmado')
        order.refresh_from_db()
        self.assertEqual(order.status, 'ENTREGUE')
