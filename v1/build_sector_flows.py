import pandas as pd

def main():
    input_path = "contracts_with_sectors.csv"
    output_path = "sector_flows.csv"
    df = pd.read_csv(input_path)
    df = df[df["price"].notna()]
    df = df[df["price"] > 0]
    flows = (
        df.groupby(["customer_sector", "supplier_sector"], as_index=False)["price"]
        .sum()
        .rename(columns={
            "customer_sector": "source",
            "supplier_sector": "target",
            "price": "money_flow"
        })
        .sort_values("money_flow", ascending=False)
    )
    flows.to_csv(output_path, index=False, encoding="utf-8-sig")
    print(f"Сохранено: {output_path}")
    print(flows.head(20))

if __name__ == "__main__":
    main()
