from django.contrib.auth.models import User
from django.http import HttpResponse

import dal.copo_da as da
from dal.copo_da import Sample


def get_number_of_users(request):
    users = User.objects.all()
    number = len(users)
    return HttpResponse(number)


def get_number_of_samples(request):
    number = Sample().get_number_of_samples()
    return HttpResponse(number)


def get_number_of_profiles(request):
    number = da.handle_dict["profile"].count({})
    return HttpResponse(number)


def get_number_of_datafiles(request):
    number = da.handle_dict["datafile"].count({})
    return HttpResponse(number)
