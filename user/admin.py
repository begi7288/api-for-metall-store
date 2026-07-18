from django.contrib import admin
from .models import Xodim, Mijoz, Biznes, Tarif

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

