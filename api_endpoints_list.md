# API Endpoints List

Base URL: `https://metall-store-api.onrender.com`

---

## 1. Authentication & User Management (Prefix: `/users/`)

### Register
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
  *(Note: Password is auto-generated and sent to Telegram bot)*

### Login
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

### Tarif (CRUD)
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

## 2. Products Management (Prefix: `/products/`)

### Products (CRUD)
* **List:** `GET` `https://metall-store-api.onrender.com/products/`
* **Create:** `POST` `https://metall-store-api.onrender.com/products/`
* **Detail:** `GET` `https://metall-store-api.onrender.com/products/<id>/`
* **Update:** `PUT/PATCH` `https://metall-store-api.onrender.com/products/<id>/`
* **Delete:** `DELETE` `https://metall-store-api.onrender.com/products/<id>/`

### Dokon / Stores (CRUD)
* **List:** `GET` `https://metall-store-api.onrender.com/products/dokon/`
* **Create:** `POST` `https://metall-store-api.onrender.com/products/dokon/`
* **Detail:** `GET` `https://metall-store-api.onrender.com/products/dokon/<id>/`
* **Update:** `PUT/PATCH` `https://metall-store-api.onrender.com/products/dokon/<id>/`
* **Delete:** `DELETE` `https://metall-store-api.onrender.com/products/dokon/<id>/`

### Import (CRUD)
* **List:** `GET` `https://metall-store-api.onrender.com/products/import/`
* **Create:** `POST` `https://metall-store-api.onrender.com/products/import/`
* **Detail:** `GET` `https://metall-store-api.onrender.com/products/import/<id>/`

### Transfer (CRUD)
* **List:** `GET` `https://metall-store-api.onrender.com/products/transfer/`
* **Create:** `POST` `https://metall-store-api.onrender.com/products/transfer/`
* **Detail:** `GET` `https://metall-store-api.onrender.com/products/transfer/<id>/`

### Write-off (CRUD)
* **List:** `GET` `https://metall-store-api.onrender.com/products/write-off/`
* **Create:** `POST` `https://metall-store-api.onrender.com/products/write-off/`
* **Detail:** `GET` `https://metall-store-api.onrender.com/products/write-off/<id>/`

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

### Custom Fields (CRUD)
* **List:** `GET` `https://metall-store-api.onrender.com/products/fields/`
* **Create:** `POST` `https://metall-store-api.onrender.com/products/fields/`
* **Detail:** `GET` `https://metall-store-api.onrender.com/products/fields/<id>/`

### Bundles / Toplam (CRUD)
* **List:** `GET` `https://metall-store-api.onrender.com/products/toplam/`
* **Create:** `POST` `https://metall-store-api.onrender.com/products/toplam/`
* **Detail:** `GET` `https://metall-store-api.onrender.com/products/toplam/<id>/`

### Price Tag Templates (CRUD)
* **List:** `GET` `https://metall-store-api.onrender.com/products/price-tag-templates/`
* **Create:** `POST` `https://metall-store-api.onrender.com/products/price-tag-templates/`
* **Detail:** `GET` `https://metall-store-api.onrender.com/products/price-tag-templates/<id>/`

---

## 3. Supplier Orders (Prefix: `/products/order/`)

### Supplier Orders (CRUD)
* **List:** `GET` `https://metall-store-api.onrender.com/products/order/`
* **Create:** `POST` `https://metall-store-api.onrender.com/products/order/`
* **Detail:** `GET` `https://metall-store-api.onrender.com/products/order/<id>/`

### Suppliers / Taminotchilar (CRUD)
* **List:** `GET` `https://metall-store-api.onrender.com/products/order/taminotchilar/`
* **Create:** `POST` `https://metall-store-api.onrender.com/products/order/taminotchilar/`
* **Detail:** `GET` `https://metall-store-api.onrender.com/products/order/taminotchilar/<id>/`

### Returns (CRUD)
* **List:** `GET` `https://metall-store-api.onrender.com/products/order/returns/`
* **Create:** `POST` `https://metall-store-api.onrender.com/products/order/returns/`
* **Detail:** `GET` `https://metall-store-api.onrender.com/products/order/returns/<id>/`

---

## 4. API Auto-Documentation (Swagger)

* **OpenAPI Schema (JSON):** `https://metall-store-api.onrender.com/api/schema/`
* **Swagger UI:** `https://metall-store-api.onrender.com/api/schema/swagger-ui/`
* **Redoc UI:** `https://metall-store-api.onrender.com/api/schema/redoc/`
