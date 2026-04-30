from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

class School(models.Model):
    name = models.CharField(max_length=255)
    address = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class Profile(models.Model):
    ROLE_CHOICES = [
        ('SUPER_ADMIN', 'Super Admin'),
        ('DOS', 'Director of Study'),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='DOS')
    school = models.ForeignKey(School, on_delete=models.SET_NULL, null=True, blank=True)
    is_first_login = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.user.username} - {self.role}"

class Threshold(models.Model):
    school = models.OneToOneField(School, on_delete=models.CASCADE)
    pass_mark = models.FloatField(default=50.0)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.school.name} Threshold: {self.pass_mark}"

class Student(models.Model):
    name = models.CharField(max_length=255)
    school = models.ForeignKey(School, on_delete=models.CASCADE)
    
    # Numeric Features
    hours_studied = models.IntegerField(default=20)
    attendance = models.IntegerField(default=90)
    sleep_hours = models.IntegerField(default=7)
    previous_scores = models.IntegerField(default=70)
    tutoring_sessions = models.IntegerField(default=0)
    physical_activity = models.IntegerField(default=3)
    
    # Categorical/Ordinal
    parental_involvement = models.CharField(max_length=20, default='Medium')
    access_to_resources = models.CharField(max_length=20, default='Medium')
    extracurricular_activities = models.CharField(max_length=3, default='No')
    motivation_level = models.CharField(max_length=20, default='Medium')
    internet_access = models.CharField(max_length=3, default='Yes')
    family_income = models.CharField(max_length=20, default='Medium')
    teacher_quality = models.CharField(max_length=20, default='Medium')
    school_type = models.CharField(max_length=20, default='Public')
    peer_influence = models.CharField(max_length=20, default='Neutral')
    learning_disabilities = models.CharField(max_length=3, default='No')
    parental_education_level = models.CharField(max_length=30, default='College')
    distance_from_home = models.CharField(max_length=20, default='Near')
    gender = models.CharField(max_length=10, default='Male')

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.school.name})"

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()
