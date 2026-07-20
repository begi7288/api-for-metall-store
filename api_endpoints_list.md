# API Endpoints List (Complete)

Base URL: `https://metall-store-api.onrender.com`

---

## 1. Authentication & User Management (Prefix: `/users/`)

### Register (Sign Up)
* **URL:** `https://metall-store-api.onrender.com/users/register/`
* **Method:** `POST`
* **Body:**
  ```json
  {
    "ism": "Ali",
    "telefon_raqam": "+998901234567",
    "biznes_nomi": "Alining Biznesi"
  }
  ```
  *(Note: 6-digit verification code is generated and sent to Telegram bot)*

### Login (Sign In)
* **URL:** `https://metall-store-api.onrender.com/users/login/`
* **Method:** `POST`
* **Body:**
  ```json
  {
    "telefon_raqam": "+998901234567",
    "parol": "123456"
  }
  ```

### Logout
* **URL:** `https://metall-store-api.onrender.com/users/logout/`
* **Method:** `POST`
* **Headers:** `Authorization: Token <token_key>`

### Get Current User Profile
* **URL:** `https://metall-store-api.onrender.com/users/me/`
* **Method:** `GET`
* **Headers:** `Authorization: Token <token_key>`

### Change Password
* **URL:** `https://metall-store-api.onrender.com/users/change-password/`
* **Method:** `POST`
* **Headers:** `Authorization: Token <token_key>`
* **Body:**
  ```json
  {
    "eski_parol": "123456",
    "yangi_parol": "NewSecurePass123!",
    "yangi_parol_tasdiqlash": "NewSecurePass123!"
  }
  ```

### Biznes (CRUD)
* **List:** `GET` `https://metall-store-api.onrender.com/users/biznes/`
* **Detail:** `GET` `https://metall-store-api.onrender.com/users/biznes/<id>/`
* **Update:** `PUT/PATCH` `https://metall-store-api.onrender.com/users/biznes/<id>/`

### Tarif
* **List:** `GET` `https://metall-store-api.onrender.com/users/tarif/`
* **Detail:** `GET` `https://metall-store-api.onrender.com/users/tarif/<id>/`

### Xodimlar / Employees (CRUD)
* **List:** `GET` `https://metall-store-api.onrender.com/users/xodimlar/`
* **Create:** `POST` `https://metall-store-api.onrender.com/users/xodimlar/`
* **Detail:** `GET` `https://metall-store-api.onrender.com/users/xodimlar/<id>/`
* **Update:** `PUT/PATCH` `https://metall-store-api.onrender.com/users/xodimlar/<id>/`
* **Delete:** `DELETE` `https://metall-store-api.onrender.com/users/xodimlar/<id>/`

### Mijozlar / Customers (CRUD)
* **List:** `GET` `https://metall-store-api.onrender.com/users/mijozlar/`
* **Create:** `POST` `https://metall-store-api.onrender.com/users/mijozlar/`
* **Detail:** `GET` `https://metall-store-api.onrender.com/users/mijozlar/<id>/`
* **Update:** `PUT/PATCH` `https://metall-store-api.onrender.com/users/mijozlar/<id>/`
* **Delete:** `DELETE` `https://metall-store-api.onrender.com/users/mijozlar/<id>/`

---

## 2. Products & Inventory Management (Prefix: `/products/`)

### Products (CRUD & Actions)
* **List:** `GET` `https://metall-store-api.onrender.com/products/`
* **Create:** `POST` `https://metall-store-api.onrender.com/products/`
* **Detail:** `GET` `https://metall-store-api.onrender.com/products/<id>/`
* **Update:** `PUT/PATCH` `https://metall-store-api.onrender.com/products/<id>/`
* **Delete:** `DELETE` `https://metall-store-api.onrender.com/products/<id>/`
* **Bulk Operations:** `POST` `https://metall-store-api.onrender.com/products/bulk_operations/`
* **Stats:** `GET` `https://metall-store-api.onrender.com/products/stats/`
* **Under Limit Products:** `GET` `https://metall-store-api.onrender.com/products/under_limit/`
* **Toggle Archive:** `POST` `https://metall-store-api.onrender.com/products/<id>/toggle_archive/`

