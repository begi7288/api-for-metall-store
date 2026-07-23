from django.contrib import admin
from .models import Sale, SaleItem, Xarajat, XarajatKategoriyasi

class SaleItemInline(admin.TabularInline):
    model = SaleItem
    extra = 0

@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ('id', 'kod', 'biznes', 'dokon', 'mijoz', 'tolov_usuli', 'yakuniy_summa', 'holat', 'yaratilgan_vaqt')
    list_filter = ('holat', 'tolov_usuli', 'biznes', 'dokon')
    search_fields = ('kod', 'mijoz__ism', 'mijoz__familiya')
    inlines = [SaleItemInline]

@admin.register(SaleItem)
class SaleItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'sotuv', 'mahsulot', 'miqdori', 'sotish_narxi', 'jami_summa')
    search_fields = ('mahsulot__nomi',)

@admin.register(XarajatKategoriyasi)
class XarajatKategoriyasiAdmin(admin.ModelAdmin):
    list_display = ('id', 'biznes', 'nomi', 'yaratilgan_vaqt')
    search_fields = ('nomi',)

@admin.register(Xarajat)
class XarajatAdmin(admin.ModelAdmin):
    list_display = ('id', 'biznes', 'kategoriya', 'miqdor', 'tolov_turi', 'xodim', 'sana')
    list_filter = ('tolov_turi', 'biznes', 'kategoriya')
    search_fields = ('izoh',)
