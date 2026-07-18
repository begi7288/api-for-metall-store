from rest_framework import serializers
from products.models import Dokon
from user.serializers import XSSSanitizerMixin

class DokonSerializer(XSSSanitizerMixin, serializers.ModelSerializer):
    class Meta:
        model = Dokon
        fields = ['id', 'biznes', 'nomi', 'tavsif', 'yaratilgan_vaqt', 'yangilangan_vaqt']
        read_only_fields = ['biznes', 'yaratilgan_vaqt', 'yangilangan_vaqt']
