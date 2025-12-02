from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("inventory", "0004_extend_access_sections"),
    ]

    operations = [
        migrations.AddField(
            model_name="sale",
            name="payment_details",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AlterField(
            model_name="sale",
            name="payment_method",
            field=models.CharField(choices=[("kaspi", "Kaspi"), ("halyk", "Halyk"), ("cash", "Наличные"), ("mixed", "Смешанная")], max_length=10),
        ),
    ]
