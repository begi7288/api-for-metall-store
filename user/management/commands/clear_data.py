from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.apps import apps

class Command(BaseCommand):
    help = "Clears all database records except superusers and basic setup data (Tarif)."

    def handle(self, *args, **options):
        self.stdout.write("Starting database clean up...")

        # 1. Delete non-superuser django Users (and related Xodim records via cascade)
        deleted_users, _ = User.objects.filter(is_superuser=False).delete()
        self.stdout.write(f"Deleted {deleted_users} non-superuser accounts.")

        # 2. Models to exclude from deletion
        exclude_models = [
            'User', 'Permission', 'ContentType', 'Session', 'Migration',
            'Tarif'
        ]

        for model in apps.get_models():
            model_name = model.__name__
            if model_name in exclude_models:
                continue
            
            try:
                count, _ = model.objects.all().delete()
                if count > 0:
                    self.stdout.write(f"Deleted {count} records from model: {model_name}.")
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"Could not delete {model_name}: {str(e)}"))

        self.stdout.write(self.style.SUCCESS("Database cleanup complete! (Admins preserved)"))
