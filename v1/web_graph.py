import math
import json
import re
import pandas as pd
import networkx as nx
from pyvis.network import Network

NODE_COLORS = {
    "government": "#4C78A8",
    "government_other": "#7A9CC6",
    "healthcare": "#E45756",
    "healthcare_suppliers": "#F28E8C",
    "education": "#72B7B2",
    "education_suppliers": "#9ED9D4",
    "culture": "#B279A2",
    "social": "#FF9DA6",
    "housing_utilities": "#8C6D31",
    "energy": "#F2CF5B",
    "construction": "#59A14F",
    "it_equipment": "#79706E",
    "security": "#D37295",
    "waste_ecology": "#76B7B2",
    "water_utilities": "#86BCB6",
    "sports": "#A0CBE8",
    "office_household": "#BAB0AC",
    "business_other": "#9C755F",
    "individual_entrepreneur": "#FFBE7D",
}

def hex_to_rgba(hex_color, alpha=0.38):
    hex_color = hex_color.lstrip("#")
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"

def fmt_money(x):
    try:
        return f"{float(x):,.2f} ₽".replace(",", " ")
    except Exception:
        return str(x)

def sanitize_for_json(value):
    if pd.isna(value):
        return ""
    return str(value)

def build_sector_details(flows_df, contracts_df):
    details = {}
    all_sectors = sorted(set(flows_df["source"]).union(set(flows_df["target"])))

    for sector in all_sectors:
        outgoing = (
            flows_df[flows_df["source"] == sector][["target", "money_flow"]]
            .sort_values("money_flow", ascending=False)
            .head(7)
        )
        incoming = (
            flows_df[flows_df["target"] == sector][["source", "money_flow"]]
            .sort_values("money_flow", ascending=False)
            .head(7)
        )
        outgoing_targets = set(outgoing["target"].tolist())
        incoming_sources = set(incoming["source"].tolist())
        outgoing_contracts = contracts_df[
            (contracts_df["customer_sector"] == sector) &
            (contracts_df["supplier_sector"].isin(outgoing_targets))
        ].copy()
        incoming_contracts = contracts_df[
            (contracts_df["supplier_sector"] == sector) &
            (contracts_df["customer_sector"].isin(incoming_sources))
        ].copy()
        related_contracts = pd.concat(
            [outgoing_contracts, incoming_contracts],
            ignore_index=True
        )
        related_contracts = related_contracts.sort_values(
            "price", ascending=False
        ).head(10)
        contract_examples = []
        for _, row in related_contracts.iterrows():
            contract_examples.append({
                "customer": sanitize_for_json(row.get("customer", "")),
                "supplier": sanitize_for_json(row.get("supplier_name", "")),
                "price": fmt_money(row.get("price", 0)),
                "customer_sector": sanitize_for_json(row.get("customer_sector", "")),
                "supplier_sector": sanitize_for_json(row.get("supplier_sector", ""))
            })
        details[sector] = {
            "outgoing": [
                {
                    "label": sanitize_for_json(r["target"]),
                    "value": fmt_money(r["money_flow"])
                }
                for _, r in outgoing.iterrows()
            ],
            "incoming": [
                {
                    "label": sanitize_for_json(r["source"]),
                    "value": fmt_money(r["money_flow"])
                }
                for _, r in incoming.iterrows()
            ],
            "contracts": contract_examples
        }
    return details
  
