from django.db import models
# Create Virtual Cases File Upload Modal

class CaseFile(models.Model):

    case_title = models.CharField(max_length=200)
    case_file = models.FileField(upload_to='uploads/cases/')
    case_timestamp = models.DateTimeField('date published')

    def __str__(self):
        return self.case_title