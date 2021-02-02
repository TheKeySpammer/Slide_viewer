from django.db import models

import os
import errno
import sys
import time
import shutil
import subprocess
from io import open
from subprocess import Popen, PIPE
from django.db import models
from django.db.models.signals import pre_save, post_save, pre_delete
from django.core.signals import request_finished
from django.dispatch import receiver
from django.core import management
from django.conf import settings
from collections import OrderedDict
from django.apps import apps

# Create Virtual Cases File Upload Modal

class TestApp(models.Model):
    test_title = models.CharField(max_length=200)
    test_timestamp = models.DateTimeField('date published')
    
    def __str__(self):
        return self.test_title

def generate_app(self):
    management.call_command('startapp', self)

def generate_app_model(self):
    app_name = self
    class_name = str(app_name).capitalize()
    model_file_code = """

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


class """+class_name+"""(models.Model):
    SlideType_choices = ((1, 'DICOM'), (2, 'openslide'))
    Name = models.CharField(max_length=50)
    ScannedBy = models.CharField(max_length=50, blank=True)
    ScannedDate = models.DateField(blank=True)
    InsertedBy = models.CharField(max_length=50, blank=True)
    InsertedDate = models.DateField(blank=True)
    SlideType = models.IntegerField(choices=SlideType_choices)    
    UrlPath = models.FileField(upload_to='media/uploads/"""+class_name.lower()+"""/')
    LabelUrlPath = models.ImageField(upload_to= UploadToPathAndRename(os.path.join(settings.STATICFILES_DIRS[0],'labels')),default=os.path.join(settings.STATICFILES_DIRS[0],'labels','placeholder.png'), max_length=500)
    Group = models.IntegerField(default=0)
    GroupName = models.CharField(max_length=100, default='"""+class_name+""" Default Group')
    Annotations = models.BooleanField(default=True)


    class Meta:
        ordering = ['UrlPath']

    def __str__(self):
        return self.Name

        
class Annotation(models.Model):
    Slide_Id = models.ForeignKey("""+class_name+""", on_delete=models.CASCADE)
    Json = models.TextField()
    AnnotationText = models.TextField()
    Type = models.CharField(max_length=10,blank=False)

    
"""
    with open(os.path.join(settings.BASE_DIR, app_name + '/models.py'), 'w') as file:
        file.write(model_file_code)
        file.close()

def generate_admin(self):
    app_name = self
    class_name = str(app_name).capitalize()

    admin_file_code_ = """

from os import walk, path
from datetime import date
from django.contrib import admin
from django.conf import settings
from .models import """+class_name+"""
from django.utils.html import format_html
from django.utils.safestring import mark_safe

def default_domain():
    return {'default_domain': settings.DEFAULT_DOMAIN}

#Generate Openslide link
def openslide_file(self):
    slide_id = self.id
    return format_html(
       '<a href="{}" target="_blank">{}</a>',
       ("%s%s" % ('/"""+class_name.lower()+"""/slide/', slide_id)),
       'View Case',
    )
openslide_file.short_description = 'View Cases'

def generate_iframe(self):
    slide_id = self.id
    return format_html('{} <div id="iframe_dialog"><textarea class="iframe_code" readonly rows="4" cols="91">{}</textarea></div>',
        mark_safe('<button type="button" id="open_dialog">View Iframe Code</button>'),
        mark_safe('<body style="margin:0px;padding:0px;overflow:hidden"><iframe src="/"""+class_name.lower()+"""/slide/'+str(slide_id)+'" frameborder="0" style="overflow:hidden;height:100%;width:100%" height="100%" width="100%"></iframe></body>'),
    )

def download_slide(self):
    slide_id = self.id
    return format_html(
       '<a href="{}" target="_blank">{}</a>',
       ("%s%s%s" % ('/"""+class_name.lower()+"""/slide/', slide_id, '/download')),
       'Download Case',
    )
download_slide.short_description = 'Download Case'

def delete_slide(self):
    slide_id = self.id
    return format_html(
       '<a href="{}" target="_blank">{}</a>',
       ("%s%s%s" % ('/"""+class_name.lower()+"""/slide/', slide_id, '/delete')),
       'Delete Case',
    )
delete_slide.short_description = 'Delete Case'

class """+class_name+"""Admin(admin.ModelAdmin):
    actions = ['add_new_slides']
    list_display = ['Name', openslide_file, 'ScannedBy', 'ScannedDate', 'InsertedBy', 'InsertedDate', download_slide, delete_slide]

    def add_new_slides(self, request, queryset):
        # Collect all new slide files in the media dir
        currentuser = request.user.username
        for root, dirs, files in walk(path.join(settings.HISTOSLIDE_SLIDEROOT), followlinks=True):
            for slide_file in files:
                if slide_file.lower().endswith(settings.SLIDEFILE_EXTENSIONS):
                    urlnew = path.join(path.relpath(root, settings.HISTOSLIDE_SLIDEROOT), slide_file)
                    # only include slides that are not in the slide list yet
                    try:
                        slide = """+class_name+""".objects.get(UrlPath=str(urlnew))
                    except """+class_name+""".DoesNotExist:
                        slide = """+class_name+"""(Name=path.splitext(slide_file)[0], ScannedBy=currentuser,
                                      ScannedDate=date.today(), InsertedBy=currentuser, InsertedDate=date.today(),
                                      SlideType=2, UrlPath=str(urlnew))
                        slide.save()

    class Media:
        css = {
            'all': ('admin/css/vendor/jquery-ui.min.css', 'admin/css/vendor/jquery-ui.theme.css', 'admin/css/custom.css')
        }
        js = ('admin/js/jquery-ui.min.js', 'admin/js/custom.js')


admin.site.register("""+class_name+""", """+class_name+"""Admin)

"""

    with open(os.path.join(settings.BASE_DIR, app_name + '/admin.py'), 'w') as file:
        file.write(admin_file_code_)
        file.close()

