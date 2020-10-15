import unittest, os, time
from selenium import webdriver
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.keys import Keys


# SystemTest class does testing on system level 
# and checks workflow from users perspective in different scenarios
# (Due to time limitation, it is not 100% coverage. 
#  However, it has fully demonstrateed the testing process and should have a good amount of coverage)

class Test(unittest.TestCase):
    driver = None

    # setUp will run before running any testing functions
    # tables are dropped and re-created to make sure emptiness
    # insert initial values into tables for later testing
    def setUp(self):
        self.driver = webdriver.Chrome()

    # tearDown runs after testing finished
    # it will close the webdriver and remove user session
    def tearDown(self):
        self.driver.close()

    # Test register
    def test_register(self):
        driver = self.driver
        driver.get("http://localhost:5000/register")
        self.assertIn("Unigames", driver.title)
        first_name_field = self.driver.find_element_by_id('first_name')
        last_name_field = self.driver.find_element_by_id('last_name')
        email_field = self.driver.find_element_by_id('email')
        password_field = self.driver.find_element_by_id('password')
        password2_field = self.driver.find_element_by_id('password2')
        submit = self.driver.find_element_by_id('submit')

        first_name_field.send_keys('Saul')
        last_name_field.send_keys('WANG')
        email_field.send_keys('hnwsr@hotmail.com')
        password_field.send_keys('wangsirui1')
        password2_field.send_keys('wangsirui1')
        submit.click()
        time.sleep(1)

        #output

        assert "No results found." not in driver.page_source

    #test Login
    def test_login(self):
        driver = self.driver
        driver.get("http://localhost:5000/login")
        self.assertIn("Login", driver.title)
        email_field = self.driver.find_element_by_id('email')
        password_field = self.driver.find_element_by_id('password')
        rememberme_field = self.driver.find_element_by_id('remember_me')
        submit = self.driver.find_element_by_id('submit')

        email_field.send_keys('hnwsr@hotmail.com')
        password_field.send_keys('wangsirui1')
        rememberme_field.click()
        submit.click()
        time.sleep(1)

        #output
        login_identifier = self.driver.find_element_by_tag_name('h3')
        self.assertEqual(login_identifier, 'Unigames Library Management System')

        return True

    def test_admin(self):
        
        #Login process
        driver = self.driver
        driver.get("http://localhost:5000/login")
        self.assertIn("Login", driver.title)
        email_field = self.driver.find_element_by_id('email')
        password_field = self.driver.find_element_by_id('password')
        rememberme_field = self.driver.find_element_by_id('remember_me')
        submit = self.driver.find_element_by_id('submit')

        email_field.send_keys('hnwsr@hotmail.com')
        password_field.send_keys('wangsirui1')
        rememberme_field.click()
        submit.click()
        time.sleep(1)

        #check
        login_identifier = self.driver.find_element_by_tag_name('h3')
        self.assertEqual(login_identifier, 'Unigames Library Management System')

        #Dashboard Operations


        #Library Operations
        #Create an item
        library=self.driver.find_element_by_id('collapseLibrary')
        library.click()
        create_link = self.driver.find_element_by_link_text('Create an item')
        create_link.click()

        title = self.driver.find_element_by_id('Title')
        description = self.driver.find_element_by_id('description')
        tag = self.driver.find_element_by_id('selection')
        submit = self.driver.find_element_by_id('submit')

        title.send_keys('aaa')
        description.send_keys('bbb')
        #tag.
        submit.click()
        time.sleep(1)

        #check
        search= self.driver.find_element_by_id('dataTable_filter')

        search.send_keys('aaa')

        search_identifier = self.driver.find_element_by_tag_id('dataTable_info')
        self.assertEqual(search_identifier, 'Showing 1 to 1 of 1 entries')


        #Search for items
        library=self.driver.find_element_by_id('collapseLibrary')
        library.click()
        search_link = self.driver.find_element_by_link_text('Search for items')
        search_link.click()
        time.sleep(1)

        search = self.driver.find_element_by_name('tagSearchInput')
        submit = self.driver.find_element_by_type('submit')

        search.send_keys('book')
        submit.click()
        time.sleep(1)

        #check
        result_identifier = self.driver.find_element_by_tag_name('h5')
        self.assertEqual(result_identifier, 'Search results')

        #All items
        library=self.driver.find_element_by_id('collapseLibrary')
        library.click()
        all_link = self.driver.find_element_by_link_text('All items')
        all_link.click()
        time.sleep(1)

        all_options = self.driver.find_element_by_name('dataTable_length')
        search = self.driver.find_element_by_id('dataTable_filter')

        for option in all_options:
            print("Value is: %s" % option.get_attribute("value"))
            option.click()
            time.sleep(1)

        search.send_keys('Bob')

        #Tags operations
        #create a tag
        tag=self.driver.find_element_by_id('#collapseItem')
        tag.click()
        time.sleep(1)
        search_link = self.driver.find_element_by_link_text('Create a tag')
        search_link.click()
        time.sleep(1)

        name = self.driver.find_element_by_id('name')
        submit = self.driver.find_element_by_id('submit')

        name.send_keys('new tag')
        submit.click()
        time.sleep(1)

        #check
        check_link = self.driver.find_element_by_link_text('new tag')
        check_link.click()
        time.sleep(1)

        check_identifier = self.driver.find_element_by_tag_name('h3')
        self.assertEqual(check_identifier, 'Tag Edit')

        #delete
        delete = self.driver.find_element_by_link_text('Delete tag')
        delete.click()
        time.sleep(1)

        alert = self.driver.switchTo().alert()
        alert.accept()
        time.sleep(1)

        check_identifier = self.driver.find_element_by_tag_name('h5')
        self.assertEqual(check_identifier, 'Tag: new tag dropped')



        #All tags
        tag=self.driver.find_element_by_id('#collapseItem')
        tag.click()
        time.sleep(1)
        search_link = self.driver.find_element_by_link_text('All tags')
        search_link.click()
        time.sleep(1)

        book_link = self.driver.find_element_by_link_text('book')
        book_link.click()
        time.sleep(1)

        # add all tags
        options = self.driver.find_element_by_id('select_parent')
        submit = self.driver.find_element_by_id('submit')
        clear_link = self.driver.find_element_by_link_text('Clear all implications')
        for option in options:
            print("Value is: %s" % option.get_attribute("value"))
            option.click()
            submit.click()
            time.sleep(1)
        clear_link.click()
        

        #All implicatoins
        tag=self.driver.find_element_by_id('#collapseItem')
        tag.click()
        search_link = self.driver.find_element_by_link_text('All implicatoins')
        search_link.click()
        time.sleep(1)

        all_options = self.driver.find_element_by_name('dataTable_length')
        for option in all_options:
            print("Value is: %s" % option.get_attribute("value"))
            option.click()
            time.sleep(1)

        

