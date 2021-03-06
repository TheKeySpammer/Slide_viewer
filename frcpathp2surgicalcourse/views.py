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
from .models import Frcpathp2surgicalcourse, Annotation, Activity
import base64
import re
from virtualcases.dicom_deepzoom import ImageCreator, get_PIL_image
from virtualcases.openslide_deepzoom import save_dzi
import os
import pydicom
import psutil
import datetime
import shutil

OUTPUT_PATH = os.path.join(settings.BASE_DIR, 'static/dzi/Frcpathp2surgicalcourse/')
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


def _get_free_space():
    free_space = psutil.disk_usage('/').free
    free_space = free_space / (1024*1024*1024)
    return free_space

def _get_free_ram():
    return psutil.virtual_memory().percent

def _optimize_disk_space(slide_id=None):
    # Get current disk space
    free_space = _get_free_space()
    # If free spce is less than 20GB try to free up space by deleting 10 least used cached dzi files
    if free_space < 20:
        acs = Activity.objects.all().filter(Saved=True).order_by('LastAccessed')
        delete_count = 10
        if len(acs) < 5:
            return
        if len(acs) < 10:
            delete_count = 5
        if len(acs) < 15:
            delete_count = 8
        
        for i in range(delete_count):
            ac = acs[i]
            sd = ac.Slide_Id
            ac.Saved = False
            ac.save()
            if sd == slide_id:
                continue
            dzi_file = os.path.join(OUTPUT_PATH, str(sd)+'.dzi')
            dzi_folder = os.path.join(OUTPUT_PATH, str(sd)+'_files')
            if os.path.exists(dzi_folder):
                shutil.rmtree(dzi_folder, ignore_errors=True)
            if os.path.exists(dzi_file):
                os.remove(dzi_file)
            

def loading_slide(request, slide_id):
    pass

def slide(request, slide_id):
    # Check if slide exists
    try:
        s = Frcpathp2surgicalcourse.objects.get(pk=slide_id)
    except Frcpathp2surgicalcourse.DoesNotExist:
        raise Http404
    # Check if slide exists as a dzi file, if yes then serve and update activity
    # DZI FILE PATH
    dzi_file = os.path.join(OUTPUT_PATH, str(slide_id)+'.dzi')
    if (os.path.exists(dzi_file)):
        # Updating activity
        try:
            ac = Activity.objects.get(Slide_Id=s.id)
            ac.Saved = True
            ac.LastAccessed = datetime.datetime.utcnow()
            ac.save()
        except Activity.DoesNotExist:
            ac = Activity(Slide_Id=s, Saved=True, LastAccessed=datetime.datetime.utcnow())
            ac.save()

        param = request.GET.get('url')
        back_url = None
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
        return render(request, 'frcpathp2surgicalcourse/slide.html', {'Slide': s, 'Label': request.build_absolute_uri('/static/labels/'+path.basename(s.LabelUrlPath.url)), 'back_url': back_url, 'annotations': s.Annotations, 'cached': True})

    # If slide does not exists, if slide type == 1, save
    # Optimize disk space
    _optimize_disk_space(slide_id)

    # Load Back URL
    param = request.GET.get('url')
    back_url = None
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

    
    # If slide type is 1 then create dzi
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

    # Check if slide dzi is available
    dzi_file = os.path.join(OUTPUT_PATH, str(slide_id)+'.dzi')
    if not os.path.exists(dzi_file):
        # check available disk space
        if _get_free_space() < 12:
            # check avilable RAM
            if _get_free_ram() < 87:
                return render(request, 'frcpathp2surgicalcourse/slide.html', {'Slide': s, 'Label': request.build_absolute_uri('/static/labels/'+path.basename(s.LabelUrlPath.url)), 'back_url': back_url, 'annotations': s.Annotations, 'cached': False})
            else:
                return render(request, 'server_busy.html')
        else:
            # save file as dzi
            save_dzi(os.path.join(settings.HISTOSLIDE_SLIDEROOT, str(s.UrlPath)), OUTPUT_PATH, str(slide_id))
    return render(request, 'frcpathp2surgicalcourse/slide.html', {'Slide': s, 'Label': request.build_absolute_uri('/static/labels/'+path.basename(s.LabelUrlPath.url)), 'back_url': back_url, 'annotations': s.Annotations, 'cached': True})
    
    


def load_slide(slide_id, slidefile):
    sl = open_slide(slidefile)
    Openslides.insertslide(slide_id, sl)
    

def get_slide(slide_id):
    if slide_id not in Openslides._slides:
        s = Frcpathp2surgicalcourse.objects.get(pk=slide_id)
        load_slide(s.pk, path.join(settings.HISTOSLIDE_SLIDEROOT, str(s.UrlPath)))
    return Openslides.getslide(slide_id)
    

def get_deepzoom(slide_id):
    if slide_id not in Openslides._slides:
        s = Frcpathp2surgicalcourse.objects.get(pk=slide_id)
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
        s = Frcpathp2surgicalcourse.objects.get(pk=slide_id)
    except Frcpathp2surgicalcourse.DoesNotExist:
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
        s = Frcpathp2surgicalcourse.objects.get(pk=slide_id)
    except Frcpathp2surgicalcourse.DoesNotExist:
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
        s = Frcpathp2surgicalcourse.objects.get(pk=slide_id)
    except Frcpathp2surgicalcourse.DoesNotExist:
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
        s = Frcpathp2surgicalcourse.objects.get(pk=slide_id)
    except Frcpathp2surgicalcourse.DoesNotExist:
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
        s = Frcpathp2surgicalcourse.objects.get(pk=slide_id)
    except Frcpathp2surgicalcourse.DoesNotExist:
        raise Http404
    groupId = s.Group
    listSlide = Frcpathp2surgicalcourse.objects.filter(Group=groupId).order_by('Name')
    
    return JsonResponse({
        'status': 'success',
        'slides': [{'id': l.id, 'name': l.Name} for l in listSlide],
    })

def get_property(request, slide_id):
    try:
        s = Frcpathp2surgicalcourse.objects.get(pk=slide_id)
    except Frcpathp2surgicalcourse.DoesNotExist:
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
        s = Frcpathp2surgicalcourse.objects.get(pk=slide_id)
    except Frcpathp2surgicalcourse.DoesNotExist:
        raise Http404
    return JsonResponse({
        'status': 'success',
        'name': s.Name
    })


def download_slide(request, slide_id):
    try:
        s = Frcpathp2surgicalcourse.objects.get(pk=slide_id)
    except Frcpathp2surgicalcourse.DoesNotExist:
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
        s = Frcpathp2surgicalcourse.objects.get(pk=slide_id)
    except Frcpathp2surgicalcourse.DoesNotExist:
        raise Http404
    return render(request, 'deleteConfirm.html', {'name': s.Name, 'filename': path.basename(str(s.UrlPath)), 'url':request.build_absolute_uri()+'confirm'})

def delete_confirm_slide(request, slide_id):
    if (request.method == 'POST'):
        key = request.POST['key']
        if (key == '~$A=+V_SR3[jsRd<'):
            try:
                s = Frcpathp2surgicalcourse.objects.get(pk=slide_id)
                file = path.join(settings.HISTOSLIDE_SLIDEROOT, str(s.UrlPath))
                remove(file)
                s.delete()
                return JsonResponse({'status': 'success'})
            except Frcpathp2surgicalcourse.DoesNotExist:
                raise Http404
        else:
            raise Http404
    else:
        raise Http404

def add_annotation(request):
    if (request.method == "POST"):
        data = request.POST
        slide = Frcpathp2surgicalcourse.objects.get(
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
