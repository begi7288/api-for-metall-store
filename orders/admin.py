from django.contrib import admin
from .models import Taminotchi, SupplierOrder, SupplierOrderItem, SupplierOrderPayment, SupplierOrderReturn, SupplierOrderReturnItem

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