def generate_view(self):
    app_name = self
    class_name = str(app_name).capitalize()

    view_file_code_ = """

from io import BytesIO
from threading import Lock
from os import path
from os import remove
from json import dumps
from django.conf import settings
from django.shortcuts import render
from django.http import HttpResponse, Http404, JsonResponse
from openslide import open_slide
from openslide import OpenSlide
from openslide.deepzoom import DeepZoomGenerator
from PIL import Image
from .models import """+class_name+""", Annotation
import base64
import re
from virtualcases.dicom_deepzoom import ImageCreator, get_PIL_image
import os
import pydicom

OUTPUT_PATH = os.path.join(settings.BASE_DIR, 'static/dzi/"""+class_name+"""/')
MAX_THUMBNAIL_SIZE = 200, 200

regex = re.compile(
        r'^(?:http|ftp)s?://' # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|' #domain...
        r'localhost|' #localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})' # ...or ip
        r'(?::\d+)?' # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)


class Openslides:
    _slides = {}
    _deepzooms = {}
    _dict_lock = Lock()

    def __init__(self):
        pass
    
    @classmethod
    def insertslide(cls, key, sl):
        opts = {'tile_size': settings.DEEPZOOM_TILE_SIZE, 'overlap': settings.DEEPZOOM_OVERLAP}
        with cls._dict_lock:
            cls._slides[key] = sl
            cls._deepzooms[key] = DeepZoomGenerator(sl, **opts)
            
    @classmethod
    def getslide(cls, key):
        with cls._dict_lock:
            return cls._slides[key]

    @classmethod
    def getdeepzoom(cls, key):
        with cls._dict_lock:
            return cls._deepzooms[key]


def slide(request, slide_id):
    try:
        s = """+class_name+""".objects.get(pk=slide_id)
    except """+class_name+""".DoesNotExist:
        raise Http404
    param = request.GET.get('url')
    back_url = None
    if s.SlideType == 1:
        if not os.path.exists(OUTPUT_PATH):
            os.mkdir(OUTPUT_PATH)
        
        if not os.path.exists(OUTPUT_PATH+''+str(slide_id)+'.dzi'):
            SOURCE = str(s.UrlPath)
            # Create Deep Zoom Image creator with weird parameters
            creator = ImageCreator(
                tile_size=128,
                tile_overlap=2,
                tile_format="jpg",
                image_quality=0.8,
                resize_filter="bicubic",
            )

            # Create Deep Zoom image pyramid from source
            creator.create_dicom(SOURCE, OUTPUT_PATH+''+str(slide_id)+'.dzi')

    if param is not None:
        try:
            param_bytes = param.encode('ascii')
            enc = base64.urlsafe_b64decode(param_bytes)
            back_url = enc.decode('ascii')
        except:
            back_url = None
        
        if back_url is not None:
            if re.match(regex, back_url) is None:
                back_url = None

    return render(request, '"""+class_name.lower()+"""/slide.html', {'Slide': s, 'Label': request.build_absolute_uri('/static/labels/'+path.basename(s.LabelUrlPath.url)), 'back_url': back_url, 'annotations': s.Annotations})


def load_slide(slide_id, slidefile):
    sl = open_slide(slidefile)
    Openslides.insertslide(slide_id, sl)
    

def get_slide(slide_id):
    if slide_id not in Openslides._slides:
        s = """+class_name+""".objects.get(pk=slide_id)
        load_slide(s.pk, path.join(settings.HISTOSLIDE_SLIDEROOT, str(s.UrlPath)))
    return Openslides.getslide(slide_id)
    

def get_deepzoom(slide_id):
    if slide_id not in Openslides._slides:
        s = """+class_name+""".objects.get(pk=slide_id)
        load_slide(s.pk, path.join(settings.HISTOSLIDE_SLIDEROOT, str(s.UrlPath)))
    return Openslides.getdeepzoom(slide_id)


def dzi(request, slug):
    slideformat = settings.DEEPZOOM_FORMAT
    try:
        slug = int(slug)
        resp = HttpResponse(get_deepzoom(slug).get_dzi(slideformat), content_type='application/xml')
        return resp
    except KeyError:
        # Unknown slug
        raise Http404


def properties(request, slug):
    # Get a JSON object with slide properties
    sl = get_slide(int(slug))
    response_data = {'width': sl.dimensions[0], 'height': sl.dimensions[1],
                     'mppx': float(sl.properties.get("openslide.mpp-x", "0.0")),
                     'mppy': float(sl.properties.get("openslide.mpp-y", "0.0")),
                     'vendor': sl.properties.get("openslide.vendor", "")}
    return HttpResponse(dumps(response_data), content_type="application/json")



def dztile(request, slug, level, col, row, slideformat):
    slideformat = slideformat.lower()
    slug = int(slug)
    level = int(level)
    col = int(col)
    row = int(row)
    if slideformat != 'jpeg' and slideformat != 'png':
        # Not supported by Deep Zoom
        raise Http404
    try:
        tile = get_deepzoom(slug).get_tile(level, (col, row))
    except KeyError:
        # Unknown slug
        raise Http404
    except ValueError:
        # Invalid level or coordinates
        raise Http404
    buf = BytesIO()
    tile.save(buf, slideformat, quality=75)
    resp = HttpResponse(buf.getvalue(), content_type='image/%s' % slideformat)
    return resp


def gmtile(request, slug, level, col, row, slideformat):
    return dztile(request, slug, int(level)+8, col, row, slideformat)


def gen_thumbnail_url(request, slide_id):
    try:
        s = """+class_name+""".objects.get(pk=slide_id)
    except """+class_name+""".DoesNotExist:
        raise Http404
    label_name = str(s.LabelUrlPath).split('/')[-1]
    if label_name != 'placeholder.png':
        return JsonResponse( {
        'thumbnail': request.build_absolute_uri(str(s.LabelUrlPath)),
        })
    else:
        if s.SlideType == 1:
            ds = pydicom.dcmread(str(s.UrlPath))
            thumbnail = get_PIL_image(ds)
            response = HttpResponse(content_type='image/png')
            thumbnail.thumbnail(MAX_THUMBNAIL_SIZE)
            filename = str(s.UrlPath).split('/')[-1]
            fWithoutExt = filename.split('.')
            fWithoutExt.pop()
            fWithoutExt = ''.join(fWithoutExt)
            thumbnailName = fWithoutExt+'.thumbnail'
            dirPath = settings.STATICFILES_DIRS[0]+'/images/thumbnail'
            thumbnail.save(dirPath+'/'+thumbnailName, 'JPEG')
            return JsonResponse({
                'thumbnail': request.build_absolute_uri('/static/images/thumbnail/')+thumbnailName,
            })
        else:
            file = path.join(settings.HISTOSLIDE_SLIDEROOT, str(s.UrlPath))
            slide = OpenSlide(file)
            thumbnail = slide.get_thumbnail((800, 600))
            filename = str(s.UrlPath).split('/')[-1]
            fWithoutExt = filename.split('.')
            fWithoutExt.pop()
            fWithoutExt = ''.join(fWithoutExt)
            thumbnailName = fWithoutExt+'.thumbnail'
            dirPath = settings.STATICFILES_DIRS[0]+'/images/thumbnail'
            thumbnail.save(dirPath+'/'+thumbnailName, 'JPEG')
            return JsonResponse({
                'thumbnail': request.build_absolute_uri('/static/images/thumbnail/')+thumbnailName,
            })

def gen_label(request, slide_id):
    try:
        s = """+class_name+""".objects.get(pk=slide_id)
    except """+class_name+""".DoesNotExist:
        raise Http404
    label_name = str(s.LabelUrlPath).split('/')[-1]
    if label_name != 'placeholder.png':
        file_path = str(s.LabelUrlPath)
        if path.exists(file_path):
            with open(file_path, 'rb') as fh:
                response = HttpResponse(fh.read(), content_type="image/*")
                response['Content-Disposition'] = 'inline; filename=' + path.basename(file_path)
                return response
    if s.SlideType == 1:
        ds = pydicom.dcmread(str(s.UrlPath))
        label = get_PIL_image(ds)
        response = HttpResponse(content_type='image/png')
        label.thumbnail(MAX_THUMBNAIL_SIZE)
        label.save(response, "PNG", optimize=True, quality=95)
        response['Content-Disposition'] = 'attachment; filename="label.png"'
        return response
    else:
        file = path.join(settings.HISTOSLIDE_SLIDEROOT, str(s.UrlPath))
        slide = OpenSlide(file)
        if ('label' in slide.associated_images.keys() and slide.associated_images['label'] != None):
            response = HttpResponse(content_type='image/png')
            label = slide.associated_images['label']
            if (label.size[0] < label.size[1]):
                label = label.transpose(Image.ROTATE_270)
            label.save(response, "PNG")
            response['Content-Disposition'] = 'attachment; filename="label.png"'
            return response
        elif (('macro' in slide.associated_images.keys() and slide.associated_images['macro'] != None)):
            response = HttpResponse(content_type='image/png')
            label = slide.associated_images['macro']
            basewidth = 600
            wpercent = (basewidth / float(label.size[0]))
            hsize = int((float(label.size[1]) * float(wpercent)))
            label = label.resize((basewidth, hsize), Image.ANTIALIAS)
            if (label.size[0] > label.size[1]):
                label = label.transpose(Image.ROTATE_270)
            label.save(response, "PNG")
            response['Content-Disposition'] = 'attachment; filename="label.png"'
            return response
        else:
            file_path = settings.STATICFILES_DIRS[0]+'/images/placeholder-image.png'
            if path.exists(file_path):
                with open(file_path, 'rb') as fh:
                    response = HttpResponse(fh.read(), content_type="image/*")
                    response['Content-Disposition'] = 'inline; filename=' + path.basename(file_path)
                    return response
            raise Http404


def get_thumbnail(request, slide_id):
    try:
        s = """+class_name+""".objects.get(pk=slide_id)
    except """+class_name+""".DoesNotExist:
        raise Http404
    label_name = str(s.LabelUrlPath).split('/')[-1]
    if label_name != 'placeholder.png':
        file_path = str(s.LabelUrlPath)
        if path.exists(file_path):
            with open(file_path, 'rb') as fh:
                response = HttpResponse(fh.read(), content_type="image/*")
                response['Content-Disposition'] = 'inline; filename=' + path.basename(file_path)
                return response
    if s.SlideType == 1:
        ds = pydicom.dcmread(str(s.UrlPath))
        label = get_PIL_image(ds)
        response = HttpResponse(content_type='image/png')
        label.thumbnail(MAX_THUMBNAIL_SIZE)
        label.save(response, "PNG", optimize=True, quality=95)
        response['Content-Disposition'] = 'attachment; filename="label.png"'
        return response
    else:
        file = path.join(settings.HISTOSLIDE_SLIDEROOT, str(s.UrlPath))
        slide = OpenSlide(file)
        if (('macro' in slide.associated_images.keys() and slide.associated_images['macro'] != None)):
            response = HttpResponse(content_type='image/png')
            label = slide.associated_images['macro']
            if (label.size[0] > label.size[1]):
                label = label.transpose(Image.ROTATE_270)
            basewidth = 200
            wpercent = (basewidth / float(label.size[0]))
            hsize = int((float(label.size[1]) * float(wpercent)))
            label = label.resize((basewidth, hsize), Image.ANTIALIAS)
            if (label.size[1] > 620):
                label = label.crop((0, 120, label.size[0], label.size[1]))
            
            if (('label' in slide.associated_images.keys() and slide.associated_images['label'] != None)):
                barcode = slide.associated_images['label']
                if (barcode.size[0] < barcode.size[1]):
                    barcode = barcode.transpose(Image.ROTATE_270)
                bw = 200
                wp = (bw / float(barcode.size[0]))
                hs = int((float(barcode.size[1]) * float(wp)))
                barcode = barcode.resize((bw, hs), Image.ANTIALIAS)
                new_image = Image.new('RGB',(200, barcode.size[1] + label.size[1]), (250,250,250))
                new_image.paste(barcode,(0,0))
                new_image.paste(label,(0,barcode.size[1]))
                label = new_image

            label.save(response, "PNG")
            response['Content-Disposition'] = 'attachment; filename="label.png"'
            return response
        else:
            file_path = settings.STATICFILES_DIRS[0]+'/images/placeholder-image.png'
            if path.exists(file_path):
                with open(file_path, 'rb') as fh:
                    response = HttpResponse(fh.read(), content_type="image/*")
                    response['Content-Disposition'] = 'inline; filename=' + path.basename(file_path)
                    return response
            raise Http404

def get_barcode(request, slide_id):
    try:
        s = """+class_name+""".objects.get(pk=slide_id)
    except """+class_name+""".DoesNotExist:
        raise Http404
    if s.SlideType == 1:
        ds = pydicom.dcmread(str(s.UrlPath))
        label = get_PIL_image(ds)
        response = HttpResponse(content_type='image/png')
        label.thumbnail(MAX_THUMBNAIL_SIZE)
        label.save(response, "PNG")
        response['Content-Disposition'] = 'attachment; filename="label.png"'
        return response
    else:
        file = path.join(settings.HISTOSLIDE_SLIDEROOT, str(s.UrlPath))
        slide = OpenSlide(file) 
        if ('label' in slide.associated_images.keys() and slide.associated_images['label'] != None):
            response = HttpResponse(content_type='image/png')
            label = slide.associated_images['label']
            if (label.size[0] < label.size[1]):
                label = label.transpose(Image.ROTATE_270)
            basewidth = 200
            wpercent = (basewidth / float(label.size[0]))
            hsize = int((float(label.size[1]) * float(wpercent)))
            label = label.resize((basewidth, hsize), Image.ANTIALIAS)
            label.save(response, "PNG")
            response['Content-Disposition'] = 'attachment; filename="barcode.png"'
            return response
        elif (('macro' in slide.associated_images.keys() and slide.associated_images['macro'] != None)):
            response = HttpResponse(content_type='image/png')
            label = slide.associated_images['macro']
            if (label.size[0] > label.size[1]):
                label = label.transpose(Image.ROTATE_270)
            basewidth = 200
            wpercent = (basewidth / float(label.size[0]))
            hsize = int((float(label.size[1]) * float(wpercent)))
            label = label.resize((basewidth, hsize), Image.ANTIALIAS)
            label = label.crop((0, 0, 200, 200))
            label.save(response, "PNG")
            response['Content-Disposition'] = 'attachment; filename="barcode.png"'
            return response
        else:
            file_path = settings.STATICFILES_DIRS[0]+'/images/placeholder-image.png'
            if path.exists(file_path):
                with open(file_path, 'rb') as fh:
                    response = HttpResponse(fh.read(), content_type="image/*")
                    response['Content-Disposition'] = 'inline; filename=' + path.basename(file_path)
                    return response
            raise Http404



def get_group_list(request, slide_id):
    try:
        s = """+class_name+""".objects.get(pk=slide_id)
    except """+class_name+""".DoesNotExist:
        raise Http404
    groupId = s.Group
    listSlide = """+class_name+""".objects.filter(Group=groupId).order_by('Name')
    
    return JsonResponse({
        'status': 'success',
        'slides': [{'id': l.id, 'name': l.Name} for l in listSlide],
    })

def get_property(request, slide_id):
    try:
        s = """+class_name+""".objects.get(pk=slide_id)
    except """+class_name+""".DoesNotExist:
        raise Http404

    if s.SlideType == 2:
        file = path.join(settings.HISTOSLIDE_SLIDEROOT, str(s.UrlPath))
        slide = OpenSlide(file)
        return JsonResponse({
            'status': 'success',
            'data': dict(slide.properties)
        })
    else:
        return JsonResponse({
            'status': 'success',
            'data': dict()
        })


    
def get_name(request, slide_id):
    try:
        s = """+class_name+""".objects.get(pk=slide_id)
    except """+class_name+""".DoesNotExist:
        raise Http404
    return JsonResponse({
        'status': 'success',
        'name': s.Name
    })


def download_slide(request, slide_id):
    try:
        s = """+class_name+""".objects.get(pk=slide_id)
    except """+class_name+""".DoesNotExist:
        raise Http404
    file_path = path.join(settings.HISTOSLIDE_SLIDEROOT, str(s.UrlPath))
    if path.exists(file_path):
        with open(file_path, 'rb') as fh:
            response = HttpResponse(fh.read(), content_type="application/octet-stream")
            response['Content-Disposition'] = 'inline; filename=' + path.basename(file_path)
            return response
    raise Http404


def delete_slide(request, slide_id):
    try:
        s = """+class_name+""".objects.get(pk=slide_id)
    except """+class_name+""".DoesNotExist:
        raise Http404
    return render(request, 'deleteConfirm.html', {'name': s.Name, 'filename': path.basename(str(s.UrlPath)), 'url':request.build_absolute_uri()+'confirm'})

def delete_confirm_slide(request, slide_id):
    if (request.method == 'POST'):
        key = request.POST['key']
        if (key == '~$A=+V_SR3[jsRd<'):
            try:
                s = """+class_name+""".objects.get(pk=slide_id)
                file = path.join(settings.HISTOSLIDE_SLIDEROOT, str(s.UrlPath))
                remove(file)
                s.delete()
                return JsonResponse({'status': 'success'})
            except """+class_name+""".DoesNotExist:
                raise Http404
        else:
            raise Http404
    else:
        raise Http404

def add_annotation(request):
    if (request.method == "POST"):
        data = request.POST
        slide = """+class_name+""".objects.get(
            pk=int(data['slideId']))
        annotation = Annotation(
            Slide_Id=slide, Json=data['Json'], AnnotationText=data['text'], Type=data['type'])
        
        annotation.save()
        return JsonResponse({'id': annotation.id})


def delete_annotation(request, id):
    if (request.method == "POST"):
        toBeDeleted = Annotation.objects.get(pk=(int(id)))
        
        toBeDeleted.delete()
        return JsonResponse({'success': True})


def edit_annotation(request, id):
    if (request.method == "POST"):
        annotation = Annotation.objects.get(pk=(int(id)))
        data = request.POST
        try:
            annotation.Json = data['json']
        except(KeyError):
            pass
        try:
            annotation.AnnotationText = data['text']
        except(KeyError):
            pass
        annotation.save()
        
        return JsonResponse({'success': True})


def get_annotation(request, slide_id):
    if (request.method == "GET"):
        annotations = Annotation.objects.filter(Slide_Id=slide_id)
        
        return JsonResponse({'annotations': [{'id': annotation.id, 'json': annotation.Json, 'text': annotation.AnnotationText, 'type': annotation.Type} for annotation in annotations]})

"""
    
    with open(os.path.join(settings.BASE_DIR, app_name + '/views.py'), 'w') as file:
        file.write(view_file_code_)
        file.close()

