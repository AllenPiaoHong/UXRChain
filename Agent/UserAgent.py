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

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from prompts import SYSTEM_UI_PROMPT_Example,Interviewee_PROMPT_Example

from utils import *

class Useragent():

    def __init__(self,index,args,logging,result_dir,result_clear_dir,demographic,info=""):

        self.init_message = info
        self.options = driver_config(args)
        self.logging = logging
        self.args=args
        self.index = index
        self.driver_task = self.init_task()
        self.task_dir = result_dir
        self.messages = []
        self.demograpic = demographic
        self.result_clear_dir = result_clear_dir

    def interview(self,question):

        # self.logging.info(f'#########UX Team Starts Interviewing with Agent {self.index}##########')
        self.messages.append({'role': 'system', 'content':Interviewee_PROMPT_Example})
        curr_msg = format_msg(question,1)
        self.messages.append(curr_msg)
        error_messages, gpt_4v_res  = call_gpt4v_User(self.messages,self.logging)
        self.messages.append({'role': 'assistant', 'content': gpt_4v_res})
        return gpt_4v_res
        # self.logging.info(gpt_4v_res)

    def init_task(self):
        
        self.logging.info(f'#############User Agent {self.index} Working##########')
        self.driver_task = webdriver.Chrome(options=self.options)
        self.driver_task.maximize_window()

        return self.driver_task
    
    def work(self,task):

        max_time = 1
        current_time = 0
        last_action = ""
        last_last_action = ""
        last_round_info = ""

        while (current_time<max_time):
            current_time +=1
            self.driver_task.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {"source": """Object.defineProperty(navigator, 'webdriver', {get: () => false})"""})
            self.driver_task.get(task['web'])
            time.sleep(20)
            self.driver_task.execute_script("""window.onkeydown = function(e) {if(e.keyCode == 32 && e.target.type != 'text' && e.target.type != 'textarea') {e.preventDefault();}};""")
            self.driver_task.delete_all_cookies()

            with open('cookies.txt','r') as cookief:
                cookieslist = json.load(cookief)
                for cookie in cookieslist:
                    self.driver_task.add_cookie(cookie)
                    
            self.driver_task.refresh()
            time.sleep(10)
            # self.driver_task.execute_script("""window.onkeydown = function(e) {if(e.keyCode == 32 && e.target.type != 'text' && e.target.type != 'textarea') {e.preventDefault();}};""")

            fail_obs = ""  # When error execute the action
            warn_obs = ""  # Type warning
            # pattern = r'Reflection:|Thought:|Action:|Improvement Advices:|Function Perceive:|ActionComparison:'
            pattern = r'ActionComparison:|Thought:|Action:|Improvement Advices:|Reflection:'

            self.messages.append({'role': 'system', 'content': self.init_message+" "+ SYSTEM_UI_PROMPT_Example+" and this your demographic information "+ self.demograpic})

            init_msg = f"""Now given a task: {task['users']}  Please interact with https://www.example.com and get the answer. Remember you need to include Reflection, Thought, Action, and Improvement in your replies!\n"""
            init_msg = init_msg.replace('https://www.example.com', task['web'])
            # init_msg += "You last action on the web page is " + last_action

            previous_action =""
            it = 0
            while(it<self.args.max_iter):
                
                it += 1
                self.logging.info("######### Times: "+str(current_time)+" ######### Operation: "+str(it)+"#######################")
                time.sleep(15)

                if not fail_obs:
                    init_msg = ""
                    try:
                        rects, web_eles, web_eles_text,web_eles_text_list = get_web_element_rect(self.driver_task, fix_color=self.args.fix_box_color)
                    except Exception as e:
                            self.logging.error('Driver error when adding set-of-mark.')
                            self.logging.error(e)
                            break
                    img_path = os.path.join(self.task_dir, "time_"+str(current_time)+' _agent_'+str(self.index)+'_screenshot_{}.png'.format(it))
                    img_path_clear = os.path.join(self.result_clear_dir, "time_"+str(current_time)+' _agent_'+str(self.index)+'_screenshot_{}_clear.png'.format(it))
                    self.driver_task.save_screenshot(img_path)
                    self.driver_task.save_screenshot(img_path_clear)
                    compress_image(img_path)
                    b64_img = encode_image(img_path)
                    if it >2:
                        init_msg += "Remember two actions are similar are because they are interacting with same element (e.g., element with same tag text and tag number) \
                            or keep typing sentences without responses from the web pages. Otherwise, these two elements are not silimar"
                        init_msg += "Currently, you last action on the web page is "+last_action + "Your last last action is " + last_last_action +\
                                          ".You need to carefully reply wheather these two actions are similar or not in your reply.\
                                          Please just justify the similartiy these actions and do not confuse with the previous actions."
                        self.logging.info("You last action on the web page is "+last_action + " Your last last action is " + last_last_action)
                        if last_last_action==last_action:
                            self.logging.info("From rules: The actions should be the same")
                            init_msg += "Your previous two actions are similar."
                        else:
                            init_msg += "Your previous two actions are not similar. Now you need to carefully consider whether your previous two actions are interacting with same element."
                        init_msg += "This is the information from your last round "+last_round_info+".You need to pay attention to whether your similarity output is wrong \
                            or whether you have kept acting similar actions or whether you last action is satiefied or not"
                        init_msg += "Remember! The last action and the last last action are similar are because they are interacting with same element (e.g., element with same tag text and tag number) \
                            or keep typing sentences without responses from the web pages. Otherwise, these two elements are not silimar!"
                        init_msg += "Your last action on the web page is "+last_action + "Your last last action is " + last_last_action
                        init_msg += "Remember you are comparing your last action and last last action! Not other actions! Do not compare with your current action !"
                        init_msg += "Also, try to avoid taking the same action as the previous two ones."

                    curr_msg = format_msg_user(it,init_msg, warn_obs, b64_img, web_eles_text)
                    # logging.info(curr_msg)
                    self.messages.append(curr_msg)
                
                else:
                    curr_msg = {
                        'role': 'user',
                        'content': fail_obs + " Please conduct other action on this page."
                    }
                    self.messages.append(curr_msg)

                self.messages = clip_message_and_obs(self.messages, self.args.max_attached_imgs)
                error_messages, gpt_4v_res  = call_gpt4v_User(self.messages,self.logging)

                if gpt_4v_res is None:

                    self.logging.error("Sever Reponse Issue")
                    self.messages.pop()
                    it-=1
                    continue

                try:
                    assert 'Thought:' in gpt_4v_res and 'Action:' in gpt_4v_res and "Reflection" in gpt_4v_res and "ActionComparison" in gpt_4v_res
                
                except AssertionError as e:
                    
                    self.logging.error("Output format problem")
                    it-=1
                    fail_obs = "'ActionComparison','Thought','Action', 'Improvement Advices', and 'Reflection' should be included in your reply. Please strictly follow the format to reply."
                    continue
                
                try:
                    assert '[Evaluation]' in re.split(pattern, gpt_4v_res)[1].strip() and "[Reason]" in re.split(pattern, gpt_4v_res)[1].strip() and "[Last Action]" in re.split(pattern, gpt_4v_res)[1].strip() and "[Last Last Action]" in re.split(pattern, gpt_4v_res)[1].strip() and "[Reason]" in re.split(pattern, gpt_4v_res)[1].strip() and "[Similarity]" in re.split(pattern, gpt_4v_res)[1].strip()
                
                except AssertionError as e:
                    
                    self.logging.error("Output format problem in actioncomparison")
                    self.logging.info(gpt_4v_res)
                    it-=1
                    # self.logging.error(e)
                    fail_obs = "[Evaluation],[Reason],[Last Action],[Last Last Action],[Similarity],[Reason]should be included in your actioncomparison section. Please strictly follow the format to reply again."
                    continue

                try:
                    assert not(it>2 and "None" in re.split(pattern, gpt_4v_res)[1].strip())

                except AssertionError as e:

                    self.logging.error("Similarity Wrong")
                    it-=1
                    print("Similarity Wrong")
                    fail_obs = " You should not answer 'None in actioncomparison, you should carefully compare the last two actions"
                    continue

                try:
                    if(it>2):
                    
                        assert re.split(pattern, gpt_4v_res)[1].strip()
                        last_action_pattern = r'\[Last Action\](.*?)\[Last Last Action\](.*?)\[Similarity\]'
                        matches = re.search(last_action_pattern, re.split(pattern, gpt_4v_res)[1])
                        last_action_content = matches.group(1).strip()
                        last_last_action_content = matches.group(2).strip()
                        assert(last_action_content==last_action and last_last_action_content==last_last_action)

                        # if matches!=None:
                        #     last_action_agent = matches.group(1).strip()
                        #     last_last_action_agent = matches.group(2).strip()
                        #     assert (last_action==last_action_agent and last_last_action==last_last_action_agent)
                        # else:
                        #     last_action_pattern= r'\[Last Action\](.*?)\[Last Last Action\](.*?)\[Similarity\]'
                        #     matches = re.search(last_action_pattern, re.split(pattern, gpt_4v_res)[1])
                        #     if matches!=None:
                        #         last_action_agent = matches.group(1).strip()
                        #         last_last_action_agent = matches.group(2).strip()
                        #         assert (last_action==last_action_agent and last_last_action==last_last_action_agent)
                        #     else:
                        #         last_action_pattern= r'\[Last Action\].*?(\d+).*?\[Last Last Action\](.*?)\[Similarity\]'
                        #         matches = re.search(last_action_pattern, re.split(pattern, gpt_4v_res)[1])
                        #         if matches!=None:
                        #             last_action_agent = matches.group(1).strip()
                        #             last_last_action_agent = matches.group(2).strip()
                        #             assert (last_action==last_action_agent and last_last_action==last_last_action_agent)
                        #         else:
                        #             last_action_pattern= r'\[Last Action\](.*?)\[Last Last Action\].*?(\d+).*?\[Similarity\]'
                        #             matches = re.search(last_action_pattern, re.split(pattern, gpt_4v_res)[1])
                            
                except AssertionError as e:

                    it-=1
                    self.logging.error("Similarity Mess")
                    self.logging.info(re.split(pattern, gpt_4v_res)[1])
                    self.logging.info(last_action)
                    self.logging.info(last_last_action)
                    fail_obs = " You do not answer the last action and last last action correctly. "+"Your last action on the web page is "+last_action + "Your last last action is " + last_last_action+" .Please generate again."
                    continue

                self.messages.append({'role': 'assistant', 'content': gpt_4v_res})
                # self.logging.info(gpt_4v_res)

                if (not self.args.text_only) and rects:
                    for rect_ele in rects:
                        self.driver_task.execute_script("arguments[0].remove()", rect_ele)
                    rects = []

                # print("Your actioncomparison "+re.split(pattern, gpt_4v_res)[1].strip())

                chosen_action = re.split(pattern, gpt_4v_res)[3].strip()
                last_last_action = last_action
                # last_action = chosen_action
                action_key, info = extract_information(chosen_action)
                self.logging.info(gpt_4v_res)
                last_round_info = ""

                # if "Not sat" in re.split(pattern, gpt_4v_res)[1].strip() or "not sat" in re.split(pattern, gpt_4v_res)[1].strip():
                #         last_round_info= "Your last action " +chosen_action+ "does not help you get satisfied responses. I recomemnd you do not conduct the action:" +chosen_action +"next time"
                #         self.logging.info("Not satisfies for last action.")         
                # if it>2 and "Not similar" not in re.split(pattern, gpt_4v_res)[1].strip():
                #         self.logging.info("Similar Actions Detected")
                #         last_round_info = last_round_info+" You have conducted a simiar action for more than two times. Try to interact with other elements."
                #         self.logging.info("Similar Actions:" + last_last_action+ "have been conducted before for multiple times. You should try to conduct other actions.")
                #         self.messages.append({'role': 'user', 'content': "Similar Actions:" + last_last_action+ " have been conducted before for multiple times. You should try to conduct other actions."})
                #         error_messages, gpt_4v_res  = call_gpt4v_User(self.messages,self.logging)
                #         self.messages.append({'role': 'assistant', 'content': gpt_4v_res})
                
                # print("Problem here "+re.split(pattern, gpt_4v_res)[1].strip())
                # print("None" in re.split(pattern, gpt_4v_res)[1].strip())
                # self.logging.info(gpt_4v_res)
                # print(re.split(pattern, gpt_4v_res)[1].strip())
                # print("None" in re.split(pattern, gpt_4v_res)[1].strip() )
                # print(it)

                # if it>2 and "None" in str(re.split(pattern, gpt_4v_res)[1].strip()):
                # # if "None" in re.split(pattern, gpt_4v_res)[1].strip():
                #         self.logging.info("Similarity Wrong")
                #         print("Similarity Wrong")
                #         last_round_info = last_round_info+" You should not answer 'None in actioncomparison, you should carefully compare the last two actions"
                #         self.messages.append({'role': 'user', 'content': " You should not answer 'None in actioncomparison, you should carefully compare the last two actions and generate again."})
                #         error_messages, gpt_4v_res  = call_gpt4v_User(self.messages,self.logging)
                #         self.messages.append({'role': 'assistant', 'content': gpt_4v_res})

                if "Not sat" in re.split(pattern, gpt_4v_res)[1].strip() or "not sat" in re.split(pattern, gpt_4v_res)[1].strip():
                    last_round_info= "Your last action " +chosen_action+ "does not help you get satisfied responses. I recomemnd you do not conduct the action:" +chosen_action +"next time"
                    self.logging.info("Not satisfies for last action.")

                if it>2 and "Not similar" not in re.split(pattern, gpt_4v_res)[1].strip():
                    self.logging.info("Similar Actions Detected")
                    last_round_info = last_round_info+" You have conducted a simiar action for more than two times. Try to interact with other elements."
                    self.logging.info("Similar Actions:" + last_last_action+ "have been conducted before for multiple times. You should try to conduct other actions.")
                    self.messages.append({'role': 'user', 'content': "Similar Actions:" + last_last_action+ " have been conducted before for multiple times. You should try to conduct other actions in your next action."})
                    error_messages, gpt_4v_res  = call_gpt4v_User(self.messages,self.logging)
                    self.messages.append({'role': 'user', 'content': gpt_4v_res})

                # chosen_action = re.split(pattern, gpt_4v_res)[3].strip()
                # last_last_action = last_action
                # action_key, info = extract_information(chosen_action)

                # fail_obs = ""
                # warn_obs = ""
                # last_round_info = ""

                    # if (last_action_agent!=last_action):
                #     self.messages.append({'role': 'user', 'content': "The part about last action and last last action in your answer is wrong! Please answer carefully according to each prompt I give."})
                #     error_messages, gpt_4v_res  = call_gpt4v_User(self.messages,self.logging)
                #     self.messages.append({'role': 'assistant', 'content': gpt_4v_res})
                
                # self.logging.info(gpt_4v_res)
                # print(re.split(pattern, gpt_4v_res)[1].strip())
                # print("None" in re.split(pattern, gpt_4v_res)[1].strip() )
                # print(it)


                # last_action_pattern = r'\[Last Action\](.*?)\[Last Last Action\](.*?)\[Similarity\]'
                # matches = re.search(last_action_pattern, re.split(pattern, gpt_4v_res)[1])
                # last_action_agent = matches.group(1).strip()
                # last_last_action_agent = matches.group(2).strip()
                # print("Last Action:", last_action)
                # print("Last Last Action:", last_last_action)

                # if (last_action_agent!=last_action):
                #     self.messages.append({'role': 'user', 'content': "The part about last action and last last action in your answer is wrong! Please answer carefully according to each prompt I give."})
                #     error_messages, gpt_4v_res  = call_gpt4v_User(self.messages,self.logging)
                #     self.messages.append({'role': 'assistant', 'content': gpt_4v_res})
                
                
                try:
                    window_handle_task = self.driver_task.current_window_handle
                    self.driver_task.switch_to.window(window_handle_task)

                    if action_key == 'click':
                    
                        click_ele_number = int(info[0])
                        web_ele = web_eles[click_ele_number]
                        index = 0
                        # print(info[0])
                        for i in range(len(web_eles_text_list)):
                            if web_eles_text_list[i][:len(str(info[0]))+2]=="["+str(info[0])+"]":
                                index=i
                                break

                        # self.logging.info(web_eles_text)
                        # print()
                        click_number = re.findall(r'\d+', chosen_action)

                        # last_action = "Clicking the element "+ web_eles_text_list[index]
                        last_action = "Click ["+str(click_ele_number)+"]" 

                        # print(last_action)
                        ele_tag_name = web_ele.tag_name.lower()
                        ele_type = web_ele.get_attribute("type")      
                        exec_action_click(info, web_ele, self.driver_task)
                    
                        if ele_tag_name == 'button' and ele_type == 'submit':
                            time.sleep(10)

                    elif action_key == 'wait':
                        last_action = chosen_action
                        time.sleep(5)

                    elif action_key == 'type':

                        type_ele_number = int(info['number'])
                        # last_action = "Type [" +" "+str(type_ele_number)+" "+ info["content"]
                        last_action = "Type [" +str(type_ele_number)+"]; "+ info["content"]
                        web_ele = web_eles[type_ele_number]
                        warn_obs = exec_action_type(info, web_ele, self.driver_task)
            
                    elif action_key == 'scroll':
                        last_action = chosen_action
                        exec_action_scroll(info, web_eles, self.driver_task, self.args, None)

                    elif action_key == 'goback':
                        last_action = chosen_action
                        self.driver_task.back()
                        time.sleep(2)

                    # elif action_key == 'answer':
                    #     self.logging.info(info['content'])
                    #     self.logging.info('finish!!')
                    #     break

                    else:
                        self.logging.info("Not implemented "+ action_key)
                        raise NotImplementedError
                    fail_obs = ""
            
                except Exception as e:
                    self.logging.error('driver error info:')
                    self.logging.error(e)
                    if 'element click intercepted' not in str(e):
                        fail_obs = "The action you have chosen cannot be exected. Please double-check if you have selected the wrong Numerical Label or Action or Action format. Then provide the revised Thought and Action."
                    else:
                        fail_obs = ""
                    time.sleep(2)

        self.driver_task.quit()


