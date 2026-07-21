from django.contrib import admin
from .models import Mahsulot, Import, Dokon, Transfer, Characteristic, MahsulotRasm, MahsulotShtrixKod, Taminotchi, WriteOff, WriteOffItem

@admin.register(Characteristic)
class CharacteristicAdmin(admin.ModelAdmin):
    list_display = ('name', 'value', 'yaratilgan_vaqt')
    search_fields = ('name', 'value')

class MahsulotRasmInline(admin.TabularInline):
    model = MahsulotRasm
    extra = 1
    max_num = 5

class MahsulotShtrixKodInline(admin.TabularInline):
    model = MahsulotShtrixKod
    extra = 1

class CharacteristicInline(admin.TabularInline):
    model = Characteristic
    extra = 1

@admin.register(Mahsulot)
class MahsulotAdmin(admin.ModelAdmin):
    list_display = ('nomi', 'shtrix_kod', 'olchov_birligi', 'kelish_narxi', 'sotish_narxi', 'miqdori', 'kam_qoldi')
    search_fields = ('nomi', 'shtrix_kodlar__kod')
    list_filter = ('olchov_birligi',)
    inlines = [MahsulotRasmInline, MahsulotShtrixKodInline, CharacteristicInline]

@admin.register(Import)
class ImportAdmin(admin.ModelAdmin):
    list_display = ('nomi', 'holat', 'import_turi', 'miqdori', 'kelish_summasi', 'sotish_summasi', 'yaratilgan_vaqt')
    search_fields = ('nomi',)
    list_filter = ('holat', 'import_turi')

@admin.register(Dokon)
class DokonAdmin(admin.ModelAdmin):
    list_display = ('nomi', 'tavsif', 'yaratilgan_vaqt')
    search_fields = ('nomi',)

@admin.register(Transfer)
class TransferAdmin(admin.ModelAdmin):
    list_display = ('nomi', 'dokondan', 'dokonga', 'miqdori', 'summa', 'holat', 'yaratilgan_vaqt')
    search_fields = ('nomi', 'dokondan__nomi', 'dokonga__nomi')
    list_filter = ('holat', 'dokondan', 'dokonga')

@admin.register(Taminotchi)
class TaminotchiAdmin(admin.ModelAdmin):
    list_display = ('id', 'nomi', 'telefon_raqam')
    search_fields = ('nomi', 'telefon_raqam')

class WriteOffItemInline(admin.TabularInline):
    model = WriteOffItem
    extra = 0

@admin.register(WriteOff)
class WriteOffAdmin(admin.ModelAdmin):
    list_display = ('id', 'nomi', 'dokon', 'sababi', 'holat', 'miqdori', 'kelish_summasi', 'sotish_summasi', 'yaratgan_xodim')
    list_filter = ('holat', 'sababi', 'biznes', 'dokon')
    search_fields = ('nomi', 'dokon__nomi')
    inlines = [WriteOffItemInline]


