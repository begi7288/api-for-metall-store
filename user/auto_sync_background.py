import os
import time
import socket
import threading
import logging
import dj_database_url
from django.conf import settings
from django.db import transaction

logger = logging.getLogger(__name__)

def run_sync_task():
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        return

    try:
        remote_config = dj_database_url.config(default=database_url, conn_max_age=600)
        if remote_config.get('ENGINE') == 'django.db.backends.postgresql':
            remote_config.setdefault('OPTIONS', {})['sslmode'] = 'require'

        host = remote_config.get('HOST')
        port = int(remote_config.get('PORT') or 5432)

        if not host:
            return

        # Check internet / server reachability
        try:
            s = socket.create_connection((host, port), timeout=3)
            s.close()
        except Exception:
            return # Offline, keep working locally

        from user.sync_service import export_full_backup, SYNC_MODELS
        from django.core import serializers
        import json

        backup_data = export_full_backup()
        total = backup_data.get('total_records', 0)
        if total == 0:
            return

        remote_config.update({
            'AUTOCOMMIT': True,
            'ATOMIC_REQUESTS': False,
            'TIME_ZONE': settings.TIME_ZONE,
            'CONN_MAX_AGE': 600,
            'CONN_HEALTH_CHECKS': False,
        })
        settings.DATABASES['remote_cloud'] = remote_config

        models_data = backup_data.get('models', {})
        deserialized_count = 0

        with transaction.atomic(using='remote_cloud'):
            for model_class in SYNC_MODELS:
                model_key = f"{model_class._meta.app_label}.{model_class._meta.model_name}"
                records = models_data.get(model_key, [])
                if not records:
                    continue

                serialized_str = json.dumps(records)
                for obj in serializers.deserialize('json', serialized_str, using='remote_cloud'):
                    obj.save(using='remote_cloud')
                    deserialized_count += 1

        if deserialized_count > 0:
            logger.info(f"[AUTO-SYNC SUCCESS] {deserialized_count} yozuv Render PostgreSQL-ga avtomatik yuklandi.")

    except Exception as e:
        logger.debug(f"[AUTO-SYNC DEBUG] Background sync check: {e}")


def _auto_sync_loop(interval=30):
    while True:
        try:
            run_sync_task()
        except Exception as e:
            logger.error(f"[AUTO-SYNC ERROR] {e}")
        time.sleep(interval)


_thread_started = False

def start_auto_sync_background(interval=30):
    global _thread_started
    if _thread_started:
        return
    _thread_started = True

    t = threading.Thread(target=_auto_sync_loop, args=(interval,), daemon=True)
    t.start()
