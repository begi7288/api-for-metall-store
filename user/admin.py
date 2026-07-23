from django.contrib import admin
from .models import (
    Xodim, Mijoz, Biznes, Tarif, XodimRoli, MijozQarzi, MijozTolovi,
    SodiqlikDasturi, SodiqlikDarajasi, Valyuta, Ilova,
    BildirishnomaSozlamalari, TolovTuriSozlama, MahsulotSozlamalari, ChekSozlamalari
)

@admin.register(Tarif)
class TarifAdmin(admin.ModelAdmin):
    list_display = ('id', 'nomi', 'dokon_limiti', 'mahsulot_limiti', 'xodim_limiti')
    search_fields = ('nomi',)

@admin.register(Biznes)
class BiznesAdmin(admin.ModelAdmin):
    list_display = ('id', 'nomi', 'egasi_ism', 'tarif')
    search_fields = ('nomi', 'egasi_ism')
    list_filter = ('tarif',)

@admin.register(Xodim)
class XodimAdmin(admin.ModelAdmin):
    list_display = ('ism', 'familiya', 'telefon_raqam', 'rol', 'jinsi', 'is_active')
    search_fields = ('ism', 'familiya', 'telefon_raqam')
    list_filter = ('rol', 'jinsi', 'is_active')

@admin.register(Mijoz)
class MijozAdmin(admin.ModelAdmin):
    list_display = ('ism', 'familiya', 'otasining_ismi', 'telefon_raqam_1', 'telefon_raqam_2', 'jinsi')
    search_fields = ('ism', 'familiya', 'telefon_raqam_1', 'telefon_raqam_2')
    list_filter = ('jinsi',)

@admin.register(XodimRoli)
class XodimRoliAdmin(admin.ModelAdmin):
    list_display = ('id', 'nomi', 'role_id', 'biznes', 'yaratilgan_vaqt')
    search_fields = ('nomi', 'role_id')

@admin.register(MijozQarzi)
class MijozQarziAdmin(admin.ModelAdmin):
    list_display = ('id', 'mijoz', 'umumiy_summa', 'tolangan_summa', 'qoldiq_summa', 'holat', 'yaratilgan_vaqt')
    list_filter = ('holat',)
    search_fields = ('mijoz__ism', 'mijoz__familiya')

@admin.register(MijozTolovi)
class MijozToloviAdmin(admin.ModelAdmin):
    list_display = ('id', 'mijoz', 'summa', 'tolov_usuli', 'xodim', 'yaratilgan_vaqt')
    list_filter = ('tolov_usuli',)
    search_fields = ('mijoz__ism', 'mijoz__familiya')

@admin.register(SodiqlikDasturi)
class SodiqlikDasturiAdmin(admin.ModelAdmin):
    list_display = ('id', 'biznes', 'turi', 'is_active', 'yaratilgan_vaqt')

@admin.register(SodiqlikDarajasi)
class SodiqlikDarajasiAdmin(admin.ModelAdmin):
    list_display = ('id', 'biznes', 'nomi', 'xaridlar_summasi', 'chegirma')

@admin.register(Valyuta)
class ValyutaAdmin(admin.ModelAdmin):
    list_display = ('id', 'biznes', 'kod', 'nomi', 'is_asosiy')

@admin.register(Ilova)
class IlovaAdmin(admin.ModelAdmin):
    list_display = ('id', 'biznes', 'kod', 'nomi', 'is_connected')

@admin.register(BildirishnomaSozlamalari)
class BildirishnomaSozlamalariAdmin(admin.ModelAdmin):
    list_display = ('id', 'biznes', 'yaratilgan_vaqt')

@admin.register(TolovTuriSozlama)
class TolovTuriSozlamaAdmin(admin.ModelAdmin):
    list_display = ('id', 'biznes', 'nomi', 'is_active', 'is_asosiy', 'is_custom')

@admin.register(MahsulotSozlamalari)
class MahsulotSozlamalariAdmin(admin.ModelAdmin):
    list_display = ('id', 'biznes', 'auto_generate_barcode', 'min_stock_alert')

@admin.register(ChekSozlamalari)
class ChekSozlamalariAdmin(admin.ModelAdmin):
    list_display = ('id', 'biznes', 'nomi', 'chop_etish_turi')