def inject_sidebar(html_path, details, node_weights):
    with open(html_path, "r", encoding="utf-8") as f:
        content = f.read()

    details_json = json.dumps(details, ensure_ascii=False)
    weights_json = json.dumps(
        {k: fmt_money(v) for k, v in node_weights.items()},
        ensure_ascii=False,
    )
    content = re.sub(
        r'<body[^>]*>.*?<div id="mynetwork" class="card-body"></div>',
        """
<body>
<div class="wrapper">
    <div id="graph">
        <div id="mynetwork" class="card-body"></div>
    </div>
    <div id="sidepanel">
        <h2>Информация по отрасли</h2>
        <div class="card">
            Нажми на узел графа, чтобы увидеть:
            <ul>
                <li>общий оборот отрасли</li>
                <li>топ исходящих потоков</li>
                <li>топ входящих потоков</li>
                <li>примеры контрактов</li>
            </ul>
        </div>
    </div>
</div>
""",
        content,
        count=1,
        flags=re.DOTALL,
    )

    style_and_data = f"""
<style>
html, body {{
    margin: 0;
    padding: 0;
    width: 100%;
    height: 100%;
    overflow: hidden;
    font-family: Arial, sans-serif;
    background: #ffffff;
}}

.wrapper {{
    display: flex;
    width: 100vw;
    height: 100vh;
}}

#graph {{
    flex: 1 1 auto;
    min-width: 0;
    height: 100vh;
    background: #ffffff;
    overflow: hidden;
}}

#mynetwork {{
    width: 100% !important;
    height: 100vh !important;
    background: #ffffff !important;
    border: none !important;
}}

#sidepanel {{
    width: 430px;
    height: 100vh;
    overflow-y: auto;
    box-sizing: border-box;
    padding: 18px 20px;
    background: #fafafa;
    border-left: 1px solid #dddddd;
}}

#sidepanel h2 {{
    margin-top: 0;
    font-size: 24px;
}}

#sidepanel h3 {{
    margin-top: 18px;
    margin-bottom: 8px;
    font-size: 16px;
}}

.card {{
    background: white;
    border: 1px solid #e4e4e4;
    border-radius: 10px;
    padding: 12px;
    margin-bottom: 12px;
}}

.small {{
    color: #666666;
    font-size: 13px;
}}

ul {{
    padding-left: 18px;
    margin-top: 6px;
}}

li {{
    margin-bottom: 6px;
}}

.contract {{
    border-top: 1px solid #eeeeee;
    padding-top: 10px;
    margin-top: 10px;
}}
</style>

<script>
const sectorDetails = {details_json};
const sectorWeights = {weights_json};

function escapeHtml(text) {{
    if (!text) return "";
    return String(text)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}}

function renderSectorPanel(sector) {{
    const panel = document.getElementById("sidepanel");
    const details = sectorDetails[sector];

    if (!details) {{
        panel.innerHTML = `
            <h2>Информация по отрасли</h2>
            <div class="card">Нет данных.</div>
        `;
        return;
    }}

    const outgoingHtml = details.outgoing.length
        ? "<ul>" + details.outgoing.map(x =>
            `<li><b>${{escapeHtml(x.label)}}</b>: ${{escapeHtml(x.value)}}</li>`
          ).join("") + "</ul>"
        : "<div class='small'>Нет исходящих потоков</div>";

    const incomingHtml = details.incoming.length
        ? "<ul>" + details.incoming.map(x =>
            `<li><b>${{escapeHtml(x.label)}}</b>: ${{escapeHtml(x.value)}}</li>`
          ).join("") + "</ul>"
        : "<div class='small'>Нет входящих потоков</div>";

    const contractsHtml = details.contracts.length
        ? details.contracts.map(c => `
            <div class="contract">
                <div><b>Заказчик:</b> ${{escapeHtml(c.customer)}}</div>
                <div><b>Поставщик:</b> ${{escapeHtml(c.supplier)}}</div>
                <div><b>Сумма:</b> ${{escapeHtml(c.price)}}</div>
                <div class="small">${{escapeHtml(c.customer_sector)}} → ${{escapeHtml(c.supplier_sector)}}</div>
            </div>
        `).join("")
        : "<div class='small'>Нет примеров контрактов</div>";

    panel.innerHTML = `
        <h2>${{escapeHtml(sector)}}</h2>
        <div class="card">
            <div><b>Общий оборот:</b> ${{escapeHtml(sectorWeights[sector] || "нет данных")}}</div>
        </div>
        <div class="card">
            <h3>Куда идут деньги</h3>
            ${{outgoingHtml}}
        </div>
        <div class="card">
            <h3>Откуда приходят деньги</h3>
            ${{incomingHtml}}
        </div>
        <div class="card">
            <h3>Примеры контрактов</h3>
            ${{contractsHtml}}
        </div>
    `;
}}
</script>
"""

    content = content.replace("</head>", style_and_data + "\n</head>")

    click_script = """
<script>
setTimeout(function() {
    if (typeof network !== "undefined") {
        network.fit({
            animation: {
                duration: 600,
                easingFunction: "easeInOutQuad"
            }
        });

        network.on("click", function(params) {
            if (params.nodes.length > 0) {
                const nodeId = params.nodes[0];
                renderSectorPanel(nodeId);
            }
        });
    }
}, 300);
</script>
"""

    content = content.replace("</body>", click_script + "\n</body>")

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(content)


