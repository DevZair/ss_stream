from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("inventory", "0013_merge_0011"),
    ]

    operations = [
        migrations.AlterField(
            model_name="stock",
            name="quantity",
            field=models.IntegerField(default=0),
        ),
    ]
