from django.conf.urls import patterns, include, url

from django.contrib import admin
admin.autodiscover()

import hello.views
import api.views

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'hello.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),

    url(r'^$', hello.views.index, name='index'),
    url(r'^api', api.views.index, name='index'),


)