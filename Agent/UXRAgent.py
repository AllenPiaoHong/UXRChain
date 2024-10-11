import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import platform
import argparse
import time
import json
import re
import os
import shutil
import logging
import requests
from prompts import SYSTEM_UXRMember_InitRQ_Prompt_Temp,SYSTEM_UXRMember_UserProduce_Prompt_Temp,SYSTEM_Interviewer_Prompt 

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from utils import *
from utils import format_msg 
from UserAgent import Useragent

class  UXStudyExcutionAgent():

    def __init__(self,logging,info=""):

        self.init_message = info
        self.logging = logging
        self.messages = []

    def study_execute(self,Question_list,User,Study_type): 

        if Study_type == "Interviews":
            self.logging.info(f'#############Interview UXTeam Agent Working##########')
            self.messages.append({'role': 'system', 'content': SYSTEM_Interviewer_Prompt})
            for i in range(len(Question_list)):

                self.logging.info("###############Now we have a new question##############")
                Current_Question = Question_list[i]
                init_msg = "[Transcript]: "+ Current_Question
                curr_msg = format_msg_interviewer(init_msg)
                self.messages.append(curr_msg)
                error_messages, speaking_interviewer  = call_gpt4v_UI(self.messages,self.logging)
                response_interviewee = User.interview(speaking_interviewer)
                self.logging.info("New question from the interviewer: "+speaking_interviewer.strip())
                self.logging.info("The response from the interviewee: "+response_interviewee.strip())

                self.messages.append({'role': 'assistant', 'content': "[Transcript Question]: "+speaking_interviewer})
                self.messages.append({'role': 'user', 'content': "[User response]: "+response_interviewee})
                error_messages, speaking_interviewer  = call_gpt4v_UI(self.messages,self.logging)

                while "New Transcript" not in speaking_interviewer:
                    
                    self.messages.append({'role': 'assistant', 'content': speaking_interviewer})
                    self.logging.info("Further question from the interviewer "+speaking_interviewer.strip())
                    response_interviewee = User.interview(speaking_interviewer)
                    self.messages.append({'role': 'user', 'content': "[User response]: "+response_interviewee})
                    self.logging.info("The response from the interviewee: "+response_interviewee.strip())
                    error_messages, speaking_interviewer  = call_gpt4v_UI(self.messages,self.logging)
            

class UXDemographicAgent():

    def __init__(self,logging,info=""):

        self.init_message = info
        self.logging = logging
        
    def generate_user(self,demographic,user_amount):
        
        self.logging.info(f'#############User Generation Agent Working##########')
        messages = [{'role': 'system', 'content': self.init_message + " " + SYSTEM_UXRMember_UserProduce_Prompt_Temp}]
        init_msg = "Now we have following user generation requirements, please start "+user_amount+"user generation: "+demographic
        curr_msg = format_msg(init_msg,0)
        messages.append(curr_msg)
        error_messages, gpt_4v_res  = call_gpt4v_UI(messages,self.logging)
        self.logging.info(gpt_4v_res)
        messages.append({'role': 'assistant', 'content': gpt_4v_res})
        user_number_generated =  len(re.findall(r'User \d+',gpt_4v_res))
        # if user_number_generated<int(user_amount):
        #     iterative_message = "Now we have following user generation requirements, please start "+user_amount-user_number_generated+"user generation: "+demographic
        #     curr_msg = format_msg_user(iterative_message,1)
        #     messages.append(curr_msg)
        #     error_messages, gpt_4v_res  = call_gpt4v_UI(messages,self.logging)
        #     self.logging.info(gpt_4v_res)
        return gpt_4v_res

