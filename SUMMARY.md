# Project Plans & Summary

Tizimdagi barcha joriy, yakunlangan va rejalashtirilgan ishlar hamda arxitektura rejalari.

---

## 1. Yakunlangan imkoniyatlar (Completed)

* **Ko'p rasm yuklash (Multi-Image Upload)**: 
  * Bitta mahsulotga 5 tagacha rasm biriktirish imkoniyati (`MahsulotRasm` modeli).
  * Rasm o'lchami validation (max 5MB).
  * Rasmlarni alohida `/products/images/` orqali boshqarish.
* **Ko'p shtrix-kodlar (Multi-Barcode)**:
  * Bir mahsulotga cheksiz shtrix-kodlar bog'lash (`MahsulotShtrixKod` modeli).
  * Shtrix-kod uzunligi (8, 12, 13 raqamli) va format tekshiruvi.
  * Oxirgi shtrix-kodni o'chirishdan himoya.
  * Import/Serializers orqali comma-separated va ro'yxat ko'rinishida shtrix-kod qabul qilish.
* **Buyurtmalar (Orders / Xarid buyurtmalari)**:
  * Yetkazib beruvchilardan tovar buyurtma qilish va qabul qilish.
  * Excel (XLSX, XLS, CSV) shablonlari orqali buyurtma yuklash va yangi mahsulotlarni avtomatik bazada yaratish.
  * "Farqli narxlar" solishtirish interfeysi orqali narxlarni solishtirish va yangilash logikasi.
  * To'lovlar tarixi, naqd/karta va yetkazib beruvchi balansidan qoplash imkoniyatlari.
  * Qaytarish (Supplier Return) orqali zaxirani kamaytirish va balansni to'g'rilash.
* **Yetkazib beruvchilar (Suppliers)**:
  * Aloqa ma'lumotlari, balans monitoringi va har bir biznes uchun alohida tenant izolyatsiyasi.

---

## 2. Faol va Rejalashtirilgan Rejalar (Active & Upcoming)

* **Do'konlar bo'yicha qoldiqlar (Shop-Specific Inventory)**:
  * Har bir do'kon uchun alohida qoldiqlar (`DokonQoldiq` modeli: `miqdori`, `ogohlantirish`).
  * Yangi mahsulot qo'shishda kamida bitta do'konda qoldiq kiritish majburiyligi.
  * API GET so'rovlarda faqat qoldig'i bor do'konlarni ko'rsatish (`miqdori > 0`).
  * Import va Transfer jarayonida do'konlar bo'yicha qoldiqlarni to'g'ri yangilash.
* **Xavfsizlik va Validation Hardening (Betondek Mustahkam Qilish)**:
  * **SaaS Tenant Izolyatsiyasi**: Tizimdagi barcha obyektlarni biznes egasiga qarab qat'iy filtrlash yakunlandi.
  * **Mijoz multi-tenancy**: Mijoz telefon raqamlarini unikalligini biznes darajasida cheklash yakunlandi.
  * **Xodim Limit Tekshiruvi**: Xodimlar limiti va obuna cheklovlari tekshiruvi yakunlandi.

---

## 3. SaaS Arxitekturasi va Tarif Cheklovlari

* **Logical Isolation**: Har bir jadvalda `biznes` (ForeignKey) maydoni mavjud va u orqali so'rovlar filtrlanadi.
* **Tarif va Cheklovlar**:
  * `Tarif` modeli: `dokon_limiti`, `mahsulot_limiti`, `xodim_limiti`.
  * Do'kon, mahsulot yoki xodim qo'shish jarayonida tarif rejasidagi limitlar tekshiriladi.

---

## 4. Yo'l xaritasi (Roadmap: Version 1)

1. **Katalog (Catalog)** - ⚙️ *Hardening & Security updates*
2. **Kirim (Import)** - ⚙️ *Hardening & Security updates*
3. **Transfer (O'tkazma)** - ⚙️ *Hardening & Security updates*
4. **Mijozlar (Customers)** - ⚙️ *Hardening & Security updates*
5. **Buyurtmalar (Orders)** - ✅ *Yakunlandi*
6. **Yetkazib beruvchilar (Suppliers)** - ✅ *Yakunlandi*
7. **Hisobdan chiqarish (Write-off)** - 📅 *Rejalashtirilgan*
