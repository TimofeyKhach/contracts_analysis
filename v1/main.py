import time
import pandas as pd

from parsers import get_contract_card, get_contracts_list, parse_contracts_list, parse_supplier_info
from utils import clean_price, clean_supplier_data


def main():
    all_data = []
    max_pages = int(input("Сколько страниц парсить? "))
    
    for page in range(1, max_pages + 1):
        print(f"\nСтраница {page}")
        html_list = get_contracts_list(page)
        if not html_list:
            continue
        contracts = parse_contracts_list(html_list)
        print(f"Найдено контрактов: {len(contracts)}")

        for i, contract in enumerate(contracts, 1):
            
            card_html = get_contract_card(contract['reg_number'], contract['contract_info_id'])
            if not card_html:
                print("ошибка загрузки")
                contract['supplier_name'] = ''
                all_data.append(contract)
                continue
            supplier_info = parse_supplier_info(card_html)
            full_contract = {**contract, **supplier_info}
            all_data.append(full_contract)            
            time.sleep(0.5)
        time.sleep(1)

    if all_data:
        raw_file = 'contracts_raw.csv'
        df_raw = pd.DataFrame(all_data)
        df_raw.to_csv(raw_file, index=False, encoding='utf-8-sig')
        print(f"\nСырые данные сохранены в {raw_file}")
        
        df_clean = clean_supplier_data(df_raw)
        df_clean['price'] = df_clean['price'].apply(clean_price)
        
        clean_file = 'contracts_clean.csv'
        df_clean.to_csv(clean_file, index=False, encoding='utf-8-sig')
        print(f"Очищенные данные сохранены в {clean_file}")
        print(f"   Колонки: {list(df_clean.columns)}")
    else:
        print("\nНе удалось собрать данные")


if __name__ == "__main__":
    main()
