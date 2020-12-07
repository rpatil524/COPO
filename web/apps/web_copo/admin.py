from django.contrib import admin

from web.apps.web_copo.models import UserDetails, ViewLock, banner_view

admin.site.register(UserDetails)
admin.site.register(ViewLock)
admin.site.register(banner_view)
