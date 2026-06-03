
import pandas as pd


def main():
    input_path = "contracts_with_sectors.csv"
    df = pd.read_csv(input_path)
    df = df[df["price"].notna() & (df["price"] > 0)]
    group_flows = (
        df.groupby(
            ["customer_section", "customer_group", "customer_group_name",
             "supplier_section", "supplier_group", "supplier_group_name"],
            as_index=False
        )["price"]
        .sum()
        .rename(columns={
            "customer_section": "source_section",
            "customer_group": "source_group",
            "customer_group_name": "source_group_name",
            "supplier_section": "target_section",
            "supplier_group": "target_group",
            "supplier_group_name": "target_group_name",
            "price": "money_flow",
        })
        .sort_values("money_flow", ascending=False)
    )
    group_flows.to_csv("sector_flows_groups.csv", index=False, encoding="utf-8-sig")
    print("Сохранено: sector_flows_groups.csv")
    print(group_flows.head(10).to_string())

    section_flows = (
        df.groupby(["customer_section", "supplier_section"], as_index=False)["price"]
        .sum()
        .rename(columns={
            "customer_section": "source",
            "supplier_section": "target",
            "price": "money_flow",
        })
        .sort_values("money_flow", ascending=False)
    )
    section_flows.to_csv("sector_flows.csv", index=False, encoding="utf-8-sig")
    print("\nСохранено: sector_flows.csv")


if __name__ == "__main__":
    main()
    