# if __name__ == "__main__": 

#     parser = argparse.ArgumentParser()
#     parser.add_argument('--test_file', type=str, default='../task/tasks_test.json')
#     parser.add_argument('--max_iter', type=int, default=2)
#     parser.add_argument("--output_dir", type=str, default='results')
#     parser.add_argument("--max_attached_imgs", type=int, default=2)
#     parser.add_argument("--temperature", type=float, default=1.0)
#     parser.add_argument("--download_dir", type=str, default="downloads")
#     parser.add_argument("--text_only", action='store_true')
#     parser.add_argument("--headless", action='store_true', help='The window of selenium')
#     parser.add_argument("--window_width", type=int, default=1024)
#     parser.add_argument("--window_height", type=int, default=768)  # for headless mode, there is no address bar
#     parser.add_argument("--fix_box_color", action='store_true')
#     args = parser.parse_args()

#     current_time = time.strftime("%Y%m%d_%H_%M_%S", time.localtime())
#     result_dir = os.path.join(args.output_dir, current_time)
#     os.makedirs(result_dir, exist_ok=True)     
#     tasks = []
#     with open(args.test_file, 'r', encoding='utf-8') as f:
#         for line in f:
#             tasks.append(json.loads(line))
#     task = tasks[0]

#     args = parser.parse_args()
#     test_agent.work(task)

#     question_list = ["Do you like this page? Give me a clear and detailed answer. Out of a hundred, how many points would you be willing to give?","Can you use some examples to explain your opinions ?","How do you like the usability of this page ?"]
#     for i in range(len(question_list)):
#         test_agent.interview(question_list[i])

