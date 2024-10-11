import platform
import argparse
import time
import json
import re
import os
import shutil
import logging
import requests
import base64
import re
import os
import json
import time
import logging
import numpy as np
import PIL
from PIL import Image
# from utils_webarena import fetch_browser_info, fetch_page_accessibility_tree,\
#                     parse_accessibility_tree, clean_accesibility_tree

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains

# from utils import get_web_element_rect, encode_image, extract_information, print_message,clip_message_and_obs


import base64
import re
import os
import json
import time
import logging
import numpy as np
from PIL import Image
# from utils_webarena import fetch_browser_info, fetch_page_accessibility_tree,\
#                     parse_accessibility_tree, clean_accesibility_tree


def setup_logger(folder_path,index):

    log_file_path = os.path.join(folder_path, "agent_"+str(index)+".log")
    logger = logging.getLogger(str(index))
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
        handler.close()

    handler = logging.FileHandler(log_file_path,encoding="utf-8")
    formatter = logging.Formatter('%(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    return logger

def driver_config(args):

    options = webdriver.ChromeOptions()
    options.add_argument("lang=en-us")
    options.add_argument("--force-device-scale-factor=1")

    if args.headless:
        options.add_argument("--headless")
        options.add_argument(
            "--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
        )
    options.add_experimental_option(
        "prefs", {
            "download.default_directory": args.download_dir,
            "plugins.always_open_pdf_externally": True
        }
    )
    return options

def format_msg_user(it, init_msg, warn_obs, web_img_b64, web_text):
    if it == 1:
        init_msg += f"I've provided the tag name of each element and the text it contains (if text exists). Note that <textarea> or <input> may be textbox, but not exactly. Please focus more on the screenshot and then refer to the textual information.\n{web_text}"
        init_msg_format = {
            'role': 'user',
            'content': [
                {'type': 'text', 'text': init_msg},
            ]
        }
        init_msg_format['content'].append({"type": "image_url",
                                           "image_url": {"url": f"data:image/png;base64,{web_img_b64}"}})
        return init_msg_format
    else:
        curr_msg = {
            'role': 'user',
            'content': [
                {'type': 'text', 'text': f"Observation:{warn_obs} please analyze the attached screenshot and give the Thought and Action. I've provided the tag name of each element and the text it contains (if text exists). Note that <textarea> or <input> may be textbox, but not exactly. Please focus more on the screenshot and then refer to the textual information.\n{web_text}"},
                {
                    'type': 'image_url',
                    'image_url': {"url": f"data:image/png;base64,{web_img_b64}"}
                }
            ]
        }
        return curr_msg

def format_msg_planner(it, init_msg, warn_obs, web_img_b64, web_text):
    if it == 1:
        init_msg += f"I've provided the tag name of each element and the text it contains (if text exists). Note that <textarea> or <input> may be textbox, but not exactly. Please focus more on the screenshot and then refer to the textual information.\n{web_text}"
        init_msg_format = {
            'role': 'user',
            'content': [
                {'type': 'text', 'text': init_msg},
            ]
        }
        init_msg_format['content'].append({"type": "image_url",
                                           "image_url": {"url": f"data:image/png;base64,{web_img_b64}"}})
        return init_msg_format
    else:
        curr_msg = {
            'role': 'user',
            'content': [
                {'type': 'text', 'text': f"Observation:{warn_obs} please analyze the attached screenshot and give the Thought and Action. I've provided the tag name of each element and the text it contains (if text exists). Note that <textarea> or <input> may be textbox, but not exactly. Please focus more on the screenshot and then refer to the textual information.\n{web_text}"},
                {
                    'type': 'image_url',
                    'image_url': {"url": f"data:image/png;base64,{web_img_b64}"}
                }
            ]
        }
        return curr_msg



def format_msg(init_msg,iter):

    if iter==0:
        init_msg += f"I've provided the demographics requirements of the users you need to generate."
        init_msg_format = {
            'role': 'user',
            'content': [
                {'type': 'text', 'text': init_msg},
            ]
        }
        return init_msg_format
    else:
        init_msg_format = {
            'role': 'user',
            'content': [
                {'type': 'text', 'text': init_msg},
            ]
        }
        return init_msg_format

def format_msg_interviewer(init_msg):

    init_msg_format = {
    'role': 'user',
    'content': [
        {'type': 'text', 'text': init_msg},
    ]}
    
    return init_msg_format



# def format_msg_user(init_msg):

#     init_msg += f"I've provided the demographics requirements of the users you need to generate."
#     init_msg_format = {
#         'role': 'user',
#         'content': [
#             {'type': 'text', 'text': init_msg},
#         ]
#     }
#     return init_msg_format

def call_gpt4v_Analysis(messages,logging):

    API_url = ""
    token = ""
    payload = {"model": "gpt-4o","messages": messages,"max_tokens": 4000,"temperature": 0.7}
    headers = {"Content-Type": "application/json","Authorization": f"Bearer {token}"}

    retry_times = 0
    while True:
        try:
            response = requests.post(API_url, headers=headers, json=payload)
            logging.info(response)
            logging.info("Prompt Token Cost: "+str(response.json()["usage"]["prompt_tokens"]))
            logging.info("Completen Token Cost: "+str(response.json()["usage"]["completion_tokens"]))
            return False,response.json()["choices"][0]["message"]["content"]
        
        except Exception as e:
            logging.info(f'Error occurred, retrying. Error type: {type(e).__name__}')

            if type(e).__name__ == 'RateLimitError':
                time.sleep(10)

            elif type(e).__name__ == 'APIError':
                time.sleep(15)

            else:
                return True, None

        retry_times += 1
        if retry_times == 10:
            logging.info('Retrying too many times')
            return True, None


def call_gpt4v_User(messages,logging):

    API_url = ""
    token = ""
    payload = {"model": "gpt-4o","messages": messages,"max_tokens": 4000,"temperature": 0.7}
    headers = {"Content-Type": "application/json","Authorization": f"Bearer {token}"}


    retry_times = 0
    # i =0
    while True:
        # i=i+1
        try:
            # if not args.text_only:
            # logging.info('Calling gpt4v API...')
            # logging.info(payload)
            response = requests.post(API_url, headers=headers, json=payload)
            logging.info(response)
            logging.info("Prompt Token Cost: "+str(response.json()["usage"]["prompt_tokens"]))
            logging.info("Completen Token Cost: "+str(response.json()["usage"]["completion_tokens"]))
            # logging.info(response.json()["choices"][0]["message"]["content"]+"\n")
            # logging.info(response)
            return False,response.json()["choices"][0]["message"]["content"]

        except Exception as e:
            logging.info(f'Error occurred, retrying. Error type: {type(e).__name__}')

            if type(e).__name__ == 'RateLimitError':
                time.sleep(10)

            elif type(e).__name__ == 'APIError':
                time.sleep(15)

            else:
                return True, None

        retry_times += 1
        if retry_times == 10:
            logging.info('Retrying too many times')
            return True, None

def call_gpt4v_UI(messages,logging):

    API_url = ""
    token = ""
    payload = {"model": "gpt-4o","messages": messages,"max_tokens": 4096,"temperature": 0.7}
    headers = {"Content-Type": "application/json","Authorization": f"Bearer {token}"}


    retry_times = 0
    # i =0
    while True:
        # i=i+1
        try:
            # if not args.text_only:
            # logging.info('Calling gpt4v API...')
            # logging.info(payload)
            response = requests.post(API_url, headers=headers, json=payload)
            logging.info(response)
            logging.info("Prompt Token Cost: "+str(response.json()["usage"]["prompt_tokens"]))
            logging.info("Completen Token Cost: "+str(response.json()["usage"]["completion_tokens"]))
            # logging.info(response.json()["choices"][0]["message"]["content"]+"\n")
            return False,response.json()["choices"][0]["message"]["content"]

        except Exception as e:
            logging.info(f'Error occurred, retrying. Error type: {type(e).__name__}')

            if type(e).__name__ == 'RateLimitError':
                time.sleep(10)

            elif type(e).__name__ == 'APIError':
                time.sleep(15)

            else:
                return True, None

        retry_times += 1
        if retry_times == 10:
            logging.info('Retrying too many times')
            return True, None


def exec_action_click(info, web_ele, driver_task):
    driver_task.execute_script("arguments[0].setAttribute('target', '_self')", web_ele)
    web_ele.click()
    time.sleep(3)


def exec_action_type(info, web_ele, driver_task):
    
    warn_obs = ""
    type_content = info['content']

    ele_tag_name = web_ele.tag_name.lower()
    ele_type = web_ele.get_attribute("type")
    # outer_html = web_ele.get_attribute("outerHTML")
    if (ele_tag_name != 'input' and ele_tag_name != 'textarea') or (ele_tag_name == 'input' and ele_type not in ['text', 'search', 'password', 'email', 'tel']):
        warn_obs = f"note: The web element you're trying to type may not be a textbox, and its tag name is <{web_ele.tag_name}>, type is {ele_type}."
    try:
        # Not always work to delete
        web_ele.clear()
        # Another way to delete
        if platform.system() == 'Darwin':
            web_ele.send_keys(Keys.COMMAND + "a")
        else:
            web_ele.send_keys(Keys.CONTROL + "a")
        web_ele.send_keys(" ")
        web_ele.send_keys(Keys.BACKSPACE)
    except:
        pass

    actions = ActionChains(driver_task)
    actions.click(web_ele).perform()
    actions.pause(1)

    try:
        driver_task.execute_script("""window.onkeydown = function(e) {if(e.keyCode == 32 && e.target.type != 'text' && e.target.type != 'textarea' && e.target.type != 'search') {e.preventDefault();}};""")
    except:
        pass

    actions.send_keys(type_content)
    actions.pause(2)

    actions.send_keys(Keys.ENTER)
    actions.perform()
    time.sleep(10)
    return warn_obs


def exec_action_scroll(info, web_eles, driver_task, args, obs_info):
    scroll_ele_number = info['number']
    scroll_content = info['content']
    if scroll_ele_number == "WINDOW":
        if scroll_content == 'down':
            driver_task.execute_script(f"window.scrollBy(0, {args.window_height*2//3});")
        else:
            driver_task.execute_script(f"window.scrollBy(0, {-args.window_height*2//3});")
    else:
        if not args.text_only:
            scroll_ele_number = int(scroll_ele_number)
            web_ele = web_eles[scroll_ele_number]
        else:
            element_box = obs_info[scroll_ele_number]['union_bound']
            element_box_center = (element_box[0] + element_box[2] // 2, element_box[1] + element_box[3] // 2)
            web_ele = driver_task.execute_script("return document.elementFromPoint(arguments[0], arguments[1]);", element_box_center[0], element_box_center[1])
        actions = ActionChains(driver_task)
        driver_task.execute_script("arguments[0].focus();", web_ele)
        if scroll_content == 'down':
            actions.key_down(Keys.ALT).send_keys(Keys.ARROW_DOWN).key_up(Keys.ALT).perform()
        else:
            actions.key_down(Keys.ALT).send_keys(Keys.ARROW_UP).key_up(Keys.ALT).perform()
    time.sleep(3)

def resize_image(image_path):
    image = Image.open(image_path)
    width, height = image.size

    if min(width, height) < 512:
        return image
    elif width < height:
        new_width = 512
        new_height = int(height * (new_width / width))
    else:
        new_height = 512
        new_width = int(width * (new_height / height))

    resized_image = image.resize((new_width, new_height), Image.LANCZOS)
    resized_image.save(image_path)
    # return resized_image

# base64 encoding
# Code from OpenAI Document
def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

# interact with webpage and add rectangles on elements
def get_web_element_rect(browser, fix_color=True):
    if fix_color:
        selected_function = "getFixedColor"
        # color_you_like = '#5210da'
    else:
        selected_function = "getRandomColor"

    js_script = """
        let labels = [];

        function markPage() {
            var bodyRect = document.body.getBoundingClientRect();

            var items = Array.prototype.slice.call(
                document.querySelectorAll('*')
            ).map(function(element) {
                var vw = Math.max(document.documentElement.clientWidth || 0, window.innerWidth || 0);
                var vh = Math.max(document.documentElement.clientHeight || 0, window.innerHeight || 0);
                
                var rects = [...element.getClientRects()].filter(bb => {
                var center_x = bb.left + bb.width / 2;
                var center_y = bb.top + bb.height / 2;
                var elAtCenter = document.elementFromPoint(center_x, center_y);

                return elAtCenter === element || element.contains(elAtCenter) 
                }).map(bb => {
                const rect = {
                    left: Math.max(0, bb.left),
                    top: Math.max(0, bb.top),
                    right: Math.min(vw, bb.right),
                    bottom: Math.min(vh, bb.bottom)
                };
                return {
                    ...rect,
                    width: rect.right - rect.left,
                    height: rect.bottom - rect.top
                }
                });

                var area = rects.reduce((acc, rect) => acc + rect.width * rect.height, 0);

                return {
                element: element,
                include: 
                    (element.tagName === "INPUT" || element.tagName === "TEXTAREA" || element.tagName === "SELECT") ||
                    (element.tagName === "BUTTON" || element.tagName === "A" || (element.onclick != null) || window.getComputedStyle(element).cursor == "pointer") ||
                    (element.tagName === "IFRAME" || element.tagName === "VIDEO" || element.tagName === "LI" || element.tagName === "TD" || element.tagName === "OPTION")
                ,
                area,
                rects,
                text: element.textContent.trim().replace(/\s{2,}/g, ' ')
                };
            }).filter(item =>
                item.include && (item.area >= 20)
            );

            // Only keep inner clickable items
            // first delete button inner clickable items
            const buttons = Array.from(document.querySelectorAll('button, a, input[type="button"], div[role="button"]'));

            //items = items.filter(x => !buttons.some(y => y.contains(x.element) && !(x.element === y) ));
            items = items.filter(x => !buttons.some(y => items.some(z => z.element === y) && y.contains(x.element) && !(x.element === y) ));
            items = items.filter(x => 
                !(x.element.parentNode && 
                x.element.parentNode.tagName === 'SPAN' && 
                x.element.parentNode.children.length === 1 && 
                x.element.parentNode.getAttribute('role') &&
                items.some(y => y.element === x.element.parentNode)));

            items = items.filter(x => !items.some(y => x.element.contains(y.element) && !(x == y)))

            // Function to generate random colors
            function getRandomColor(index) {
                var letters = '0123456789ABCDEF';
                var color = '#';
                for (var i = 0; i < 6; i++) {
                color += letters[Math.floor(Math.random() * 16)];
                }
                return color;
            }

            function getFixedColor(index) {
                var color = '#000000'
                return color
            }
            //function getFixedColor(index){
            //    var colors = ['#FF0000', '#00FF00', '#0000FF', '#000000']; // Red, Green, Blue, Black
            //    return colors[index % 4];
            //}
            

            // Lets create a floating border on top of these elements that will always be visible
            items.forEach(function(item, index) {
                item.rects.forEach((bbox) => {
                newElement = document.createElement("div");
                var borderColor = COLOR_FUNCTION(index);
                newElement.style.outline = `2px dashed ${borderColor}`;
                newElement.style.position = "fixed";
                newElement.style.left = bbox.left + "px";
                newElement.style.top = bbox.top + "px";
                newElement.style.width = bbox.width + "px";
                newElement.style.height = bbox.height + "px";
                newElement.style.pointerEvents = "none";
                newElement.style.boxSizing = "border-box";
                newElement.style.zIndex = 2147483647;
                // newElement.style.background = `${borderColor}80`;
                
                // Add floating label at the corner
                var label = document.createElement("span");
                label.textContent = index;
                label.style.position = "absolute";
                //label.style.top = "-19px";
                label.style.top = Math.max(-19, -bbox.top) + "px";
                //label.style.left = "0px";
                label.style.left = Math.min(Math.floor(bbox.width / 5), 2) + "px";
                label.style.background = borderColor;
                label.style.color = "white";
                label.style.padding = "2px 4px";
                label.style.fontSize = "12px";
                label.style.borderRadius = "2px";
                newElement.appendChild(label);
                
                document.body.appendChild(newElement);
                labels.push(newElement);
                // item.element.setAttribute("-ai-label", label.textContent);
                });
            })

            // For the first way
            // return [labels, items.map(item => ({
            //     rect: item.rects[0] // assuming there's at least one rect
            // }))];

            // For the second way
            return [labels, items]
        }
        return markPage();""".replace("COLOR_FUNCTION", selected_function)
    rects, items_raw = browser.execute_script(js_script)

    # format_ele_text = [f"[{web_ele_id}]: \"{items_raw[web_ele_id]['text']}\";" for web_ele_id in range(len(items_raw)) if items_raw[web_ele_id]['text'] ]
    format_ele_text = []
    
    for web_ele_id in range(len(items_raw)):
        label_text = items_raw[web_ele_id]['text']
        ele_tag_name = items_raw[web_ele_id]['element'].tag_name
        ele_type = items_raw[web_ele_id]['element'].get_attribute("type")
        ele_aria_label = items_raw[web_ele_id]['element'].get_attribute("aria-label")
        input_attr_types = ['text', 'search', 'password', 'email', 'tel']

        if not label_text:
            if (ele_tag_name.lower() == 'input' and ele_type in input_attr_types) or ele_tag_name.lower() == 'textarea' or (ele_tag_name.lower() == 'button' and ele_type in ['submit', 'button']):
                if ele_aria_label:
                    format_ele_text.append(f"[{web_ele_id}]: <{ele_tag_name}> \"{ele_aria_label}\";")
                else:
                    format_ele_text.append(f"[{web_ele_id}]: <{ele_tag_name}> \"{label_text}\";" )

        elif label_text and len(label_text) < 200:
            if not ("<img" in label_text and "src=" in label_text):
                if ele_tag_name in ["button", "input", "textarea"]:
                    if ele_aria_label and (ele_aria_label != label_text):
                        format_ele_text.append(f"[{web_ele_id}]: <{ele_tag_name}> \"{label_text}\", \"{ele_aria_label}\";")
                    else:
                        format_ele_text.append(f"[{web_ele_id}]: <{ele_tag_name}> \"{label_text}\";")
                else:
                    if ele_aria_label and (ele_aria_label != label_text):
                        format_ele_text.append(f"[{web_ele_id}]: \"{label_text}\", \"{ele_aria_label}\";")
                    else:
                        format_ele_text.append(f"[{web_ele_id}]: \"{label_text}\";")

    format_ele_text_list =format_ele_text
    format_ele_text = '\t'.join(format_ele_text)


    return rects, [web_ele['element'] for web_ele in items_raw], format_ele_text, format_ele_text_list


def extract_information(text):
    patterns = {
        "click": r"Click \[?(\d+)\]?",
        "type": r"Type \[?(\d+)\]?[; ]+\[?(.[^\]]*)\]?",
        # "delete_and_type": r"Delete_and_Type \[?(\d+)\]?[; ]+\[?(.[^\]]*)\]?",
        "scroll": r"Scroll \[?(\d+|WINDOW)\]?[; ]+\[?(up|down)\]?",
        "wait": r"^Wait",
        "goback": r"^GoBack",
        "google": r"^Google",
        "answer": r"ANSWER[; ]+\[?(.[^\]]*)\]?"
    }

    for key, pattern in patterns.items():
        match = re.search(pattern, text)
        if match:
            if key in ["click", "wait", "goback", "google"]:
                # no content
                return key, match.groups()
            else:
                return key, {"number": match.group(1), "content": match.group(2)} if key in ["type", "scroll"] else {"content": match.group(1)}
    return None, None


def clip_message(msg, max_img_num):
    clipped_msg = []
    img_num = 0
    for idx in range(len(msg)):
        curr_msg = msg[len(msg) - 1 - idx]
        if curr_msg['role'] != 'user':
            clipped_msg = [curr_msg] + clipped_msg
        else:
            if type(curr_msg['content']) == str:
                clipped_msg = [curr_msg] + clipped_msg
            elif img_num < max_img_num:
                img_num += 1
                clipped_msg = [curr_msg] + clipped_msg
            else:
                curr_msg_clip = {
                    'role': curr_msg['role'],
                    'content': curr_msg['content'][0]["text"]
                }
                clipped_msg = [curr_msg_clip] + clipped_msg
    return clipped_msg


def clip_message_and_obs(msg, max_img_num):
    clipped_msg = []
    img_num = 0
    for idx in range(len(msg)):
        curr_msg = msg[len(msg) - 1 - idx]
        if curr_msg['role'] != 'user':
            clipped_msg = [curr_msg] + clipped_msg
        else:
            if type(curr_msg['content']) == str:
                clipped_msg = [curr_msg] + clipped_msg
            elif img_num < max_img_num:
                img_num += 1
                clipped_msg = [curr_msg] + clipped_msg
            else:
                msg_no_pdf = curr_msg['content'][0]["text"].split("Observation:")[0].strip() + "Observation: A screenshot and some texts. (Omitted in context.)"
                msg_pdf = curr_msg['content'][0]["text"].split("Observation:")[0].strip() + "Observation: A screenshot, a PDF file and some texts. (Omitted in context.)"
                curr_msg_clip = {
                    'role': curr_msg['role'],
                    'content': msg_no_pdf if "You downloaded a PDF file" not in curr_msg['content'][0]["text"] else msg_pdf
                }
                clipped_msg = [curr_msg_clip] + clipped_msg
    return clipped_msg


def clip_message_and_obs_text_only(msg, max_tree_num):
    clipped_msg = []
    tree_num = 0
    for idx in range(len(msg)):
        curr_msg = msg[len(msg) - 1 - idx]
        if curr_msg['role'] != 'user':
            clipped_msg = [curr_msg] + clipped_msg
        else:
            if tree_num < max_tree_num:
                tree_num += 1
                clipped_msg = [curr_msg] + clipped_msg
            else:
                msg_no_pdf = curr_msg['content'].split("Observation:")[0].strip() + "Observation: An accessibility tree. (Omitted in context.)"
                msg_pdf = curr_msg['content'].split("Observation:")[0].strip() + "Observation: An accessibility tree and a PDF file. (Omitted in context.)"
                curr_msg_clip = {
                    'role': curr_msg['role'],
                    'content': msg_no_pdf if "You downloaded a PDF file" not in curr_msg['content'] else msg_pdf
                }
                clipped_msg = [curr_msg_clip] + clipped_msg
    return clipped_msg


def print_message(json_object, save_dir=None):
    remove_b64code_obj = []
    for obj in json_object:
        if obj['role'] != 'user':
            # print(obj)
            logging.info(obj)
            remove_b64code_obj.append(obj)
        else:
            if type(obj['content']) == str:
                # print(obj)
                logging.info(obj)
                remove_b64code_obj.append(obj)
            else:
                print_obj = {
                    'role': obj['role'],
                    'content': obj['content']
                }
                for item in print_obj['content']:
                    if item['type'] == 'image_url':
                        item['image_url'] =  {"url": "data:image/png;base64,{b64_img}"}
                # print(print_obj)
                logging.info(print_obj)
                remove_b64code_obj.append(print_obj)
    if save_dir:
        with open(os.path.join(save_dir, 'interact_messages.json'), 'w', encoding='utf-8') as fw:
            json.dump(remove_b64code_obj, fw, indent=2)
    # return remove_b64code_obj


# def get_webarena_accessibility_tree(browser, save_file=None):
#     browser_info = fetch_browser_info(browser)
#     accessibility_tree = fetch_page_accessibility_tree(browser_info, browser, current_viewport_only=True)
#     content, obs_nodes_info = parse_accessibility_tree(accessibility_tree)
#     content = clean_accesibility_tree(content)
#     if save_file:
#         with open(save_file + '.json', 'w', encoding='utf-8') as fw:
#             json.dump(obs_nodes_info, fw, indent=2)
#         with open(save_file + '.txt', 'w', encoding='utf-8') as fw:
#             fw.write(content)
            
#     return content, obs_nodes_info


def compare_images(img1_path, img2_path):
    img1 = Image.open(img1_path)
    img2 = Image.open(img2_path)

    img1_array = np.asarray(img1)
    img2_array = np.asarray(img2)

    difference = np.abs(img1_array - img2_array)

    total_difference = np.sum(difference)

    return total_difference


def get_pdf_retrieval_ans_from_assistant(client, pdf_path, task):
    # print("You download a PDF file that will be retrieved using the Assistant API.")
    logging.info("You download a PDF file that will be retrieved using the Assistant API.")
    file = client.files.create(
        file=open(pdf_path, "rb"),
        purpose='assistants'
    )
    # print("Create assistant...")
    logging.info("Create assistant...")
    assistant = client.beta.assistants.create(
        instructions="You are a helpful assistant that can analyze the content of a PDF file and give an answer that matches the given task, or retrieve relevant content that matches the task.",
        model="gpt-4-1106-preview",
        tools=[{"type": "retrieval"}],
        file_ids=[file.id]
    )
    thread = client.beta.threads.create()
    message = client.beta.threads.messages.create(
        thread_id=thread.id,
        role="user",
        content=task,
        file_ids=[file.id]
    )
    run = client.beta.threads.runs.create(
        thread_id=thread.id,
        assistant_id=assistant.id
    )
    while True:
        # Retrieve the run status
        run_status = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
        if run_status.status == 'completed':
            break
        time.sleep(2)
    messages = client.beta.threads.messages.list(thread_id=thread.id)
    messages_text = messages.data[0].content[0].text.value
    file_deletion_status = client.beta.assistants.files.delete(
        assistant_id=assistant.id,
        file_id=file.id
    )
    # print(file_deletion_status)
    logging.info(file_deletion_status)
    assistant_deletion_status = client.beta.assistants.delete(assistant.id)
    # print(assistant_deletion_status)
    logging.info(assistant_deletion_status)
    return messages_text

def compress_image(image_path,quality=40):

    with Image.open(image_path) as image:
        width, height = int(image.width * 0.2), int(image.height * 0.2)
        image.thumbnail((width, height), PIL.Image.LANCZOS)
        image.save(image_path, optimize=True, quality=quality)


def interviews (Interviewer_agent,Interviewees_Agent_list):

    for i in range(len(Interviewees_Agent_list)):
        interview_one_pair(Interviewer_agent,Interviewees_Agent_list[i])
        


def interview_one_pair(Interviewer_agent, Interviewee_agent,logging,max_iter=100,):

    iter=0
    iterview_finished = False
    while (iter<=max_iter and iterview_finished):  
        iter+=1
        










# def compress_image(image_path,quality=50):

#     with Image.open(image_path) as image:
#         width, height = int(image.width * 0.5), int(image.height * .5)
#         image.thumbnail((width, height), Image.ANTIALIAS)
#         image.save(image_path, optimize=True, quality=quality)
 

# compress_image(r'C:\Users\Allen\Desktop\Project\App_Test_Agent\Agent\results\20240906_15_30_08\screenshot1.png', quality=85)

