# Generated by Django 3.0.8 on 2021-01-11 11:49

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Frcpathp2surgicalcourse',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('Name', models.CharField(max_length=50)),
                ('ScannedBy', models.CharField(blank=True, max_length=50)),
                ('ScannedDate', models.DateField(blank=True)),
                ('InsertedBy', models.CharField(blank=True, max_length=50)),
                ('InsertedDate', models.DateField(blank=True)),
                ('SlideType', models.IntegerField(choices=[(2, 'openslide')])),
                ('UrlPath', models.FileField(upload_to='media/uploads/frcpathp2surgicalcourse/')),
            ],
            options={
                'ordering': ['UrlPath'],
            },
        ),
        migrations.CreateModel(
            name='Annotation',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('Json', models.TextField()),
                ('AnnotationText', models.TextField()),
                ('Type', models.CharField(max_length=10)),
                ('Slide_Id', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='frcpathp2surgicalcourse.Frcpathp2surgicalcourse')),
            ],
        ),
    ]
