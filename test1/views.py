from os import remove
from io import BytesIO
from threading import Lock 
from os import path
from json import dumps
from django.conf import settings
from django.shortcuts import render
from django.http import HttpResponse, Http404
from openslide import open_slide
from openslide.deepzoom import DeepZoomGenerator
from .models import Test1


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
        s = Test1.objects.get(pk=slide_id)
    except Test1.DoesNotExist:
        raise Http404
    return render(request, 'test1/slide.html', {'Slide': s})


def load_slide(slide_id, slidefile):
    sl = open_slide(slidefile)
    Openslides.insertslide(slide_id, sl)
    

def get_slide(slide_id):
    if slide_id not in Openslides._slides:
        s = Test1.objects.get(pk=slide_id)
        load_slide(s.pk, path.join(settings.HISTOSLIDE_SLIDEROOT, str(s.UrlPath)))
    return Openslides.getslide(slide_id)
    

def get_deepzoom(slide_id):
    if slide_id not in Openslides._slides:
        s = Test1.objects.get(pk=slide_id)
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
    
def download_slide(request, slide_id):
    try:
        s = Test1.objects.get(pk=slide_id)
    except Test1.DoesNotExist:
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
        s = Test1.objects.get(pk=slide_id)
    except Test1.DoesNotExist:
        raise Http404
    return render(request, 'deleteConfirm.html', {'name': s.Name, 'filename': path.basename(str(s.UrlPath)), 'url':request.build_absolute_uri()+'confirm'})

def delete_confirm_slide(request, slide_id):
    if (request.method == 'POST'):
        key = request.POST['key']
        if (key == '~$A=+V_SR3[jsRd<'):
            try:
                s = Test1.objects.get(pk=slide_id)
                file = path.join(settings.HISTOSLIDE_SLIDEROOT, str(s.UrlPath))
                remove(file)
                s.delete()
                return JsonResponse({'status': 'success'})
            except Test1.DoesNotExist:
                raise Http404
        else:
            raise Http404
    else:
        raise Http404



def gmtile(request, slug, level, col, row, slideformat):
    return dztile(request, slug, int(level)+8, col, row, slideformat)

