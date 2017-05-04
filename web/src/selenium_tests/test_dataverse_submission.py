# COPO python file created 25/04/2017 by fshaw

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import unittest

browser = None
test_url = 'http://127.0.0.1:8000/copo'
sub_url = 'http://127.0.0.1:8000/copo/copo_submissions/58f6272c68236bb74cc4c070/view'


class DataverseTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        url = 'http://127.0.0.1:8000/copo/login'
        global browser
        browser = webdriver.Firefox()
        browser.get('http://127.0.0.1:8000/copo/login')
        WebDriverWait(browser, 3).until(
            EC.title_contains('COPO')
        )
        browser.find_element_by_class_name('login-button').click()
        WebDriverWait(browser, 3).until(
            EC.element_to_be_clickable((By.LINK_TEXT, "Sign In"))
        )
        browser.find_element_by_link_text('Sign In').click()
        browser.find_element_by_name("userId").send_keys('felix.shaw@tgac.ac.uk')
        browser.find_element_by_name("password").send_keys('Apple123')
        browser.find_element_by_id("login-authorize-button").click()
        WebDriverWait(browser, 3).until(
            EC.title_contains('COPO')
        )

    @classmethod
    def tearDownClass(cls):
        global browser
        browser.quit()

    def testPageTitle(self):
        browser.get(test_url)
        self.assertIn('COPO', browser.title)

    def testDataverseSubmission(self):
        browser.get(sub_url)
        browser.find_elements_by_css_selector('.upload_button')[0].click()
        self.assertIn('COPO', browser.title)

    if __name__ == '__main__':
        unittest.main(verbosity=2)
