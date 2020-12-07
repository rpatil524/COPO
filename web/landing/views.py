from django.shortcuts import render

from web.apps.web_copo.models import banner_view


def index(request):
    banner = banner_view.objects.all()
    if len(banner) > 0:
        context = {'user': request.user, "banner": banner[0]}
    else:
        context = {'user': request.user}
    return render(request, 'index_new.html', context)
