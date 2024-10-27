import csv
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time,os
from pymongo import MongoClient


# Set up Chrome options
chrome_options = Options()
chrome_options.add_argument("--disable-gpu")  
chrome_options.add_argument("--no-sandbox")  
service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=chrome_options)


os.environ['DISPLAY'] = ':99'


client = MongoClient('mongodb://admin:wgiryraT1@ec2-3-133-7-67.us-east-2.compute.amazonaws.com:27017/admin')
db = client['report_db']
dish_collection = db['dish_name']
spelling_error_collection = db['spelling_error']

# Open the URL
driver.get("https://www.scribbr.com/grammar-checker/")
time.sleep(10)

WebDriverWait(driver, 20).until(EC.frame_to_be_available_and_switch_to_it((By.ID, "QuillBotGrmrIframe")))
input_element = WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.XPATH, "//div[@contenteditable='true']")))

dish_names = dish_collection.find({}, {"dishName": 1, "_id": 0})

for dish in dish_names:
    restaurant_name = dish['dishName']
    input_element.clear()
    input_element.send_keys(restaurant_name)
    time.sleep(5)
    
    try:
        error_message = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, "//div[contains(text(), '0')]")))
        print(f"Spelling is correct for: {restaurant_name}")
    except:
        print(f"Spelling mistake found for: {restaurant_name}")
        spelling_error_collection.insert_one({"dishName": restaurant_name})

driver.switch_to.default_content()
driver.quit()
