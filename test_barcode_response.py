import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'temirdokon_v1.settings')
django.setup()

from django.test import Client
from django.core.files.uploadedfile import SimpleUploadedFile
import openpyxl
from io import BytesIO

# Create a dummy excel file in memory
wb = openpyxl.Workbook()
ws = wb.active
ws.append(['Nomi', 'Shtrix-kod', 'Miqdori', 'Kelish narxi', 'Sotish narxi', "O'lchov birligi"])
ws.append(['Test Mahsulot API', '', 50, 1000, 1500, 'dona'])

excel_file = BytesIO()
wb.save(excel_file)
excel_file.seek(0)

c = Client(SERVER_NAME='localhost')
response = c.post('/products/import/', {
    'nomi': 'API Test Import',
    'fayl': SimpleUploadedFile('test.xlsx', excel_file.read(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
    'shtrixkod_generatsiya_qilish': True
})

print(response.status_code)
import json
print(json.dumps(response.json(), indent=2))