### Dokon / Stores (CRUD)
* **List:** `GET` `https://metall-store-api.onrender.com/products/dokon/`
* **Create:** `POST` `https://metall-store-api.onrender.com/products/dokon/`
* **Detail:** `GET` `https://metall-store-api.onrender.com/products/dokon/<id>/`
* **Update:** `PUT/PATCH` `https://metall-store-api.onrender.com/products/dokon/<id>/`
* **Delete:** `DELETE` `https://metall-store-api.onrender.com/products/dokon/<id>/`

### Import (CRUD & Actions)
* **List:** `GET` `https://metall-store-api.onrender.com/products/import/`
* **Create:** `POST` `https://metall-store-api.onrender.com/products/import/`
* **Detail:** `GET` `https://metall-store-api.onrender.com/products/import/<id>/`
* **Confirm Import:** `POST` `https://metall-store-api.onrender.com/products/import/<id>/confirm/`
* **Get Import Template File:** `GET` `https://metall-store-api.onrender.com/products/import/template/`

### Transfer (CRUD & Actions)
* **List:** `GET` `https://metall-store-api.onrender.com/products/transfer/`
* **Create:** `POST` `https://metall-store-api.onrender.com/products/transfer/`
* **Detail:** `GET` `https://metall-store-api.onrender.com/products/transfer/<id>/`
* **Confirm Transfer:** `POST` `https://metall-store-api.onrender.com/products/transfer/<id>/confirm/`

### Write-off (CRUD & Actions)
* **List:** `GET` `https://metall-store-api.onrender.com/products/write-off/`
* **Create:** `POST` `https://metall-store-api.onrender.com/products/write-off/`
* **Detail:** `GET` `https://metall-store-api.onrender.com/products/write-off/<id>/`
* **Confirm Write-off:** `POST` `https://metall-store-api.onrender.com/products/write-off/<id>/confirm/`
* **Cancel Write-off:** `POST` `https://metall-store-api.onrender.com/products/write-off/<id>/cancel/`
* **Stats:** `GET` `https://metall-store-api.onrender.com/products/write-off/stats/`

### Characteristics (CRUD)
* **List:** `GET` `https://metall-store-api.onrender.com/products/characteristics/`
* **Create:** `POST` `https://metall-store-api.onrender.com/products/characteristics/`
* **Detail:** `GET` `https://metall-store-api.onrender.com/products/characteristics/<id>/`

### Product Images (CRUD)
* **List:** `GET` `https://metall-store-api.onrender.com/products/images/`
* **Create:** `POST` `https://metall-store-api.onrender.com/products/images/`
* **Detail:** `GET` `https://metall-store-api.onrender.com/products/images/<id>/`
* **Delete:** `DELETE` `https://metall-store-api.onrender.com/products/images/<id>/`

### Product Barcodes (CRUD)
* **List:** `GET` `https://metall-store-api.onrender.com/products/barcodes/`
* **Create:** `POST` `https://metall-store-api.onrender.com/products/barcodes/`
* **Detail:** `GET` `https://metall-store-api.onrender.com/products/barcodes/<id>/`
* **Delete:** `DELETE` `https://metall-store-api.onrender.com/products/barcodes/<id>/`

### Custom Fields / XususiyatMaydoni (CRUD)
* **List:** `GET` `https://metall-store-api.onrender.com/products/fields/`
* **Create:** `POST` `https://metall-store-api.onrender.com/products/fields/`
* **Detail:** `GET` `https://metall-store-api.onrender.com/products/fields/<id>/`