def generate_urls(self):
    app_name = self

    url_file_code_ = """


from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^slide/(?P<slide_id>\d+)/$', views.slide),
    url(r'^slide/(?P<slide_id>\d+)/thumbnail/$', views.gen_thumbnail_url),
    url(r'^slide/(?P<slide_id>\d+)/fullthumbnail/$', views.get_thumbnail),
    url(r'^slide/(?P<slide_id>\d+)/barcode/$', views.get_barcode),
    url(r'^slide/(?P<slide_id>\d+)/label/$', views.gen_label),
    url(r'^slide/(?P<slide_id>\d+)/download/$', views.download_slide),
    url(r'^slide/(?P<slide_id>\d+)/delete/$', views.delete_slide),
    url(r'^slide/(?P<slide_id>\d+)/delete/confirm/$', views.delete_confirm_slide),
    url(r'^slide/(?P<slide_id>\d+)/group/$', views.get_group_list),
    url(r'^slide/(?P<slide_id>\d+)/property/$', views.get_property),
    url(r'^slide/(?P<slide_id>\d+)/name/$', views.get_name),
    url(r'^(?P<slug>\d+).dzi$', views.dzi),
    url(r'^(?P<slug>\d+).dzi.json$', views.properties),
    url(r'^(?P<slug>\d+)_files/(?P<level>\d+)/(?P<col>\d+)_(?P<row>\d+)\.(?P<slideformat>jpeg|png)$', views.dztile),
    url(r'^(?P<slug>\d+)_map/(?P<level>\d+)/(?P<col>\d+)_(?P<row>\d+)\.(?P<slideformat>jpeg|png)$', views.gmtile),
    url(r'^annotation/add$', views.add_annotation),
    url(r'^annotation/edit/(?P<id>\d+)$', views.edit_annotation),
    url(r'^annotation/delete/(?P<id>\d+)$', views.delete_annotation),
    url(r'^annotation/(?P<slide_id>\d+)$', views.get_annotation),
]

"""
    with open(os.path.join(settings.BASE_DIR, app_name + '/urls.py'), 'w') as file:
        file.write(url_file_code_)
        file.close()


