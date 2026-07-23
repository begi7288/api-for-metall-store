from django.contrib import admin
from .models import SupplierOrder, SupplierOrderItem, SupplierOrderPayment, SupplierOrderReturn, SupplierOrderReturnItem

class SupplierOrderItemInline(admin.TabularInline):
    model = SupplierOrderItem
    extra = 0

class SupplierOrderPaymentInline(admin.TabularInline):
    model = SupplierOrderPayment
    extra = 0

@admin.register(SupplierOrder)
class SupplierOrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'nomi', 'taminotchi', 'dokon', 'holat', 'umumiy_summa', 'tolangan_summa', 'nasiya_summa')
    list_filter = ('holat', 'biznes', 'dokon')
    search_fields = ('nomi', 'taminotchi__nomi')
    inlines = [SupplierOrderItemInline, SupplierOrderPaymentInline]

@admin.register(SupplierOrderReturn)
class SupplierOrderReturnAdmin(admin.ModelAdmin):
    list_display = ('id', 'order', 'dokon', 'taminotchi', 'holat', 'qaytarish_summasi')
    list_filter = ('holat', 'biznes')

@admin.register(SupplierOrderItem)
class SupplierOrderItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'order', 'mahsulot', 'miqdori', 'kelish_narxi', 'sotish_narxi')
    search_fields = ('mahsulot__nomi',)

@admin.register(SupplierOrderPayment)
class SupplierOrderPaymentAdmin(admin.ModelAdmin):
    list_display = ('id', 'order', 'tolangan_summa', 'tolov_turi', 'xodim')
    list_filter = ('tolov_turi',)

@admin.register(SupplierOrderReturnItem)
class SupplierOrderReturnItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'return_obj', 'mahsulot', 'miqdori', 'kelish_narxi')
    search_fields = ('mahsulot__nomi',)
