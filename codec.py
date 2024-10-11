from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import time,os
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from pymongo import MongoClient
from webdriver_manager.chrome import ChromeDriverManager
from twocaptcha import TwoCaptcha
from selenium.common.exceptions import NoSuchElementException


# MongoDB Connection
client = MongoClient('mongodb://admin:wgiryraT1@ec2-18-191-101-237.us-east-2.compute.amazonaws.com:27017/admin')
db = client['report_db']
collection = db['name_store']
collectio_data=db['data_db']

# Chrome options
chrome_options = Options()
chrome_options.add_argument("--disable-blink-features=AutomationControlled")
chrome_options.add_argument("--disable-infobars")
chrome_options.add_argument("--disable-popup-blocking")
chrome_options.add_argument("--headless")  
chrome_options.add_argument("--disable-gpu")


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

# Fetch the first_name and last_name from MongoDB
names = collection.find({}, {"first_name": 1, "last_name": 1, "_id": 0})  # Fetch first_name and last_name records



def solve_captcha(driver):
    while True:  # Start the while loop for continuous CAPTCHA solving

        try:
            driver.execute_script("window.scrollTo(0, 200);")
            
            try:
                iframe = driver.find_element(By.XPATH, "//iframe[contains(@src, 'ecensofront/html/homeColegiados.iface')]")
                driver.switch_to.frame(iframe)
                print("Switched to iframe.")
            except Exception:
                print("Iframe not found, proceeding without switching.")
            
            time.sleep(5)

            try:
                text_appear = driver.find_element(By.XPATH, "//div[@id='j_id23:CaptchaPopup']//label[contains(text(), 'Introduzca los caracteres de la imagen, por favor.')]")
                print("Captcha prompt found.")
            except Exception:
                print("Captcha prompt not found. No captcha to solve.")
                return None
            
            if 'Introduzca los caracteres de la imagen, por favor.' in text_appear.text:
                try:
                    img_element = driver.find_element(By.XPATH, "//td[@class='icePnlGrdCol1 popupBodyCol1']//img")
                    img_dir = '/home/ec2-user/websitscrape/captcha/'
                    os.makedirs(img_dir, exist_ok=True)
                    img_path = os.path.join(img_dir, 'captcha.png')
                    img_element.screenshot(img_path)

                    # 2Captcha API key and solving the CAPTCHA
                    api_key = os.getenv('APIKEY_2CAPTCHA', '5d86aab767ee78ecb8014a692c8990ea')
                    solver = TwoCaptcha(api_key)
                    result = solver.normal(img_path)
                    print('Solved captcha:', result)
                    
                    time.sleep(2)

                    # Entering the solved CAPTCHA
                    text_write = driver.find_element(By.XPATH, "//input[@id='j_id23:answer']")
                    text_write.send_keys(result['code'])

                    submit_element = driver.find_element(By.XPATH, "//a[contains(text(), 'Aceptar')]")
                    submit_element.click()

                    time.sleep(2)

                    # Switching back to default content and scrolling up
                    driver.switch_to.default_content()
                    driver.execute_script("window.scrollTo(0, 0);")
                    print("Scrolled up successfully.")

                    # Switch back to the iframe to continue
                    iframe = driver.find_element(By.XPATH, "//iframe[contains(@src, 'ecensofront/html/homeColegiados.iface')]")
                    driver.switch_to.frame(iframe)

                    time.sleep(2)


                    try:
                        element = driver.find_element(By.XPATH, "//div[@class='icePnlPop corePopup']")
                        print("Element found.")
                        # Perform operations if needed
                    except NoSuchElementException:
                        print("Element not found. Breaking the loop.")
                        break  # Exit the loop if the element is not found

                except Exception as e:
                    print(f"Error occurred while solving captcha: {e}")

        except Exception as e:
            print(f"An error occurred: {e}")

def insert_data_mongo(nombre, colegio, alta_colegiacion, n_colegiado, ejerciente, residente, direccion_profesional, telefono, fax):
    try:
        
        # Prepare the data to insert
        data = {
            "Nombre": nombre,
            "Colegio": colegio,
            "Alta_Colegiacion": alta_colegiacion,
            "N_Colegiado": n_colegiado,
            "Ejerciente": ejerciente,
            "Residente": residente,
            "Direccion_Profesional": direccion_profesional,
            "Telefono": telefono,
            "Fax": fax
        }
        
        # Insert the data into MongoDB
        collectio_data.insert_one(data)
        print(f"Inserted data for {nombre} into MongoDB successfully")

    except Exception as e:
        print(f"Error inserting data for {nombre}: {e}")


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

for record in names:
    first_name = record['first_name']
    last_name = record.get('last_name', '')  # Get last_name or use an empty string if it's not present

    existing_record = collectio_data.find_one({"Nombre": f"{first_name} {last_name}"})
    if existing_record:
        print(f"Record for {first_name} {last_name} already exists. Skipping.")
        continue  # Skip the current iteration if the record exists



    
    # Input first name
    input_first_value = wait.until(EC.presence_of_element_located((By.XPATH, '//input[@id="j_id23:j_id33"]')))
    input_first_value.clear()  # Clear the input field before entering new text
    input_first_value.send_keys(first_name)

    # Input last name
    input_second_value = wait.until(EC.presence_of_element_located((By.XPATH, '//input[@id="j_id23:j_id41"]')))
    input_second_value.clear()  # Clear the input field before entering new text
    input_second_value.send_keys(last_name)

    print(f'Searching for: {first_name} {last_name}')


    time.sleep(5)


    
    # Submit the form (or click the search button)
    search_button = wait.until(EC.element_to_be_clickable((By.XPATH, '//a[contains(text(), "Buscar")]')))
    search_button.click()



    solve_captcha(driver)

    time.sleep(10)  



    name_rows = driver.find_element(By.XPATH, ".//td[contains(@style, 'width:140px')]//span")
    name_rows.click()

    time.sleep(5)

    info = extract_information(driver)
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

    insert_data_mongo(nombre, colegio, alta_colegiacion, n_colegiado, ejerciente, residente, direccion_profesional, telefono,fax)

    WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, "//a[@id='j_id23:j_id50']"))
    ).click()
    
    solve_captcha(driver)

    time.sleep(10)













