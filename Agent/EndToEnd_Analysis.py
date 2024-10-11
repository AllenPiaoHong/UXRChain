import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import platform
import argparse
import time
import random
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
from prompts import SYSTEM_Analysis_Prompt

from utils import *

class ResultAnalysisagent():

    def __init__(self, material_log,analysis_report_name):
        
        self.material_log = material_log
        self.analysis_log_file = analysis_report_name
        self.messages = []
        self.logging = logging.getLogger('Analysis Logger')
        
        file_handler = logging.FileHandler(self.analysis_log_file,encoding="utf-8")
        formatter = logging.Formatter('%(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)

        self.logging.addHandler(file_handler)
        self.logging.setLevel(logging.INFO)

    def resultAnalysis (self,chinese_analysis_file):

        clogging = logging.getLogger('Chinese Analysis Logger')
        file_handler = logging.FileHandler(chinese_analysis_file,encoding="utf-8")
        formatter = logging.Formatter('%(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        clogging.addHandler(file_handler)
        clogging.setLevel(logging.INFO)

        with open(self.material_log, 'r', encoding='utf-8') as file:
            log_content = ''.join(line.strip() + '\n' for line in file if line.strip())

        # improvement_advices = re.findall(r'(?<=ActionComparison:)(.*?)(?=\n\n|Thought: |$)', log_content , re.DOTALL)
        improvement_advices = re.findall(r'\[Evaluation\]not satisfied\[Reason\](.*?)\[\w+\]', log_content , re.DOTALL)
        improvement_content = "".join(line.strip() + '\n' for line in improvement_advices if line.strip())
        transcript_questions_and_answers = re.findall(r'(INFO - (New question) from the interviewer: \[.*?\]:.*?)(INFO - The response from the interviewee: \[Answer\]:.*?)(?=INFO - <Response \[200\]>|$)',  log_content , re.DOTALL)
        further_questions_and_answers = re.findall(r'(question from the interviewer \[.*?\]:.*?)(INFO - The response from the interviewee: \[Answer\]:.*?)(?=INFO - <Response \[200\]>|$)',  log_content , re.DOTALL)
       
        Question_Answer_list= []

        for question, _,answer in transcript_questions_and_answers:

            Question_Answer_list.append(question.strip())
            Question_Answer_list.append(answer.strip())
        
        for question, answer in further_questions_and_answers:

            Question_Answer_list.append(question.strip())
            Question_Answer_list.append(answer.strip())
       
        interview_content = " ".join(Question_Answer_list)
       # self.logging.info(improvement_content)
        print(len(interview_content))

        # self.logging.info("###################Findings from Interview Session #########")
        # self.messages = []
        # self.messages.append({'role': 'system', 'content':SYSTEM_Analysis_Prompt})

        self.logging.info("###################Findings from ThinkAloud Session")
        self.messages = []
        self.messages.append({'role': 'system', 'content':SYSTEM_Analysis_Prompt})
        curr_msg = format_msg(improvement_content,1)
        # self.logging.info(curr_msg)
        self.messages.append(curr_msg)
        error_messages, gpt_4v_res  = call_gpt4v_User(self.messages,self.logging)
        # while ("[Usability Deficiencies 1]" not in gpt_4v_res):
        #     curr_msg = format_msg("I need you to analyze the materials following the formats!",1)
        #     self.messages.append(curr_msg)
        #     error_messages, gpt_4v_res  = call_gpt4v_User(self.messages,self.logging)
        self.logging.info(gpt_4v_res)
        self.messages.pop()
        self.messages.append({'role': 'system', 'content':SYSTEM_Analysis_Prompt})
        messages = []
        messages.append({'role': 'system', 'content':"Change the following report into Chinese. Do not change the format. Try to combine same"})
        curr_msg = format_msg(gpt_4v_res,1)
        messages.append(curr_msg)
        error_messages, gpt_4v_res  = call_gpt4v_User(messages,clogging)
        clogging.info(gpt_4v_res)

        self.messages = []
        order = [0,1]
        random.shuffle(order)
        # print(order[0])
        for i in range(2):
            self.logging.info("###################Findings from Interview Section: "+str(i+1))
            self.messages.append({'role': 'system', 'content':SYSTEM_Analysis_Prompt})
            curr_msg = format_msg(interview_content[int(len(interview_content)/3)* order[i]:int(len(interview_content)/3)*(order[i]+1)],1)
            # self.logging.info(curr_msg)
            self.messages.append(curr_msg)
            error_messages, gpt_4v_res  = call_gpt4v_User(self.messages,self.logging)
            self.logging.info(gpt_4v_res)
            # # while ("[Usability Deficiencies 1]" not in gpt_4v_res):
            # #     curr_msg = format_msg("I need you to analyze the materials following the formats!",1)
            # #     self.messages.append(curr_msg)
            # #     error_messages, gpt_4v_res  = call_gpt4v_User(self.messages,self.logging)
            # self.logging.info(gpt_4v_res)
            self.messages.pop()
            self.messages.append({'role': 'system', 'content':SYSTEM_Analysis_Prompt})
            messages = []
            messages.append({'role': 'system', 'content':"Change the following report into Chinese. Do not change the format. Try to combine same"})
            curr_msg = format_msg(gpt_4v_res,1)
            messages.append(curr_msg)
            error_messages, gpt_4v_res  = call_gpt4v_User(messages,clogging)
            clogging.info(gpt_4v_res)

        
if __name__ == "__main__": 

    parser = argparse.ArgumentParser()
    parser.add_argument('--log_file', type=str, default='D:\Data\WWW_UXRChain\TB_IT_50\Summary\TB_IT_50.log')
    parser.add_argument('--analysis_file', type=str, default='TB_IT_50_Analysis.log')
    parser.add_argument('--chinese_analysis_file', type=str, default='TB_IT_50_CN.log')

    args = parser.parse_args()

    if os.path.exists(args.analysis_file):
        os.remove(args.analysis_file)
    Analy_Agent = ResultAnalysisagent(args.log_file,args.analysis_file)
    Analy_Agent.resultAnalysis(args.chinese_analysis_file)
