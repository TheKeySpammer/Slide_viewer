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

class """+class_name+"""(models.Model):
    SlideType_choices = (
        (2, 'openslide'),)
    Name = models.CharField(max_length=50)
    ScannedBy = models.CharField(max_length=50, blank=True)
    ScannedDate = models.DateField(blank=True)
    InsertedBy = models.CharField(max_length=50, blank=True)
    InsertedDate = models.DateField(blank=True)
    SlideType = models.IntegerField(choices=SlideType_choices)    
    UrlPath = models.FileField(upload_to='media/uploads/"""+app_name+"""/')

    class Meta:
        ordering = ['UrlPath']

    def __str__(self):
        return self.Name
        
class Annotation(models.Model):
    Slide_Id = models.ForeignKey("""+class_name+""", on_delete=models.CASCADE)
    Json = models.TextField()
    AnnotationText = models.TextField()
    Type = models.CharField(max_length=10,blank=False)"""
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
       ("%s%s" % (settings.DEFAULT_DOMAIN+ '/"""+app_name+"""/slide/', slide_id)),
       'View Case',
    )
openslide_file.short_description = 'View Cases'

def generate_iframe(self):
    slide_id = self.id
    return format_html('{} <div id="iframe_dialog"><textarea class="iframe_code" readonly rows="4" cols="91">{}</textarea></div>',
        mark_safe('<button type="button" id="open_dialog">View Iframe Code</button>'),
        mark_safe('<body style="margin:0px;padding:0px;overflow:hidden"><iframe src="'+settings.DEFAULT_DOMAIN+'/"""+app_name+"""/slide/'+str(slide_id)+'" frameborder="0" style="overflow:hidden;height:100%;width:100%" height="100%" width="100%"></iframe></body>'),
    )
generate_iframe.short_description = 'Code'

class """+class_name+"""Admin(admin.ModelAdmin):
    actions = ['add_new_slides']
    list_display = ['Name', openslide_file, 'ScannedBy', 'ScannedDate', 'InsertedBy', 'InsertedDate', generate_iframe]

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


admin.site.register("""+class_name+""", """+class_name+"""Admin)"""
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
from json import dumps
from django.conf import settings
from django.shortcuts import render
from django.http import HttpResponse, Http404, JsonResponse
from openslide import open_slide
from openslide.deepzoom import DeepZoomGenerator
from .models import """+class_name+""", Annotation


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
    return render(request, '"""+app_name+"""/slide.html', {'Slide': s})


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

def add_annotation(request):
    if (request.method == "POST"):
        data = request.POST
        slide = """+class_name+""".objects.get(
            pk=int(data['slideId']))
        annotation = Annotation(
            Slide_Id=slide, Json=data['Json'], AnnotationText=data['text'], Type=data['type'])
        print(annotation)
        annotation.save()
        return JsonResponse({'id': annotation.id})


def delete_annotation(request, id):
    if (request.method == "POST"):
        toBeDeleted = Annotation.objects.get(pk=(int(id)))
        print(toBeDeleted)
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
        print(annotation)
        return JsonResponse({'success': True})


def get_annotation(request, slide_id):
    if (request.method == "GET"):
        annotations = Annotation.objects.filter(Slide_Id=slide_id)
        print(annotations)
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
    url(r'^(?P<slug>\d+).dzi$', views.dzi),
    url(r'^(?P<slug>\d+).dzi.json$', views.properties),
    url(r'^(?P<slug>\d+)_files/(?P<level>\d+)/(?P<col>\d+)_(?P<row>\d+)\.(?P<slideformat>jpeg|png)$', views.dztile),
    url(r'^(?P<slug>\d+)_map/(?P<level>\d+)/(?P<col>\d+)_(?P<row>\d+)\.(?P<slideformat>jpeg|png)$', views.gmtile),
    url(r'^annotation/add$', views.add_annotation),
    url(r'^annotation/edit/(?P<id>\d+)$', views.edit_annotation),
    url(r'^annotation/delete/(?P<id>\d+)$', views.delete_annotation),
    url(r'^annotation/(?P<slide_id>\d+)$', views.get_annotation),
]"""
    with open(os.path.join(settings.BASE_DIR, app_name + '/urls.py'), 'w') as file:
        file.write(url_file_code_)
        file.close()


def generate_html(self):
    app_name = self
    app_url = 'http://'+settings.ALLOWED_HOSTS[0]
    os.makedirs(os.path.join(settings.BASE_DIR, app_name + '/templates/'+app_name), exist_ok=True)
    html_file_code_ =  """
<!DOCTYPE html>
<html lang="en">

