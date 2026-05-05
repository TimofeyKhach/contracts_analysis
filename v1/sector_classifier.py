import re
import pandas as pd
from sector_rules import CUSTOMER_SECTOR_RULES, SUPPLIER_SECTOR_RULES

def normalize(text: str) -> str:
    if pd.isna(text):
        return ""
    text = str(text).lower().replace("ё", "е")
    text = re.sub(r'[^a-zа-я0-9\s"]+', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def classify_by_rules(text: str, rules: dict, default: str = "other") -> str:
    text = normalize(text)
    scores = {}
    for sector, keywords in rules.items():
        scores[sector] = sum(1 for kw in keywords if kw in text)
    best_sector = max(scores, key=scores.get) if scores else default
    return best_sector if scores.get(best_sector, 0) > 0 else default

def classify_customer_sector(customer: str) -> str:
    return classify_by_rules(customer, CUSTOMER_SECTOR_RULES, default="government_other")

def classify_supplier_sector(supplier: str) -> str:
    supplier = normalize(supplier)
    if "индивидуальный предприниматель" in supplier or re.fullmatch(r"[а-я]+\s+[а-я]+\s+[а-я]+", supplier):
        return "individual_entrepreneur"
    return classify_by_rules(supplier, SUPPLIER_SECTOR_RULES, default="business_other")


def main():
    input_path = "contracts_clean.csv"
    output_path = "contracts_with_sectors.csv"
    df = pd.read_csv(input_path)
    df["customer_sector"] = df["customer"].apply(classify_customer_sector)
    df["supplier_sector"] = df["supplier_name"].apply(classify_supplier_sector)
    df.to_csv(output_path, index=False, encoding="utf-8-sig")
    print(f"Сохранено: {output_path}")
    print(df[["customer", "customer_sector", "supplier_name", "supplier_sector"]].head(10))

if __name__ == "__main__":
    main()
