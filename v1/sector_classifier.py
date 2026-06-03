import re
import os
import pandas as pd
from sector_rules import OKVED_GROUP_RULES, OKVED_SECTIONS, GROUP_TO_SECTION, GROUP_NAMES


def normalize(text: str) -> str:
    if pd.isna(text):
        return ""
    text = str(text).lower().replace("ё", "е")
    text = re.sub(r'[^a-zа-я0-9\s"]+', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def classify_by_okved_group(text: str, default_group: str = "46", default_section: str = "G") -> tuple:
    text = normalize(text)
    if not text:
        return default_group, default_section

    scores = {}
    for group_code, section, name, keywords in OKVED_GROUP_RULES:
        score = sum(1 for kw in keywords if kw in text)
        if score > 0:
            scores[(group_code, section)] = score

    if not scores:
        return default_group, default_section

    best = max(scores, key=scores.get)
    return best[0], best[1]


def classify_supplier(supplier: str) -> tuple:
    norm = normalize(supplier)
    if not norm:
        return "46", "G"
    if "индивидуальный предприниматель" in norm or re.fullmatch(r"[а-я]+ [а-я]+ [а-я]+", norm):
        return "IP", "IP"
    return classify_by_okved_group(norm)


def main():
    input_path = os.path.join(os.path.dirname(__file__), "contracts_clean.csv")
    output_path = "contracts_with_sectors.csv"

    df = pd.read_csv(input_path)

    customer_results = df["customer"].apply(lambda x: classify_by_okved_group(x, "84", "O"))
    df["customer_group"] = customer_results.apply(lambda x: x[0])
    df["customer_section"] = customer_results.apply(lambda x: x[1])

    supplier_results = df["supplier_name"].apply(classify_supplier)
    df["supplier_group"] = supplier_results.apply(lambda x: x[0])
    df["supplier_section"] = supplier_results.apply(lambda x: x[1])

    df["customer_group_name"] = df["customer_group"].map(GROUP_NAMES).fillna("Прочее")
    df["customer_section_name"] = df["customer_section"].map(OKVED_SECTIONS).fillna("Прочее")
    df["supplier_group_name"] = df["supplier_group"].map(GROUP_NAMES).fillna("ИП / Физлицо")
    df["supplier_section_name"] = df["supplier_section"].map(OKVED_SECTIONS).fillna("ИП / Физлицо")

    df.to_csv(output_path, index=False, encoding="utf-8-sig")
    print(f"Сохранено: {output_path}")
    print(df[["customer", "customer_section", "customer_group",
              "supplier_name", "supplier_section", "supplier_group"]].head(10).to_string())


if __name__ == "__main__":
    main()

