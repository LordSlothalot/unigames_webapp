# System tests written by : Mingchuan Tian (22636589)

import unittest, os, time
from app import app, db
from app.models import User
from app.models import User, Question, QuizSet, Answer, Grade
from selenium import webdriver
from selenium.webdriver.support.ui import Select
basedir = os.path.abspath(os.path.dirname(__file__))

# SystemTest class does testing on system level 
# and checks workflow from users perspective in different scenarios
# (Due to time limitation, it is not 100% coverage. 
#  However, it has fully demonstrateed the testing process and should have a good amount of coverage)

class SystemTest(unittest.TestCase):
    driver = None

    # setUp will run before running any testing functions
    # tables are dropped and re-created to make sure emptiness
    # insert initial values into tables for later testing
    def setUp(self):
        self.driver = webdriver.Firefox(executable_path=os.path.join(basedir,'geckodriver'))
        if not self.driver:
            self.skipTest
        else:
            db.init_app(app)
            db.drop_all()
            db.create_all()
            u1 = User(name='Ming', email='mingchuantian@gmail.com', faculty="Science", title="Mr.", phone = "499382201", is_teacher=True, address="311 road") 
            u1.set_password('mingchuan')
            db.session.add(u1)
            u2 = User(name='chenshu', email='chenshu730@gmail.com', faculty="Science", title="Mrs.", phone = "499382201", is_teacher=False, address="311 road") 
            u2.set_password('chenshu')
            db.session.add(u2)
            quizset1 = QuizSet(title="testquiz", quiz_id="888", question_num=1, time_limit=2)
            question1 = Question(Question='Test question', quizset_id=1)
            db.session.add(quizset1)
            db.session.add(question1)
            db.session.commit()
            self.driver.maximize_window()

    # tearDown runs after testing finished
    # it will close the webdriver and remove user session
    def tearDown(self):
        if self.driver:
            self.driver.close()
            db.session.remove()

    # Test teacher's account login function
    # returns ERROR or False if anything goes wrong
    def test_login(self):
        self.driver.get('http://localhost:5000/login/teacher?')
        time.sleep(1) 
        email_field = self.driver.find_element_by_id('email')
        password_field = self.driver.find_element_by_id('password') 
        submit = self.driver.find_element_by_id('submit')

        email_field.send_keys('mingchuantian@gmail.com')
        password_field.send_keys('mingchuan')
        submit.click()
        time.sleep(1)

        login_identifier = self.driver.find_element_by_id('Logged in successful').get_attribute('innerHTML')
        self.assertEqual(login_identifier, 'The University of Western Australia')
    
    
    # Test user's register function
    # returns ERROR or False if anything goes wrong
    def test_register(self):
        self.driver.get('http://localhost:5000/register?')
        time.sleep(1)
        name_field = self.driver.find_element_by_id('name')
        email_field = self.driver.find_element_by_id('email')
        password_field = self.driver.find_element_by_id('password')
        is_teacher = self.driver.find_element_by_id('teacher')
        submit = self.driver.find_element_by_id('submit')

        name_field.send_keys('tian')
        email_field.send_keys('1120509786@qq.com')
        password_field.send_keys('Tianmingchuan123')
        is_teacher.click()
        submit.click()
        time.sleep(4)

        signup_identifier = self.driver.find_element_by_id('notif').get_attribute('innerHTML')
        self.assertEqual(signup_identifier, 'The user is successfully registered')
    

    
    # Test teacher's workflow for adding a new quiz
    # returns ERROR or False if anything goes wrong
    
    def test_addQuiz(self):
        #Login process
        self.driver.get('http://localhost:5000/login/teacher?')
        time.sleep(1) 
        email_field = self.driver.find_element_by_id('email')
        password_field = self.driver.find_element_by_id('password') 
        submit = self.driver.find_element_by_id('submit')

        email_field.send_keys('mingchuantian@gmail.com')
        password_field.send_keys('mingchuan')
        submit.click()
        time.sleep(1)

        login_identifier = self.driver.find_element_by_id('Logged in successful').get_attribute('innerHTML')
        self.assertEqual(login_identifier, 'The University of Western Australia')

        #Open quiz page
        make_quiz = self.driver.find_element_by_id('b1')
        make_quiz.click()
        time.sleep(1)
        quiz_identifier = self.driver.find_element_by_id('quizPage')    #return null if not found
        self.assertTrue(quiz_identifier)    

        #add quiz
        title = self.driver.find_element_by_id('title')
        quizID =self.driver.find_element_by_id('quiz_id')
        question_num = Select(self.driver.find_element_by_id('question_num'))
        time_limit = self.driver.find_element_by_id('time_limit')
        submit = self.driver.find_element_by_id('submit')
        title.send_keys('This is test quiz')
        quizID.send_keys('111')
        question_num.select_by_value('1')
        time_limit.send_keys('30')
        submit.click()
        time.sleep(1)

        #add question
        question = self.driver.find_element_by_id('question')
        submit = self.driver.find_element_by_id('submit')
        question.send_keys('This is a test question')
        submit.click()

        #check database
        q = Question.query.get(2)
        self.assertTrue(q.Question == 'This is a test question')