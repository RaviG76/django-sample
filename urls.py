from django.conf.urls import patterns, include, url
from django.views.generic import TemplateView
from django.contrib.auth.decorators import login_required

from services.views import *

urlpatterns = patterns('',
    url(r'v1/', include([
        url(r'^lead/(?P<method>\w{1,50})/$', process_request),
        url(r'^lead/(?P<method>\w{1,50})/$', process_request),
    ])),
)