# Generated by Django 3.0.2 on 2020-02-09 18:13

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Liverpooldermpathcourse2020',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('Name', models.CharField(max_length=50)),
                ('ScannedBy', models.CharField(blank=True, max_length=50)),
                ('ScannedDate', models.DateField(blank=True)),
                ('InsertedBy', models.CharField(blank=True, max_length=50)),
                ('InsertedDate', models.DateField(blank=True)),
                ('SlideType', models.IntegerField(choices=[(2, 'openslide')])),
                ('UrlPath', models.FileField(upload_to='media/uploads/liverpooldermpathcourse2020/')),
            ],
            options={
                'ordering': ['UrlPath'],
            },
        ),
    ]
