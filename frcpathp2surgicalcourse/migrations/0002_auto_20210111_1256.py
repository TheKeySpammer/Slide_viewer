# Generated by Django 3.0.8 on 2021-01-11 12:56

from django.db import migrations, models
import frcpathp2surgicalcourse.models


class Migration(migrations.Migration):

    dependencies = [
        ('frcpathp2surgicalcourse', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='frcpathp2surgicalcourse',
            name='Group',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='frcpathp2surgicalcourse',
            name='LabelUrlPath',
            field=models.ImageField(default='/mnt/d/projects/slide_app/static/labels/placeholder.png', upload_to=frcpathp2surgicalcourse.models.UploadToPathAndRename('/mnt/d/projects/slide_app/static/labels')),
        ),
    ]