from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from django.conf.urls import include, url
from django.views.generic.base import RedirectView
# from histoslide import urls



from test1 import urls
from liverpooldermpathcourse2020 import urls
from virtualacp import urls
from jclinpathtest import urls
from patient import urls
from frcpathp2surgicalcourse import urls
from alopecia import urls
#Add Custom APP URL Entry
urlpatterns = [
	url(r'^$', RedirectView.as_view(url='/admin')),
    path('admin/', admin.site.urls),
	url(r'^alopecia/', include('alopecia.urls')),
	url(r'^frcpathp2surgicalcourse/', include('frcpathp2surgicalcourse.urls')),
	url(r'^patient/', include('patient.urls')),
	url(r'^jclinpathtest/', include('jclinpathtest.urls')),
	url(r'^virtualacp/', include('virtualacp.urls')),
	url(r'^liverpooldermpathcourse2020/', include('liverpooldermpathcourse2020.urls')),
	url(r'^test1/', include('test1.urls')),
	

    # url(r'^histoslide/', include('histoslide.urls'))
]

# + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
