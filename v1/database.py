import pandas as pd
from sqlalchemy import create_engine, text

from config import CREATE_TABLE_SQL, DATABASE_URL, DB_CONFIG

# DB_CONFIG = {
#     'host': 'localhost',
#     'port': 5432,
#     'database': 'zakupki_db',
#     'user': 'zakupki_user',
#     'password': 'zakupki_pass'
# }

# DATABASE_URL = f"postgresql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"

# CREATE_TABLE_SQL = """
# CREATE TABLE IF NOT EXISTS contracts (
#     id SERIAL PRIMARY KEY,
#     reg_number VARCHAR(50) UNIQUE NOT NULL,
#     contract_info_id VARCHAR(50),
#     status VARCHAR(100),
#     customer TEXT,
#     price NUMERIC(20,2),
#     supplier_name TEXT,
#     supplier_inn VARCHAR(20),
#     supplier_kpp VARCHAR(20),
#     supplier_okpo VARCHAR(20),
#     supplier_address TEXT,
#     supplier_phone VARCHAR(50),
#     supplier_email VARCHAR(100),
#     supplier_country VARCHAR(100),
#     supplier_registration_date DATE,
#     parsed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
#     updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
# );
# """

def main():
    df = pd.read_csv('contracts_clean.csv')
    df = df.where(pd.notnull(df), None)
    
    engine = create_engine(DATABASE_URL)
    
    with engine.connect() as conn:
        conn.execute(text(CREATE_TABLE_SQL))
        conn.commit()
        
        conn.execute(text("CREATE TEMP TABLE temp_contracts (LIKE contracts INCLUDING ALL) ON COMMIT DROP;"))
        
        df.to_sql('temp_contracts', conn, if_exists='append', index=False, method='multi')
        
        conn.execute(text("""
            INSERT INTO contracts (
                reg_number, contract_info_id, status, customer, price,
                supplier_name, supplier_inn, supplier_kpp, supplier_address,
                supplier_phone, supplier_email, updated_at
            )
            SELECT 
                reg_number, contract_info_id, status, customer, price,
                supplier_name, supplier_inn, supplier_kpp, supplier_address,
                supplier_phone, supplier_email, CURRENT_TIMESTAMP
            FROM temp_contracts
            ON CONFLICT (reg_number) DO UPDATE SET
                contract_info_id = EXCLUDED.contract_info_id,
                status = EXCLUDED.status,
                customer = EXCLUDED.customer,
                price = EXCLUDED.price,
                supplier_name = EXCLUDED.supplier_name,
                supplier_inn = EXCLUDED.supplier_inn,
                supplier_kpp = EXCLUDED.supplier_kpp,
                supplier_address = EXCLUDED.supplier_address,
                supplier_phone = EXCLUDED.supplier_phone,
                supplier_email = EXCLUDED.supplier_email,
                updated_at = CURRENT_TIMESTAMP;
        """))
        conn.commit()
    
    print(f"Обработано {len(df)} записей")

if __name__ == "__main__":
    main()
