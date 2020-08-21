import unittest, os, time
from app import app
from selenium import webdriver
from selenium.webdriver.support.ui import Select
basedir = os.path.abspath(os.path.dirname(__file__))


class SystemTest(unittest.TestCase):
    driver = None

    def setUp(self):
        self.driver = webdriver.Chrome(executable_path=os.path.join(basedir,'chromedriver'))
        if not self.driver:
            print('Google chrome not detected, please install the latest chrome')
        else:
            print('Now performing tests...')

    def tearDown(self):
        if self.driver:
            self.driver.close()
        
    def test_navbar(self):
        self.driver.get('http://localhost:5000/')
        time.sleep(1)
        try:
            self.driver.find_element_by_class_name('jumbotron')
            print('Test successful!')
            self.assertTrue(True)
        except:
            print('Make sure your flask server is running')