# Generated by Django 3.0.8 on 2021-01-18 15:25

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('frcpathp2surgicalcourse', '0007_auto_20210118_1525'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='frcpathp2surgicalcourse',
            name='GroupName',
        ),
    ]
