from django.contrib.auth.models import User
from dal.copo_da import Sample
from django.http import HttpResponse
import json

def get_number_of_users(request):
    users = User.objects.all()
    number = len(users)
    return HttpResponse(json.dumps({"number_found":number}))

def get_number_of_dtol_samples(request):
    number = Sample().get_number_of_dtol_samples()
    return HttpResponse(json.dumps({"number_found": number}))