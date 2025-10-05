import time
import json
from playwright.sync_api import sync_playwright, Playwright
import re
import firebase_admin
from firebase_admin import credentials, firestore

def run(playwright: Playwright):
    chromium = playwright.chromium # or "firefox" or "webkit".
    browser = chromium.launch(headless=True)
    page = browser.new_page()
    salvar_em = "output/contacts.json"

    data_list = []
    # Load the JSON file
    with open("inputs/search_list.json", "r", encoding="utf-8") as file:
        data_list = json.load(file)['segments']

    # Iterate over each entry in the JSON file
    for data in data_list:
        pesquisa = f"{data['name']} em {data['city']}"
        Erro = True
        count=0
        while Erro and count < 3:
            try:
                page.goto("http://google.com/maps/")
                inputSearch = page.locator("#searchboxinput")
                inputSearch.wait_for(state="visible", timeout=5000)
                inputSearch.click()
                inputSearch.fill(pesquisa)
                time.sleep(4)
                page.keyboard.press("Enter")
                time.sleep(4)

                # Wait for search results to load
                page.wait_for_selector(".hfpxzc", timeout=3000)
                time.sleep(3)
                Erro = False

                # Function to scroll the container automatically
                def auto_scroll(page, container_selector, scroll_step=800, delay=5000):
                    print("Processando..." + pesquisa)
                    while True:
                        # Get the current scroll position and the scroll height
                        scroll_position = page.evaluate(
                            f"document.querySelector('{container_selector}').scrollTop"
                        )
                        scroll_height = page.evaluate(
                            f"document.querySelector('{container_selector}').scrollHeight"
                        )
                        client_height = page.evaluate(
                            f"document.querySelector('{container_selector}').clientHeight"
                        )

                        # Check if the scroll has reached the bottom
                        if scroll_position + client_height >= scroll_height:
                            break

                        # Scroll down by the specified step
                        page.evaluate(
                            f"document.querySelector('{container_selector}').scrollTop += {scroll_step}"
                        )
                        time.sleep(delay / 1000)  # Convert delay to seconds

                # Call the auto_scroll function
                conteiner_selector = '#QA0Szd > div > div > div.w6VYqd > div.bJzME.tTVLSc > div > div.e07Vkf.kA9KIf > div > div > div.m6QErb.DxyBCb.kA9KIf.dS8AEf.XiKgde.ecceSd > div.m6QErb.DxyBCb.kA9KIf.dS8AEf.XiKgde.ecceSd'
                auto_scroll(page, conteiner_selector)

                print('Coletando dados...' + pesquisa)
                #iterar sobre cada elemento coletando os dados
                # Get all search results
                containeres = page.locator("xpath=//div[contains(@class,'Nv2PK')]")
                time.sleep(3)
                count = containeres.count()
                print(f"Total de resultados encontrados: {count}")

                for i in range(count):
                    container = containeres.nth(i)
                    container.click()
                    time.sleep(3)
                    try:
                        feed = page.locator("xpath=//div[contains(@class, 'm6QErb')]")
                        time.sleep(3)
                        results = feed.locator("xpath=//div[contains(@class, 'AeaXub')]/div[contains(@class, 'rogA2c')]/div[contains(@class, 'Io6YTe')]").all_inner_texts()
                        name = feed.locator("xpath=//h1[contains(@class, 'lfPIob')]").inner_text()
                        segmento = data['name']
                        if feed.locator('xpath=//button[contains(@class, "DkEaL")]').is_visible():
                            # If the button is visible, click it to get the segment
                            segmento = feed.locator('xpath=//button[contains(@class, "DkEaL")]').text_content()
                            time.sleep(3)
                        
                        # Define the regex pattern for phone numbers
                        phone_pattern = re.compile(r"\(\d{2}\) \d{4,5}-\d{4}")
                        phone = [p for p in results if phone_pattern.match(p)]

                        if phone:
                            endereco = [p for p in results if results[0]][0]
                            key = [re.sub(r"[^\d]", "", p) for p in phone][0] if phone else None
                            
                            path_file = salvar_em

                            # Load existing data
                            try:
                                with open(path_file, mode="r", encoding="utf-8") as file:
                                    existing_data = json.load(file)
                            except (FileNotFoundError, json.JSONDecodeError):
                                existing_data = []

                            # Update existing entry or add a new one
                            updated = False
                            for entry in existing_data:
                                if entry["key"] == key:
                                    entry.update({
                                        "name": name,
                                        "endereco": endereco,
                                        "phone": phone[0],
                                        "segmento": segmento
                                    })
                                    updated = True
                                    print(f"Local: Data for key {key} has been updated.")
                                    break

                            if not updated:
                                existing_data.append({
                                    "key": key,
                                    "name": name,
                                    "endereco": endereco,
                                    "phone": phone[0],
                                    "segmento": segmento
                                })
                                print(f"Local: Data for key {key} has been added.")

                            # Save updated data back to the file
                            with open(path_file, mode="w", encoding="utf-8") as file:
                                json.dump(existing_data, file, ensure_ascii=False, indent=4)

                            # print(f"Data for key {key} has been {'updated' if updated else 'added'}.")

                            # Save data to Firestore
                            try:

                                # Initialize Firebase Admin SDK
                                if not firebase_admin._apps:
                                    cred = credentials.Certificate("firebaseConfig.json")
                                    firebase_admin.initialize_app(cred)

                                db = firestore.client()

                                # Reference to the Firestore collection
                                collection_ref = db.collection("contacts")

                                # Check if the document already exists
                                doc_ref = collection_ref.document(key)
                                doc = doc_ref.get()

                                if doc.exists:
                                    # Update the existing document
                                    # doc_ref.update({
                                    #     "name": name,
                                    #     "endereco": endereco,
                                    #     "phone": phone[0],
                                    #     "segmento": segmento
                                    # })
                                    print(f"Firestore: Data for key {key} has exists.")
                                else:
                                    # Add a new document
                                    doc_ref.set({
                                        "name": name,
                                        "endereco": endereco,
                                        "phone": phone[0],
                                        "segmento": segmento
                                    })
                                    print(f"Firestore: Data for key {key} has been added.")
                            except Exception as e:
                                print(f"Error saving data to Firestore: {e}")
                                
                        else:
                            print("No valid phone numbers found.")
                    except Exception as e:
                        print(f"Error processing container {i}: {e}")
            except Exception as e:
                print(f"Error navigating to Google Maps: {e}")
                time.sleep(5)  # Wait before retrying
                count += 1
                if count >= 3:
                    print(f"Failed to load Google Maps after 3 attempts for {pesquisa}.")
                    break
                continue

    browser.close()

# To call the function
def main():
    with sync_playwright() as playwright:
        run(playwright)

main()