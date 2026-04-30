import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'education_project.settings')
django.setup()

from django.contrib.auth.models import User
from analytics.models import School, Profile, Threshold

def seed():
    # 1. Create Super Admin
    if not User.objects.filter(username='admin').exists():
        admin = User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
        profile = admin.profile
        profile.role = 'SUPER_ADMIN'
        profile.save()
        print("Super Admin created (admin/admin123)")

    # 2. Create School
    school, created = School.objects.get_or_create(name="St. Julian's Academy", address="123 Education Lane")
    if created:
        Threshold.objects.create(school=school, pass_mark=60.0)
        print("Sample School created")

    # 3. Create DOS
    if not User.objects.filter(username='dos').exists():
        dos = User.objects.create_user('dos', 'dos@example.com', 'dos123')
        profile = dos.profile
        profile.role = 'DOS'
        profile.school = school
        profile.save()
        print("DOS user created (dos/dos123)")

if __name__ == '__main__':
    seed()
