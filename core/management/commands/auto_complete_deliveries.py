from django.core.management.base import BaseCommand

from core.tasks import auto_complete_deliveries


class Command(BaseCommand):
    help = "Marca automaticamente como entregues os pedidos com mais de 2 horas em rota."

    def handle(self, *args, **options):
        auto_complete_deliveries()

        self.stdout.write(
            self.style.SUCCESS(
                "Verificação de entregas concluída."
            )
        )
