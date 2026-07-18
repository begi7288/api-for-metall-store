from decimal import Decimal
from django.db import models
from rest_framework.pagination import PageNumberPagination
from user.permissions import IsAdminOrOmborchiOrReadOnly, IsAdminOrOmborchi
import openpyxl
from django.http import HttpResponse

class DynamicPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100

    def paginate_queryset(self, queryset, request, view=None):
        if 'page' not in request.query_params and 'page_size' not in request.query_params:
            return None
        return super().paginate_queryset(queryset, request, view)


def generate_excel_response(filename, headers, rows):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Ma'lumotlar"
    ws.append(headers)
    for row in rows:
        ws.append(row)
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename={filename}.xlsx'
    wb.save(response)
    return response