class UXPlanningAgent():

    def __init__(self,index,args,result_dir,info=""):

        self.init_message = info
        self.options = driver_config(args)
        self.logging = setup_logger(result_dir,index)
        self.args=args
        self.index = index
        self.driver_task = self.init_task()
        self.task_dir = result_dir

    def init_task(self):
        
        self.logging.info(f'#########Study Plannning Agent Working##########')
        self.driver_task = webdriver.Chrome(options=self.options)
        self.driver_task.maximize_window()
        return self.driver_task
    
    def work(self,task):

        # with open('cookies.txt','r') as cookief:
        #     cookieslist = json.load(cookief)
        #     for cookie in cookieslist:
        #         self.driver_task.add_cookie(cookie)

        # usr_data_dir ="C:\\Users\\Allen\\AppData\\Local\\Google\\Chrome\\User Data"
        # self.options.add_argument(f'--user-data-dir={usr_data_dir}')
       
        script = '''
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined
        })
        '''
        self.driver_task.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {"source": script})
        
        self.driver_task.get(task['web'])
        self.driver_task.delete_all_cookies()

        with open('cookies.txt','r') as cookief:
            cookieslist = json.load(cookief)
            for cookie in cookieslist:
                self.driver_task.add_cookie(cookie)    
        self.driver_task.refresh()

        # time.sleep(30)

        # with open('cookies.txt','w') as cookief:
        #     cookief.write(json.dumps(self.driver_task.get_cookies()))
        # print("cookie_finish")
        
        # self.driver.close()

        time.sleep(30)
        self.driver_task.execute_script("""window.onkeydown = function(e) {if(e.keyCode == 32 && e.target.type != 'text' && e.target.type != 'textarea') {e.preventDefault();}};""")

        pattern  = r'\[Method\]|\[Number of Users\]|\[The requirement of the recruited users\]|\[Study Plan\]'
        messages = [{'role': 'system', 'content': self.init_message + " " + SYSTEM_UXRMember_InitRQ_Prompt_Temp}]

        init_msg = f"""Now given a task: {task['ques']}  Please interact with https://www.example.com and get the answer. \n"""
        init_msg = init_msg.replace('https://www.example.com', task['web'])
        init_msg = init_msg 
        time.sleep(10)

        try:
            rects, web_eles, web_eles_text,web_eles_text_list = get_web_element_rect(self.driver_task, fix_color=self.args.fix_box_color)
        except Exception as e:
                self.logging.error('Driver error when adding set-of-mark.')
                self.logging.error(e)

        img_path = os.path.join(self.task_dir,'study_page.png')
        self.driver_task.save_screenshot(img_path)
        compress_image(img_path)
    
        b64_img = encode_image(img_path)
        curr_msg = format_msg_planner(1, init_msg=init_msg, warn_obs="",web_img_b64=b64_img, web_text=web_eles_text)
        messages.append(curr_msg)
        messages = clip_message_and_obs(messages, self.args.max_attached_imgs)
        
        error_messages, gpt_4v_res  = call_gpt4v_UI(messages,self.logging)
        # self.logging.info(gpt_4v_res)
        try:
            assert "Method" in gpt_4v_res and "Number of Users" in gpt_4v_res and "The requirement of the recruited users" in gpt_4v_res and "Study Plan" in gpt_4v_res
        except:
            self.logging.info("Plan wrong format V1")
            error_messages, gpt_4v_res  = call_gpt4v_UI(messages,self.logging)

        try:
            research_method = re.split(pattern, gpt_4v_res)[1].strip()
            user_number = re.split(pattern, gpt_4v_res)[2].strip()
            user_requirement = re.split(pattern, gpt_4v_res)[3].strip()
            study_plan = re.split(pattern, gpt_4v_res)[4].strip()
        except:
            self.logging.info("Plan wrong format V2")
            error_messages, gpt_4v_res  = call_gpt4v_UI(messages,self.logging)

        while True:

            try:
                self.logging.info("Research Method: "+re.split(pattern, gpt_4v_res)[1].strip())
                self.logging.info("User Number: "+re.split(pattern, gpt_4v_res)[2].strip())
                self.logging.info("User Requirement: "+re.split(pattern, gpt_4v_res)[3].strip())
                self.logging.info("Study Plan: "+re.split(pattern, gpt_4v_res)[4].strip())
                research_method = re.split(pattern, gpt_4v_res)[1].strip()
                user_number = re.split(pattern, gpt_4v_res)[2].strip()
                user_requirement = re.split(pattern, gpt_4v_res)[3].strip()
                study_plan = re.split(pattern, gpt_4v_res)[4].strip()
                self.driver_task.quit()
                break 
            except:
                self.logging.info("Plan wrong format V3")
                error_messages, gpt_4v_res  = call_gpt4v_UI(messages,self.logging)
                curr_msg = {
                        'role': 'user',
                        'content': "Please strictly follow the required format to generate again."
                    }
                messages.append(curr_msg)
                error_messages, gpt_4v_res  = call_gpt4v_UI(messages,self.logging)

        return research_method,user_number,user_requirement,study_plan,self.logging