def ensure_bidirectional_presence(visible_flows, full_flows):
    visible = visible_flows.copy()
    sectors = sorted(set(full_flows["source"]).union(set(full_flows["target"])))

    for sector in sectors:
        has_out = not visible[visible["source"] == sector].empty
        has_in = not visible[visible["target"] == sector].empty

        if not has_out:
            best_out = (
                full_flows[full_flows["source"] == sector]
                .sort_values("money_flow", ascending=False)
                .head(1)
            )
            if not best_out.empty:
                visible = pd.concat([visible, best_out], ignore_index=True)

        if not has_in:
            best_in = (
                full_flows[full_flows["target"] == sector]
                .sort_values("money_flow", ascending=False)
                .head(1)
            )
            if not best_in.empty:
                visible = pd.concat([visible, best_in], ignore_index=True)

    visible = visible.drop_duplicates(subset=["source", "target"])
    return visible


def main():
    full_flows = pd.read_csv("sector_flows.csv")
    contracts = pd.read_csv("contracts_with_sectors.csv")

    full_flows = full_flows[full_flows["money_flow"] > 0].copy()
    full_flows = full_flows.sort_values("money_flow", ascending=False)

    threshold = full_flows["money_flow"].quantile(0.55)
    flows = full_flows[full_flows["money_flow"] >= threshold].copy()

    flows = ensure_bidirectional_presence(flows, full_flows)

    G = nx.DiGraph()

    for _, row in flows.iterrows():
        source = row["source"]
        target = row["target"]
        value = float(row["money_flow"])

        if G.has_edge(source, target):
            G[source][target]["weight"] += value
        else:
            G.add_edge(source, target, weight=value)

    node_weights = {}
    for node in G.nodes():
        total_weight = (
            sum(data["weight"] for _, _, data in G.in_edges(node, data=True))
            + sum(data["weight"] for _, _, data in G.out_edges(node, data=True))
        )
        node_weights[node] = total_weight

    net = Network(
        height="100vh",
        width="100%",
        directed=True,
        bgcolor="#ffffff",
        font_color="#222222",
    )

    net.toggle_physics(False)

    nodes = list(G.nodes())
    n = len(nodes)
    radius = 520

    for i, node in enumerate(nodes):
        angle = 2 * math.pi * i / n
        x = radius * math.cos(angle)
        y = radius * math.sin(angle)

        base_color = NODE_COLORS.get(node, "#4C78A8")
        size = max(18, min(58, 10 + node_weights[node] ** 0.12))

        net.add_node(
            node,
            label=node,
            title=f"{node} | Общий оборот: {fmt_money(node_weights[node])}",
            x=x,
            y=y,
            physics=False,
            color=base_color,
            size=size,
            borderWidth=2,
        )

    max_weight = max(data["weight"] for _, _, data in G.edges(data=True))

    for source, target, data in G.edges(data=True):
        weight = data["weight"]
        base_color = NODE_COLORS.get(source, "#4C78A8")
        width = 1 + 8 * (weight / max_weight)

        net.add_edge(
            source,
            target,
            value=weight,
            width=width,
            color=hex_to_rgba(base_color, 0.40),
            title=f"{source} → {target} | {fmt_money(weight)}",
            arrows="to",
            smooth={"type": "curvedCW", "roundness": 0.14},
        )

    output_path = "sector_graph.html"
    net.write_html(output_path, notebook=False)

    details = build_sector_details(flows, contracts)
    inject_sidebar(output_path, details, node_weights)

    print(f"Сохранено: {output_path}")


if __name__ == "__main__":
    main()
