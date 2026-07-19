# TemirDokon API Yo'riqnomasi (Frontend uchun)

Ushbu hujjat frontend dasturchilar uchun backend API bilan integratsiya qilish jarayonini osonlashtirish maqsadida yaratildi. Barcha asosiy API'lar, ularning parametrlari, so'rov va javob formatlari batafsil keltirilgan.

---

## 1. Umumiy qoidalar va Autentifikatsiya

### Baza URL (Base URL)
* Mahalliy muhit (Local dev): `http://127.0.0.1:8000` or `http://localhost:8000`
* Production muhit: Render yoki boshqa server URL manzili.

### Autentifikatsiya (Token Authentication)
Tizimga kirish uchun **Token-based** autentifikatsiyadan foydalaniladi.
1. `/users/login/` orqali POST so'rov yuborib `token` olinadi.
2. Barcha autentifikatsiya talab qiluvchi so'rovlarga quyidagi header qo'shilishi shart:
   ```http
   Authorization: Token <olingan_token_qiymati>
   ```
   *Masalan: `Authorization: Token 9944b09199c62bcf9418ad846dd0e4bbdf3c2742`*

### Content-Type
* Oddiy so'rovlar uchun: `application/json`
* Fayl yoki rasm yuklash so'rovlari uchun (masalan, Mahsulot rasm yoki Import fayli yuklashda): `multipart/form-data`

---

## 2. API Jadvali (Endpoints Directory)

