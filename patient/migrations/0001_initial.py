# Generated by Django 2.2 on 2020-06-23 18:01

from django.db import migrations, models
import django.db.models.deletion
import patient.models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Patient',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('Name', models.CharField(max_length=50)),
                ('ScannedBy', models.CharField(blank=True, max_length=50)),
                ('ScannedDate', models.DateField(blank=True)),
                ('InsertedBy', models.CharField(blank=True, max_length=50)),
                ('InsertedDate', models.DateField(blank=True)),
                ('SlideType', models.IntegerField(choices=[(2, 'openslide')])),
                ('UrlPath', models.FileField(upload_to='media/uploads/patient/')),
                ('LabelUrlPath', models.ImageField(default='/var/www/vhosts/uralensiswebapp.co.uk/slides.uralensiswebapp.co.uk/VirtualCasesApp/static/labels/placeholder.png', upload_to=patient.models.UploadToPathAndRename('/var/www/vhosts/uralensiswebapp.co.uk/slides.uralensiswebapp.co.uk/VirtualCasesApp/static/labels'))),
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
                ('Slide_Id', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='patient.Patient')),
            ],
        ),
    ]
