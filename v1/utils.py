import pandas as pd
import re


def clean_price(price_str):
    if pd.isna(price_str) or price_str == '':
        return None
    cleaned = re.sub(r'[^\d.,]', '', str(price_str))
    cleaned = cleaned.replace(',', '.')
    parts = cleaned.split('.')
    if len(parts) > 2:
        integer_part = ''.join(parts[:-1])
        decimal_part = parts[-1]
        cleaned = f"{integer_part}.{decimal_part}"
    try:
        return float(cleaned)
    except ValueError:
        return None


def clean_supplier_data(df):
    """Очищает данные о поставщике и возвращает df только с нужными колонками"""
    df['supplier_name_clean'] = ''
    df['supplier_inn_clean'] = ''
    df['supplier_kpp_clean'] = ''
    df['supplier_address_clean'] = ''
    df['supplier_phone_clean'] = ''
    df['supplier_email_clean'] = ''
    for idx, row in df.iterrows():
        text = str(row['supplier_name']) if pd.notna(row['supplier_name']) else ''
        if not text or text == 'nan':
            continue
        inn_match = re.search(r'ИНН[:\s]*(\d{10}|\d{12})', text)
        if inn_match:
            df.at[idx, 'supplier_inn_clean'] = inn_match.group(1)
        kpp_match = re.search(r'КПП[:\s]*(\d{9})', text)
        if kpp_match:
            df.at[idx, 'supplier_kpp_clean'] = kpp_match.group(1)
        email_match = re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text)
        if email_match:
            df.at[idx, 'supplier_email_clean'] = email_match.group(0)
        phone_match = re.search(r'[\+\d][\d\s\-\(\)]{8,}', text)
        if phone_match:
            df.at[idx, 'supplier_phone_clean'] = phone_match.group(0).strip()
        address_match = re.search(r'Адрес[:\s]*([^,\n]+(?:ул\.|д\.|к\.|площадь|проспект)[^,\n]+)', text, re.I)
        if address_match:
            df.at[idx, 'supplier_address_clean'] = address_match.group(1).strip()
        name = text
        name = re.sub(r'ИНН[:\s]*\d{10,12}', '', name)
        name = re.sub(r'КПП[:\s]*\d{9}', '', name)
        name = re.sub(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', '', name)
        name = re.sub(r'[\+\d][\d\s\-\(\)]{8,}', '', name)
        name = re.sub(r'Индивидуальный\s*предприниматель', '', name)
        name = re.sub(r'\s+', ' ', name).strip()
        name = re.sub(r',\s*$', '', name)
        df.at[idx, 'supplier_name_clean'] = name if len(name) > 5 else text[:100]
    df = df.drop(
        columns=[
            col for col in df.columns if col.startswith('supplier_') and not col.endswith('_clean')
        ]
    )
    rename_map = {
        'supplier_name_clean': 'supplier_name',
        'supplier_inn_clean': 'supplier_inn',
        'supplier_kpp_clean': 'supplier_kpp',
        'supplier_address_clean': 'supplier_address',
        'supplier_phone_clean': 'supplier_phone',
        'supplier_email_clean': 'supplier_email'
    }
    df = df.rename(columns=rename_map)
    
    return df