def generate_html(self):
    app_name = self
    class_name = str(app_name).capitalize()
    app_url = 'http://'+settings.ALLOWED_HOSTS[0]
    os.makedirs(os.path.join(settings.BASE_DIR, app_name + '/templates/'+app_name), exist_ok=True)
    html_file_code_ =  """
<!DOCTYPE html>
<html lang="en">

<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="icon" href="/static/favicon.ico" type="image/gif" sizes="16x16">
    <title>"""+class_name+"""</title>

    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bulma@0.8.0/css/bulma.min.css">
    <link rel="stylesheet" href="/static/stylesheets/roundslider.min.css">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@simonwep/pickr/dist/themes/nano.min.css" />
    <link rel="stylesheet" type="text/css" href="/static/stylesheets/slick.css"/>
    <link rel="stylesheet" type="text/css" href="/static/stylesheets/slick-theme.css"/>
    <link rel="stylesheet" type="text/css" href="/static/stylesheets/bulma-slider.min.css"/>
    <link rel="stylesheet" href="/static/stylesheets/style.css">
    


    <script src="https://code.jquery.com/jquery-3.4.1.min.js"
        integrity="sha256-CSXorXvZcTkaix6Yvo6HppcZGetbYMGWSFlBw8HfCJo=" crossorigin="anonymous"></script>



    <script src="/static/javascripts/openseadragon.min.js"></script>
    <script src="/static/javascripts/openseadragon-scalebar.js"></script>


    <script src="/static/javascripts/canvas-toBlob.js"></script>
    <script src="/static/javascripts/FileSaver.js"></script>
    <script defer src="/static/javascripts/fontawesome.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/@simonwep/pickr/dist/pickr.min.js"></script>
    <script src="/static/javascripts/roundslider.min.js"></script>
    <script src="/static/javascripts/html2canvas.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/camanjs/4.1.2/caman.full.min.js"></script>
    <script src="/static/javascripts/canvas2image.js"></script>
    <script src="/static/javascripts/paper-full.js"></script>
    <script src="/static/javascripts/openseadragon-paperjs-overlay.js"></script>
    <script src="/static/javascripts/openseadragon-filtering.js"></script>
    <script src="/static/javascripts/jquery.fullscreen.js"></script>
    <script src="/static/javascripts/bulma-slider.js"></script>
    <script type="text/javascript" src="//cdn.jsdelivr.net/npm/slick-carousel@1.8.1/slick/slick.min.js"></script>
    {% if Slide.SlideType == 1 %}
    <script>
        const image = "/static/dzi/"""+class_name+"""/{{Slide.pk}}.dzi";
        const slideId = '{{Slide.pk}}';
    </script>
    {% endif %}
    {% if Slide.SlideType == 2 %}
    <script>
        const image = "/"""+class_name.lower()+"""/{{Slide.pk}}.dzi";
        const slideId = '{{Slide.pk}}';
    </script>
    {% endif %}
    <script src="/static/javascripts/app.js"></script>
</head>

<body>
    <div id="page">
        
        <nav class="navbar" role="navigation" aria-label="main navigation">
            <div class="navbar-brand">
                <a class="navbar-item" href="https://pathhub.uk/">
                    <img id="pathub-logo" width="100" height="53" src="/static/images/logo.png">
                </a>
            </div>

            <div id="viewer-navbar" class="navbar-menu">
                <div class="navbar-start">
                    <div class="navbar-item">
                        <button id="home-btn" title="Fit to Screen" class="button is-rounded"> <i
                                class="fas fa-home"></i> </button>
                    </div>

                    <div class="separator"></div>

                    <div class="navbar-item">
                        <button id="zoomin-btn" title="Zoom in" class="button is-rounded"> <i
                                class="fas fa-search-plus"></i> </button>
                    </div>

                    <div class="navbar-item">
                        <button id="zoomout-btn" title="Zoom out" class="button is-rounded"> <i
                                class="fas fa-search-minus"></i> </button>
                    </div>

                    <div class="navbar-item">
                        <div id="zoom-value-container">
                            <div class="columns">
                                <div class="column is-1" id="zoom-value-icon-container">
                                    <i class="fas fa-search fa-sm"></i>
                                </div>
                                <div class="column">
                                    <div id="zoom-value-display">
                                        50x
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div class="separator"></div>

                    <div class="navbar-item zoom-button-container">
                        <button value="2" title="Zoom in 2x" class="button zoom-button"
                            style="border-top: none; background: url(/static/images/2x.png); "></button>
                    </div>

                    <div class="navbar-item zoom-button-container">
                        <button value="5" title="Zoom in 5x" class="button zoom-button"
                            style="border-top: none; background: url(/static/images/5x.png); "></button>
                    </div>

                    <div class="navbar-item zoom-button-container">
                        <button value="10" title="Zoom in 10x" class="button zoom-button"
                            style="border-top: none; background: url(/static/images/10x.png); "></button>
                    </div>

                    <div class="navbar-item zoom-button-container">
                        <button value="20" title="Zoom in 20x" class="button zoom-button"
                            style="border-top: none; background: url(/static/images/20x.png); "></button>
                    </div>

                    <div class="navbar-item zoom-button-container">
                        <button value="40" title="Zoom in 40x" class="button zoom-button"
                            style="border-top: none; background: url(/static/images/40x.png); "></button>
                    </div>

                    <div class="separator"></div>

                    <div id="rotation-selector-dropdown" class="navbar-item has-dropdown">
                        <button id="rotation-dropdown-button" title="Rotate" class="button is-rounded"> <i
                                class="fas fa-sync"></i> </button>
                        <div class="navbar-dropdown">
                            <div class="navbar-item">
                                <div id="rotation-selector" class="rotation-selector-class"></div>
                            </div>
                        </div>
                    </div>
                    <div class="navbar-item rotate-preset-container">
                        <button id="btn-rotate-preset-1" title="Rotate to 0" value="0" class="button is-rounded">
                            <strong>0&#176;</strong></button>
                    </div>

                    <div class="navbar-item rotate-preset-container">
                        <button id="btn-rotate-preset-2" title="Rotate to 90" value="90" class="button is-rounded">
                            <strong> 90&#176; </strong></button>
                    </div>

                    <div class="navbar-item rotate-preset-container">
                        <button id="btn-rotate-preset-3" title="Rotate to 180" value="180" class="button is-rounded">
                            <strong> 180&#176; </strong></button>
                    </div>

                    <div class="separator"></div>

                    <div class="navbar-item">
                        <button id="screenshot-btn" title="Take Screenshot" class="button is-rounded"> <i
                                class="fas fa-camera"></i> </button>
                    </div>
                    {% if annotations %} 
                    <div id="draw-menu-dropdown" class="navbar-item has-dropdown">
                        <button id="draw-button" title="Annotations Menu" class="button is-rounded"> <i
                                class="fas fa-pen"></i> </button>
                        <div class="navbar-dropdown">
                            <div class="navbar-item">
                                <div id="draw-menu">
                                    <label class="label">Select Tool</label>
                                    <div class="columns" id="select-tool-container">
                                        
                                        <div class="column" style="padding-left: 2px;">
                                            <button id="rect-button" title="Rectangle Annotation"
                                                class="button is-rounded">
                                                <svg width="25" height="25">
                                                    <rect width="25" height="25"
                                                        style="stroke-width: 4; fill: rgb(255, 255, 255); stroke: rgb(0, 0, 0)">
                                                    </rect>
                                                </svg>
                                            </button>
                                        </div>
                                        <div class="column">
                                            <button id="circle-button" title="Circle Annotation"
                                                class="button is-rounded"> <span class="circle-annotation"></span> </button>
                                        </div>
                                        
                                        <div class="column">
                                            <button id="circle-button-20" title="Circle Annotation"
                                                class="button is-rounded"> <span class="circle-annotation" style="text-align: center; font-size: 0.7rem; padding-top: 3px;">20x</span> </button>
                                        </div>
                                        <div class="column">
                                            <button id="circle-button-40" title="Circle Annotation"
                                                class="button is-rounded"> <span class="circle-annotation" style="text-align: center; font-size: 0.7rem; padding-top: 3px;">40x</span> </button>
                                        </div>
                                    </div>
                                    <div class="horizontal-divider"></div>
                                    <div class="columns" id="select-tool-settings">
                                        <div class="column is-4">
                                            <label class="label light-label">Size</label>
                                            <input id="stroke-width-input" value="4" type="number"
                                                class="input is-rounded" width="30px" min="1" max="12">

                                        </div>
                                        <div class="column">
                                            <label class="label light-label">Color</label>
                                            <div id="annotation-border-picker" class="color-picker"></div>
                                        </div>
                                        <div class="column">
                                            <div id="color-palette-container">
                                                <div class="columns">
                                                    <div class="column"> <div class="color-palette" title="Black" style="background-color: black;" ></div> </div>
                                                    <div class="column"> <div class="color-palette" title="White" style="background-color: white; border: 1px solid black;" ></div> </div>
                                                    <div class="column"> <div class="color-palette" title="Gray" style="background-color: gray;" ></div> </div>
                                                    <div class="column"> <div class="color-palette" title="Pink" style="background-color: pink;" ></div> </div>
                                                    <div class="column"> <div class="color-palette" title="Violet" style="background-color: violet;" ></div> </div>
                                                </div>
                                                <div class="columns">
                                                    <div class="column"> <div class="color-palette" title="Red" style="background-color: red;" ></div> </div>
                                                    <div class="column"> <div class="color-palette" title="Orange" style="background-color: orange;" ></div> </div>
                                                    <div class="column"> <div class="color-palette" title="Yellow" style="background-color: yellow;" ></div> </div>
                                                    <div class="column"> <div class="color-palette" title="Green" style="background-color: green;" ></div> </div>
                                                    <div class="column"> <div class="color-palette" title="Blue" style="background-color: blue;" ></div> </div>
                                                </div>
                                                <div class="columns">
                                                    <div class="column"> <div class="color-palette" title="Purple" style="background-color: purple;" ></div> </div>
                                                    <div class="column"> <div class="color-palette" title="Brown" style="background-color: brown;" ></div> </div>
                                                    <div class="column"> <div class="color-palette" title="Magenta" style="background-color: magenta;" ></div> </div>
                                                    <div class="column"> <div class="color-palette" title="Tan" style="background-color: tan;" ></div> </div>
                                                    <div class="column"> <div class="color-palette" title="Cyan" style="background-color: cyan;" ></div> </div>
                                                </div>
                                                <div class="columns">
                                                    <div class="column"> <div class="color-palette" title="Olive" style="background-color: olive;" ></div> </div>
                                                    <div class="column"> <div class="color-palette" title="Maroon" style="background-color: maroon;" ></div> </div>
                                                    <div class="column"> <div class="color-palette" title="Navy" style="background-color: navy;" ></div> </div>
                                                    <div class="column"> <div class="color-palette" title="Aquamarine" style="background-color: aquamarine;" ></div> </div>
                                                    <div class="column"> <div class="color-palette" title="Turquoise" style="background-color: turquoise;" ></div> </div>
                                                </div>
                                            </div>
                                        </div>
                                    </div>

                                </div>
                            </div>
                        </div>
                    </div>
                    <div class="navbar-item">
                        <button id="line-button" title="Measure Tool" class="button is-rounded" style="background: url('/static/images/measurement-button.png') center no-repeat">
                            
                        </button>
                    </div>
                    {% endif %}

                    <div class="navbar-item">
                        <button id="annotation-hide-button" title="Hide Annotation" class="button is-rounded"> <i
                                class="far fa-eye"></i> </button>
                    </div>
                    
                    <div class="navbar-item">
                        <button id="navigator-hide-button" title="Hide Navigator" class="button is-rounded"><i class="far fa-compass fa-lg"></i></button>
                    </div>
                    
                    <div class="navbar-item">
                        <button id="stats-button" title="Show Stats" class="button is-rounded" style="background: url('/static/images/stats-button.png') center no-repeat"></button>
                    </div>
                    <div class="navbar-item">
                        <button id="fullscreen-btn" title="full-screen" class="button is-rounded"> <i
                                class="fas fa-expand-arrows-alt"></i> </button>
                    </div>
                    <div id="open-slide-dropdown" class="navbar-item has-dropdown ">
                        <button id="open-slide-button" title="Open Slide" class="button is-rounded"> <i
                                class="fas fa-folder-open"></i> </button>
                        <div class="navbar-dropdown">
                            <div class="navbar-item">
                                <div>
                                    <label class="label">Sync View</label>
                                    <div class="slot-container">
                                        <label>Slot 1</label>
                                        <div id="slot-1" class="slot is-selected"></div>
                                    </div>

                                    <div class="slot-container">
                                        <label>Slot 2</label>
                                        <div class="is-flex" style="align-items: center;">
                                            <div id="slot-2" class="slot text-light">Add Slide</div>
                                            <a id="slot-delete-2" class="delete slot-delete"></a>
                                        </div>

                                    </div>

                                    <div class="slot-container">
                                        <label>Slot 3</label>
                                        <div class="is-flex" style="align-items: center;">
                                            <div id="slot-3" class="slot text-light">Add Slide</div>
                                            <a id="slot-delete-3" class="delete slot-delete"></a>
                                        </div>
                                    </div>

                                    <div class="slot-container">
                                        <label>Slot 4</label>
                                        <div class="is-flex" style="align-items: center;">
                                            <div id="slot-4" class="slot text-light">Add Slide</div>
                                            <a id="slot-delete-4" class="delete slot-delete"></a>
                                        </div>
                                    </div>

                                </div>
                            </div>
                        </div>
                    </div>

                    <div class="navbar-item">
                        <button id="sync-lock-button" title="Lock Sync" class="button is-rounded"> <i
                                class="fas fa-lock-open"></i> </button>
                    </div>

                    <div class="navbar-item">
                        <button id="filter-button" title="Filter" class="button is-rounded"> <i
                                class="fas fa-palette"></i> </button>
                    </div>
                </div>
                {% if back_url is not None %}
                <div class="navbar-end">
                    <a href="{{back_url}}" class="navbar-item">
                        <strong>Back</strong>
                    </a>
                </div>
                {% endif %}
                

            </div>
        </nav>

        <div id="viewer-container" style="width: 100%; height: 80%;">

        </div>
        
        <div id="slide-tray-container">
            <div id="slide-tray-with-buttons">
                <div id="slide-tray-button-container">
                    <button class="slide-tray-button" id="slide-tray-large-button"></button>
                    <button class="slide-tray-button" id="slide-tray-med-button"></button>
                    <button class="slide-tray-button" id="slide-tray-small-button"></button>
                    <button id="slide-tray-hide-button"><i class="fas fa-caret-down fa-lg"></i></button>
                    <button id="slide-tray-show-button"><i class="fas fa-caret-up fa-lg"></i></button>
                </div>
                <div id="slide-tray">
                    
                </div>
            </div>
        </div>


        <div class="modal" id="annotation-modal">
            <div class="modal-background"></div>
            <div class="modal-card">
                <header class="modal-card-head">
                    <p class="modal-card-title" id="annotation-modal-title">Annotation Setting</p>
                    <button class="delete annotation-modal-close" arai-label="close"></button>
                </header>
                <section class="modal-card-body">
                    <div class="container">
                        <label for="annotation-text" class="label">Annotation Text</label>
                        <textarea name="annotation-text" id="annotation-text" cols="15" rows="5"
                            class="textarea"></textarea>
                    </div>
                </section>
                <footer class="modal-card-foot">
                    <button class="button is-success" id="annotation-save-btn">Save</button>
                    <button class="button annotation-modal-close">Cancel</button>
                </footer>
            </div>
        </div>


        <div class="modal" id="open-slide-modal">
            <div class="modal-background"></div>
            <div class="modal-card">
                <header class="modal-card-head">
                    <p class="modal-card-title" id="open-slide-title">Select Slide</p>
                    <button class="delete annotation-modal-close" arai-label="close"></button>
                </header>
                <section class="modal-card-body">
                    <div class="container" id='slide-selector-container'>

                    </div>
                </section>

            </div>
        </div>

        
        <div class="modal" id="new-slide-modal">
            <div class="modal-background"></div>
            <div class="modal-card">
                <header class="modal-card-head">
                    <p class="modal-card-title" id="new-slide-title">Open Slide In</p>
                    <button class="delete new-slide-modal-close" arai-label="close"></button>
                </header>
                <section class="modal-card-body">
                    <div class="columns">
                        <!-- <div class="column"> <button onclick="" id="open-new-slide-new-button" class="button is-info">New Window</button></div>
                        <div class="column"> <button onclick="" id="open-new-slide-same-button" class="button is-info">Same Window</button></div>
                        <div class="column"> <button onclick="" id="open-new-slide-parallel-button" class="button is-info">Parallel View</button> </div> -->
                        <div class="column">
                            <div class="open-slide-button-container" id="open-new-slide-new-button">
                                <img src="/static/images/new_window.png" alt="" srcset="">
                                <label for="">New Window</label>
                            </div>
                        </div>
                        <div class="column">
                            <div class="open-slide-button-container" id="open-new-slide-same-button">
                                <img src="/static/images/same_window.png" alt="" srcset="">
                                <label for="">Same Window</label>
                            </div>
                        </div>
                        <div class="column">
                            <div class="open-slide-button-container" id="open-new-slide-parallel-button">
                                <img src="/static/images/parallel_view.png" alt="" srcset="">
                                <label for="">Parallel View</label>
                            </div>
                        </div>
                    </div>
                </section>

            </div>
        </div>


        
        <div class="modal" id="stats-modal">
            <div class="modal-background"></div>
            <div class="modal-card">
                <header class="modal-card-head">
                    <p class="modal-card-title" id="stats-title">Slide Properties</p>
                    <button class="delete stats-modal-close" arai-label="close"></button>
                </header>
                <section class="modal-card-body">
                    <h4 class="title is-5">Optical Parameters</h4>
                    <div class="columns">
                        <div class="column is-6">
                            <p>Property</p>
                            <p>Property</p>
                            <p>Property</p>
                            <p>Property</p>
                            <p>Property</p>
                        </div>
                        <div class="column is-4">
                            <p>Value</p>
                            <p>Value</p>
                            <p>Value</p>
                            <p>Value</p>
                            <p>Value</p>
                        </div>
                    </div>
                    <h4 class="title is-5" >Scan Information</h4>
                    <div class="columns">
                        <div class="column is-6">
                            <p>Property</p>
                            <p>Property</p>
                            <p>Property</p>
                        </div>
                        <div class="column is-4">
                            <p>Value</p>
                            <p>Value</p>
                            <p>Value</p>
                        </div>
                    </div>
                    <h4 class="title is-5" >Image parameters</h4>
                    <div class="columns">
                        <div class="column is-6">
                            <p>Property</p>
                            <p>Property</p>
                        </div>
                        <div class="column is-4">
                            <p>Value</p>
                            <p>Value</p>
                        </div>
                    </div>
                    <h4 class="title is-5" >Optical Parameters</h4>
                    <div class="columns">
                        <div class="column is-6">
                            <p>Property</p>
                        </div>
                        <div class="column is-4">
                            <p>Value</p>
                        </div>
                    </div>
                </section>

            </div>
        </div>

        <div class="draggle-menu" style="display: none;">
            <div class="draggle-menu-header has-text-centered">
                <span><strong>Filters</strong></span>
                <button class="delete" aria-label="close"></button>
            </div>
            <div class="draggle-menu-body">
                <p> <strong>Brightness</strong></p>
                <div class="columns">
                    <div class="column" style="padding-right: 0px">
                        <input id="brightness-slider" class="slider has-output is-fullwidth" min="-150" max="150" value="0" step="5" type="range">
                        <output for="brightness-slider">0</output>
                    </div>
                    <div class="column is-2" style="padding: 5px;">
                        <button class="undo-button-brightness button is-rounded" style="padding: 0;">
                            <i class="fas fa-undo fa-sm"></i>
                        </button>
                    </div>
                </div>
                <p><strong>Colors</strong></p>
                <p>Red</p>
                <div class="columns" style="margin-bottom: 0px;">
                    <div class="column" style="padding-right: 0px; padding-bottom: 0; padding-top: 5px;">
                        <input id="red-slider" class="slider is-danger has-output is-fullwidth" min="0" max="100" value="0" step="5" type="range">
                        <output for="red-slider">0</output>
                    </div>
                    <div style="padding: 0; padding-left: 5px;" class="column is-2">
                        <button class="undo-button-red button is-rounded" style="padding: 0;">
                            <i class="fas fa-undo fa-sm"></i>
                        </button>
                    </div>
                </div>
                <p>Green</p>
                <div class="columns" style="margin-bottom: 0px;">
                    <div class="column" style="padding-right: 0px; padding-bottom: 0; padding-top: 5px;">
                        <input id="green-slider" class="slider is-success has-output is-fullwidth" min="0" max="100" value="0" step="5" type="range">
                        <output for="green-slider">0</output>
                    </div>
                    <div style="padding: 0; padding-left: 5px;" class="column is-2">
                        <button class="undo-button-green button is-rounded" style="padding: 0;">
                            <i class="fas fa-undo fa-sm"></i>
                        </button>
                    </div>
                </div>
                <p>Blue</p>
                <div class="columns" style="margin-bottom: 0px;">
                    <div class="column" style="padding-right: 0px; padding-bottom: 0; padding-top: 5px;">
                        <input id="blue-slider" class="slider is-link has-output is-fullwidth" min="0" max="100" value="0" step="5" type="range">
                        <output for="blue-slider">0</output>
                    </div>
                    <div style="padding: 0; padding-left: 5px;" class="column is-2">
                        <button class="undo-button-blue button is-rounded" style="padding: 0;">
                            <i class="fas fa-undo fa-sm"></i>
                        </button>
                    </div>
                </div>
                <p>Strength</p>
                <div class="columns" style="margin-bottom: 0px;">
                    <div class="column" style="padding-right: 0px; padding-bottom: 0; padding-top: 5px;">
                        <input id="strength-slider" class="slider has-output is-fullwidth" min="0" max="100" value="0" step="5" type="range">
                        <output for="strength-slider">0</output>
                    </div>
                    <div style="padding: 0; padding-left: 5px;" class="column is-2">
                        <button class="undo-button-strength button is-rounded" style="padding: 0;">
                            <i class="fas fa-undo fa-sm"></i>
                        </button>
                    </div>
                </div>
            </div>
        </div>

        <div id="loading-modal" class="modal">
            <div class="modal-background"></div>
            <div class="modal-content">
                <p class="image">
                    <img style="width: 67px; height: 67px;" src="/static/images/loading.gif" alt="Loading...">
                </p>
            </div>
            <button class="modal-close is-large" aria-label="close"></button>
        </div>

        <div class="modal" id="delete-confirm">
            <div class="modal-background"></div>
            <div class="modal-content">
                <div class="card">
                    <div class="card-content">
                        <p class="is-size-5">
                            Delete Annotation?
                        </p>
                    </div>
                    <footer class="card-footer">
                        <p class="card-footer-item">
                            <button id="delete-button" class="button is-danger">Delete</button>
                        </p>
                        <p class="card-footer-item">
                            <button id="cancel-button" class="button">Cancel</button>
                        </p>
                    </footer>
                </div>
            </div>
            <button class="modal-close is-large" aria-label="close"></button>
        </div>
    </div>
</body>

</html>
"""
    with open(os.path.join(settings.BASE_DIR, app_name + '/templates/'+app_name+'/slide.html'), 'w', encoding="utf-8") as file:
        file.write(html_file_code_)
        file.close()


