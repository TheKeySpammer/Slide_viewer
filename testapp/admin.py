
from django.contrib.auth.models import User, Group
from django.contrib import admin
from .models import TestApp
from django.core import management
# Create your views here.

#admin.site.unregister(User)
#admin.site.unregister(Group)

admin.site.site_header = "Virtual Cases Portal"
admin.site.site_title = "Virtual Cases"
admin.site.index_title = "Welcome to Virtual Cases Portal"

class TestFileAdmin(admin.ModelAdmin):
    list_display = ['test_title', 'test_timestamp']
    list_filter = ['test_timestamp']
    search_fields = ['test_title']
    list_per_page = 15
    actions = None

admin.site.register(TestApp, TestFileAdmin)


management.call_command('makemigrations')
# management.call_command('migrate')
