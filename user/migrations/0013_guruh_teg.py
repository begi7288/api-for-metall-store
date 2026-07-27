# Generated manually

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0012_ilova'),
    ]

    operations = [
        migrations.CreateModel(
            name='Guruh',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('yaratilgan_vaqt', models.DateTimeField(auto_now_add=True)),
                ('yangilangan_vaqt', models.DateTimeField(auto_now=True)),
                ('nomi', models.CharField(max_length=255)),
                ('chegirma_foizi', models.CharField(blank=True, default='0', max_length=255, null=True)),
                ('chegirma_qollash', models.CharField(blank=True, max_length=255, null=True)),
                ('holat', models.CharField(default='Faol', max_length=50)),
                ('tavsif', models.TextField(blank=True, null=True)),
                ('biznes', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='mijoz_guruhlari', to='user.biznes')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Teg',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('yaratilgan_vaqt', models.DateTimeField(auto_now_add=True)),
                ('yangilangan_vaqt', models.DateTimeField(auto_now=True)),
                ('nomi', models.CharField(max_length=255)),
                ('tur', models.CharField(default="Qo'lda", max_length=50)),
                ('holat', models.CharField(default='Faol', max_length=50)),
                ('tavsif', models.TextField(blank=True, null=True)),
                ('biznes', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='mijoz_teglari', to='user.biznes')),
            ],
            options={
                'abstract': False,
            },
        ),
    ]
