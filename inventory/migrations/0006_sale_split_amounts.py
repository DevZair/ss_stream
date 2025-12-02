from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("inventory", "0005_sale_payment_mixed"),
    ]

    operations = [
        migrations.AddField(
            model_name="sale",
            name="cash_amount",
            field=models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=12),
        ),
        migrations.AddField(
            model_name="sale",
            name="halyk_amount",
            field=models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=12),
        ),
        migrations.AddField(
            model_name="sale",
            name="kaspi_amount",
            field=models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=12),
        ),
    ]