### Bundles / Toplam (CRUD)
* **List:** `GET` `https://metall-store-api.onrender.com/products/toplam/`
* **Create:** `POST` `https://metall-store-api.onrender.com/products/toplam/`
* **Detail:** `GET` `https://metall-store-api.onrender.com/products/toplam/<id>/`

### Price Tag Templates / YorliqShablon (CRUD)
* **List:** `GET` `https://metall-store-api.onrender.com/products/price-tag-templates/`
* **Create:** `POST` `https://metall-store-api.onrender.com/products/price-tag-templates/`
* **Detail:** `GET` `https://metall-store-api.onrender.com/products/price-tag-templates/<id>/`

### Suppliers / Taminotchi (CRUD & Actions)
* **List:** `GET` `https://metall-store-api.onrender.com/products/suppliers/`
* **Create:** `POST` `https://metall-store-api.onrender.com/products/suppliers/`
* **Detail:** `GET` `https://metall-store-api.onrender.com/products/suppliers/<id>/`
* **Update:** `PUT/PATCH` `https://metall-store-api.onrender.com/products/suppliers/<id>/`
* **Delete:** `DELETE` `https://metall-store-api.onrender.com/products/suppliers/<id>/`
* **Pay Supplier:** `POST` `https://metall-store-api.onrender.com/products/suppliers/<id>/pay/`
* **Payment History:** `GET` `https://metall-store-api.onrender.com/products/suppliers/<id>/history/`
* **Orders History:** `GET` `https://metall-store-api.onrender.com/products/suppliers/<id>/orders/`
* **Stats:** `GET` `https://metall-store-api.onrender.com/products/suppliers/stats/`

---

## 3. Supplier Orders & Xaridlar (Prefix: `/products/order/`)

### Supplier Orders (CRUD & Actions)
* **List:** `GET` `https://metall-store-api.onrender.com/products/order/`
* **Create:** `POST` `https://metall-store-api.onrender.com/products/order/`
* **Detail:** `GET` `https://metall-store-api.onrender.com/products/order/<id>/`
* **Confirm Order:** `POST` `https://metall-store-api.onrender.com/products/order/<id>/confirm/`
* **Cancel Order:** `POST` `https://metall-store-api.onrender.com/products/order/<id>/cancel/`
* **Get Order Items:** `GET` `https://metall-store-api.onrender.com/products/order/<id>/items/`
* **Pay for Order:** `POST` `https://metall-store-api.onrender.com/products/order/<id>/pay/`

### Suppliers / Taminotchilar (CRUD & Actions)
* **List:** `GET` `https://metall-store-api.onrender.com/products/order/taminotchilar/`
* **Create:** `POST` `https://metall-store-api.onrender.com/products/order/taminotchilar/`
* **Detail:** `GET` `https://metall-store-api.onrender.com/products/order/taminotchilar/<id>/`
* **Stats:** `GET` `https://metall-store-api.onrender.com/products/order/taminotchilar/stats/`

### Returns (CRUD & Actions)
* **List:** `GET` `https://metall-store-api.onrender.com/products/order/returns/`
* **Create:** `POST` `https://metall-store-api.onrender.com/products/order/returns/`
* **Detail:** `GET` `https://metall-store-api.onrender.com/products/order/returns/<id>/`
* **Confirm Return:** `POST` `https://metall-store-api.onrender.com/products/order/returns/<id>/confirm/`
* **Cancel Return:** `POST` `https://metall-store-api.onrender.com/products/order/returns/<id>/cancel/`
* **Stats:** `GET` `https://metall-store-api.onrender.com/products/order/returns/stats/`

---

## 4. API Auto-Documentation (Swagger)

* **OpenAPI Schema (JSON):** `https://metall-store-api.onrender.com/api/schema/`
* **Swagger UI:** `https://metall-store-api.onrender.com/api/schema/swagger-ui/`
* **Redoc UI:** `https://metall-store-api.onrender.com/api/schema/redoc/`
