# src/scraper.py

import time
import json
import re
from playwright.sync_api import Playwright, Page
from .utils.firebase_utils import save_to_firestore # Importação de função utilitária

INPUT_FILE = "inputs/search_list.json"
OUTPUT_FILE = "output/contacts.json"

def load_search_data(file_path: str) -> list:
    """Carrega a lista de pesquisa do arquivo JSON de entrada."""
    print(f"Carregando dados de pesquisa de {file_path}...")
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            return json.load(file).get('segments', [])
    except FileNotFoundError:
        print(f"Erro: Arquivo de entrada não encontrado em {file_path}")
        return []
    except json.JSONDecodeError:
        print(f"Erro: Não foi possível decodificar o JSON em {file_path}")
        return []

def update_local_json(path_file: str, new_data: dict, key: str):
    """Carrega dados locais existentes, atualiza ou adiciona um novo registro e salva."""
    print("Atualizando dados locais...")
    try:
        with open(path_file, mode="r", encoding="utf-8") as file:
            existing_data = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        existing_data = []

    updated = False
    for entry in existing_data:
        if entry.get("key") == key:
            entry.update(new_data)
            updated = True
            print(f"Local: Dados para a chave {key} atualizados.")
            break

    if not updated:
        new_data["key"] = key
        existing_data.append(new_data)
        print(f"Local: Dados para a chave {key} adicionados.")

    # Salva os dados atualizados de volta no arquivo
    with open(path_file, mode="w", encoding="utf-8") as file:
        json.dump(existing_data, file, ensure_ascii=False, indent=4)

def auto_scroll(page: Page, container_selector: str, scroll_step: int = 800, delay: int = 5000):
    """Rola o container de resultados até o final da página."""
    print("Relacionando dados do container...")
    while True:
        # Pega a posição de rolagem e a altura total
        scroll_position = page.evaluate(
            f"document.querySelector('{container_selector}').scrollTop"
        )
        scroll_height = page.evaluate(
            f"document.querySelector('{container_selector}').scrollHeight"
        )
        client_height = page.evaluate(
            f"document.querySelector('{container_selector}').clientHeight"
        )

        # Checa se chegou ao final
        if scroll_position + client_height >= scroll_height:
            print("Rolagem concluída.")
            break

        # Rola para baixo
        page.evaluate(
            f"document.querySelector('{container_selector}').scrollTop += {scroll_step}"
        )
        time.sleep(delay / 1000)

def run(playwright: Playwright):
    """Função principal de raspagem."""
    print("Iniciando o processo de raspagem...")
    chromium = playwright.chromium
    browser = chromium.launch(headless=True) # Mantenha o headless como opção
    page = browser.new_page()

    data_list = load_search_data(INPUT_FILE)
    if not data_list:
        browser.close()
        return # Encerra se não houver dados

    # Define o padrão regex para números de telefone
    phone_pattern = re.compile(r"\(\d{2}\) \d{4,5}-\d{4}")

    # Iterar sobre cada entrada no arquivo JSON
    for data in data_list:
        pesquisa = f"{data['name']} em {data['city']}"
        attempts = 0
        max_attempts = 3
        
        while attempts < max_attempts:
            try:
                # 1. Navegação e Pesquisa
                print(f"\nTentativa {attempts + 1}/{max_attempts}: Pesquisando '{pesquisa}'...")
                page.goto("https://www.google.com/maps")
                
                inputSearch = page.locator("#searchboxinput")
                inputSearch.wait_for(state="visible", timeout=10000)
                inputSearch.click()
                inputSearch.fill(pesquisa)
                page.keyboard.press("Enter")
                time.sleep(4) # Pausa para carregar os resultados

                # 2. Rolagem dos Resultados
                page.wait_for_selector(".hfpxzc", timeout=10000)
                
                # Seletor do container de resultados
                conteiner_selector = '#QA0Szd > div > div > div.w6VYqd > div.bJzME.tTVLSc > div > div.e07Vkf.kA9KIf > div > div > div.m6QErb.DxyBCb.kA9KIf.dS8AEf.XiKgde.ecceSd > div.m6QErb.DxyBCb.kA9KIf.dS8AEf.XiKgde.ecceSd'
                auto_scroll(page, conteiner_selector)

                # 3. Coleta de Dados
                print(f'Coletando detalhes para: {pesquisa}')
                containeres = page.locator("xpath=//div[contains(@class,'Nv2PK')]")
                count = containeres.count()
                print(f"Total de resultados encontrados: {count}")

                for i in range(count):
                    container = containeres.nth(i)
                    container.click()
                    time.sleep(3) # Pausa para carregar os detalhes

                    try:
                        feed = page.locator("xpath=//div[contains(@class, 'm6QErb')]")
                        results = feed.locator("xpath=//div[contains(@class, 'AeaXub')]/div[contains(@class, 'rogA2c')]/div[contains(@class, 'Io6YTe')]").all_inner_texts()
                        
                        # Extrai Nome e Segmento
                        name_element = feed.locator("xpath=//h1[contains(@class, 'lfPIob')]")
                        name = name_element.inner_text() if name_element.is_visible() else "N/A"
                        
                        segmento_element = feed.locator('xpath=//button[contains(@class, "DkEaL")]')
                        segmento = segmento_element.text_content() if segmento_element.is_visible() else data['name']
                        
                        # Extrai Telefone e Endereço
                        phone = [p for p in results if phone_pattern.match(p)]
                        
                        if phone:
                            endereco = results[0] if results else "N/A" # O primeiro elemento costuma ser o endereço
                            key = re.sub(r"[^\d]", "", phone[0])
                            
                            contact_data = {
                                "name": name,
                                "endereco": endereco,
                                "phone": phone[0],
                                "segmento": segmento
                            }

                            # Salva Localmente e no Firestore
                            update_local_json(OUTPUT_FILE, contact_data, key)
                            save_to_firestore(contact_data, key) # Chama a função do módulo utils

                        else:
                            print(f"Resultado {i+1}: '{name}' - Nenhum número de telefone válido encontrado.")
                            
                    except Exception as e:
                        print(f"Erro ao processar container {i+1}: {e}")
                        
                break # Sai do loop 'while' de tentativas se o scraping for bem-sucedido

            except Exception as e:
                print(f"Erro fatal na navegação ou pesquisa: {e}")
                attempts += 1
                time.sleep(5) # Espera antes de tentar novamente
                
        if attempts >= max_attempts:
            print(f"Falha ao carregar o Google Maps após {max_attempts} tentativas para '{pesquisa}'. Pulando para próxima pesquisa.")

    browser.close()
    print("\nProcesso de raspagem concluído.")