def generate_settings(self):
    app_name = self

    final_name = app_name+'.apps.'+str(app_name).capitalize()+'Config'
    with open(os.path.join(settings.BASE_DIR, 'virtualcases/settings_local.py'), 'w') as file:

        from .models import TestApp

        list_db_apps = TestApp.objects.values_list('test_title', flat = True)
        print(list_db_apps);
        list_db_apps_array = list(list_db_apps)
        installed_apps = "ADDITIONAL_APPS = " + str(list_db_apps_array).strip().replace(" ", "").lower()

        file.writelines(installed_apps)
   


def generate_app_urls(self):
    app_name = self

    with open(os.path.join(settings.BASE_DIR, 'virtualcases/urls.py'), 'r') as file:
        app_url_file = file.readlines()

    new_app_url = """url(r'^"""+app_name+"""/', include('"""+app_name+""".urls'))"""
    new_app_conf = """from """+app_name+""" import urls"""
    new_url_settings = []
    for line in app_url_file:

        if "#Add Custom APP URL Entry" in line:
            new_url_settings.append("%s\n" % new_app_conf)

        if "path('admin/', admin.site.urls)," in line:
            new_url_settings.append(line.replace("path('admin/', admin.site.urls),", "path('admin/', admin.site.urls),\n\t%s," % new_app_url))
        else:
            new_url_settings.append(line)

    with open(os.path.join(settings.BASE_DIR, 'virtualcases/urls.py'), 'w') as file:
        file.write("".join(new_url_settings))
        file.close()

        