<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>"""+app_name.capitalize()+"""</title>

    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bulma@0.8.0/css/bulma.min.css">
    <link rel="stylesheet" href="/static/stylesheets/roundslider.min.css">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@simonwep/pickr/dist/themes/nano.min.css" />
    <style>
        html,
        body {
            height: 100%;
            padding: 0px;
            margin: 0px;
            overflow-x: hidden;
            overflow-y: hidden;
        }

        #page {
            width: 100%;
            height: 100%;
        }

        #openseadragon-viewer {
            width: 100%;
        }

        #delete-confirm>.modal-content {
            width: 300px;

        }


        .card {
            width: 150px;
        }

        #openseadragon-viewer>.card>.card-content {
            padding: 0;
            padding-top: 15px;
            padding-right: 10px;
        }

        .measurement {
            font-size: 0.8rem;
        }

        .annotation-text {
            line-height: 1.1rem;
        }

        .pcr-button {
            box-shadow: 2px 6px 6px #ccc;
        }

        .cursor-move {
            cursor: move;
        }

        .navbar {
            padding-left: 30px;
            padding-right: 30px;
            box-shadow: 0px 3px 15px rgba(200, 200, 200, 0.5);
            height: 50px;
        }

        .button.is-rounded {
            border: none;
            padding-left: 0.71rem;
            padding-right: 0.71rem;
        }

        .button:focus {
            border-color: rgba(0, 0, 0, 0);
            color: none;
        }

        .orange-button {
            background-color: #f68a42;
            color: white !important;
        }

        .red-button {
            background-color: red;
            color: white !important;
        }

        .yellow-button {
            background-color: hsl(48, 100%, 67%);
        }

        .green-button {
            background-color: green;
            color: white !important;
        }

        .blue-button {
            background-color: blue;
            color: white !important;
        }

        .zoom-button {
            height: 35px;
            padding: 0 15px;
            border-radius: 25px;
            border: none;
        }

        #rotation-dropdown-button {
            margin-top: auto;
            margin-bottom: auto;
        }

        #rotation-selector .rs-range-color {
            background-color: #33B5E5;
        }

        #rotation-selector .rs-path-color {
            background-color: #C2E9F7;
        }

        #rotation-selector .rs-handle {
            background-color: #33B5E5;
            padding: 7px;
            border: 2px solid #33B5E5;
        }

        #rotation-selector .rs-handle.rs-focus {
            border-color: #33B5E5;
        }

        #rotation-selector .rs-handle:after {
            border-color: #33B5E5;
            background-color: #33B5E5;
        }

        #rotation-selector .rs-border {
            border-color: transparent;
        }

        #rotation-selector-dropdown>.navbar-dropdown {
            padding: 0 25px;
            padding-bottom: 25px;
            background-color: rgba(0, 0, 0, 0);
            box-shadow: none;
            margin-left: -45px;
        }

        #draw-button {
            margin-top: auto;
            margin-bottom: auto;
        }


        #draw-menu-dropdown {
            padding-left: 0.45rem;
            padding-right: 0.45rem;
        }

        #draw-menu-dropdown>.navbar-dropdown {
            margin-left: -50px;
        }

        #rotation-selector-dropdown {
            padding-right: 0.45rem;
        }


        #rotation-selector-dropdown>.navbar-dropdown>.navbar-item {
            padding: 0;
        }

        #btn-rotate-preset-1-container {
            padding-left: 0;
        }

        .navbar-brand {
            margin-right: 20px;
            margin-left: 20px;
        }

        .navbar-brand>a.navbar-item {
            padding: 0;
        }

        .navbar-item img {
            max-height: 100px;
        }

        #zoomin-btn:active,
        #zoomout-btn:active {
            background-color: hsl(141, 53%, 53%);
            color: white;
        }


        .navbar-item {
            padding-left: 0.45rem;
            padding-right: 0.45rem;
        }


        .toolbar-heading {
            padding: 8px 8px;
            background-color: #1f2833;
            color: white;
            border: 2px solid #17954caa;
            text-align: center;
            border-radius: 20%;
            margin: 0px 10px;
        }


        .separator {
            width: 1px;
            height: 100%;
            background-color: #aaa;
            margin: 0px 10px;
        }

        #annotation-modal>.modal-background {
            opacity: 0.2;
        }

        #annotation-modal>.modal-card {
            width: 20vw;
        }


        #loading-modal>.modal-content>.image {
            padding: 10px;
        }

        #loading-modal>.modal-content>.image>img {
            margin: auto;
        }

        #border-example {
            width: 100%;
            height: 4px;
            background-color: black;
            margin-top: 15px;
        }

        #hamburger {
            display: none;
            width: 90px;
            height: 40px;
            border: none;
            box-shadow: none;
        }

        #hamburger:active {
            background-color: #aacfcf;
        }

        .fa-bars {
            font-size: 25px;
        }

        .card-control {
            float: right;
            margin-top: 5px;
            margin-right: 5px;
            border-radius: 100%;
            width: 20px;
            height: 20px;
            border: none;
        }

        .edit-button {
            background-color: #ffdd57;
        }

        .delete-button {
            background-color: #fa4a5f;
        }

        @media screen and (max-width: 1160px) {
            .separator {
                margin: 0px 0px;
            }

            .toolbar-container {
                margin-left: 0;
            }
        }

        @media screen and (max-width: 1024px) {
            .navbar-menu {
                display: block;
            }

            .navbar-menu {
                width: 200px;
                margin-left: -25px;
            }

            #rotation-selector {
                margin-left: 20px;
            }

            #rotation-dropdown-button {
                display: none;
            }

            .rotate-preset-container {
                display: none;
            }

            #draw-button {
                display: none;
            }

            #draw-menu-dropdown>.navbar-dropdown {
                margin-left: -20px;
            }

            .navbar-end {
                display: none;
            }
        }

        @media screen and (max-width: 1024px) and (max-height: 900px) {
            .zoom-button-container {
                display: none;
            }
        }

        @media screen and (max-width: 1200px) {
            #annotation-modal>.modal-card {
                width: 250px;
            }
        }



        @media (max-height: 600px) {
            #toolbar {
                height: 8%;
            }

            #openseadragon-viewer {
                height: 92%;
            }
        }
    </style>


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
    <script src="/static/javascripts/canvas2image.js"></script>
    <script src="/static/javascripts/paper-full.js"></script>
    <script src="/static/javascripts/openseadragon-paperjs-overlay.js"></script>

    <script>
        $(document).ready(function () {

            // Tooltip Variable Settings
            OpenSeadragon.setString('Tooltips.SelectionToggle', 'Selection Demo');
            OpenSeadragon.setString('Tooltips.SelectionConfirm', 'Ok');
            OpenSeadragon.setString('Tooltips.SelectionCancel', 'Cancel');
            OpenSeadragon.setString('Tooltips.ImageTools', 'Image tools');
            OpenSeadragon.setString('Tool.brightness', 'Brightness');
            OpenSeadragon.setString('Tool.contrast', 'Contrast');
            OpenSeadragon.setString('Tool.reset', 'Reset');
            OpenSeadragon.setString('Tooltips.HorizontalGuide', 'Add Horizontal Guide');
            OpenSeadragon.setString('Tooltips.VerticalGuide', 'Add Vertical Guide');
            OpenSeadragon.setString('Tool.rotate', 'Rotate');
            OpenSeadragon.setString('Tool.close', 'Close');

            // Set viewer height
            var navbarHeight = $(".navbar").height();
            var pageHeight = $("#page").height();
            $("#openseadragon-viewer").height(pageHeight - navbarHeight);

            var image = "/"""+app_name+"""/{{ Slide.pk }}.dzi";

            paper.install(window);



            // Variable declarations
            var ppm = 1000000;
            var viewer_is_new;
            var bm_center;
            var bm_zoom;
            var bm_goto;
            var rotator; // Stores the Rotation slider data
            var annotation_border_picker; // Stores the Overlay Border color data
            var default_border_color = "red";
            var editMode = false;
            var currentEditingOverlay = null;
            var paperOverlay;
            var viewerOpen = false;
            var stroke_color = default_border_color;
            var stroke_width = 4;
            var selectingColor = false;
            var viewZoom;
            var rotating = false;
            var showingAnnotation = true;
            var hitTest = null;
            var csrftoken = $("[name=csrfmiddlewaretoken]").val();

            function csrfSafeMethod(method) {
                // these HTTP methods do not require CSRF protection
                return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
            }
            $.ajaxSetup({
                beforeSend: function (xhr, settings) {
                    if (!csrfSafeMethod(settings.type) && !this.crossDomain) {
                        xhr.setRequestHeader("X-CSRFToken", csrftoken);
                    }
                }
            });

            /*
            0 - Drawing Mode off
            1 - Line Mode
            2 - Rect Mode
            3 - Circle Mode
            */
            var drawMode = 0;
            var startPoint = null;
            var currentLine = null;
            var lines = [];

            var lineDB = [];

            var currentRect = null;
            var rects = [];

            var currentCircle = null;
            var circles = [];
            var lastOverlay;

            // Initialization of Openseadragon viewer
            var viewer = OpenSeadragon({
                id: "openseadragon-viewer",
                prefixUrl: "/static/images/",
                showNavigator: true,
                animationTime: 0.5,
                blendTime: 0.1,
                constrainDuringPan: false,
                maxZoomPixelRatio: 2,
                minPixelRatio: 0.5,
                //   minZoomLevel: 0.653,
                visibilityRatio: 1,
                zoomPerScroll: 2,
                crossOriginPolicy: "Anonymous",

                zoomInButton: "zoomin-btn",
                zoomOutButton: "zoomout-btn",
                homeButton: "home-btn",

            });

            viewer.open(image);

            // Viewer Event handlers

            viewer.addHandler("open", function () {
                viewer.source.minLevel = 8;
                /* Start zoomed in, then return to home position after
                loading.  Workaround for blurry viewport on initial
                load (OpenSeadragon #95). */
                var center = new OpenSeadragon.Point(0.5,
                    1 / (2 * viewer.source.aspectRatio));
                viewer.viewport.zoomTo(2, center, true);
                viewer_is_new = true;

                setTimeout(function () {
                    $("#home-btn").addClass("is-info");
                    viewer.viewport.minZoomLevel = viewer.viewport.getHomeZoom();
                    viewerOpen = true;
                    stroke_width = stroke_width / paper.view.zoom;
                    viewZoom = paper.view.zoom;
                    loadAnnotations();
                }, 500);

                viewer.drawer.viewer = viewer;
            });

            viewer.addHandler("update-viewport", function () {
                if (viewer_is_new) {
                    setTimeout(function () {
                        if (viewer.viewport) {
                            viewer.viewport.goHome(false);
                        }
                    }, 5);
                    viewer_is_new = false;
                }
                lines.forEach(function (line) {
                    updateLineCardDivText(line.text, line.line.firstSegment.point, line.line.lastSegment.point);
                });
                rects.forEach(function (rect) {
                    updateRectCardDivText(rect.text, rect.rect.strokeBounds.topLeft, rect.rect.strokeBounds.topRight, rect.rect.strokeBounds.bottomRight);
                });
                circles.forEach(function (circle) {
                    updateCircleCardDivText(circle.text, circle.circle.position.add(new Point(0, circle.circle.radius + circle.circle.strokeWidth)), circle.circle.radius);
                });
            });

            viewer.addHandler("home", function () {
                if (bm_goto) {
                    setTimeout(function () {
                        if (viewer.viewport) {
                            viewer.viewport.zoomTo(bm_zoom, bm_center, false);
                        }
                    }, 200);
                    bm_goto = false;
                }
                rotator.setValue(0);
                updateRotation(0);
                resetZoomButtons();
                fixRotatorTooltip();
            });


            viewer.addHandler("zoom", function (event) {

                if (!viewerOpen) return;
                var z = event.zoom;
                var homeZoom = viewer.viewport.getHomeZoom();
                if (z.toFixed(2) == homeZoom.toFixed(2) && viewer.viewport.getRotation() == 0) {
                    $("#home-btn").addClass("is-info");
                    $("#btn-rotate-preset-1").removeClass("is-info");
                } else {
                    $("#home-btn").removeClass("is-info");
                }

                $(".zoom-button").get().forEach(function (btn) {
                    switch (parseInt(btn.value)) {
                        case 2:
                            if (z == 2) {
                                $(btn).addClass("orange-button");
                            } else {
                                $(btn).removeClass("orange-button");
                            }
                            break;

                        case 5:
                            if (z == 5) {
                                $(btn).addClass("red-button");
                            } else {
                                $(btn).removeClass("red-button");
                            }
                            break;

                        case 10:
                            if (z == 10) {
                                $(btn).addClass("yellow-button");
                            } else {
                                $(btn).removeClass("yellow-button");
                            }
                            break;

                        case 20:
                            if (z == 20) {
                                $(btn).addClass("green-button");
                            } else {
                                $(btn).removeClass("green-button");
                            }
                            break;

                        case 40:
                            if (z == 40) {
                                $(btn).addClass("blue-button");
                            } else {
                                $(btn).removeClass("blue-button");
                            }
                            break;
                    }
                });
            });

            viewer.addHandler("rotate", function (event) {
                if (!viewerOpen) return;
                $("#btn-rotate-preset-1").removeClass("is-info");
                $("#btn-rotate-preset-2").removeClass("is-info");
                $("#btn-rotate-preset-3").removeClass("is-info");

                switch (event.degrees) {
                    case 0:
                        $("#btn-rotate-preset-1").addClass("is-info");
                        break;
                    case 90:
                        $("#btn-rotate-preset-2").addClass("is-info");
                        break;
                    case 180:
                        $("#btn-rotate-preset-3").addClass("is-info");
                        break;
                }

                var homeZoom = viewer.viewport.getHomeZoom();
                if (viewer.viewport.getZoom().toFixed(2) == homeZoom.toFixed(2) && event.degrees == 0) {
                    $("#home-btn").addClass("is-info");
                    $("#btn-rotate-preset-1").removeClass("is-info");
                } else {
                    $("#home-btn").removeClass("is-info");
                }


            });


            // Openseadragon Plugin initialization

            // Scalebar plugin
            viewer.scalebar({
                type: OpenSeadragon.ScalebarType.MICROSCOPY,
                pixelsPerMeter: ppm,
                minWidth: "160px",
                location: OpenSeadragon.ScalebarLocation.BOTTOM_RIGHT,
                yOffset: 40,
                stayInsideImage: false,
                color: "blue",
                fontColor: "blue",
                backgroundColor: "rgb(255, 255, 255, 0.8)",
                fontSize: "large",
                barThickness: 4
            });



            // Paperjs overlay
            paperOverlay = viewer.paperjsOverlay();

            // Other tool Initialization

            // Rotation slider
            $("#rotation-selector").roundSlider({
                radius: 45,
                width: 8,
                handleSize: "+8",
                handleShape: "dot",
                sliderType: "min-range",
                value: 50,
                tooltipFormat: tooltipInDegrees,
                change: updateRotationSlider,
                drag: updateRotationSlider,
                min: 0,
                max: 360,
                start: function () { rotating = true; },
                stop: function () {
                    rotating = false;
                    if (!$("#rotation-selector-dropdown").is(":hover")) {
                        $("#rotation-selector-dropdown").removeClass("is-active");
                        $("#rotation-dropdown-button").removeClass("is-info");
                    }
                }
            });

            // Event Handlers for Rotation Slider
            function tooltipInDegrees(args) {
                return args.value + "\u00B0";
            }

            function updateRotationSlider(e) {
                updateRotation(e.value);
            }

            rotator = $("#rotation-selector").data("roundSlider");

            // Fix tooltip not in center
            setTimeout(function () {
                fixRotatorTooltip();
            }, 500);

            function fixRotatorTooltip() {
                $(".rs-tooltip").css({
                    "margin-top": "-15.5px",
                    "margin-left": "-16.652px"
                });
            }

            // Color picker initialization
            // Overlay Border
            annotation_border_picker = Pickr.create({
                el: '#annotation-border-picker',
                theme: 'nano', // or 'monolith', or 'nano'
                default: default_border_color,

                swatches: [
                    'red',
                    'yellow',
                    'green',
                    'black',
                    'orange',
                    'purple',
                    'gray'
                ],

                components: {

                    // Main components
                    preview: true,
                    opacity: false,
                    hue: true,

                    // Input / output Options
                    interaction: {
                        hex: false,
                        rgba: false,
                        hsla: false,
                        hsva: false,
                        cmyk: false,
                        input: false,
                        clear: true,
                        save: true
                    }
                }
            });

            // Overlay Background

            annotation_border_picker.on('save', function (event) {
                annotation_border_picker.hide();
                stroke_color = annotation_border_picker.getColor().toHEXA().toString();
            });


            annotation_border_picker.on('change', function (event) {
                stroke_color = annotation_border_picker.getColor().toHEXA().toString();
            });

            annotation_border_picker.on('show', function (event) {
                selectingColor = true;
            });

            annotation_border_picker.on('hide', function (event) {
                selectingColor = false;
            });

            $("#stroke-width-input").on('change', function (event) {
                stroke_width = event.target.valueAsNumber;
                stroke_width = stroke_width / viewZoom;
            });

            $("#annotation-hide-button").click(function () {
                var i;
                if (showingAnnotation) {
                    $(this).attr('title', 'Show Annotation');
                    $(this).children("svg").remove();
                    i = document.createElement("i");
                    $(i).addClass("far");
                    $(i).addClass("fa-eye-slash");
                    $(this).append(i);
                    lines.forEach(function (line) {
                        line.line.visible = false;
                        $(line.text).hide();
                    });

                    rects.forEach(function (rect) {
                        rect.rect.visible = false;
                        $(rect.text).hide();
                    });

                    circles.forEach(function (circle) {
                        circle.circle.visible = false;
                        $(circle.text).hide();
                    });


                } else {
                    $(this).attr('title', 'Hide Annotation');
                    $(this).children("svg").remove();
                    i = document.createElement("i");
                    $(i).addClass("far");
                    $(i).addClass("fa-eye");
                    $(this).append(i);

                    lines.forEach(function (line) {
                        line.line.visible = true;
                        $(line.text).show();
                    });

                    rects.forEach(function (rect) {
                        rect.rect.visible = true;
                        $(rect.text).show();
                    });

                    circles.forEach(function (circle) {
                        circle.circle.visible = true;
                        $(circle.text).show();
                    });


                }
                showingAnnotation = !showingAnnotation;
            });


            // Helper Functions
            function updateRotation(deg) {
                viewer.viewport.setRotation(deg);
            }

            function resetZoomButtons() {
                $("#zoom-buttons").children().removeClass("btn-active");
            }

            function addOverlay(text, overlay) {
                // Add Tooltip with text
                overlay.annotation = text;
                if (text.length !== 0) {
                    $(overlay.text).children(".card-content").children(".annotation-text").html(text);
                    var newWidth = 100;
                    if (text.length > 10) {
                        newWidth = 150;
                    } if (text.length > 20) {
                        newWidth = 200;
                    }
                    $(overlay.text).css("width", newWidth + "px");
                }


                if (overlay.type == 'l') {
                    updateLineCardDivText(overlay.text, overlay.line.firstSegment.point, overlay.line.lastSegment.point);
                }
                else if (overlay.type == 'r') {
                    updateRectCardDivText(overlay.text, overlay.rect.strokeBounds.topLeft, overlay.rect.strokeBounds.topRight, overlay.rect.strokeBounds.bottomRight);
                } else if (overlay.type == 'c') {
                    updateCircleCardDivText(overlay.text, overlay.circle.position.add(new Point(0, overlay.circle.radius + overlay.circle.strokeWidth)), overlay.circle.radius);
                }
                var editButton = $(overlay.text).children(".edit-button").get(0);
                var deleteButton = $(overlay.text).children(".delete-button").get(0);
                var confirmationModal = $("#delete-confirm").clone();
                $(confirmationModal).children(".modal-content").children(".card").css({
                    "width": "300px",
                    "margin": "auto"
                });
                $(confirmationModal).attr('id', '');
                $("#page").append(confirmationModal);
                $(deleteButton).click(function () {
                    $(confirmationModal).addClass('is-active');
                });


                $(confirmationModal).children().find("#cancel-button").click(function () {
                    $(confirmationModal).removeClass('is-active');
                });

                $(confirmationModal).children().find("#delete-button").click(function () {
                    $(confirmationModal).removeClass('is-active');
                    $(confirmationModal).remove();
                    $(overlay.text).remove();
                    $.post('"""+app_url+"""/"""+app_name+"""/annotation/delete/' + overlay.id);
                    if (overlay.type == 'c') {
                        overlay.circle.remove();
                        var index;
                        for (index = 0; index < circles.length; index++) {
                            var element = circles[index];
                            if (element.circle === overlay.circle) {
                                circles.splice(index, 1);
                                break;
                            }
                        }

                    } else if (overlay.type == 'r') {
                        overlay.rect.remove();
                        var i;
                        for (i = 0; i < rects.length; i++) {
                            var e = rects[i];
                            if (e.rect === overlay.rect) {
                                rects.splice(i, 1);
                                break;
                            }
                        }

                    } else if (overlay.type == 'l') {
                        overlay.line.remove();
                        var j;
                        for (j = 0; j < lines.length; j++) {
                            var e1 = lines[j];
                            if (e1.line === overlay.line) {
                                lines.splice(j, 1);
                                break;
                            }
                        }

                    }

                });

                $(editButton).click(function () {
                    $("#annotation-modal-title").html("Edit Annotation");
                    $("#annotation-modal").addClass("is-active");
                    $("#annotation-save-btn").val(overlay.type + '-' + overlay.id);
                    editMode = true;
                    $("#annotation-text").val(overlay.annotation);
                    currentEditingOverlay = overlay;
                });

                $(overlay.text).hover(function () {
                    $(deleteButton).show();
                    $(editButton).show();
                    if (overlay.type == 'l') {
                        updateLineCardDivText(overlay.text, overlay.line.firstSegment.point, overlay.line.lastSegment.point);
                    }
                    else if (overlay.type == 'r') {
                        updateRectCardDivText(overlay.text, overlay.rect.strokeBounds.topLeft, overlay.rect.strokeBounds.topRight, overlay.rect.strokeBounds.bottomRight);
                    }
                    else if (overlay.type == 'c') {
                        updateCircleCardDivText(overlay.text, overlay.circle.position.add(new Point(0, overlay.circle.radius + overlay.circle.strokeWidth)), overlay.circle.radius);
                    }
                }, function () {
                    $(deleteButton).hide();
                    $(editButton).hide();
                    if (overlay.type == 'l') {
                        updateLineCardDivText(overlay.text, overlay.line.firstSegment.point, overlay.line.lastSegment.point);
                    }
                    else if (overlay.type == 'r') {
                        updateRectCardDivText(overlay.text, overlay.rect.strokeBounds.topLeft, overlay.rect.strokeBounds.topRight, overlay.rect.strokeBounds.bottomRight);
                    }
                    else if (overlay.type == 'c') {
                        updateCircleCardDivText(overlay.text, overlay.circle.position.add(new Point(0, overlay.circle.radius + overlay.circle.strokeWidth)), overlay.circle.radius);
                    }
                });

            }

            function closeAnnotation() {
                $("canvas").removeClass('cursor-crosshair');
            }

            function loadAnnotations() {
                $.get('"""+app_url+"""/"""+app_name+"""/annotation/{{Slide.pk}}', function (data, status) {
                    data.annotations.forEach(function (annotation) {
                        if (annotation.type == 'l') {
                            var l = {
                                id: annotation.id,
                                line: Path.importJSON(annotation.json),
                                annotation: annotation.text,
                                text: createDivText(),
                                type: 'l'
                            };
                            project.activeLayer.addChild(l.line);
                            addOverlay(l.annotation, l);
                            console.log(l);
                            lines.push(l);
                        } else if (annotation.type == 'r') {
                            var r = {
                                id: annotation.id,
                                rect: Shape.importJSON(annotation.json),
                                annotation: annotation.text,
                                text: createDivText(),
                                type: 'r'
                            };
                            $(r.text).css("width", "115px");
                            $(r.text).children(".card-content").children(".measurement").css("font-size", "0.65rem");
                            project.activeLayer.addChild(r.rect);
                            addOverlay(r.annotation, r);
                            rects.push(r);
                            r.rect.onMouseEnter = function () {
                                $("#page").addClass("cursor-move");
                            };
                            r.rect.onMouseLeave = function () {
                                $("#page").removeClass("cursor-move");
                            };
                        } else if (annotation.type == 'c') {
                            var c = {
                                id: annotation.id,
                                circle: Shape.importJSON(annotation.json),
                                annotation: annotation.text,
                                text: createDivText(),
                                type: 'c'
                            };
                            $(c.text).css("width", "90px");
                            $(c.text).children(".card-content").children(".measurement").css("font-size", "0.65rem");
                            project.activeLayer.addChild(c.circle);
                            addOverlay(c.annotation, c);
                            circles.push(c);
                            c.circle.onMouseEnter = function () {
                                $("#page").addClass("cursor-move");
                            };
                            c.circle.onMouseLeave = function () {
                                $("#page").removeClass("cursor-move");
                            };
                        }
                    });
                });

            }

            function resetAnnotationModal() {
                $("#annotation-text").val('');
                $("#annotation-modal-title").html("Add Annotation");
            }

            function updateAnnotation(text) {
                currentEditingOverlay.annotation = text;
                $.post('"""+app_url+"""/"""+app_name+"""/annotation/edit/' + currentEditingOverlay.id, { text: text });
                if (text.length !== 0) {
                    $(currentEditingOverlay.text).children(".card-content").children(".annotation-text").html(text);
                    var newWidth = 100;
                    if (text.length > 10) {
                        newWidth = 150;
                    } if (text.length > 20) {
                        newWidth = 200;
                    }
                    $(currentEditingOverlay.text).css("width", newWidth + "px");
                }
                else {
                    var nWidth = 70;
                    if (currentEditingOverlay.type == 'r') {
                        nWidth = 150;
                    } else if (currentEditingOverlay.type == 'c') {
                        nWidth = 100;
                    }
                    $(currentEditingOverlay.text).css("width", nWidth + "px");
                }
                if (currentEditingOverlay.type == 'l') {
                    updateLineCardDivText(currentEditingOverlay.text, currentEditingOverlay.line.firstSegment.point, currentEditingOverlay.line.lastSegment.point);
                }
                else if (currentEditingOverlay.type == 'r') {
                    updateRectCardDivText(currentEditingOverlay.text, currentEditingOverlay.rect.strokeBounds.topLeft, currentEditingOverlay.rect.strokeBounds.topRight, currentEditingOverlay.rect.strokeBounds.bottomRight);
                }
                else if (currentEditingOverlay.type == 'c') {
                    var radius = currentEditingOverlay.circle.radius;
                    updateCircleCardDivText(currentEditingOverlay.text, currentEditingOverlay.circle.position.add(new Point(0, radius + stroke_width)), currentEditingOverlay.circle.radius);
                }
            }

            // Event Handlers

            // Toolbar Buttons

            $("#zoomin-btn").click(function () {
                resetZoomButtons();
            });

            $("#zoomout-btn").click(function () {
                resetZoomButtons();
            });

            // Zoom Preset Buttons
            $(".zoom-button").click(function (e) {
                viewer.viewport.zoomTo(parseInt(e.target.value));
            });

            $("#screenshot-btn").click(function () {
                $(this).addClass("is-success");
                $("#loading-modal").addClass("is-active");
                var parent = $('.openseadragon-container').get(0);
                var toBeHidden = $(parent).children().get(2);
                $(toBeHidden).hide();
                html2canvas($("#openseadragon-viewer").get(0)).then(function (canvas) {
                    Canvas2Image.saveAsPNG(canvas);
                    $("#loading-modal").removeClass("is-active");
                    $(toBeHidden).show();
                    $("#screenshot-btn").removeClass("is-success");
                });
            });


            $("#btn-rotate-preset-1").click(function () {
                rotator.setValue(0);
                updateRotation(0);
                fixRotatorTooltip();
            });

            $("#btn-rotate-preset-2").click(function () {
                rotator.setValue(90);
                updateRotation(90);
                fixRotatorTooltip();
            });

            $("#btn-rotate-preset-3").click(function () {
                rotator.setValue(180);
                updateRotation(180);
                fixRotatorTooltip();
            });

            $("#rotation-selector-dropdown").hover(function () {
                $(this).addClass("is-active");
                $("#rotation-dropdown-button").addClass("is-info");
            }, function () {
                if (!rotating) {
                    $(this).removeClass("is-active");
                    $("#rotation-dropdown-button").removeClass("is-info");
                }
            });

            $("#draw-menu-dropdown").hover(function () {
                $(this).addClass("is-active");
                $("#draw-button").addClass("is-danger");
            }, function () {
                if (!selectingColor) {
                    $(this).removeClass("is-active");
                    if (drawMode === 0) {
                        $("#draw-button").removeClass("is-danger");
                    }
                }
            });

            $("#line-button").click(function () {
                if (drawMode !== 1)
                    changeDrawMode(1);
                else
                    changeDrawMode(0);
            });

            $("#rect-button").click(function () {
                if (drawMode !== 2)
                    changeDrawMode(2);
                else
                    changeDrawMode(0);
            });

            $("#circle-button").click(function () {
                if (drawMode !== 3)
                    changeDrawMode(3);
                else
                    changeDrawMode(0);
            });

            // Modal Control Events (Modal for annotation input)

            $(".annotation-modal-close ").click(function () {
                $("#annotation-modal").removeClass("is-active");
                if (!editMode) {
                    if (lastOverlay.type == 'r') {
                        lastOverlay.rect.remove();
                    } else if (lastOverlay.type == 'c') {
                        lastOverlay.circle.remove();
                    } else if (lastOverlay.type == 'l') {
                        lastOverlay.line.remove();
                    }
                    $(lastOverlay.text).remove();
                }
                editMode = false;
                resetAnnotationModal();
                closeAnnotation();
            });

            $("#annotation-save-btn").click(function (event) {
                $("#annotation-modal").removeClass("is-active");
                var text = $("#annotation-text").val();
                if (editMode) {
                    updateAnnotation(text);
                } else {

                }
                editMode = false;
                closeAnnotation();
                resetAnnotationModal();
            });

            $("#border-width-input").on('change', function (event) {
                var height = event.target.value;
                $("#border-example").css("height", height);
            });


            // Resize event
            window.onresize = function () {
                paperOverlay.resize();
                paperOverlay.resizecanvas();
                var navbarHeight = $(".navbar").height();
                var pageHeight = $("#page").height();
                $("#openseadragon-viewer").height(pageHeight - navbarHeight);
                setTimeout(function () {
                    if (viewer.viewport.getZoom() < viewer.viewport.getHomeZoom()) {
                        viewer.viewport.zoomTo(viewer.viewport.getHomeZoom());
                    }
                    viewer.viewport.minZoomLevel = viewer.viewport.getHomeZoom();
                }, 100);
                lines.forEach(function (line) {
                    updateLineCardDivText(line.text, line.line.firstSegment.point, line.line.lastSegment.point);
                });
                rects.forEach(function (rect) {
                    updateRectCardDivText(rect.text, rect.rect.strokeBounds.topLeft, rect.rect.strokeBounds.topRight, rect.rect.strokeBounds.bottomRight);
                });
                circles.forEach(function (circle) {
                    updateCircleCardDivText(circle.text, circle.circle.position.add(new Point(0, radius + stroke_width)), circle.circle.radius);
                });
            };


            // Paperjs Drawing tool

            // Openseadragon Mouse events
            var mouseTracker = new OpenSeadragon.MouseTracker({
                element: viewer.canvas,
                pressHandler: pressHandler,
                dragHandler: dragHandler,
                dragEndHandler: dragEndHandler,
                scrollHandler: resetZoomButtons,
            });
            mouseTracker.setTracking(true);



            function pressHandler(event) {

                var transformedPoint = view.viewToProject(new Point(event.position.x, event.position.y));
                startPoint = transformedPoint;
                switch (drawMode) {
                    case 0:
                        hitTest = null;
                        var tPoint = view.viewToProject(new Point(event.position.x, event.position.y));
                        var hitTestResult = project.hitTest(tPoint);
                        if (hitTestResult && hitTestResult.item instanceof Shape) {
                            if (hitTestResult.item.type == 'circle') {
                                circles.forEach(function (circle) {
                                    if (circle.circle === hitTestResult.item) {
                                        hitTest = circle;
                                    }
                                });
                            } else if (hitTestResult.item.type == 'rectangle') {
                                rects.forEach(function (rect) {
                                    if (rect.rect === hitTestResult.item) {
                                        hitTest = rect;
                                    }
                                });
                            }
                        }
                        break;
                    case 1:
                        linePressHandler();
                        break;

                    case 2:
                        rectPressHandler();
                        break;

                    case 3:
                        circlePressHandler();
                        break;
                }
            }

            function dragHandler(event) {
                var tPoint = view.viewToProject(new Point(event.position.x, event.position.y));
                switch (drawMode) {
                    case 0:
                        if (hitTest) {
                            var tPoint1 = view.viewToProject(new Point(0, 0));
                            var tPoint2 = view.viewToProject(new Point(event.delta.x, event.delta.y));

                            if (hitTest.type == 'r') {
                                hitTest.rect.position = hitTest.rect.position.add(tPoint2.subtract(tPoint1));
                                updateRectCardDivText(hitTest.text, hitTest.rect.strokeBounds.topLeft, hitTest.rect.strokeBounds.topRight, hitTest.rect.strokeBounds.bottomRight);
                            } else if (hitTest.type == 'c') {
                                hitTest.circle.position = hitTest.circle.position.add(tPoint2.subtract(tPoint1));
                                var radius = hitTest.circle.radius;
                                updateCircleCardDivText(hitTest.text, hitTest.circle.position.add(new Point(0, radius + stroke_width)), radius);
                            }
                            viewer.setMouseNavEnabled(false);
                        }
                        break;
                    case 1:
                        lineDragHandler(tPoint);
                        break;

                    case 2:
                        rectDragHandler(tPoint);
                        break;

                    case 3:
                        circleDragHandler(tPoint);
                        break;
                }
            }

            function dragEndHandler(event) {
                var tPoint = view.viewToProject(new Point(event.position.x, event.position.y));
                switch (drawMode) {
                    case 0:
                        if (hitTest) {
                            viewer.setMouseNavEnabled(true);
                            var json = '';
                            if (hitTest.type == 'l') {
                                json = hitTest.line.exportJSON();
                            }
                            else if (hitTest.type == 'r') {
                                json = hitTest.rect.exportJSON();
                            }
                            else if (hitTest.type == 'c') {
                                json = hitTest.circle.exportJSON();
                            }
                            $.post('"""+app_url+"""/"""+app_name+"""/annotation/edit/' + hitTest.id, { json: json });
                        }
                        hitTest = null;
                        break;
                    case 1:
                        lineDragEndHandler(tPoint);
                        break;

                    case 2:
                        rectDragEndHandler(tPoint);
                        break;

                    case 3:
                        circleDragEndHandler(tPoint);
                        break;
                }

                startPoint = null;
                changeDrawMode(0);

            }


            // Helper function
            function linePressHandler() {
                currentLine = {
                    line: new Path(),
                    text: createDivText(),
                };
                currentLine.line.strokeColor = stroke_color;
                currentLine.line.fillColor = currentLine.line.strokeColor;
                currentLine.line.strokeWidth = stroke_width;
                currentLine.line.add(startPoint);
            }

            function lineDragHandler(current) {
                var firstSeg = currentLine.line.firstSegment;
                currentLine.line.removeSegments();
                currentLine.line.add(firstSeg, current);
                updateLineCardDivText(currentLine.text, current, firstSeg.point);
            }

            function lineDragEndHandler(current) {
                var dup = {
                    line: currentLine.line.clone(),
                    text: currentLine.text,
                    id: null,
                    annotation: '',
                    type: 'l'
                };
                currentLine.line.remove();
                currentLine = null;

                lastOverlay = dup;
                lines.push(lastOverlay);
                addOverlay("", lastOverlay);
                $.post('"""+app_url+"""/"""+app_name+"""/annotation/add', { slideId: '{{Slide.pk}}', Json: lastOverlay.line.exportJSON(), text: '', type: 'l' }, function (data) {
                    lastOverlay.id = parseInt(data.id);
                });
            }

            function circlePressHandler() {
                currentCircle = {
                    circle: null,
                    text: createDivText(),
                };
                $(currentCircle.text).css("width", "90px");
                $(currentCircle.text).children(".card-content").children(".measurement").css("font-size", "0.65rem");
            }

            function circleDragHandler(current) {
                if (currentCircle.circle === null) {
                    currentCircle.circle = createCircle(startPoint, startPoint.getDistance(current));
                }
                currentCircle.circle.remove();
                currentCircle.circle = createCircle(startPoint, startPoint.getDistance(current));

                var radius = currentCircle.circle.radius;
                updateCircleCardDivText(currentCircle.text, currentCircle.circle.position.add(new Point(0, radius + stroke_width)), radius);

            }

            function circleDragEndHandler(current) {
                if (currentCircle !== null) {
                    var c = createCircle(currentCircle.circle.position, currentCircle.circle.radius);

                    var obj = {
                        id: null,
                        type: 'c',
                        circle: c,
                        text: currentCircle.text
                    };

                    lastOverlay = obj;
                    currentCircle.circle.remove();
                    circles.push(lastOverlay);
                    addOverlay("", lastOverlay);
                    lastOverlay.circle.onMouseEnter = function () {
                        $("#page").addClass("cursor-move");
                    };
                    lastOverlay.circle.onMouseLeave = function () {
                        $("#page").removeClass("cursor-move");
                    };
                    $.post('"""+app_url+"""/"""+app_name+"""/annotation/add', { slideId: '{{Slide.pk}}', Json: lastOverlay.circle.exportJSON(), text: '', type: 'c' }, function (data) {
                        lastOverlay.id = parseInt(data.id);
                    });
                }
            }

            function rectPressHandler() {
                currentRect = {
                    rect: null,
                    text: createDivText(),
                };
                $(currentRect.text).css("width", "115px");
                $(currentRect.text).children(".card-content").children(".measurement").css("font-size", "0.65rem");
            }

            function rectDragHandler(current) {
                if (currentRect.rect === null) {
                    currentRect.rect = createRect(startPoint, current);
                }
                currentRect.rect.remove();
                currentRect.rect = createRect(startPoint, current);
                updateRectCardDivText(currentRect.text, currentRect.rect.strokeBounds.topLeft, currentRect.rect.strokeBounds.topRight, currentRect.rect.strokeBounds.bottomRight);
            }

            function rectDragEndHandler(current) {
                if (currentRect.rect !== null) {
                    var finalRect = createRect(startPoint, current);
                    var obj = {
                        id: null,
                        type: 'r',
                        rect: finalRect,
                        text: currentRect.text
                    };
                    lastOverlay = obj;
                    currentRect.rect.remove();

                    // Open annotation menu
                    rects.push(lastOverlay);
                    addOverlay("", lastOverlay);

                    lastOverlay.rect.onMouseEnter = function () {
                        $("#page").addClass("cursor-move");
                    };
                    lastOverlay.rect.onMouseLeave = function () {
                        $("#page").removeClass("cursor-move");
                    };
                    $.post('"""+app_url+"""/"""+app_name+"""/annotation/add', { slideId: '{{Slide.pk}}', Json: lastOverlay.rect.exportJSON(), text: '', type: 'r' }, function (data) {
                        lastOverlay.id = parseInt(data.id);
                    });
                }

            }


            function createCircle(center, radius) {
                var c = new Shape.Circle(center, radius);
                c.strokeColor = stroke_color;
                c.fillColor = 'rgba(255, 255, 255, 0.05)';
                c.strokeWidth = stroke_width;
                return c;
            }

            function createRect(from, to) {
                var c = new Shape.Rectangle(from, to);
                c.strokeColor = stroke_color;
                c.fillColor = 'rgba(255, 255, 255, 0.05)';
                c.strokeWidth = stroke_width;
                return c;
            }

            function createDivText() {
                var card = document.createElement("div");
                $(card).width("70px");
                $(card).addClass("card");
                var deleteButton = document.createElement("button");
                $(deleteButton).addClass("card-control");
                $(deleteButton).addClass("delete-button");
                var delIcon = document.createElement("i");
                $(delIcon).addClass("fas");
                $(delIcon).addClass("fa-times");
                $(deleteButton).append(delIcon);

                var editButton = document.createElement("button");
                $(editButton).addClass("card-control");
                $(editButton).addClass("edit-button");
                var editIcon = document.createElement("i");
                $(editIcon).addClass("fas");
                $(editIcon).addClass("fa-edit");
                $(editButton).append(editIcon);
                $(card).append(deleteButton);
                $(card).append(editButton);

                $(editButton).hide();
                $(deleteButton).hide();

                var cardContent = document.createElement("div");
                $(cardContent).css({ "padding": "0", "text-align": "center" });
                $(cardContent).addClass("card-content");
                $(card).append(cardContent);
                var p = document.createElement("p");
                $(p).addClass("measurement");
                var annote = document.createElement("p");
                $(annote).addClass("annotation-text");
                $(cardContent).append(annote);
                $(cardContent).append(p);
                $("#openseadragon-viewer").append(card);
                return card;
            }

            function updateLineCardDivText(card, start, end) {
                var rot = angleFromHorizontal(start, end);

                var content = converterToSI(start.getDistance(end));
                $(card).children(".card-content").children(".measurement").html(content);
                // If in first or third quadrand
                if ((end.x > start.x && end.y < start.y) || (end.x < start.x && end.y > start.y)) {
                    rot = rot * -1;
                }
                var mid = midPoint(start, end).subtract(new Point(0, stroke_width));
                var pos = view.projectToView(mid);
                var textRot = rot * (Math.PI / 180.0);

                var w = ($(card).width() / 2.0);
                var h = $(card).height();
                var xOff = w * Math.cos(textRot) - h * Math.sin(textRot);
                var yOff = w * Math.sin(textRot) + h * Math.cos(textRot);

                var off = new Point(xOff, yOff);
                pos = pos.subtract(off);


                $(card).css({
                    "position": "absolute",
                    "top": pos.y + $(".navbar").height(),
                    "left": pos.x,
                    "transform-origin": "top left",
                    "-ms-transform": "rotate(" + rot + "deg)",
                    "transform": "rotate(" + rot + "deg)",
                });

            }

            function updateRectCardDivText(card, topLeft, topRight, bottomRight) {

                var content = converterToSI(topLeft.getDistance(topRight)) + "X" + converterToSI(topRight.getDistance(bottomRight));
                $(card).children(".card-content").children(".measurement").html(content);

                var mid = midPoint(topLeft, topRight);
                var pos = view.projectToView(mid);

                var w = ($(card).width() / 2.0);
                var h = $(card).height();

                var off = new Point(w, h);
                pos = pos.subtract(off);


                $(card).css({
                    "position": "absolute",
                    "top": pos.y + $(".navbar").height(),
                    "left": pos.x,
                });

            }

            function updateCircleCardDivText(card, position, radius) {

                var content = "r=" + converterToSI(radius);
                $(card).children(".card-content").children(".measurement").html(content);

                var pos = view.projectToView(position);

                var w = ($(card).width() / 2.0);

                var off = new Point(w, 0);
                pos = pos.subtract(off);


                $(card).css({
                    "position": "absolute",
                    "top": pos.y + $(".navbar").height(),
                    "left": pos.x,
                });

            }

            function converterToSI(val) {
                val = val / ppm;
                var unit = 'm';
                // Convert to mm 
                val = val * 1000.0;
                unit = '\u339c';
                var test = parseInt(val * 1000);
                if (test.toString().length <= 2) {
                    val = val * 1000.0;
                    unit = '\u339b';
                    test = parseInt(val * 1000);
                    if (test.toString().length <= 2) {
                        val = val * 1000.0;
                        unit = '\u339a';
                    }
                }
                val = val.toFixed(2);
                return val.toString() + unit;
            }

            function midPoint(a, b) {
                return new Point((a.x + b.x) / 2, (a.y + b.y) / 2);
            }

            function angleFromHorizontal(a, b) {
                var max = Point.max(a, b);
                var min = Point.min(a, b);
                var vec = max.subtract(min);

                return vec.getAngle(new Point(1, 0));
            }

            function changeDrawMode(mode) {
                $("#draw-button").removeClass("is-danger");
                $("#line-button").removeClass("is-success");
                $("#rect-button").removeClass("is-success");
                $("#circle-button").removeClass("is-success");
                drawMode = mode;
                if (mode === 0) {
                    viewer.setMouseNavEnabled(true);
                    $("canvas").removeClass('cursor-crosshair');
                } else {
                    viewer.setMouseNavEnabled(false);
                    $("#draw-button").addClass("is-danger");
                    $("canvas").addClass('cursor-crosshair');
                    if (mode === 1) {
                        $("#line-button").addClass("is-success");
                    } else if (mode === 2) {
                        $("#rect-button").addClass("is-success");
                    } else if (mode === 3) {
                        $("#circle-button").addClass("is-success");
                    }
                }
            }
            function getCookie(name) {
                var cookieValue = null;
                if (document.cookie && document.cookie !== '') {
                    var cookies = document.cookie.split(';');
                    for (var i = 0; i < cookies.length; i++) {
                        var cookie = cookies[i].trim();
                        // Does this cookie string begin with the name we want?
                        if (cookie.substring(0, name.length + 1) === (name + '=')) {
                            cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                            break;
                        }
                    }
                }
                return cookieValue;
            }


        });

    </script>

</head>

<body>
    {%csrf_token%}
    <div id="page">
        <nav class="navbar" role="navigation" aria-label="main navigation">
            <div class="navbar-brand">
                <a class="navbar-item" href="#">
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

                    <div class="separator"></div>

                    <div class="navbar-item zoom-button-container">
                        <button value="2" title="Zoom in 2x" class="button zoom-button"
                            style="border: 2px solid #f68a42; border-top: none;"> 2x </button>
                    </div>

                    <div class="navbar-item zoom-button-container">
                        <button value="5" title="Zoom in 5x" class="button zoom-button"
                            style="border: 2px solid red; border-top: none;"> 5x </button>
                    </div>

                    <div class="navbar-item zoom-button-container">
                        <button value="10" title="Zoom in 10x" class="button zoom-button"
                            style="border: 2px solid hsl(48, 100%, 67%); border-top: none;"> 10x </button>
                    </div>

                    <div class="navbar-item zoom-button-container">
                        <button value="20" title="Zoom in 20x" class="button zoom-button"
                            style="border: 2px solid green; border-top: none"> 20x </button>
                    </div>

                    <div class="navbar-item zoom-button-container">
                        <button value="40" title="Zoom in 40x" class="button zoom-button"
                            style="border: 2px solid blue; border-top: none"> 40x </button>
                    </div>

                    <div class="separator"></div>

                    <div id="rotation-selector-dropdown" class="navbar-item has-dropdown">
                        <button id="rotation-dropdown-button" title="Rotate" class="button is-rounded"> <i
                                class="fas fa-sync"></i> </button>
                        <div class="navbar-dropdown">
                            <div class="navbar-item">
                                <div id="rotation-selector"></div>
                            </div>
                        </div>
                    </div>
                    <div class="navbar-item rotate-preset-container">
                        <button id="btn-rotate-preset-1" title="Rotate to 0" value="0" class="button is-rounded">
                            0&#176; </button>
                    </div>

                    <div class="navbar-item rotate-preset-container">
                        <button id="btn-rotate-preset-2" title="Rotate to 90" value="90" class="button is-rounded">
                            90&#176; </button>
                    </div>

                    <div class="navbar-item rotate-preset-container">
                        <button id="btn-rotate-preset-3" title="Rotate to 180" value="180" class="button is-rounded">
                            180&#176; </button>
                    </div>

                    <div class="separator"></div>

                    <div class="navbar-item">
                        <button id="screenshot-btn" title="Take Screenshot" class="button is-rounded"> <i
                                class="fas fa-camera"></i> </button>
                    </div>

                    <div id="draw-menu-dropdown" class="navbar-item has-dropdown">
                        <button id="draw-button" title="Annotations Menu" class="button is-rounded"> <i
                                class="fas fa-pen"></i> </button>
                        <div class="navbar-dropdown">
                            <div class="navbar-item">
                                <div id="draw-menu">
                                    <label class="label">Select Tool</label>
                                    <div class="columns">
                                        <div class="column">
                                            <button id="rect-button" title="Rectangle Annotation"
                                                class="button is-rounded">
                                                <svg width="15" height="15">
                                                    <rect width="15" height="15"
                                                        style="stroke-width: 3; fill: rgb(255, 255, 255); stroke: rgb(0, 0, 0)">
                                                    </rect>
                                                </svg>
                                            </button>
                                        </div>
                                        <div class="column">
                                            <button id="circle-button" title="Circle Annotation"
                                                class="button is-rounded"> <i class="far fa-circle"></i> </button>
                                        </div>
                                        <div class="column">
                                            <button id="line-button" title="Measure Tool" class="button is-rounded">
                                                <i class="fas fa-pencil-ruler"></i>
                                            </button>
                                        </div>
                                    </div>
                                    <div class="columns">
                                        <div class="column">
                                            <label class="label">Stroke Color</label>
                                            <div id="annotation-border-picker" class="color-picker"></div>
                                        </div>
                                        <div class="column">
                                            <label class="label">Storke Width</label>
                                            <input id="stroke-width-input" value="4" type="number"
                                                class="input is-rounded" width="30px" min="1" max="30">
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                    <div class="navbar-item">
                        <button id="annotation-hide-button" title="Hide Annotation" class="button is-rounded"> <i
                                class="far fa-eye"></i> </button>
                    </div>

                </div>
                <div class="navbar-end">
                    <div class="navbar-item">
                        <button class="button is-rounded"> <i class="fas fa-cog"></i> </button>
                    </div>
                </div>

            </div>
        </nav>


        <div id="openseadragon-viewer">
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

    with open(os.path.join(settings.BASE_DIR, 'virtualcases/settings_local.py'), 'r+') as file:

        from .models import TestApp

        list_db_apps = TestApp.objects.values_list('test_title', flat = True)
        print(list_db_apps);
        list_db_apps_array = list(list_db_apps)
        installed_apps = "ADDITIONAL_APPS = " + str(list_db_apps_array).strip().replace(" ", "").lower()

        file.writelines(installed_apps)
    # try:
    #     local_setting_file_ = open(os.path.join(settings.BASE_DIR, 'virtualcases/settings_local.py'), 'r+')
    # except IOError:
    #     print("An error was found. Either path is incorrect or file doesn't exist!")
    # finally:
    #     from .models import TestApp

    #     list_db_apps = TestApp.objects.values_list('test_title', flat = True)
    #     list_db_apps_array = list(list_db_apps)
    #     installed_apps = "ADDITIONAL_APPS = " + str(list_db_apps_array).lower()
        
    #     local_setting_file_.writelines(installed_apps)
    #     local_setting_file_.close()

    # final_name = app_name+'.apps.'+str(app_name).capitalize()+'Config'
    # with open(os.path.join(settings.BASE_DIR, 'virtualcases/settings.py'), 'r') as file:
    #     old_settings = file.readlines()

    # new_settings = []
    # for line in old_settings:

    #     if "INSTALLED_APPS" in line:
    #         new_settings.append(line.replace("INSTALLED_APPS = [", "INSTALLED_APPS = [\n\t%s" % "'"+final_name+"',"))
    #     else:
    #         new_settings.append(line)

    # with open(os.path.join(settings.BASE_DIR, 'virtualcases/settings.py'), 'w') as file:
    #     file.write("".join(new_settings))


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
