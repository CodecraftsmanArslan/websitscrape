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

# MongoDB Connection
client = MongoClient('localhost', 27017)
db = client['report_db']
collection = db['report']

# Chrome options
chrome_options = Options()
chrome_options.add_argument("--disable-blink-features=AutomationControlled")
chrome_options.add_argument("--disable-infobars")
chrome_options.add_argument("--disable-popup-blocking")

# Create a Service object for the Chrome driver
chrome_driver_path = r'C:\Program Files (x86)\chromedriver.exe'
service = Service(chrome_driver_path)

# Initialize the WebDriver
driver = webdriver.Chrome(service=service, options=chrome_options)
driver.get('https://www.abogacia.es/servicios-abogacia/censo-de-letrados/')

time.sleep(10)

iframe_element = driver.find_element(By.XPATH, '//iframe[contains(@src, "censo.abogacia.es")]')
driver.switch_to.frame(iframe_element)

input_value = driver.find_element(By.XPATH, '//input[@id="j_id23:j_id33"]')
input_value.send_keys('a')

time.sleep(2)

submit_element = driver.find_element(By.XPATH, '//a[contains(text(), "Buscar")]')
submit_element.click()

time.sleep(10)
print('Website opened and form submitted within iframe')



def get_existing_names():
    """Retrieve all first names from the database and store them in a set for fast lookup."""
    existing_names = set()
    for entry in collection.find({}, {"first_name": 1, "_id": 0}):
        existing_names.add(entry["first_name"])
    return existing_names

existing_names = get_existing_names()  # Pre-load all existing names before the loop

def name_exists_in_memory(first_name):
    """Check if the first name exists in the pre-loaded set."""
    return first_name in existing_names


def insert_data_mongo(first_name,nombre, colegio, alta_colegiacion, n_colegiado, ejerciente, residente, direccion_profesional, telefono,fax):
    try:
        data = {
            "first_name":first_name,
            "Nombre": nombre,
            "Colegio": colegio,
            "Alta_Colegiacion": alta_colegiacion,
            "N_Colegiado": n_colegiado,
            "Ejerciente": ejerciente,
            "Residente": residente,
            "Direccion_Profesional": direccion_profesional,
            "Telefono": telefono,
            "Fax:":fax
        }
        # Insert the data into MongoDB
        collection.insert_one(data)
        print("Inserted data into MongoDB successfully")

    except Exception as e:
        print(f"Error inserting data: {e}")


def extract_information_optimized_selenium(driver):
    labels = {
        "Nombre:": "Nombre",
        "Colegio:": "Colegio",
        "Alta Colegiación:": "Alta Colegiación",
        "N. Colegiado:": "N. Colegiado",
        "Ejerciente": "Ejerciente",
        "Residente": "Residente",
        "Dirección Profesional:": "Dirección Profesional",
        "Teléfono:": "Teléfono",
        "Fax:":"Fax"
    }

    result = {}

    for label, key in labels.items():
        try:
            label_element = driver.find_element(By.XPATH, f"//label[text()='{label}']")
            sibling_span = label_element.find_element(By.XPATH, "following-sibling::span")
            result[key] = sibling_span.text.strip()
        except Exception as e:
            pass

    return result


def captcha_solve(driver):
    try:
        try:
            iframe = driver.find_element(By.XPATH, "//iframe[contains(@src, 'ecensofront/html/homeColegiados.iface')]")
            driver.switch_to.frame(iframe)
            print("Switched to iframe.")
        except Exception:
            print("Iframe not found, proceeding without switching.")
        
        time.sleep(3)

        try:
            text_appear = driver.find_element(By.XPATH, "//div[@id='j_id23:CaptchaPopup']//label[contains(text(), 'Introduzca los caracteres de la imagen, por favor.')]")
            print("Captcha prompt found.")
        except Exception:
            print("Captcha prompt not found. No captcha to solve.")
            return None
        
        if 'Introduzca los caracteres de la imagen, por favor.' in text_appear.text:
            try:
                img_element = driver.find_element(By.XPATH, "//td[@id='j_id23:j_id51-1-0']//img")
                img_path = 'D:/WEB-CRAWLERS/Scraping_Websites/Census/captcha/captcha.jpg'
                img_element.screenshot(img_path)

                api_key = os.getenv('APIKEY_2CAPTCHA', '8290cf554382059820ac19d0eb2f5c7a')
                solver = TwoCaptcha(api_key)
                result = solver.normal(img_path)
                print('Solved captcha:', result)
                
                time.sleep(2)

                text_write = driver.find_element(By.XPATH, "//input[@id='j_id23:answer']")
                text_write.send_keys(result['code'])

                submit_element = driver.find_element(By.XPATH, "//a[contains(text(), 'Aceptar')]")
                submit_element.click()
                return result['code']

            except Exception as e:
                print(f"Error occurred while solving captcha: {e}")
                return None

    except Exception as e:
        print(f"An error occurred: {e}")
    


i=0
while True:
    # Handling table details
    detail_element = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, ".//table[@class='iceDatTbl tablaElementos']//tbody"))
    )

    rows = detail_element.find_elements(By.XPATH, ".//td[contains(@style, 'width:140px')]")

    for page_number in range(len(rows)):
        time.sleep(5)
        
        try:
            detail_element = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, ".//table[@class='iceDatTbl tablaElementos']//tbody"))
            )
            rows = detail_element.find_elements(By.XPATH, ".//td[contains(@style, 'width:140px')]")
            
            if page_number < len(rows):
                current_row = rows[page_number]
                name_element = current_row.find_element(By.XPATH, ".//span")
                name_text = name_element.text.strip()
                print(name_text)

                if name_exists_in_memory(name_text):
                    print(f"{name_text} already exists in the database, skipping...")
                    continue  # Skip this entry if it already exists

                name_element.click()
                time.sleep(5)

                info = extract_information_optimized_selenium(driver)
                print(info)



                first_name=name_text
                nombre = info.get("Nombre", "")
                colegio = info.get("Colegio", "")
                alta_colegiacion = info.get("Alta Colegiación", "")
                n_colegiado = info.get("N. Colegiado", "")
                ejerciente = info.get("Ejerciente", "")
                residente = info.get("Residente", "")
                direccion_profesional = info.get("Dirección Profesional", "")
                telefono = info.get("Teléfono", None)
                if telefono == "":
                    telefono = None
                fax=info.get("Fax", None)
                if fax == "":
                    fax = None
                
                insert_data_mongo(first_name,nombre, colegio, alta_colegiacion, n_colegiado, ejerciente, residente, direccion_profesional, telefono,fax)
                
                WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//a[@id='j_id23:j_id50']"))
                ).click()
                
                captcha_solve(driver)
                time.sleep(5)
    
        except Exception as e:
            print(f"Error processing row {page_number}: {e}")
            continue

    next_page=driver.find_element(By.XPATH,"//img[@id='j_id23:j_id79']")
    next_page.click()
    i+=1
    print(f"page_number-{i}")