if __name__ == "__main__": 

    parser = argparse.ArgumentParser()
    parser.add_argument('--test_file', type=str, default='../task/tasks_test.json')
    parser.add_argument('--max_iter', type=int, default=20)
    parser.add_argument("--output_dir", type=str, default='results')
    parser.add_argument("--max_attached_imgs", type=int, default=2)
    parser.add_argument("--temperature", type=float, default=1.0)
    parser.add_argument("--download_dir", type=str, default="downloads")
    parser.add_argument("--text_only", action='store_true')
    parser.add_argument("--headless", action='store_true', help='The window of selenium')
    parser.add_argument("--window_width", type=int, default=1024)
    parser.add_argument("--window_height", type=int, default=768)  # for headless mode, there is no address bar
    parser.add_argument("--fix_box_color", action='store_true')
    args = parser.parse_args()

    current_time = time.strftime("%Y%m%d_%H_%M_%S", time.localtime())
    result_dir = os.path.join(args.output_dir, current_time)
    result_clear_dir = os.path.join(args.output_dir, current_time,"clear")
    os.makedirs(result_dir, exist_ok=True) 
    os.makedirs(result_clear_dir, exist_ok=True) 

    tasks = []
    with open(args.test_file, 'r', encoding='utf-8') as f:
        for line in f:
            tasks.append(json.loads(line))
    task = tasks[0]

    args = parser.parse_args()
    planning_agent = UXPlanningAgent(result_dir=result_dir,index=0,args=args)
    research_method,user_number,user_requirement,study_plan,study_logging = planning_agent.work(task)
    questions = re.findall(r'\[Interview Question \d+\](.*?\?)',study_plan)
    pattern = r'\[User \d+\]\[Age\](.*?)\[Online Shopping Preference\](.*?)\[Online Shopping Habits\](.*?)\[Gender\](.*?)\[Job\](.*?)\[Aesthetic Preference\](.*?)\[Cultural Background\](.*?)\[Educational Level\](.*?)\[Personality\](.*?)\[Internet usage level\](.*?)\[recent emotions\](.*?)\[reason for joining\](.*?)(?=\[User \d+\]|$)'

    with open(args.test_file, 'r', encoding='utf-8') as f:
        for line in f:
            tasks.append(json.loads(line))
    task = tasks[0]

    demo_agent = UXDemographicAgent(study_logging)
    demo_info = demo_agent.generate_user(user_requirement,user_number)
    # print(demo_info)
    
    demo_info_list = []
    user_pattern = r'\[User \d+\](.*?)((?=\[User \d+\])|\Z)'
    user_matches = re.findall(user_pattern, demo_info, re.DOTALL)

    for user in user_matches:
        user_info = user[0] or user[1]  # 选择非空的匹配
        fields = re.findall(r'\[(.*?)\](.*?)(?=\[|$)', user_info)
        user_dict = {field[0]: field[1].strip() for field in fields}
        demo_info_list.append(user_dict)

    # print(len(demo_info_list))


    for i in range(len(demo_info_list)):

        match = demo_info_list[i]

        age = match["Age"]
        shopping_preference = match["Online Shopping Preference"]
        shopping_habits = match["Online Shopping Habits"]
        gender = match["Gender"]
        job = match["Job"]
        aesthetic_preference = match["Aesthetic Preference"]
        cultural_background = match["Cultural Background"]
        educational_level = match["Educational Level"]
        personality = match["Personality"]
        internet_usage_level = match["Internet usage level"]
        description = (
            f"A {age}-year-old {gender} who works as a {job}. "
            f"They prefer {shopping_preference} when shopping online, focusing on {shopping_habits}. "
            f"With a {educational_level}, they have a {personality} personality and an aesthetic preference for {aesthetic_preference}. "
            f"Their cultural background is {cultural_background}, and they are highly proficient with the internet, "
            f"spending 4-5 hours on websites daily. Recently, they have felt generally positive but slightly stressed due to work deadlines. "
            f"They are interested in exploring new online shopping experiences and trends."
        )
        study_logging.info(description)
        execute_agent = UXStudyExcutionAgent(study_logging)
        user_agent = Useragent(logging=study_logging,result_dir=result_dir,result_clear_dir=result_clear_dir,index=i+1,args=args, demographic=description)
        user_agent.work(task)
        execute_agent.study_execute(questions,user_agent,"Interviews")
