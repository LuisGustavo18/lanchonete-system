from django.test import TestCase
from django.contrib.auth.models import User
from datetime import timedelta
from django.utils import timezone
from .tasks import auto_complete_deliveries

from .models import Business, Customer, Membership, Order, Product, Category

class TestePedido(TestCase):

        def test_pedido_comeca_com_status_novo(self):
            business = Business.objects.create(
                name="Lanchonete Teste",
                phone="15999999999"
            )

            customer = Customer.objects.create(
                business=business,
                name="Cliente Teste",
                phone="15988888888"
            )

            order = Order.objects.create(
                business=business,
                customer=customer,
                order_type=Order.OrderType.PICKUP,
                payment_method=Order.PaymentMethod.PIX
            )


        def test_confirmacao_expirada_nao_entrega_pedido(self):
            business = Business.objects.create(
                name="Lanchonete Teste",
                phone="15999999999"
            )

            customer = Customer.objects.create(
                business=business,
                name="Cliente Teste",
                phone="15988888888"
            )

            order = Order.objects.create(
                business=business,
                customer=customer,
                order_type=Order.OrderType.DELIVERY,
                payment_method=Order.PaymentMethod.PIX,
                status=Order.Status.OUT_FOR_DELIVERY,
                out_for_delivery_at=timezone.now() - timedelta(hours=3)
            )

            response = self.client.post(
                f"/seu-pedido/confirmar/{order.confirmation_token}/"
            )

            self.assertEqual(response.status_code, 200)


            order.refresh_from_db()

            self.assertEqual(
                order.status,
                Order.Status.OUT_FOR_DELIVERY
            )

            self.assertEqual(
                order.status,
                Order.Status.OUT_FOR_DELIVERY    
            )

        def test_usuario_da_mesma_empresa_pode_aceitar_pedido(self):
            business = Business.objects.create(
                name="Lanchonete Teste",
                phone="15999999999"
            )

            user = User.objects.create_user(
                username="usuario_teste",
                password="senha123"
            )

            Membership.objects.create(
                user=user,
                business=business,
                role=Membership.Role.OWNER
            )

            customer = Customer.objects.create(
                business=business,
                name="Cliente Teste",
                phone="15988888888"
            )

            order = Order.objects.create(
                business=business,
                customer=customer,
                order_type=Order.OrderType.PICKUP,
                payment_method=Order.PaymentMethod.PIX
            )

            self.client.force_login(user)

            response = self.client.get(
                f"/pedido/{order.id}/aceitar/"
            )

            self.assertEqual(response.status_code, 302)

            order.refresh_from_db()

            self.assertEqual(
                order.status,
                Order.Status.ACCEPTED
            )


        def test_staff_da_mesma_empresa_pode_aceitar_pedido(self):
            business = Business.objects.create(
                name="Lanchonete Teste",
                phone="15999999999"
            )

            user = User.objects.create_user(
                username="usuario_teste",
                password="senha123"
            )

            Membership.objects.create(
                user=user,
                business=business,
                role=Membership.Role.STAFF
            )

            customer = Customer.objects.create(
                business=business,
                name="Cliente Teste",
                phone="15988888888"
            )

            order = Order.objects.create(
                business=business,
                customer=customer,
                order_type=Order.OrderType.PICKUP,
                payment_method=Order.PaymentMethod.PIX
            )

            self.client.force_login(user)

            response = self.client.get(
                f"/pedido/{order.id}/aceitar/"
            )

            self.assertEqual(response.status_code, 302)

            order.refresh_from_db()

            self.assertEqual(
                order.status,
                Order.Status.ACCEPTED
            )

        def test_usuario_de_outra_empresa_nao_pode_aceitar_pedido(self):
            business_a = Business.objects.create(
                name="Lanchonete A",
                phone="15999999999"
            )

            business_b = Business.objects.create(
                name="Lanchonete B",
                phone="15977777777"
            )

            user_a = User.objects.create_user(
                username="usuario_a",
                password="senha123"
            )

            user_b = User.objects.create_user(
                username="usuario_b",
                password="senha123"
            )

            Membership.objects.create(
                user=user_a,
                business=business_a,
                role=Membership.Role.OWNER
            )

            Membership.objects.create(
                user=user_b,
                business=business_b,
                role=Membership.Role.STAFF
            )

            customer_a = Customer.objects.create(
                business=business_a,
                name="Cliente da Empresa A",
                phone="15966666666"
            )

            order_a = Order.objects.create(
                business=business_a,
                customer=customer_a,
                order_type=Order.OrderType.PICKUP,
                payment_method=Order.PaymentMethod.PIX
            )

            self.client.force_login(user_b)

            response = self.client.get(
                f"/pedido/{order_a.id}/aceitar/"
            )

            self.assertEqual(
                response.status_code,
                404
            )


        def test_usuario_de_outra_empresa_nao_pode_iniciar_preparo(self):
            business_a = Business.objects.create(
                name="Lanchonete A",
                phone="15999999999"
            )

            business_b = Business.objects.create(
                name="Lanchonete B",
                phone="15977777777"
            )

            user_a = User.objects.create_user(
                username="usuario_a",
                password="senha123"
            )

            user_b = User.objects.create_user(
                username="usuario_b",
                password="senha123"
            )

            Membership.objects.create(
                user=user_a,
                business=business_a,
                role=Membership.Role.OWNER
            )

            Membership.objects.create(
                user=user_b,
                business=business_b,
                role=Membership.Role.STAFF
            )

            customer_a = Customer.objects.create(
                business=business_a,
                name="Cliente da Empresa A",
                phone="15966666666"
            )

            order_a = Order.objects.create(
                business=business_a,
                customer=customer_a,
                order_type=Order.OrderType.PICKUP,
                payment_method=Order.PaymentMethod.PIX,
                status=Order.Status.ACCEPTED
            )

            self.client.force_login(user_b)

            response = self.client.get(
                f"/pedido/{order_a.id}/preparar/"
            )

            self.assertEqual(
                response.status_code,
                404
            )


        def test_pedido_entregue_nao_pode_ser_confirmado_novamente(self):
            business = Business.objects.create(
                name="Lanchonete Teste",
                phone="15999999999"
            )

            customer = Customer.objects.create(
                business=business,
                name="Cliente Teste",
                phone="15988888888"
            )

            order = Order.objects.create(
                business=business,
                customer=customer,
                order_type=Order.OrderType.DELIVERY,
                payment_method=Order.PaymentMethod.PIX,
                status=Order.Status.DELIVERED,
                delivery_confirmed_by="CLIENTE"
            )

            response = self.client.post(
                f"/seu-pedido/confirmar/{order.confirmation_token}/"
            )

            self.assertEqual(response.status_code, 302)


            order.refresh_from_db()

            self.assertEqual(
                order.status,
                Order.Status.DELIVERED
            )


        def test_usuario_da_mesma_empresa_pode_iniciar_preparo(self):
            business = Business.objects.create(
                name="Lanchonete Teste",
                phone="15999999999"
            )

            user = User.objects.create_user(
                username="usuario_teste",
                password="senha123"
            )

            Membership.objects.create(
                user=user,
                business=business,
                role=Membership.Role.OWNER
            )

            customer = Customer.objects.create(
                business=business,
                name="Cliente Teste",
                phone="15988888888"
            )

            order = Order.objects.create(
                business=business,
                customer=customer,
                order_type=Order.OrderType.PICKUP,
                payment_method=Order.PaymentMethod.PIX,
                status=Order.Status.ACCEPTED
            )

            self.client.force_login(user)

            response = self.client.get(
                f"/pedido/{order.id}/preparar/"
            )

            self.assertEqual(response.status_code, 302)

            order.refresh_from_db()

            self.assertEqual(
                order.status,
                Order.Status.PREPARING
            )


        def test_staff_da_mesma_empresa_pode_iniciar_preparo(self):
            business = Business.objects.create(
                name="Lanchonete Teste",
                phone="15999999999"
            )

            user = User.objects.create_user(
                username="usuario_teste",
                password="senha123"
            )

            Membership.objects.create(
                user=user,
                business=business,
                role=Membership.Role.STAFF
            )

            customer = Customer.objects.create(
                business=business,
                name="Cliente Teste",
                phone="15988888888"
            )

            order = Order.objects.create(
                business=business,
                customer=customer,
                order_type=Order.OrderType.PICKUP,
                payment_method=Order.PaymentMethod.PIX,
                status=Order.Status.ACCEPTED
            )

            self.client.force_login(user)

            response = self.client.get(
                f"/pedido/{order.id}/preparar/"
            )

            self.assertEqual(response.status_code, 302)

            order.refresh_from_db()

            self.assertEqual(
                order.status,
                Order.Status.PREPARING
            )

        def test_usuario_da_mesma_empresa_pode_marcar_pedido_como_pronto(self):
            business = Business.objects.create(
                name="Lanchonete Teste",
                phone="15999999999"
            )

            user = User.objects.create_user(
                username="usuario_teste",
                password="senha123"
            )

            Membership.objects.create(
                user=user,
                business=business,
                role=Membership.Role.OWNER
            )

            customer = Customer.objects.create(
                business=business,
                name="Cliente Teste",
                phone="15988888888"
            )

            order = Order.objects.create(
                business=business,
                customer=customer,
                order_type=Order.OrderType.PICKUP,
                payment_method=Order.PaymentMethod.PIX,
                status=Order.Status.PREPARING
            )

            self.client.force_login(user)

            response = self.client.get(
                f"/pedido/{order.id}/pronto/"
            )

            self.assertEqual(response.status_code, 302)

            order.refresh_from_db()

            self.assertEqual(
                order.status,
                Order.Status.READY
            )


        def test_staff_da_mesma_empresa_pode_marcar_pedido_como_pronto(self):
            business = Business.objects.create(
                name="Lanchonete Teste",
                phone="15999999999"
            )

            user = User.objects.create_user(
                username="usuario_teste",
                password="senha123"
            )

            Membership.objects.create(
                user=user,
                business=business,
                role=Membership.Role.STAFF
            )

            customer = Customer.objects.create(
                business=business,
                name="Cliente Teste",
                phone="15988888888"
            )

            order = Order.objects.create(
                business=business,
                customer=customer,
                order_type=Order.OrderType.PICKUP,
                payment_method=Order.PaymentMethod.PIX,
                status=Order.Status.PREPARING
            )

            self.client.force_login(user)

            response = self.client.get(
                f"/pedido/{order.id}/pronto/"
            )

            self.assertEqual(response.status_code, 302)

            order.refresh_from_db()

            self.assertEqual(
                order.status,
                Order.Status.READY
            )


        def test_usuario_da_mesma_empresa_pode_colocar_pedido_em_entrega(self):
            business = Business.objects.create(
                name="Lanchonete Teste",
                phone="15999999999"
            )

            user = User.objects.create_user(
                username="usuario_teste",
                password="senha123"
            )

            Membership.objects.create(
                user=user,
                business=business,
                role=Membership.Role.OWNER
            )

            customer = Customer.objects.create(
                business=business,
                name="Cliente Teste",
                phone="15988888888"
            )

            order = Order.objects.create(
                business=business,
                customer=customer,
                order_type=Order.OrderType.DELIVERY,
                payment_method=Order.PaymentMethod.PIX,
                status=Order.Status.READY
            )

            self.client.force_login(user)

            response = self.client.get(
                f"/pedido/{order.id}/entrega/"
            )

            self.assertEqual(response.status_code, 302)

            order.refresh_from_db()

            self.assertEqual(
                order.status,
                Order.Status.OUT_FOR_DELIVERY
            )

            self.assertIsNotNone(
                order.out_for_delivery_at
            )


        def test_usuario_da_mesma_empresa_pode_marcar_pedido_como_entregue(self):
            business = Business.objects.create(
                name="Lanchonete Teste",
                phone="15999999999"
            )

            user = User.objects.create_user(
                username="usuario_teste",
                password="senha123"
            )

            Membership.objects.create(
                user=user,
                business=business,
                role=Membership.Role.OWNER
            )

            customer = Customer.objects.create(
                business=business,
                name="Cliente Teste",
                phone="15988888888"
            )

            order = Order.objects.create(
                business=business,
                customer=customer,
                order_type=Order.OrderType.DELIVERY,
                payment_method=Order.PaymentMethod.PIX,
                status=Order.Status.OUT_FOR_DELIVERY
            )

            self.client.force_login(user)

            response = self.client.get(
                f"/pedido/{order.id}/entregue/"
            )

            self.assertEqual(response.status_code, 302)

            order.refresh_from_db()

            self.assertEqual(
                order.status,
                Order.Status.DELIVERED
            )


        def test_staff_da_mesma_empresa_pode_marcar_pedido_como_entregue(self):
            business = Business.objects.create(
                name="Lanchonete Teste",
                phone="15999999999"
            )

            user = User.objects.create_user(
                username="usuario_teste",
                password="senha123"
            )

            Membership.objects.create(
                user=user,
                business=business,
                role=Membership.Role.STAFF
            )

            customer = Customer.objects.create(
                business=business,
                name="Cliente Teste",
                phone="15988888888"
            )

            order = Order.objects.create(
                business=business,
                customer=customer,
                order_type=Order.OrderType.DELIVERY,
                payment_method=Order.PaymentMethod.PIX,
                status=Order.Status.OUT_FOR_DELIVERY
            )

            self.client.force_login(user)

            response = self.client.get(
                f"/pedido/{order.id}/entregue/"
            )

            self.assertEqual(response.status_code, 302)

            order.refresh_from_db()

            self.assertEqual(
                order.status,
                Order.Status.DELIVERED
            )

        def test_entrega_e_concluida_automaticamente_apos_2_horas(self):
            business = Business.objects.create(
                name="Lanchonete Teste",
                phone="15999999999"
            )

            customer = Customer.objects.create(
                business=business,
                name="Cliente Teste",
                phone="15988888888"
            )

            order = Order.objects.create(
                business=business,
                customer=customer,
                order_type=Order.OrderType.DELIVERY,
                payment_method=Order.PaymentMethod.PIX,
                status=Order.Status.OUT_FOR_DELIVERY,
                out_for_delivery_at=timezone.now() - timedelta(hours=3)
            )

            auto_complete_deliveries()

            order.refresh_from_db()

            self.assertEqual(
                order.status,
                Order.Status.DELIVERED
            )

            self.assertEqual(
                order.delivery_confirmed_by,
                "AUTOMATICO"
            )

            historico = order.orderstatushistory_set.filter(
            status=Order.Status.DELIVERED
            )

            self.assertEqual(
                historico.count(),
                1  
            )

        def test_entrega_nao_e_concluida_antes_de_2_horas(self):
            business = Business.objects.create(
                name="Lanchonete Teste",
                phone="15999999999"
            )

            customer = Customer.objects.create(
                business=business,
                name="Cliente Teste",
                phone="15988888888"
            )

            order = Order.objects.create(
                business=business,
                customer=customer,
                order_type=Order.OrderType.DELIVERY,
                payment_method=Order.PaymentMethod.PIX,
                status=Order.Status.OUT_FOR_DELIVERY,
                out_for_delivery_at=timezone.now() - timedelta(hours=1)
            )

            auto_complete_deliveries()

            order.refresh_from_db()

            self.assertEqual(
            order.status,
            Order.Status.OUT_FOR_DELIVERY
            )

        def test_staff_nao_pode_criar_produto(self):
            user = User.objects.create_user(
                username="staff",
                password="123456"
            )

            business = Business.objects.create(
                name="Lanchonete Teste",
                phone="15999999999"
            )

            Membership.objects.create(
                user=user,
                business=business,
                role="STAFF",
                is_active=True
            )


            self.client.login(
                username="staff",
                password="123456"
            )

            response = self.client.get("/produtos/novo/")


            self.assertEqual(
                response.status_code,
                302
            )

        def test_owner_pode_acessar_criacao_de_produto(self):
            user = User.objects.create_user(
            username="owner",
            password="123456"   
            )

            business = Business.objects.create(
            name="Lanchonete Teste",
            phone="15999999999"
            )

            Membership.objects.create(
            user=user,
            business=business,
            role="OWNER",
            is_active=True
            )


            self.client.login(
            username="owner",
            password="123456"
            )    

            response = self.client.get("/produtos/novo/")

            self.assertEqual(
            response.status_code,
            200
            )


        def test_manager_pode_acessar_criacao_de_produto(self):
            user = User.objects.create_user(
                username="manager",
                password="123456"
            )

            business = Business.objects.create(
                name="Lanchonete Teste",
                phone="15999999999"
            )

            Membership.objects.create(
                user=user,
                business=business,
                role="MANAGER",
                is_active=True
            )    

            self.client.login(
                username="manager",
                password="123456"
            )


            response = self.client.get("/produtos/novo/")


            self.assertEqual(response.status_code, 200)


        def test_usuario_nao_pode_acessar_produto_de_outra_empresa(self):
            business_a = Business.objects.create(
                    name="Lanchonete A",
                    phone="15999999999"
            )

            business_b = Business.objects.create(
                    name="Lanchonete B",
                    phone="15977777777"
            )


            user_b = User.objects.create_user(
                    username="usuario_b",
                    password="senha123"
            )


            Membership.objects.create(
                    user=user_b,
                    business=business_b,
                    role="OWNER",
                    is_active=True
            )

            category = Category.objects.create(
                business=business_a,
                name="Lanches"
            )


            product = Product.objects.create(
                business=business_a,
                category=category,
                name="Lanche da Empresa A",
                price=20
            )


            self.client.force_login(user_b)

            response = self.client.get(
                     f"/produtos/{product.id}/editar/"
            )


            self.assertEqual(response.status_code, 404)