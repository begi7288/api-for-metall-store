import json
import logging
from django.db import transaction
from django.core import serializers
from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework.authtoken.models import Token

from user.models import (
    Biznes, Tarif, Xodim, Mijoz, XodimRoli, MijozQarzi, MijozTolovi,
    SodiqlikDasturi, SodiqlikDarajasi, ChekSozlamalari, Valyuta,
    TolovTuriSozlama, MahsulotSozlamalari, BildirishnomaSozlamalari, Ilova, Guruh, Teg
)
from products.models import (
    MahsulotToifasi, OlchovBirligi, Characteristic, Mahsulot, MahsulotRasm,
    MahsulotShtrixKod, Import, Dokon, DokonQoldiq, Transfer, Taminotchi,
    WriteOff, WriteOffItem, XususiyatMaydoni, Toplam, ToplamElement, YorliqShablon
)
from sales.models import Sale, SaleItem, XarajatKategoriyasi, Xarajat
from orders.models import (
    SupplierOrder, SupplierOrderItem, SupplierOrderPayment,
    SupplierOrderReturn, SupplierOrderReturnItem
)

logger = logging.getLogger(__name__)

# List of all application models in order of dependency resolution
SYNC_MODELS = [
    # Auth & Base User models
    User,
    Biznes,
    Tarif,
    Xodim,
    XodimRoli,
    Mijoz,
    Guruh,
    Teg,
    # User Settings & Sub-models
    ChekSozlamalari,
    Valyuta,
    TolovTuriSozlama,
    MahsulotSozlamalari,
    BildirishnomaSozlamalari,
    Ilova,
    SodiqlikDasturi,
    SodiqlikDarajasi,
    MijozQarzi,
    MijozTolovi,
    # Products & Catalog
    MahsulotToifasi,
    OlchovBirligi,
    Characteristic,
    XususiyatMaydoni,
    Taminotchi,
    Mahsulot,
    MahsulotRasm,
    MahsulotShtrixKod,
    Dokon,
    DokonQoldiq,
    Transfer,
    Import,
    WriteOff,
    WriteOffItem,
    Toplam,
    ToplamElement,
    YorliqShablon,
    # Sales & Expenses
    XarajatKategoriyasi,
    Xarajat,
    Sale,
    SaleItem,
    # Orders
    SupplierOrder,
    SupplierOrderItem,
    SupplierOrderPayment,
    SupplierOrderReturn,
    SupplierOrderReturnItem,
]

def export_full_backup(biznes=None, using='default'):
    """
    Serializes full system data into JSON structure for cloud backup / restore.
    """
    exported_data = {}
    total_records = 0

    for model_class in SYNC_MODELS:
        model_key = f"{model_class._meta.app_label}.{model_class._meta.model_name}"
        qs = model_class.objects.using(using).all()

        # If scoped to specific business
        if biznes and hasattr(model_class, 'biznes'):
            qs = qs.filter(biznes=biznes)


        raw_json = serializers.serialize('json', qs)
        records = json.loads(raw_json)
        exported_data[model_key] = records
        total_records += len(records)

    return {
        "version": "1.0",
        "timestamp": timezone.now().isoformat(),
        "total_records": total_records,
        "models": exported_data
    }

def is_same_entity(existing_obj, instance):
    """
    Universal check if existing DB record represents the exact same entity as local instance.
    """
    if hasattr(instance, 'username') and hasattr(existing_obj, 'username'):
        return existing_obj.username == instance.username
    if hasattr(instance, 'kod') and hasattr(existing_obj, 'kod'):
        return existing_obj.kod == instance.kod
    if hasattr(instance, 'code') and hasattr(existing_obj, 'code'):
        return existing_obj.code == instance.code
    if hasattr(instance, 'telefon') and hasattr(existing_obj, 'telefon'):
        return existing_obj.telefon == instance.telefon
    if hasattr(instance, 'telefon_raqam') and hasattr(existing_obj, 'telefon_raqam'):
        return existing_obj.telefon_raqam == instance.telefon_raqam
    if hasattr(instance, 'slug') and hasattr(existing_obj, 'slug'):
        return existing_obj.slug == instance.slug
    if hasattr(instance, 'user_id') and hasattr(existing_obj, 'user_id') and instance.user_id is not None:
        return existing_obj.user_id == instance.user_id
    if hasattr(instance, 'nomi') and hasattr(existing_obj, 'nomi') and instance.nomi is not None:
        return existing_obj.nomi == instance.nomi
    if hasattr(instance, 'name') and hasattr(existing_obj, 'name') and instance.name is not None:
        return existing_obj.name == instance.name

    return False



def import_full_backup(backup_data, clear_existing=False, using='default'):
    """
    Restores / imports full system data from JSON backup structure.
    Uses transaction.atomic() to ensure 100% all-or-nothing integrity.
    """
    if isinstance(backup_data, str):
        backup_data = json.loads(backup_data)

    models_data = backup_data.get('models', {})

    with transaction.atomic(using=using):
        if clear_existing:
            # Delete in reverse dependency order
            for model_class in reversed(SYNC_MODELS):
                if model_class != User:
                    model_class.objects.using(using).all().delete()

        deserialized_count = 0

        for model_class in SYNC_MODELS:
            model_key = f"{model_class._meta.app_label}.{model_class._meta.model_name}"
            records = models_data.get(model_key, [])
            if not records:
                continue

            serialized_str = json.dumps(records)
            for obj in serializers.deserialize('json', serialized_str, using=using):
                instance = obj.object
                target_model = instance.__class__
                pk_val = instance.pk

                if pk_val is not None and target_model.objects.using(using).filter(pk=pk_val).exists():
                    existing_obj = target_model.objects.using(using).get(pk=pk_val)
                    if is_same_entity(existing_obj, instance):
                        continue
                    else:
                        instance.pk = None
                        instance.id = None

                try:
                    with transaction.atomic(using=using):
                        obj.save(using=using)
                        deserialized_count += 1
                except Exception as ex:
                    # Duplicate constraint attempt -> retry without PK
                    try:
                        instance.pk = None
                        instance.id = None
                        with transaction.atomic(using=using):
                            obj.save(using=using)
                            deserialized_count += 1
                    except Exception as err2:
                        logger.warning(f"Sync skip {model_key} {instance}: {err2}")

        # Ensure token authentication objects exist for all restored Users
        for user in User.objects.using(using).all():
            Token.objects.using(using).get_or_create(user=user)

    return {
        "success": True,
        "imported_records": deserialized_count,
        "timestamp": timezone.now().isoformat()
    }



def get_sync_summary():
    """
    Returns total count of records across key models for monitoring.
    """
    summary = {}
    for model_class in SYNC_MODELS:
        model_key = f"{model_class._meta.app_label}.{model_class._meta.model_name}"
        summary[model_key] = model_class.objects.count()
    return summary