def create_makemigrations(self):
    app_name = self
    # my_env = os.environ.copy()
    # my_env["PATH"] = "/usr/sbin:/sbin:" + my_env["PATH"]
    # management.call_command('makemigrations')
    # subprocess.Popen(["python", "manage.py", "makemigrations", app_name], env=my_env)
    
    # settings.INSTALLED_APPS += (app_name,)
    # apps.app_configs = OrderedDict()
    # apps.apps_ready = apps.models_ready = apps.loading = apps.ready = False
    # apps.clear_cache()
    # apps.populate(settings.INSTALLED_APPS)
    

def create_migration(self):
    app_name = self
    my_env = os.environ.copy()
    my_env["PATH"] = "/usr/sbin:/sbin:" + my_env["PATH"]
    subprocess.Popen(["touch", "virtualcases/wsgi.py"], env=my_env)
    subprocess.Popen(["python", "manage.py", "migrate", app_name], env=my_env)

@receiver(pre_delete, sender=TestApp)
def delete_app(sender, **kwargs):
    the_instance = kwargs['instance']
    app_name = ''.join(the_instance.test_title.lower().split())
    try:
        local_setting_file_delete_ = open(os.path.join(settings.BASE_DIR, 'virtualcases/settings_local.py'), 'r+')
    except IOError:
        print("An error was found. Either path is incorrect or file doesn't exist!")
    finally:
        from .models import TestApp
        
        list_db_apps = TestApp.objects.values_list('test_title', flat = True)
        list_db_apps_array = list(list_db_apps)
        list_str_lower = [list_str.strip().replace(" ", "").lower() for list_str in list_db_apps_array]
        
        ##Call Revert Migration Function
        revert_migration(app_name)
        revert_project_urls(app_name)
        revert_project_urls_import(app_name)
        #################################
        
        list_str_lower.remove(str(app_name))

        local_setting_file_delete_.truncate(0)
        installed_apps = "ADDITIONAL_APPS = " + str(list_str_lower).strip().replace(" ", "").lower()
        local_setting_file_delete_.writelines(installed_apps)
        local_setting_file_delete_.close()


        my_env = os.environ.copy()
        my_env["PATH"] = "/usr/sbin:/sbin:" + my_env["PATH"]
        subprocess.Popen(["touch", "virtualcases/wsgi.py"], env=my_env)


    mydir = os.path.join(settings.BASE_DIR, app_name)
    print(mydir)
    try:
        shutil.rmtree(mydir)
        
    except OSError as e:
        print ("Error: %s - %s." % (e.filename, e.strerror))
    print(app_name)

