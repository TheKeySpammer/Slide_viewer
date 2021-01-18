"""
WSGI config for virtualcases project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/2.2/howto/deployment/wsgi/
"""

import os

import site

from django.core.wsgi import get_wsgi_application

#site.addsitedir('/home/histo/env/lib/python3.6/site-packages')
#sys.path.append('/home/histo')
#sys.path.append('/home/histo/virtualcases')


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'virtualcases.settings')


activate_this = '/mnt/d/projects/slide_app/env/bin/activate_this.py'
with open(activate_this) as file_:
         exec(file_.read(), dict(__file__=activate_this))
# import sys
# sys.path.insert(0, '/home/histo/var/www/wsgi_test/')
# from wsgi_test import app as application



application = get_wsgi_application()

