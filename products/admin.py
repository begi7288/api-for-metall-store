from django.contrib import admin
from .models import (
    Mahsulot, Import, Dokon, Transfer, Characteristic, MahsulotRasm,
    MahsulotShtrixKod, Taminotchi, WriteOff, WriteOffItem,
    OlchovBirligi, MahsulotToifasi, DokonQoldiq, Toplam, ToplamElement,
    XususiyatMaydoni, YorliqShablon
)

@admin.register(OlchovBirligi)
class OlchovBirligiAdmin(admin.ModelAdmin):
    list_display = ('id', 'nomi', 'short_name', 'biznes', 'yaratilgan_vaqt')
    search_fields = ('nomi', 'short_name')

@admin.register(MahsulotToifasi)
class MahsulotToifasiAdmin(admin.ModelAdmin):
    list_display = ('id', 'nomi', 'biznes', 'yaratilgan_vaqt')
    search_fields = ('nomi',)

@admin.register(DokonQoldiq)
class DokonQoldiqAdmin(admin.ModelAdmin):
    list_display = ('id', 'mahsulot', 'dokon', 'miqdori', 'yangilangan_vaqt')
    list_filter = ('dokon',)
    search_fields = ('mahsulot__nomi', 'dokon__nomi')

class ToplamElementInline(admin.TabularInline):
    model = ToplamElement
    extra = 0

@admin.register(Toplam)
class ToplamAdmin(admin.ModelAdmin):
    list_display = ('id', 'nomi', 'biznes', 'dokon', 'holat', 'miqdori', 'summa', 'yaratilgan_vaqt')
    search_fields = ('nomi',)
    inlines = [ToplamElementInline]

@admin.register(ToplamElement)
class ToplamElementAdmin(admin.ModelAdmin):
    list_display = ('id', 'toplam', 'mahsulot', 'miqdori')

@admin.register(XususiyatMaydoni)
class XususiyatMaydoniAdmin(admin.ModelAdmin):
    list_display = ('id', 'nomi', 'biznes', 'is_active', 'yaratilgan_vaqt')
    search_fields = ('nomi',)

@admin.register(YorliqShablon)
class YorliqShablonAdmin(admin.ModelAdmin):
    list_display = ('id', 'nomi', 'biznes', 'yaratilgan_vaqt')
    search_fields = ('nomi',)

@admin.register(MahsulotRasm)
class MahsulotRasmAdmin(admin.ModelAdmin):
    list_display = ('id', 'mahsulot', 'rasm', 'yaratilgan_vaqt')

@admin.register(MahsulotShtrixKod)
class MahsulotShtrixKodAdmin(admin.ModelAdmin):
    list_display = ('id', 'mahsulot', 'kod', 'yaratilgan_vaqt')
    search_fields = ('kod', 'mahsulot__nomi')

@admin.register(WriteOffItem)
class WriteOffItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'write_off', 'mahsulot', 'miqdori', 'kelish_narxi', 'sotish_narxi')
    search_fields = ('mahsulot__nomi',)


