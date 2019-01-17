from unittest import TestCase
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
import threading
import os





def _upload():
    options = Options()
    options.headless = False
    client = webdriver.Firefox(options=options)
    url = "http://demo.copo-project.org/copo"
    client.get(url)
    login_link = client.find_element_by_class_name("login-button")
    login_link.click()
    # sign into orcid
    username = client.find_element_by_id("userId")
    username.send_keys("felix.shaw@tgac.ac.uk")
    username = client.find_element_by_id("password")
    username.send_keys("Apple123")
    login_submit = client.find_element_by_id("form-sign-in-button")
    login_submit.click()
    # check for authorize
    try:
        authorize = WebDriverWait(client, 4).until(
            EC.presence_of_element_located((By.ID, "authorize"))
        )
        authorize.click()
    except:
        pass

    if "COPO" not in client.title:
        return False
        client.close()

    # go to uploads page
    element = client.find_elements_by_partial_link_text("Datafile")
    if type(element) is type(list()):
        element = element[0]
    element.click()
    WebDriverWait(client, 0.5)
    element = client.find_element(By.LINK_TEXT, "Upload")
    element.click()
    try:
        file_upload = WebDriverWait(client, 4).until(
            EC.presence_of_element_located((By.NAME, "file"))
        )
        f = client.find_element_by_name("file")
        client.execute_script("$('input[type=\"file\"]').val('/Users/fshaw/Desktop/small1_test.fastq'); $('input[type=\"file\"]').change()")
        #f.send_keys("/Users/fshaw/Desktop/small1_test.fastq")
        #doc = client.find_element_by_xpath("//html")
        #doc.click()

    except e:
        print(e)
    try:
        hash = WebDriverWait(client, 3).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".hash_span"))
        )
        print("file hashed....exiting")
    except:
        print("File not hashed")
    finally:
        #pass
        client.close()


def _test_text():
    url = "http://127.0.0.1:8000/copo/test"
    options = Options()
    options.headless = False
    client = webdriver.Firefox(options=options)
    client.get(url)



    el = client.find_element_by_id("input_text")
    el.send_keys("here")


for m in range(0, 1):
    #t = threading.Thread(target=_upload)
    t = threading.Thread(target=_upload)
    t.start()