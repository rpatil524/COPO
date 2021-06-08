import tempfile

import pandas
import pymongo
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


def combined_stats_json(request):
    stats = da.cursor_to_list(da.handle_dict["stats"].find({}, {"_id": 0}).sort('date', pymongo.DESCENDING))
    df = pandas.DataFrame(stats, index=None)
    return HttpResponse(df.reset_index().to_json(orient='records'))


def samples_stats_csv(request):
    stats = da.cursor_to_list(
        da.handle_dict["stats"].find({}, {"_id": 0, "date": 1, "samples": 1, }).sort('date', pymongo.ASCENDING))
    df = pandas.DataFrame(stats, index=None)
    df = df.rename(columns={"samples": "num"})
    x = df.to_json(orient="records")
    return HttpResponse(x, content_type="text/json")
