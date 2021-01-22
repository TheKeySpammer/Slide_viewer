# Generated by Django 3.0.8 on 2021-01-17 15:54

from django.db import migrations, models
import frcpathp2surgicalcourse.models


class Migration(migrations.Migration):

    dependencies = [
        ('frcpathp2surgicalcourse', '0002_auto_20210111_1256'),
    ]

    operations = [
        migrations.AlterField(
            model_name='frcpathp2surgicalcourse',
            name='LabelUrlPath',
            field=models.ImageField(default='/mnt/d/projects/slide_app/static/labels/placeholder.png', max_length=500, upload_to=frcpathp2surgicalcourse.models.UploadToPathAndRename('/mnt/d/projects/slide_app/static/labels')),
        ),
        migrations.AlterField(
            model_name='frcpathp2surgicalcourse',
            name='UrlPath',
            field=models.FileField(max_length=500, upload_to='media/uploads/frcpathp2surgicalcourse/'),
        ),
    ]