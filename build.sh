#!/usr/bin/env bash
# exit on error
set -o errexit

echo "Installing requirements..."
pip install -r requirements.txt

echo "Collecting static files..."
python manage.py collectstatic --no-input

echo "Running migrations..."
python manage.py migrate

echo "Promoting admin user..."
python manage.py shell -c "from django.contrib.auth.models import User; u = User.objects.filter(username='998909998877').first(); (setattr(u, 'is_staff', True), setattr(u, 'is_superuser', True), u.save()) if u else print('User not found')"

echo "Build process completed!"

