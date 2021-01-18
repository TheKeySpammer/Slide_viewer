from django.contrib.auth.models import User, Group
from django.contrib import admin
from .models import CaseFile
from django.utils.html import format_html
from django.utils.safestring import mark_safe

# Create your views here.

#admin.site.unregister(User)
#admin.site.unregister(Group)

admin.site.site_header = "Virtual Cases Portal"
admin.site.site_title = "Virtual Cases"
admin.site.index_title = "Welcome to Virtual Cases Portal"

#Generate Openslide link

def openslide_file(self):    
    slide_url = str(self.case_file)
    change_slide_url = slide_url.split('/')[2]
    return format_html(
       '<a href="{}" target="_blank">{}</a>',
       ("%s%s" % ('//slides.djangoapp.test/', change_slide_url)),
       'View Case',
    )
openslide_file.short_description = 'View Cases'

def generate_iframe(self):
    slide_url = str(self.case_file)
    change_slide_url = slide_url.split('/')[2]
    return format_html('{} <div id="iframe_dialog"><textarea class="iframe_code" readonly rows="4" cols="91">{}</textarea></div>',
        mark_safe('<button type="button" id="open_dialog">View Iframe Code</button>'),
        mark_safe('<body style="margin:0px;padding:0px;overflow:hidden"><iframe src="//slidesportal.co.uk/jcp_cases/'+change_slide_url+'" frameborder="0" style="overflow:hidden;height:100%;width:100%" height="100%" width="100%"></iframe></body>'),
    )
generate_iframe.short_description = 'Code'

class CaseFileAdmin(admin.ModelAdmin):
    list_display = ['case_title', openslide_file, generate_iframe, 'case_timestamp']
    list_filter = ['case_timestamp']
    search_fields = ['case_title']
    list_per_page = 15

    class Media:
        css = {
            'all': ('admin/css/vendor/jquery-ui.min.css', 'admin/css/vendor/jquery-ui.theme.css', 'admin/css/custom.css')
        }
        js = ('admin/js/jquery-ui.min.js', 'admin/js/custom.js')

admin.site.register(CaseFile, CaseFileAdmin)