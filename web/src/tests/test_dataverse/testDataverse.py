# Created by fshaw at 05/11/2018
from django.test import TestCase
from submission.dataverseSubmission import DataverseSubmit
from django.contrib.auth.models import User

class testDataverse(TestCase):

    def setUp(self):
        u = User.objects.create_user(username='john',
                                 email='jlennon@beatles.com',
                                 password='norwegianwood')
