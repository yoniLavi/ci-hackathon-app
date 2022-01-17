# Generated by Django 3.1.13 on 2022-01-13 13:50

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('hackathon', '0045_hackprojectscorecategory_is_active'),
    ]

    operations = [
        migrations.AlterField(
            model_name='hackteam',
            name='participants',
            field=models.ManyToManyField(related_name='participated_hackteams', to=settings.AUTH_USER_MODEL),
        ),
    ]
