# Generated manually on 2026-07-16

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0004_biznes_tarif_xodim_biznes_biznes_tarif'),
    ]

    operations = [
        migrations.AddField(
            model_name='mijoz',
            name='biznes',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='mijozlar', to='user.biznes'),
        ),
        migrations.AlterField(
            model_name='mijoz',
            name='telefon_raqam_1',
            field=models.CharField(max_length=13),
        ),
        migrations.AlterField(
            model_name='mijoz',
            name='telefon_raqam_2',
            field=models.CharField(max_length=13),
        ),
    ]