def revert_migration(self):
    app_name = self
    subprocess.call(['python', 'manage.py', 'migrate', app_name, 'zero'])

def revert_project_urls(self):
    app_name = self
    with open(os.path.join(settings.BASE_DIR, 'virtualcases/urls.py'), 'r') as file:
        url_settings = file.readlines()

    new_app_url = """url(r'^"""+app_name+"""/', include('"""+app_name+""".urls')),"""
    new_url_settings = []
    for line in url_settings:
        if new_app_url in line:
            new_url_settings.append(line.replace(new_app_url, ""))
        else:
            new_url_settings.append(line)

    with open(os.path.join(settings.BASE_DIR, 'virtualcases/urls.py'), 'w') as file:
        file.write("".join(new_url_settings))
        file.close()


def revert_project_urls_import(self):
    app_name = self
    with open(os.path.join(settings.BASE_DIR, 'virtualcases/urls.py'), 'r') as file:
        url_settings = file.readlines()

    new_app_conf = """from """+app_name+""" import urls"""
    new_url_settings = []
    for line in url_settings:
        if new_app_conf in line:
            new_url_settings.append(line.replace(new_app_conf, "\n"))
        else:
            new_url_settings.append(line)

    with open(os.path.join(settings.BASE_DIR, 'virtualcases/urls.py'), 'w') as file:
        file.write("".join(new_url_settings))
        file.close()


