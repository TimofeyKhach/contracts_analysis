URL_MAIN = "https://zakupki.gov.ru/epz/contract/search/results.html"

URL_CONTRACT = "https://zakupki.gov.ru/epz/contract/contractCard/common-info.html"

HEADERS = {
    'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    'accept-encoding': 'gzip, deflate, br, zstd',
    'accept-language': 'ru,en;q=0.9,bg;q=0.8',
    'cache-control': 'max-age=0',
    'connection': 'keep-alive',
    'host': 'zakupki.gov.ru',
    'sec-ch-ua': '"Not(A:Brand";v="8", "Chromium";v="144", "YaBrowser";v="26.3", "Yowser";v="2.5"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
    'sec-fetch-dest': 'document',
    'sec-fetch-mode': 'navigate',
    'sec-fetch-site': 'same-origin',
    'sec-fetch-user': '?1',
    'upgrade-insecure-requests': '1',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 YaBrowser/26.3.0.0 Safari/537.36'
}

COOKIES = {
    'contractCsvSettingsId': 'bedbed5b-1be0-4593-a390-27d64e514fb9',
    '_ym_uid': '1773671929872743520',
    '_ym_d': '1773671929',
    '_ym_isad': '1'
}

PARAMS = {
    'morphology': 'on',
    'search-filter': 'Дате размещения',
    'fz44': 'on',
    'contractStageList_1': 'on',
    'contractStageList': '1',
    'budgetLevelsIdNameHidden': '{}',
    'sortBy': 'UPDATE_DATE',
    'sortDirection': 'false',
    'recordsPerPage': '_50',
    'showLotsInfoHidden': 'false'
}

DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'zakupki_db',
    'user': 'zakupki_user',
    'password': 'zakupki_pass'
}

DATABASE_URL = f"postgresql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS contracts (
    id SERIAL PRIMARY KEY,
    reg_number VARCHAR(50) UNIQUE NOT NULL,
    contract_info_id VARCHAR(50),
    status VARCHAR(100),
    customer TEXT,
    price NUMERIC(20,2),
    supplier_name TEXT,
    supplier_inn VARCHAR(20),
    supplier_kpp VARCHAR(20),
    supplier_okpo VARCHAR(20),
    supplier_address TEXT,
    supplier_phone VARCHAR(50),
    supplier_email VARCHAR(100),
    supplier_country VARCHAR(100),
    supplier_registration_date DATE,
    parsed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""
