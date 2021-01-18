
from os import walk, path
from datetime import date
from django.contrib import admin
from django.conf import settings
from .models import Test1
from django.utils.html import format_html
from django.utils.safestring import mark_safe

def default_domain():
    return {'default_domain': settings.DEFAULT_DOMAIN}

#Generate Openslide link
def openslide_file(self):
    slide_id = self.id
    return format_html(
       '<a href="{}" target="_blank">{}</a>',
       ("%s%s" % (settings.DEFAULT_DOMAIN+ '/test1/slide/', slide_id)),
       'View Case',
    )
openslide_file.short_description = 'View Cases'

def generate_iframe(self):
    slide_id = self.id
    return format_html('{} <div id="iframe_dialog"><textarea class="iframe_code" readonly rows="4" cols="91">{}</textarea></div>',
        mark_safe('<button type="button" id="open_dialog">View Iframe Code</button>'),
        mark_safe('<body style="margin:0px;padding:0px;overflow:hidden"><iframe src="'+settings.DEFAULT_DOMAIN+'/test1/slide/'+str(slide_id)+'" frameborder="0" style="overflow:hidden;height:100%;width:100%" height="100%" width="100%"></iframe></body>'),
    )
generate_iframe.short_description = 'Code'

def download_slide(self):
    slide_id = self.id
    return format_html(
       '<a href="{}" target="_blank">{}</a>',
       ("%s%s%s" % (settings.DEFAULT_DOMAIN+ '/test1/slide/', slide_id, '/download')),
       'Download Case',
    )
download_slide.short_description = 'Download Case'

def delete_slide(self):
    slide_id = self.id
    return format_html(
       '<a href="{}" target="_blank">{}</a>',
       ("%s%s%s" % (settings.DEFAULT_DOMAIN+ '/test1/slide/', slide_id, '/delete')),
       'Delete Case',
    )
delete_slide.short_description = 'Delete Case'


class Test1Admin(admin.ModelAdmin):
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
                        slide = Test1.objects.get(UrlPath=str(urlnew))
                    except Test1.DoesNotExist:
                        slide = Test1(Name=path.splitext(slide_file)[0], ScannedBy=currentuser,
                                      ScannedDate=date.today(), InsertedBy=currentuser, InsertedDate=date.today(),
                                      SlideType=2, UrlPath=str(urlnew))
                        slide.save()

    class Media:
        css = {
            'all': ('admin/css/vendor/jquery-ui.min.css', 'admin/css/vendor/jquery-ui.theme.css', 'admin/css/custom.css')
        }
        js = ('admin/js/jquery-ui.min.js', 'admin/js/custom.js')


admin.site.register(Test1, Test1Admin)