from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium import webdriver
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import os
from twocaptcha import TwoCaptcha
from pymongo import MongoClient
from webdriver_manager.chrome import ChromeDriverManager


# MongoDB Connection
client = MongoClient('localhost', 27017)
db = client['report_db']
collection = db['report']

# Chrome options
chrome_options = Options()
chrome_options.add_argument("--disable-blink-features=AutomationControlled")
chrome_options.add_argument("--disable-infobars")
chrome_options.add_argument("--disable-popup-blocking")
chrome_options.add_argument("--headless")

# Initialize the WebDriver using ChromeDriverManager
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

# Open target website
driver.get('https://www.abogacia.es/servicios-abogacia/censo-de-letrados/')
print('Website opened')

wait = WebDriverWait(driver, 10)
# Accept cookies if the button appears
try:
    cookies_button = wait.until(EC.element_to_be_clickable((By.ID, "CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll")))
    cookies_button.click()
except Exception as e:
    print("Cookies button not found or already accepted.")

# Switch to iframe for interaction
iframe_element = wait.until(EC.presence_of_element_located((By.XPATH, '//iframe[contains(@src, "censo.abogacia.es")]')))
driver.switch_to.frame(iframe_element)

# Enter search query and submit
input_value = wait.until(EC.presence_of_element_located((By.XPATH, '//input[@id="j_id23:j_id33"]')))
input_value.send_keys('a')
submit_element = wait.until(EC.element_to_be_clickable((By.XPATH, '//a[contains(text(), "Buscar")]')))
submit_element.click()

print('Website form submitted within iframe')


def get_existing_names():
    """Retrieve all first names from the database and store them in a set for fast lookup."""
    return {entry["first_name"] for entry in collection.find({}, {"first_name": 1, "_id": 0})}


existing_names = get_existing_names()


def insert_data_mongo(data):
    """Insert a new entry into MongoDB."""
    try:
        collection.insert_one(data)
        print(f"Inserted data for {data['Nombre']} into MongoDB successfully")
    except Exception as e:
        print(f"Error inserting data: {e}")


def extract_information(driver):
    """Extract information from the webpage based on given labels."""
    labels = {
        "Nombre:": "Nombre",
        "Colegio:": "Colegio",
        "Alta Colegiación:": "Alta Colegiación",
        "N. Colegiado:": "N. Colegiado",
        "Ejerciente": "Ejerciente",
        "Residente": "Residente",
        "Dirección Profesional:": "Dirección Profesional",
        "Teléfono:": "Teléfono",
        "Fax:": "Fax"
    }

    result = {}
    for label, key in labels.items():
        try:
            label_element = driver.find_element(By.XPATH, f"//label[text()='{label}']")
            sibling_span = label_element.find_element(By.XPATH, "following-sibling::span")
            result[key] = sibling_span.text.strip()
        except Exception:
            pass  # Skip missing elements gracefully
    return result


def solve_captcha(driver):
    """Handle and solve the captcha if it appears."""
    try:
        captcha_frame = driver.find_element(By.XPATH, "//iframe[contains(@src, 'ecensofront/html/homeColegiados.iface')]")
        driver.switch_to.frame(captcha_frame)

        captcha_prompt = driver.find_element(By.XPATH, "//div[@id='j_id23:CaptchaPopup']//label[contains(text(), 'Introduzca los caracteres de la imagen')]")
        if 'Introduzca los caracteres de la imagen' in captcha_prompt.text:
            img_element = driver.find_element(By.XPATH, "//td[@id='j_id23:j_id51-1-0']//img")
            img_dir = 'captcha/'
            os.makedirs(img_dir, exist_ok=True)
            img_path = os.path.join(img_dir, 'captcha.jpg')
            img_element.screenshot(img_path)

            api_key = os.getenv('APIKEY_2CAPTCHA', '8290cf554382059820ac19d0eb2f5c7a')
            solver = TwoCaptcha(api_key)
            captcha_result = solver.normal(img_path)
            print('Solved captcha:', captcha_result)

            captcha_input = driver.find_element(By.XPATH, "//input[@id='j_id23:answer']")
            captcha_input.send_keys(captcha_result['code'])

            submit_button = driver.find_element(By.XPATH, "//a[contains(text(), 'Aceptar')]")
            submit_button.click()
            return True
    except Exception as e:
        print(f"Captcha handling error: {e}")
        return False


# Main extraction loop
i = 0
while True:
    try:
        detail_element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, ".//table[@class='iceDatTbl tablaElementos']//tbody"))
        )
        rows = detail_element.find_elements(By.XPATH, ".//td[contains(@style, 'width:140px')]")

        for page_number in range(len(rows)):
            time.sleep(5)

            rows = detail_element.find_elements(By.XPATH, ".//td[contains(@style, 'width:140px')]")  # Re-fetch rows
            if page_number < len(rows):
                current_row = rows[page_number]
                name_text = current_row.find_element(By.XPATH, ".//span").text.strip()

                if name_text in existing_names:
                    print(f"{name_text} already exists in the database, skipping...")
                    continue

                current_row.click()
                time.sleep(2)  # Allow modal to load

                info = extract_information(driver)
                if info:
                    info["first_name"] = name_text
                    insert_data_mongo(info)

                # Close modal
                WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//a[@id='j_id23:j_id50']"))
                ).click()

                # Handle captcha if it appears
                solve_captcha(driver)

        # Click 'Next Page' button
        next_page = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, "//img[@id='j_id23:j_id79']")))
        next_page.click()
        i += 1
        print(f"Navigated to page {i}")
        
    except Exception as e:
        print(f"Error on page {i}: {e}")
        break





























