import os
from django.apps import AppConfig


class UserConfig(AppConfig):
    name = 'user'

    def ready(self):
        # Prevent starting thread twice during Django dev server auto-reload
        if os.environ.get('RUN_MAIN') == 'true' or os.environ.get('SERVER_GATEWAY_INTERFACE'):
            from user.auto_sync_background import start_auto_sync_background
            start_auto_sync_background(interval=30)