| Tizim/Modul | HTTP Metod | URL Path | Auth? | Tavsif / Maqsad |
| :--- | :--- | :--- | :--- | :--- |
| **Auth** | POST | `/users/register/` | Yo'q | Yangi biznes va admin xodimni ro'yxatdan o'tkazish |
| | POST | `/users/login/` | Yo'q | Tizimga kirish va Token olish |
| | POST | `/users/logout/` | Ha | Tizimdan chiqish (tokenni bekor qilish) |
| | GET | `/users/me/` | Ha | Hozirgi foydalanuvchi ma'lumotlarini olish |
| | POST | `/users/change-password/` | Ha | Parolni o'zgartirish |
| **Do'konlar** | GET | `/products/dokon/` | Ha | Biznesga tegishli barcha do'konlar ro'yxati |
| | POST | `/products/dokon/` | Ha | Yangi do'kon yaratish |
| | GET/PUT/DELETE| `/products/dokon/<id>/` | Ha | Alohida do'konni ko'rish, o'zgartirish yoki o'chirish |
| **Mahsulotlar**| GET | `/products/` | Ha | Barcha mahsulotlar ro'yxati (filtrlash bilan) |
| | POST | `/products/` | Ha | Yangi mahsulot yaratish (shtrix-kod va do'kon qoldiqlari bilan) |
| | GET/PUT/PATCH| `/products/<id>/` | Ha | Mahsulotni ko'rish, o'zgartirish yoki arxivlash |
| | POST | `/products/bulk_operations/` | Ha | Tovar narxlarini, xususiyatlarini ommaviy o'zgartirish, rasmlar yuklash |
| | GET | `/products/stats/` | Ha | Zaxira statistikasi (jami qiymat, kam qolgan tovarlar soni va b.) |
| **Shtrix-kod** | GET | `/products/barcodes/` | Ha | Mahsulot shtrix-kodlari ro'yxati |
| | POST | `/products/barcodes/` | Ha | Mahsulotga yangi shtrix-kod bog'lash |
| | DELETE | `/products/barcodes/<id>/` | Ha | Shtrix-kodni o'chirish (oxirgi shtrix-kod o'chirilmaydi) |
| **Rasmlar** | POST | `/products/images/` | Ha | Mahsulotga alohida rasm yuklash (maks. 5 ta) |
| | DELETE | `/products/images/<id>/` | Ha | Mahsulot rasmini o'chirish |
| **Yetkazib beruvchi** | GET | `/products/order/taminotchilar/`| Ha | Yetkazib beruvchilar (taminotchilar) ro'yxati |
| | POST | `/products/order/taminotchilar/`| Ha | Yangi yetkazib beruvchi yaratish |
| **Xaridlar (Orders)** | GET | `/products/order/` | Ha | Yetkazib beruvchidan olingan buyurtmalar ro'yxati |
| | POST | `/products/order/` | Ha | Yangi buyurtma yaratish (Qoralama holatida) |
| | GET/PUT/DELETE| `/products/order/<id>/` | Ha | Buyurtma tafsiloti, o'zgartirish yoki o'chirish (faqat qoralama) |
| | POST | `/products/order/<id>/confirm/` | Ha | Buyurtmani rasmiylashtirish (holatini 'yuborilgan'ga o'tkazish) |
| | GET | `/products/order/<id>/price_differences/` | Ha | Mahsulotlarning joriy narxlari va buyurtmadagi farqlarni solishtirish |
| | POST | `/products/order/<id>/receive/` | Ha | Tovar kelganda omborga qabul qilish (ombordagi miqdor ko'payadi) |
| | POST | `/products/order/<id>/pay/` | Ha | Buyurtma uchun to'lov kiritish (naqd/karta/balans) |
| | POST | `/products/order/<id>/cancel/` | Ha | Buyurtmani bekor qilish |
| | GET | `/products/order/template/` | Ha | Excel orqali ommaviy yuklash uchun shablon (.xlsx) yuklab olish |
| **Qaytarishlar**| GET | `/products/order/returns/` | Ha | Yetkazib beruvchiga tovar qaytarishlar ro'yxati |
| | POST | `/products/order/returns/` | Ha | Qaytarish hujjati yaratish |
| | POST | `/products/order/returns/<id>/confirm/` | Ha | Qaytarishni tasdiqlash (ombordan tovar kamayib, balans to'g'rilanadi) |
| **Import (Excel)** | GET | `/products/import/` | Ha | Excel orqali tovar kirim qilish tarixi |
| | POST | `/products/import/` | Ha | Excel faylini yuklash va tovarlarni avtomatik yaratish/yangilash |
| | POST | `/products/import/<id>/confirm/`| Ha | Kirimni tasdiqlash (zaxira va qoldiqlarni yangilash) |
| **Hisobdan chiqarish** | GET | `/products/write-off/` | Ha | Yaroqsiz, buzilgan tovarlarni hisobdan chiqarish ro'yxati |
| | POST | `/products/write-off/` | Ha | Hisobdan chiqarish hujjati yaratish (qoralama) |
| | POST | `/products/write-off/<id>/confirm/`| Ha | Tasdiqlash (tovarlar zaxiradan kamayadi) |

---

## 3. Muhim so'rov va javob namunalari (Payloads)

### 3.1. Login (Tizimga kirish)
* **URL:** `/users/login/`
* **Method:** `POST`
* **Request Body (JSON):**
```json
{
  "telefon_raqam": "+998901234567",
  "parol": "JudaKuchliParol123!"
}
```
* **Response (200 OK):**
```json
{
  "token": "9944b09199c62bcf9418ad846dd0e4bbdf3c2742",
  "ism": "Eshmat",
  "familiya": "Toshmatov",
  "rol": "admin",
  "biznes_id": 1,
  "redirect_url": "/users/me/"
}
```

### 3.2. Me (Hozirgi foydalanuvchi)
* **URL:** `/users/me/`
* **Method:** `GET`
* **Headers:** `Authorization: Token <token>`
* **Response (200 OK):**
```json
{
  "id": 1,
  "ism": "Eshmat",
  "familiya": "Toshmatov",
  "telefon_raqam": "+998901234567",
  "rol": "admin",
  "biznes": {
    "id": 1,
    "nomi": "Temir Savdo MChJ",
    "tarif_nomi": "Premium"
  }
}
```

### 3.3. Mahsulot yaratish (Create Product)
Mahsulot yaratishda kamida bitta do'kondagi qoldiq (va uning minimal ogohlantirish miqdori) yuborilishi shart.
* **URL:** `/products/`
* **Method:** `POST`
* **Headers:** `Authorization: Token <token>`, `Content-Type: application/json`
* **Request Body (JSON):**
```json
{
  "nomi": "Armatura 12mm (A500C)",
  "olchov_birligi": "tonna",
  "kelish_narxi": "8200000.00",
  "ustama": 10.00,
  "ulgurji_narx": "8800000.00",
  "erkin_narx": false,
  "toifa": "Metall prokati",
  "brend": "Bekobod Metall",
  "taminotchi": 2,
  "shtrix_kod": ["4780012345678", "4780012345679"],
  "qoldiqlar": [
    {
      "dokon": 1,
      "miqdori": "15.5",
      "ogohlantirish": "2.0"
    },
    {
      "dokon": 2,
      "miqdori": "5.0",
      "ogohlantirish": "1.0"
    }
  ]
}
```
* **Eslatma:** Agar backend'da rasm fayllarini ham bir vaqtda yubormoqchi bo'lsangiz, `multipart/form-data` dan foydalaning. Rasmlar kaliti `rasm` (fayllar massivi) bo'ladi.

### 3.4. Mahsulotlarni ommaviy tahrirlash (Bulk Operations)
* **URL:** `/products/bulk_operations/`
* **Method:** `POST`
* **Request Body (JSON) namunalari:**

**A. Narxlarni ommaviy oshirish (Foizda yoki Summada):**
```json
{
  "action": "edit_prices",
  "product_ids": [12, 13, 14],
  "params": {
    "price_type": "sotish_narxi",
    "operation": "oshirish_foiz",
    "value": "15" 
  }
}
```
*(Yoki `operation` quyidagilardan biri bo'lishi mumkin: `belgilash`, `oshirish_foiz`, `kamaytirish_foiz`, `oshirish_summa`, `kamaytirish_summa`)*

**B. Kam qoldiq chegarasini ommaviy o'rnatish:**
```json
{
  "action": "set_low_stock",
  "product_ids": [12, 13, 14],
  "params": {
    "threshold": 10
  }
}
```

### 3.5. Xarid Buyurtmasini Yaratish (Supplier Order - Create)
* **URL:** `/products/order/`
* **Method:** `POST`
* **Request Body (JSON):**
```json
{
  "taminotchi": 2,
  "dokon": 1,
  "nomi": "Iyul oyi uchun armatura xaridi",
  "qabul_qilish_sanasi": "2026-07-25",
  "elementlar": [
    {
      "mahsulot": 15,
      "miqdori": "100.00",
      "kelish_narxi": "45000.00",
      "ustama": "20.00",
      "sotish_narxi": "54000.00",
      "ulgurji_narx": "52000.00"
    }
  ]
}
```

---

## 4. Filtrlar va Qidiruv parametrlari (Query Parameters)

Tovarlarni qidirish, saralash va filtrlash uchun GET so'rovida quyidagi kalitlardan foydalaning:
* **Qidiruv:** `?search=Armatura` (nomi yoki shtrix-kodi bo'yicha qidiradi)
* **Do'kon bo'yicha saralash:** `?dokon=1` (faqat do'konda zaxirasi `miqdori > 0` bo'lgan tovarlarni qaytaradi)
* **Kam qolgan tovarlar:** `?kam_qoldi=true` (ombordagi miqdori ogohlantirish miqdoriga teng yoki undan kam tovarlar)
* **Nol qoldiq:** `?nol_qoldiq=true` (miqdori tugagan tovarlar)
* **Narx oralig'i:** `?sotish_narxi_min=50000&sotish_narxi_max=150000`
* **Saralash (Ordering):** `?ordering=-yaratilgan_vaqt` (yoki `sotish_narxi`, `-miqdori`)

---

## 5. Xatoliklar Formati (Error Response Structure)

Xatolik yuz berganda API standart JSON qaytaradi:
* **Validation Xatoligi (400 Bad Request):**
```json
{
  "telefon_raqam": [
    "Ushbu raqamga ega xodim allaqachon ro'yxatdan o'tgan."
  ],
  "parol": [
    "Parol juda oddiy. Kamida bitta harf va son bo'lishi kerak."
  ]
}
```
* **Tizimli yoki Umumiy xatolik (400/403/500):**
```json
{
  "detail": "Faqat qoralama holatidagi buyurtmalarni o'zgartirish mumkin."
}
```
*(Ballar xato xabarlari bevosita UI'da foydalanuvchiga ko'rsatish uchun moslashtirilgan o'zbek tilida qaytadi)*
