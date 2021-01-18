
from django.db import models

class Jclinpathtest(models.Model):
    SlideType_choices = (
        (2, 'openslide'),)
    Name = models.CharField(max_length=50)
    ScannedBy = models.CharField(max_length=50, blank=True)
    ScannedDate = models.DateField(blank=True)
    InsertedBy = models.CharField(max_length=50, blank=True)
    InsertedDate = models.DateField(blank=True)
    SlideType = models.IntegerField(choices=SlideType_choices)    
    UrlPath = models.FileField(upload_to='media/uploads/jclinpathtest/')

    class Meta:
        ordering = ['UrlPath']

    def __str__(self):
        return self.Name
        
class Annotation(models.Model):
    Slide_Id = models.ForeignKey(Jclinpathtest, on_delete=models.CASCADE)
    Json = models.TextField()
    AnnotationText = models.TextField()
    Type = models.CharField(max_length=10,blank=False)