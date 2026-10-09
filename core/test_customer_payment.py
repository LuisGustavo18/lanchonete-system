from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import Address, Business, Category, Customer, Membership, Order, PaymentEvent, Product


class CustomerPaymentTests(TestCase):
    def setUp(self):
        self.business = Business.objects.create(
            name='Loja de teste', phone='11999991234',
            pix_key='pix@example.com', pix_recipient='Loja de teste',
        )
        self.product = self.make_product(self.business)
        self.staff = self.make_member('funcionario', Membership.Role.STAFF)
        self.manager = self.make_member('gerente', Membership.Role.MANAGER)

    def make_product(self, business):
        category = Category.objects.create(business=business, name='Lanches')
        return Product.objects.create(
            business=business, category=category, name='Lanche de teste', price=Decimal('18.50'),
        )

    def make_member(self, username, role, business=None):
        user = User.objects.create_user(username)
        Membership.objects.create(user=user, business=business or self.business, role=role)
        return user

    def checkout_data(self, *, product=None, **overrides):
        product = product or self.product
        business = product.business
        response = self.client.post(
            reverse('cart_update', args=[business.pk, product.pk]),
            {'action': 'add', 'quantity': '1'},
        )
        self.assertEqual(response.status_code, 302)
        response = self.client.get(reverse('checkout', args=[business.pk]))
        self.assertEqual(response.status_code, 200)
        data = {
            'token': response.context['checkout_token'], 'name': 'Ana Cliente',
            'phone': '(11) 99999-1234', 'order_type': Order.OrderType.PICKUP,
            'payment_method': Order.PaymentMethod.CASH,
        }
        data.update(overrides)
        return data

    def place_order(self, *, product=None, **overrides):
        product = product or self.product
        data = self.checkout_data(product=product, **overrides)
        response = self.client.post(reverse('checkout', args=[product.business_id]), data)
        self.assertEqual(response.status_code, 302)
        return Order.objects.get(checkout_token=data['token'])

    def delivery_data(self):
        return {
            'order_type': Order.OrderType.DELIVERY, 'street': 'Rua Original',
            'number': '42', 'neighborhood': 'Centro', 'city': 'Sao Paulo',
            'state': 'sp', 'zip_code': '01001-000', 'complement': 'Casa A',
            'reference': 'Portao cinza',
        }

    def payment_url(self, order):
        return reverse('payment_update', args=[order.pk])

    def test_matching_customer_and_address_are_reused_with_normalized_phone(self):
        first = self.place_order(**self.delivery_data())
        second = self.place_order(
            name='  ana   cliente  ', phone='+55 (11) 99999-1234', **self.delivery_data(),
        )
        self.assertEqual(first.customer_id, second.customer_id)
        self.assertEqual(first.address_id, second.address_id)
        self.assertEqual(Customer.objects.count(), 1)
        self.assertEqual(Address.objects.count(), 1)
        self.assertEqual(first.customer.normalized_phone, '5511999991234')
        self.assertEqual(second.customer_name, 'ana cliente')
        self.assertEqual(second.customer_phone, '+5511999991234')

    def test_shared_phone_does_not_merge_different_names_or_businesses(self):
        first = self.place_order()
        different_name = self.place_order(name='Bruno Cliente')
        other = Business.objects.create(name='Outra loja', phone='')
        other_product = self.make_product(other)
        other_order = self.place_order(product=other_product)
        self.assertEqual(Customer.objects.count(), 3)
        self.assertNotEqual(first.customer_id, different_name.customer_id)
        self.assertNotEqual(first.customer_id, other_order.customer_id)
        self.assertEqual(other_order.customer.business_id, other.pk)

    def test_historical_customer_and_address_survive_profile_edits(self):
        order = self.place_order(**self.delivery_data())
        original_address = order.address_snapshot.copy()
        order.customer.name = 'Nome alterado'
        order.customer.phone = '21988887777'
        order.customer.save()
        order.address.street = 'Rua alterada'
        order.address.number = '99'
        order.address.save()
        order.refresh_from_db()
        self.assertEqual(order.customer_name, 'Ana Cliente')
        self.assertEqual(order.customer_phone, '+5511999991234')
        self.assertEqual(order.address_snapshot, original_address)
        receipt = self.client.get(reverse('order_receipt', args=[order.confirmation_token]))
        self.assertContains(receipt, 'Rua Original')
        self.assertNotContains(receipt, 'Rua alterada')
        self.client.force_login(self.staff)
        board = self.client.get('/')
        self.assertContains(board, 'Ana Cliente')
        self.assertContains(board, 'Rua Original')
        self.assertNotContains(board, 'Nome alterado')
        self.assertNotContains(board, 'Rua alterada')

    def test_phone_query_cannot_reveal_an_existing_customer(self):
        self.place_order(name='Nome privado', **self.delivery_data())
        data = self.checkout_data()
        response = self.client.get(
            reverse('checkout', args=[self.business.pk]),
            {'phone': data['phone'], 'customer_phone': data['phone']},
        )
        for field in ('name', 'phone', 'street', 'number', 'complement', 'reference'):
            self.assertIsNone(response.context['form'][field].value())
        self.assertNotContains(response, 'Nome privado')
        self.assertNotContains(response, 'Rua Original')
        self.assertNotContains(response, 'Portao cinza')

    def test_cash_change_cannot_be_less_than_the_total(self):
        data = self.checkout_data(cash_change_for='18.49')
        response = self.client.post(reverse('checkout', args=[self.business.pk]), data)
        self.assertEqual(response.status_code, 200)
        self.assertIn('cash_change_for', response.context['form'].errors)
        self.assertFalse(Order.objects.exists())
        self.assertFalse(Customer.objects.exists())
        data['cash_change_for'] = '20.00'
        self.assertEqual(self.client.post(reverse('checkout', args=[self.business.pk]), data).status_code, 302)
        self.assertEqual(Order.objects.get().cash_change_for, Decimal('20.00'))

    def test_non_cash_orders_discard_change_requests(self):
        for method in (Order.PaymentMethod.PIX, Order.PaymentMethod.CREDIT_CARD, Order.PaymentMethod.DEBIT_CARD):
            with self.subTest(method=method):
                order = self.place_order(payment_method=method, cash_change_for='0.01')
                self.assertIsNone(order.cash_change_for)
                self.assertEqual(order.payment_method, method)

    def test_pix_requires_a_configured_business_key(self):
        self.business.pix_key = '   '
        self.business.save(update_fields=['pix_key'])
        data = self.checkout_data(payment_method=Order.PaymentMethod.PIX)
        response = self.client.get(reverse('checkout', args=[self.business.pk]))
        self.assertNotIn(Order.PaymentMethod.PIX, dict(response.context['form'].fields['payment_method'].choices))
        self.assertNotContains(response, 'value="PIX"')
        response = self.client.post(reverse('checkout', args=[self.business.pk]), data)
        self.assertIn('payment_method', response.context['form'].errors)
        self.assertFalse(Order.objects.exists())

    def test_delivery_fee_is_in_total_and_change_validation_and_is_snapshotted(self):
        self.business.delivery_fee = Decimal('5.00')
        self.business.save(update_fields=['delivery_fee'])
        data = self.checkout_data(cash_change_for='23.49', **self.delivery_data())
        response = self.client.post(reverse('checkout', args=[self.business.pk]), data)
        self.assertEqual(response.status_code, 200)
        self.assertIn('cash_change_for', response.context['form'].errors)
        self.assertFalse(Order.objects.exists())
        data['cash_change_for'] = '25.00'
        self.assertEqual(self.client.post(reverse('checkout', args=[self.business.pk]), data).status_code, 302)
        order = Order.objects.get()
        self.assertEqual(order.delivery_fee, Decimal('5.00'))
        self.assertEqual(order.total_amount, Decimal('23.50'))
        self.assertEqual(order.orderitem_set.get().get_subtotal(), Decimal('18.50'))
        self.business.delivery_fee = Decimal('9.00')
        self.business.save(update_fields=['delivery_fee'])
        order.refresh_from_db()
        self.assertEqual(order.delivery_fee, Decimal('5.00'))
        self.assertEqual(order.total_amount, Decimal('23.50'))
        pickup = self.place_order()
        self.assertEqual(pickup.delivery_fee, Decimal('0.00'))
        self.assertEqual(pickup.total_amount, Decimal('18.50'))

    def test_public_checkout_cannot_mark_paid_and_delivery_does_not_confirm_payment(self):
        order = self.place_order(payment_status=Order.PaymentStatus.PAID, paid_at='2026-01-01')
        self.assertEqual(order.payment_status, Order.PaymentStatus.PENDING)
        self.assertIsNone(order.paid_at)
        self.assertEqual(order.payment_events.count(), 0)
        order.status = Order.Status.READY
        order.save(update_fields=['status'])
        self.client.force_login(self.staff)
        self.assertEqual(self.client.post(f'/pedido/{order.pk}/entregue/').status_code, 302)
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.DELIVERED)
        self.assertEqual(order.payment_status, Order.PaymentStatus.PENDING)
        self.assertIsNone(order.paid_at)
        self.assertEqual(order.payment_events.count(), 0)

    def test_staff_payment_is_audited_and_repeat_submission_is_idempotent(self):
        order = self.place_order()
        self.client.force_login(self.staff)
        data = {'status': Order.PaymentStatus.PAID, 'note': 'Recebido no balcao'}
        self.assertEqual(self.client.post(self.payment_url(order), data).status_code, 302)
        order.refresh_from_db()
        paid_at = order.paid_at
        self.assertEqual(order.payment_status, Order.PaymentStatus.PAID)
        self.assertIsNotNone(paid_at)
        self.assertEqual(order.status, Order.Status.NEW)
        event = order.payment_events.get()
        self.assertEqual(event.changed_by, self.staff)
        self.assertEqual(event.amount, Decimal('18.50'))
        self.assertEqual(event.status, Order.PaymentStatus.PAID)
        self.assertEqual(event.note, 'Recebido no balcao')
        self.assertEqual(self.client.post(self.payment_url(order), data).status_code, 302)
        order.refresh_from_db()
        self.assertEqual(order.payment_events.count(), 1)
        self.assertEqual(order.paid_at, paid_at)

    def test_payment_changes_require_authenticated_post(self):
        order = self.place_order()
        response = self.client.post(self.payment_url(order), {'status': Order.PaymentStatus.PAID})
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get(self.payment_url(order)).status_code, 405)
        order.refresh_from_db()
        self.assertEqual(order.payment_status, Order.PaymentStatus.PENDING)
        self.assertFalse(PaymentEvent.objects.exists())

    def test_payment_changes_are_scoped_to_the_staff_business(self):
        order = self.place_order()
        other = Business.objects.create(name='Outra loja', phone='')
        other_staff = self.make_member('outra-equipe', Membership.Role.STAFF, business=other)
        self.client.force_login(other_staff)
        response = self.client.post(self.payment_url(order), {'status': Order.PaymentStatus.PAID})
        self.assertEqual(response.status_code, 404)
        order.refresh_from_db()
        self.assertEqual(order.payment_status, Order.PaymentStatus.PENDING)
        self.assertFalse(PaymentEvent.objects.exists())

    def test_staff_cannot_reverse_payment_and_manager_must_record_reason(self):
        order = self.place_order()
        self.client.force_login(self.staff)
        self.client.post(self.payment_url(order), {'status': Order.PaymentStatus.PAID})
        response = self.client.post(
            self.payment_url(order), {'status': Order.PaymentStatus.PENDING, 'note': 'Erro no recebimento'},
        )
        self.assertEqual(response.status_code, 403)
        order.refresh_from_db()
        self.assertEqual(order.payment_status, Order.PaymentStatus.PAID)
        self.assertEqual(order.payment_events.count(), 1)
        self.client.force_login(self.manager)
        response = self.client.post(self.payment_url(order), {'status': Order.PaymentStatus.PENDING, 'note': '   '})
        self.assertEqual(response.status_code, 400)
        order.refresh_from_db()
        self.assertEqual(order.payment_status, Order.PaymentStatus.PAID)
        self.assertEqual(order.payment_events.count(), 1)
        response = self.client.post(
            self.payment_url(order), {'status': Order.PaymentStatus.PENDING, 'note': 'Recebimento registrado por engano'},
        )
        self.assertEqual(response.status_code, 302)
        order.refresh_from_db()
        self.assertEqual(order.payment_status, Order.PaymentStatus.PENDING)
        self.assertIsNone(order.paid_at)
        events = list(order.payment_events.all())
        self.assertEqual([event.status for event in events], [Order.PaymentStatus.PAID, Order.PaymentStatus.PENDING])
        self.assertEqual(events[-1].changed_by, self.manager)
        self.assertEqual(events[-1].note, 'Recebimento registrado por engano')
        self.assertEqual(events[-1].amount, order.total_amount)
