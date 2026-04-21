import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import re

from config import URL_MAIN, URL_CONTRACT, HEADERS, COOKIES, PARAMS


session = requests.Session()
session.headers.update(HEADERS)
session.cookies.update(COOKIES)


def get_contracts_list(page_num=1):
    """Получает HTML страницы со списком контрактов"""
    PARAMS.update({'pageNumber': page_num})
    try:
        response = session.get(url=URL_MAIN, params=PARAMS, timeout=30)
        response.encoding = 'utf-8'
        response.raise_for_status()
        return response.text
    except Exception as e:
        print(f"Ошибка загрузки списка страницы {page_num}: {e}")
        return None


def parse_contracts_list(html):
    """Парсит список контрактов, извлекая номер и contractInfoId"""
    soup = BeautifulSoup(html, 'html.parser')
    contracts = []
    
    blocks = soup.find_all('div', class_='search-registry-entry-block')
    
    if not blocks:
        return []
    
    for block in blocks:
        contract = {}
        
        card_link = block.find('a', href=re.compile(r'/epz/contract/contractCard/common-info.html'))
        if card_link:
            contract['reg_number'] = card_link.get_text(strip=True)
            href = card_link.get('href', '')
            match = re.search(r'contractInfoId=(\d+)', href)
            if match:
                contract['contract_info_id'] = match.group(1)
            else:
                hidden_input = block.find('input', {'class': 'entityId'})
                if hidden_input and hidden_input.get('value'):
                    contract['contract_info_id'] = hidden_input.get('value')
        
        if contract.get('reg_number') and contract.get('contract_info_id'):
            status_elem = block.find('div', class_='registry-entry__header-mid__title')
            if status_elem:
                contract['status'] = status_elem.get_text(strip=True)
            
            customer_elem = block.find('div', class_='registry-entry__body-href')
            if customer_elem:
                customer_link = customer_elem.find('a')
                if customer_link:
                    contract['customer'] = customer_link.get_text(strip=True)
            
            price_elem = block.find('div', class_='price-block__value')
            if price_elem:
                contract['price'] = price_elem.get_text(strip=True)
            
            contracts.append(contract)
    
    return contracts


def get_contract_card(reg_number, contract_info_id):
    """Загружает карточку контракта"""
    params = {
        'reestrNumber': reg_number,
        'contractInfoId': contract_info_id
    }
    try:
        response = session.get(url=URL_CONTRACT, params=params, timeout=30)
        response.encoding = 'utf-8'
        response.raise_for_status()
        return response.text
    except Exception as e:
        print(f"  Ошибка загрузки карточки: {e}")
        return None

def parse_supplier_info(html):
    """Извлекает информацию о поставщике из карточки контракта"""
    soup = BeautifulSoup(html, 'html.parser')
    supplier_info = {}
    
    supplier_block = None
    
    for header in soup.find_all(['h2', 'h3'], string=re.compile(r'Информация о поставщиках', re.I)):
        supplier_block = header.find_parent('div', class_='blockInfo')
        if not supplier_block:
            supplier_block = header.parent
        break
    
    if supplier_block:
        table = supplier_block.find('table', class_=re.compile(r'blockInfo__table|participants', re.I))
        
        if table:
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all('td')
                if len(cells) >= 1:
                    first_cell = cells[0]
                    
                    org_name = first_cell.get_text(strip=True).split('\n')[0]
                    if org_name and org_name not in ['', 'Организация']:
                        supplier_info['supplier_name'] = org_name
                    
                    inn_elem = first_cell.find('span', string=re.compile(r'ИНН:', re.I))
                    if inn_elem:
                        inn_value = inn_elem.find_next_sibling('span')
                        if inn_value:
                            supplier_info['supplier_inn'] = inn_value.get_text(strip=True)
                    
                    kpp_elem = first_cell.find('span', string=re.compile(r'КПП:', re.I))
                    if kpp_elem:
                        kpp_value = kpp_elem.find_next_sibling('span')
                        if kpp_value:
                            supplier_info['supplier_kpp'] = kpp_value.get_text(strip=True)
                    
                    okpo_elem = first_cell.find('span', string=re.compile(r'ОКПО:', re.I))
                    if not okpo_elem:
                        okpo_elem = first_cell.find('span', string=re.compile(r'Код по ОКПО:', re.I))
                    if okpo_elem:
                        okpo_value = okpo_elem.find_next_sibling('span')
                        if okpo_value:
                            supplier_info['supplier_okpo'] = okpo_value.get_text(strip=True)
                    
                    if len(cells) >= 3:
                        address = cells[2].get_text(strip=True)
                        if address and len(address) > 5 and address != 'Адрес места нахождения':
                            supplier_info['supplier_address'] = address
                    
                    if len(cells) >= 4:
                        contact = cells[3].get_text(strip=True)
                        if contact:
                            lines = contact.split('\n')
                            for line in lines:
                                line = line.strip()
                                if line:
                                    if '@' in line:
                                        supplier_info['supplier_email'] = line
                                    elif re.search(r'[\d\-\(\)\s\+]+', line) and len(line) > 5:
                                        supplier_info['supplier_phone'] = line
                    
                    break
        else:
            participants_div = soup.find('div', class_=re.compile(r'participantsInnerHtml', re.I))
            if participants_div:
                text = participants_div.get_text(strip=True)
                
                org_match = re.search(r'(Акционерное общество|ООО|ОАО|ЗАО|ПАО|АО|ИП|МУП|ГУП|ФГУП)[^ИНН]+', text)
                if org_match:
                    supplier_info['supplier_name'] = org_match.group(0).strip()
                
                inn_match = re.search(r'ИНН:\s*(\d{10}|\d{12})', text)
                if inn_match:
                    supplier_info['supplier_inn'] = inn_match.group(1)
                
                kpp_match = re.search(r'КПП:\s*(\d{9})', text)
                if kpp_match:
                    supplier_info['supplier_kpp'] = kpp_match.group(1)
                
                okpo_match = re.search(r'ОКПО:\s*(\d+)', text)
                if okpo_match:
                    supplier_info['supplier_okpo'] = okpo_match.group(1)
                
                address_match = re.search(r'Адрес места нахождения\s*([^\n]+)', text)
                if address_match:
                    supplier_info['supplier_address'] = address_match.group(1).strip()
                
                phone_match = re.search(r'Телефон[:\s]*([^\n]+)', text)
                if phone_match:
                    supplier_info['supplier_phone'] = phone_match.group(1).strip()
                
                email_match = re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text)
                if email_match:
                    supplier_info['supplier_email'] = email_match.group(0)
    
    return supplier_info
