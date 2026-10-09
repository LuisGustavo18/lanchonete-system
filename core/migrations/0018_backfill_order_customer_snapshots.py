import re
from django.db import migrations


def backfill(apps, schema_editor):
    Customer = apps.get_model('core', 'Customer')
    Order = apps.get_model('core', 'Order')
    database = schema_editor.connection.alias
    for customer in Customer.objects.using(database).all().iterator():
        digits = re.sub(r'\D', '', customer.phone or '')
        if len(digits) in (10, 11):
            digits = '55' + digits
        Customer.objects.using(database).filter(pk=customer.pk).update(normalized_phone=digits)
    for order in Order.objects.using(database).select_related('customer', 'address').all().iterator():
        snapshot = {}
        if order.address:
            snapshot = {key: getattr(order.address, key) for key in (
                'street', 'number', 'neighborhood', 'city', 'state', 'zip_code', 'complement', 'reference'
            )}
        Order.objects.using(database).filter(pk=order.pk).update(
            customer_name=order.customer.name, customer_phone=order.customer.phone,
            address_snapshot=snapshot,
        )


class Migration(migrations.Migration):
    dependencies = [('core', '0017_business_pix_key_business_pix_recipient_and_more')]
    operations = [migrations.RunPython(backfill, migrations.RunPython.noop)]
