import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'temirdokon_v1.settings')
django.setup()

from django.test import Client
import io
import openpyxl

wb = openpyxl.Workbook()
ws = wb.active
ws.append(["Nomi", "Shtrix-kod", "Miqdori", "Kelish narxi", "Sotish narxi", "O'lchov birligi"])
ws.append(["Test", "", "-5", "-100", "50", "dona"])

file_stream = io.BytesIO()
wb.save(file_stream)
file_stream.seek(0)
file_stream.name = 'bad.xlsx'

c = Client()
# Using an arbitrary omborchi token if we had one, or we can just force_login
from django.contrib.auth.models import User
user = User.objects.first()
if user:
    c.force_login(user)

response = c.post('/products/import/', {
    'nomi': 'Test Bad Import',
    'fayl': file_stream
})
print(response.status_code)
print(response.content.decode('utf-8'))
