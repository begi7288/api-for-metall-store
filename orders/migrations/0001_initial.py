# Generated manually on 2026-07-16

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('user', '0005_mijoz_biznes_alter_mijoz_telefon_raqam_1_alter_mijoz_telefon_raqam_2'),
        ('products', '0013_mahsulot_artikul_mahsulot_ulgurji_narx'),
    ]

    operations = [
        migrations.CreateModel(
            name='YetkazibBeruvchi',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('yaratilgan_vaqt', models.DateTimeField(auto_now_add=True)),
                ('yangilangan_vaqt', models.DateTimeField(auto_now=True)),
                ('nomi', models.CharField(max_length=255)),
                ('telefon_raqam', models.CharField(blank=True, max_length=50, null=True)),
                ('balans', models.DecimalField(decimal_places=2, default=0.00, max_digits=15)),
                ('biznes', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='yetkazib_beruvchilar', to='user.biznes')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='SupplierOrder',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('yaratilgan_vaqt', models.DateTimeField(auto_now_add=True)),
                ('yangilangan_vaqt', models.DateTimeField(auto_now=True)),
                ('nomi', models.CharField(max_length=255)),
                ('holat', models.CharField(choices=[('qoralama', 'Qoralama'), ('rasmiylashtirilgan', 'Rasmiylashtirilgan'), ('qabul_qilingan', 'Qabul qilingan'), ('bekor_qilingan', 'Bekor qilingan')], default='qoralama', max_length=30)),
                ('qabul_qilish_sanasi', models.DateField()),
                ('haqiqiy_qabul_sana', models.DateTimeField(blank=True, null=True)),
                ('umumiy_summa', models.DecimalField(decimal_places=2, default=0.00, max_digits=15)),
                ('sotuv_summasi', models.DecimalField(decimal_places=2, default=0.00, max_digits=15)),
                ('tolangan_summa', models.DecimalField(decimal_places=2, default=0.00, max_digits=15)),
                ('nasiya_summa', models.DecimalField(decimal_places=2, default=0.00, max_digits=15)),
                ('sotuvlar_taraqqiyoti', models.FloatField(default=0.0)),
                ('fayl', models.FileField(blank=True, null=True, upload_to='supplier_orders/')),
                ('biznes', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='xarid_buyurtmalari', to='user.biznes')),
                ('dokon', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='xarid_buyurtmalari', to='products.dokon')),
                ('qabul_qilgan_xodim', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='qabul_qilgan_supplier_buyurtmalar', to='user.xodim')),
                ('yaratgan_xodim', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='yaratgan_supplier_buyurtmalar', to='user.xodim')),
                ('yetkazib_beruvchi', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='xarid_buyurtmalari', to='orders.yetkazibberuvchi')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='SupplierOrderItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('yaratilgan_vaqt', models.DateTimeField(auto_now_add=True)),
                ('yangilangan_vaqt', models.DateTimeField(auto_now=True)),
                ('miqdori', models.PositiveIntegerField()),
                ('kelish_narxi', models.DecimalField(decimal_places=2, max_digits=12)),
                ('ustama', models.DecimalField(decimal_places=2, default=0.00, max_digits=5)),
                ('sotish_narxi', models.DecimalField(decimal_places=2, max_digits=12)),
                ('ulgurji_narx', models.DecimalField(decimal_places=2, default=0.00, max_digits=12)),
                ('mahsulot', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='xarid_elementlari', to='products.mahsulot')),
                ('order', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='elementlar', to='orders.supplierorder')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='SupplierOrderPayment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('yaratilgan_vaqt', models.DateTimeField(auto_now_add=True)),
                ('yangilangan_vaqt', models.DateTimeField(auto_now=True)),
                ('tolangan_summa', models.DecimalField(decimal_places=2, max_digits=15)),
                ('tolov_turi', models.CharField(choices=[('naqd', 'Naqd'), ('karta', 'Karta'), ('balans_postavshika', 'Yetkazib beruvchi balansi'), ('uzcard', 'UzCard'), ('humo', 'HUMO'), ('visa', 'VISA'), ('mastercard', 'Mastercard'), ('unionpay', 'UnionPay'), ('ingenico', 'Ingenico')], max_length=30)),
                ('order', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='to_lovlar', to='orders.supplierorder')),
                ('xodim', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='supplier_tolovlari', to='user.xodim')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='SupplierOrderReturn',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('yaratilgan_vaqt', models.DateTimeField(auto_now_add=True)),
                ('yangilangan_vaqt', models.DateTimeField(auto_now=True)),
                ('holat', models.CharField(choices=[('kutilmoqda', 'Kutilmoqda'), ('yakunlangan', 'Yakunlangan'), ('bekor_qilingan', 'Bekor qilingan')], default='kutilmoqda', max_length=30)),
                ('qaytarish_summasi', models.DecimalField(decimal_places=2, default=0.00, max_digits=15)),
                ('miqdori', models.PositiveIntegerField(default=0)),
                ('biznes', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='xarid_qaytarishlari', to='user.biznes')),
                ('dokon', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='xarid_qaytarishlari', to='products.dokon')),
                ('order', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='qaytarishlar', to='orders.supplierorder')),
                ('yetkazib_beruvchi', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='xarid_qaytarishlari', to='orders.yetkazibberuvchi')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='SupplierOrderReturnItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('yaratilgan_vaqt', models.DateTimeField(auto_now_add=True)),
                ('yangilangan_vaqt', models.DateTimeField(auto_now=True)),
                ('miqdori', models.PositiveIntegerField()),
                ('kelish_narxi', models.DecimalField(decimal_places=2, max_digits=12)),
                ('mahsulot', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='xarid_qaytarish_elementlari', to='products.mahsulot')),
                ('return_obj', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='elementlar', to='orders.supplierorderreturn')),
            ],
            options={
                'abstract': False,
            },
        ),
    ]
