# Generated manually on 2026-07-16

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0012_dokon_biznes_import_biznes_import_dokon_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='mahsulot',
            name='artikul',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='mahsulot',
            name='ulgurji_narx',
            field=models.DecimalField(blank=True, decimal_places=2, default=0.00, max_digits=12, null=True),
        ),
    ]