def model_created(sender, **kwargs):
    the_instance = kwargs['instance']
    app_name = ''.join(the_instance.test_title.lower().split())
    if kwargs['created']:
        generate_app(app_name)
        generate_app_model(app_name)
        generate_admin(app_name)
        generate_view(app_name)
        generate_urls(app_name)
        generate_html(app_name)
        generate_settings(app_name)
        generate_app_urls(app_name)
        # create_makemigrations(app_name)
        create_migration(app_name)
        # create_openslide_wsgi_file(app_name)
        # create_openslide_vhost_file(app_name)
    else:

        print(the_instance)
        print('Hello World on Update')
post_save.connect(model_created, sender=TestApp)

def create_openslide_wsgi_file(self):
    app_name = self
    try:
        wsgi_file_ = open('/var/www/djangoapp.test/public_html/slides/'+app_name+'.wsgi',"w+")
    except IOError:
        print("An error was found. Either path is incorrect or file doesn't exist!")
    finally:
        line1 = "import os, sys\n"
        line2 = "sys.path.append('/var/www/djangoapp.test.co.uk/public_html/slides')\n"
        line3 = "from deepzoom_multiserver import app as application\n"
        line4 = "application.config.update({\n"
        line5 = "\t'SLIDE_DIR': '/var/www/djangoapp.test/public_html/cases/media/uploads/"+app_name+"\n"
        line6 = "})"
        wsgi_file_.writelines([line1, line2, line3, line4, line5, line6])
        wsgi_file_.close()

def create_openslide_vhost_file(self):
    app_name = self
    virtualhost="""
    <VirtualHost *:80>
        ServerAdmin serversupport@oxbridgemedica.com
        DocumentRoot 
        ServerName 
        ErrorLog logs/
        CustomLog logs/
    </VirtualHost>"""

    f = open('/etc/apache2/sites-available/test.vhost.conf', 'w+')
    f.write(virtualhost)
    f.close()
    # try:
    #     f = open('/etc/apache2/sites-available/slides.djangoapp.test.conf', 'a')
    #     f.write(virtualhost)
    #     f.close()
    #     # vhost_file_ = open('/etc/apache2/sites-available/slides.djangoapp.test.conf',"r+")
    # except IOError:
    #     print("An error was found. Either path is incorrect or file doesn't exist!")
    # finally:
    #     f.write(virtualhost)
    #     f.close()
    #     exit()
    exit()
