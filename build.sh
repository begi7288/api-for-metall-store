#!/usr/bin/env bash
# exit on error
set -o errexit

echo "Installing requirements..."
pip install -r requirements.txt

echo "Collecting static files..."
python manage.py collectstatic --no-input

echo "Running migrations..."
python manage.py migrate

echo "Resetting admin password..."
python manage.py shell -c "from django.contrib.auth.models import User; u, _ = User.objects.get_or_create(username='begi'); u.set_password('begibrol7'); u.is_staff=True; u.is_superuser=True; u.save(); print('Superuser begi updated!')"


echo "Build process completed!"
