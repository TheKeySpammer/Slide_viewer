

from django.db import models
from django.conf import settings
import os
from uuid import uuid4
from django.utils.deconstruct import deconstructible

@deconstructible
class UploadToPathAndRename(object):

    def __init__(self, path):
        self.sub_path = path

    def __call__(self, instance, filename):
        ext = filename.split('.')[-1]
        filename = '{}.{}'.format(uuid4().hex, ext)
        # return the whole path to the file
        return os.path.join(self.sub_path, filename)


class Alopecia(models.Model):
    SlideType_choices = ((1, 'DICOM'), (2, 'openslide'))
    Name = models.CharField(max_length=50)
    ScannedBy = models.CharField(max_length=50, blank=True)
    ScannedDate = models.DateField(blank=True)
    InsertedBy = models.CharField(max_length=50, blank=True)
    InsertedDate = models.DateField(blank=True)
    SlideType = models.IntegerField(choices=SlideType_choices)    
    UrlPath = models.FileField(upload_to='media/uploads/alopecia/')
    LabelUrlPath = models.ImageField(upload_to= UploadToPathAndRename(os.path.join(settings.STATICFILES_DIRS[0],'labels')),default=os.path.join(settings.STATICFILES_DIRS[0],'labels','placeholder.png'), max_length=500)
    Group = models.IntegerField(default=0)
    GroupName = models.CharField(max_length=100, default='Alopecia Default Group')
    Annotations = models.BooleanField(default=True)


    class Meta:
        ordering = ['UrlPath']

    def __str__(self):
        return self.Name

        
class Annotation(models.Model):
    Slide_Id = models.ForeignKey(Alopecia, on_delete=models.CASCADE)
    Json = models.TextField()
    AnnotationText = models.TextField()
    Type = models.CharField(max_length=10,blank=False)

    
