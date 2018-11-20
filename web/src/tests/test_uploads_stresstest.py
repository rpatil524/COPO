# Created by fshaw at 14/11/2018
from unittest import TestCase
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

class UploadStressTest(TestCase):

    client = None
    url = None

    @classmethod
    def setUpClass(cls):
        # start Firefox
        try:
            options = Options()
            options.headless = True
            cls.client = webdriver.Firefox(options=options)
            cls.url = "http://demo.copo-project.org/copo"
        except:
            pass

    def test_get_page(self):
        self.client.get(self.url)
        self.assertTrue("COPO" in self.client.title)

    def test_login(self):
        self.client.get(self.url)
        login_link = self.client.find_element_by_class_name("login-button")
        login_link.click()
        self.assertTrue("ORCID" in self.client.title)
        # sign into orcid
        username = self.client.find_element_by_id("userId")
        username.send_keys("felix.shaw@tgac.ac.uk")
        username = self.client.find_element_by_id("password")
        username.send_keys("Apple123")
        login_submit = self.client.find_element_by_id("form-sign-in-button")
        login_submit.click()
        # check for authorize
        try:
            authorize = WebDriverWait(self.client, 3).until(
                EC.presence_of_element_located((By.ID, "authorize"))
            )
            authorize.click()
        except:
            pass

        self.assertTrue("COPO" in self.client.title)



    @classmethod
    def tearDownClass(cls):
        cls.client.close()