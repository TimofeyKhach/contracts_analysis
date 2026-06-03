import math
import json
import re
import pandas as pd
import networkx as nx
from pyvis.network import Network

SECTION_COLORS = {
    "A": "#59A14F",
    "B": "#79706E",
    "C": "#F28E2B",
    "D": "#F2CF5B",
    "E": "#86BCB6",
    "F": "#B07AA1",
    "G": "#FF9DA7",
    "H": "#8CD17D",
    "I": "#FFBE7D",
    "J": "#4E79A7",
    "K": "#B6992D",
    "L": "#D37295",
    "M": "#A0CBE8",
    "N": "#9D7660",
    "O": "#4C78A8",
    "P": "#72B7B2",
    "Q": "#E45756",
    "R": "#B279A2",
    "S": "#BAB0AC",
    "T": "#C8D9E6",
    "U": "#9C755F",
    "IP": "#DDDDDD",
}

SECTION_LABELS = {
    "A": "A: Сельское хозяйство",
    "B": "B: Добыча",
    "C": "C: Производство",
    "D": "D: Энергетика",
    "E": "E: Водоснабжение/Отходы",
    "F": "F: Строительство",
    "G": "G: Торговля",
    "H": "H: Транспорт",
    "I": "I: Гостиницы/Питание",
    "J": "J: IT и связь",
    "K": "K: Финансы",
    "L": "L: Недвижимость",
    "M": "M: Профессиональные услуги",
    "N": "N: Административные услуги",
    "O": "O: Гос. управление",
    "P": "P: Образование",
    "Q": "Q: Здравоохранение",
    "R": "R: Культура и спорт",
    "S": "S: Прочие услуги",
    "T": "T: Домашние хозяйства",
    "U": "U: Экстерр. организации",
    "IP": "ИП / Физлица",
}


def hex_to_rgba(hex_color, alpha=0.38):
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


def fmt_money(x):
    try:
        return f"{float(x):,.0f} ₽".replace(",", " ")
    except Exception:
        return str(x)


def sanitize(value):
    if pd.isna(value):
        return ""
    return str(value)


def build_details(section_flows, group_flows, contracts_df):
    details = {}

    all_sections = sorted(set(section_flows["source"].astype(str)).union(section_flows["target"].astype(str)))
    for sec in all_sections:
        outgoing = (section_flows[section_flows["source"] == sec][["target", "money_flow"]]
                    .sort_values("money_flow", ascending=False).head(7))
        incoming = (section_flows[section_flows["target"] == sec][["source", "money_flow"]]
                    .sort_values("money_flow", ascending=False).head(7))

        examples = contracts_df[
            (contracts_df["customer_section"] == sec) | (contracts_df["supplier_section"] == sec)
        ].sort_values("price", ascending=False).head(8)

        contract_list = []
        for _, row in examples.iterrows():
            contract_list.append({
                "customer": sanitize(row.get("customer", "")),
                "supplier": sanitize(row.get("supplier_name", "")),
                "price": fmt_money(row.get("price", 0)),
                "c_group": sanitize(row.get("customer_group_name", "")),
                "s_group": sanitize(row.get("supplier_group_name", "")),
            })

        details[sec] = {
            "outgoing": [{"label": sanitize(r["target"]), "value": fmt_money(r["money_flow"])}
                         for _, r in outgoing.iterrows()],
            "incoming": [{"label": sanitize(r["source"]), "value": fmt_money(r["money_flow"])}
                         for _, r in incoming.iterrows()],
            "contracts": contract_list,
        }

    all_groups = sorted(set(group_flows["source_group"].astype(str)).union(group_flows["target_group"].astype(str)))
    for grp in all_groups:
        outgoing = (group_flows[group_flows["source_group"] == grp][["target_group", "target_group_name", "money_flow"]]
                    .sort_values("money_flow", ascending=False).head(7))
        incoming = (group_flows[group_flows["target_group"] == grp][["source_group", "source_group_name", "money_flow"]]
                    .sort_values("money_flow", ascending=False).head(7))

        examples = contracts_df[
            (contracts_df["customer_group"] == grp) | (contracts_df["supplier_group"] == grp)
        ].sort_values("price", ascending=False).head(8)

        contract_list = []
        for _, row in examples.iterrows():
            contract_list.append({
                "customer": sanitize(row.get("customer", "")),
                "supplier": sanitize(row.get("supplier_name", "")),
                "price": fmt_money(row.get("price", 0)),
                "c_group": sanitize(row.get("customer_group_name", "")),
                "s_group": sanitize(row.get("supplier_group_name", "")),
            })

        details[f"group_{grp}"] = {
            "outgoing": [{"label": f"{sanitize(r['target_group'])} {sanitize(r['target_group_name'])}",
                          "value": fmt_money(r["money_flow"])} for _, r in outgoing.iterrows()],
            "incoming": [{"label": f"{sanitize(r['source_group'])} {sanitize(r['source_group_name'])}",
                          "value": fmt_money(r["money_flow"])} for _, r in incoming.iterrows()],
            "contracts": contract_list,
        }

    return details


def ensure_all_sections_visible(visible, full):
    v = visible.copy()
    for sec in sorted(set(full["source"]).union(full["target"])):
        if v[v["source"] == sec].empty:
            best = full[full["source"] == sec].sort_values("money_flow", ascending=False).head(1)
            if not best.empty:
                v = pd.concat([v, best], ignore_index=True)
        if v[v["target"] == sec].empty:
            best = full[full["target"] == sec].sort_values("money_flow", ascending=False).head(1)
            if not best.empty:
                v = pd.concat([v, best], ignore_index=True)
    return v.drop_duplicates(subset=["source", "target"])


def build_section_graph(section_flows_df):
    full = section_flows_df[section_flows_df["money_flow"] > 0].sort_values("money_flow", ascending=False)
    threshold = full["money_flow"].quantile(0.45)
    visible = ensure_all_sections_visible(full[full["money_flow"] >= threshold], full)

    G = nx.DiGraph()
    for _, row in visible.iterrows():
        s, t, w = row["source"], row["target"], float(row["money_flow"])
        if G.has_edge(s, t):
            G[s][t]["weight"] += w
        else:
            G.add_edge(s, t, weight=w)
    return G


def inject_sidebar_and_logic(html_path, details, section_weights, group_weights,
                              section_labels, section_colors, group_flows_json):
    with open(html_path, "r", encoding="utf-8") as f:
        content = f.read()

    details_json     = json.dumps(details, ensure_ascii=False)
    sec_weights_json = json.dumps({k: fmt_money(v) for k, v in section_weights.items()}, ensure_ascii=False)
    grp_weights_json = json.dumps({k: fmt_money(v) for k, v in group_weights.items()}, ensure_ascii=False)
    sec_labels_json  = json.dumps(section_labels, ensure_ascii=False)
    sec_colors_json  = json.dumps(section_colors, ensure_ascii=False)
    group_flows_str  = json.dumps(group_flows_json, ensure_ascii=False)

    content = re.sub(
        r'<body[^>]*>.*?<div id="mynetwork" class="card-body"></div>',
        """
<body>
<div class="wrapper">
  <div id="graph">
    <div id="mode-bar">
      <span id="mode-label">Режим: <b>Разделы ОКВЭД</b></span>
      <button id="back-btn" style="display:none" onclick="switchToSections()">← Назад к разделам</button>
      <span id="hint-text" style="color:#888;font-size:13px">Двойной клик по узлу, чтобы раскрыть группы</span>
    </div>
    <div id="mynetwork" class="card-body"></div>
  </div>
  <div id="sidepanel">
    <h2>Информация по разделу</h2>
    <div class="card">
      Нажмите на узел, чтобы увидеть потоки.<br>
      Двойной клик, чтобы раскрыть группы ОКВЭД внутри раздела.
    </div>
  </div>
</div>
""",
        content, count=1, flags=re.DOTALL,
    )

    style_and_data = f"""
<style>
html,body{{margin:0;padding:0;width:100%;height:100%;overflow:hidden;font-family:Arial,sans-serif;background:#fff}}
.wrapper{{display:flex;width:100vw;height:100vh}}
#graph{{flex:1 1 auto;min-width:0;height:100vh;background:#fff;overflow:hidden;display:flex;flex-direction:column}}
#mode-bar{{padding:8px 16px;background:#f5f5f5;border-bottom:1px solid #ddd;display:flex;align-items:center;gap:12px;font-size:14px}}
#back-btn{{padding:4px 12px;background:#4C78A8;color:#fff;border:none;border-radius:5px;cursor:pointer;font-size:13px}}
#mynetwork{{flex:1;width:100%!important;background:#fff!important;border:none!important}}
#sidepanel{{width:420px;height:100vh;overflow-y:auto;box-sizing:border-box;padding:16px 18px;background:#fafafa;border-left:1px solid #ddd}}
#sidepanel h2{{margin-top:0;font-size:22px}}
#sidepanel h3{{margin-top:16px;margin-bottom:6px;font-size:15px}}
.card{{background:#fff;border:1px solid #e4e4e4;border-radius:10px;padding:12px;margin-bottom:10px}}
.small{{color:#666;font-size:12px}}
ul{{padding-left:16px;margin-top:4px}}
li{{margin-bottom:4px}}
.contract{{border-top:1px solid #eee;padding-top:8px;margin-top:8px;font-size:13px}}
</style>

<script>
const sectorDetails  = {details_json};
const sectorWeights  = {sec_weights_json};
const groupWeights   = {grp_weights_json};
const sectionLabels  = {sec_labels_json};
const sectionColors  = {sec_colors_json};
const groupFlowsData = {group_flows_str};

let currentMode = "sections";
let currentSection = null;

function esc(t){{
  if(!t) return "";
  return String(t).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;");
}}

function renderPanel(nodeId){{
  const panel = document.getElementById("sidepanel");
  const isGroup = currentMode === "groups";
  const key = isGroup ? "group_" + nodeId : nodeId;
  const d = sectorDetails[key];
  const weight = isGroup ? (groupWeights[nodeId]||"нет данных") : (sectorWeights[nodeId]||"нет данных");
  const title  = isGroup ? nodeId : (sectionLabels[nodeId]||nodeId);

  if(!d){{ panel.innerHTML=`<h2>${{esc(title)}}</h2><div class="card">Нет данных.</div>`; return; }}

  const outH = d.outgoing.length
    ? "<ul>" + d.outgoing.map(x=>`<li><b>${{esc(x.label)}}</b>: ${{esc(x.value)}}</li>`).join("") + "</ul>"
    : "<div class='small'>Нет исходящих</div>";

  const inH = d.incoming.length
    ? "<ul>" + d.incoming.map(x=>`<li><b>${{esc(x.label)}}</b>: ${{esc(x.value)}}</li>`).join("") + "</ul>"
    : "<div class='small'>Нет входящих</div>";

  const cH = d.contracts.length
    ? d.contracts.map(c=>`
        <div class="contract">
          <div><b>Заказчик:</b> ${{esc(c.customer)}}</div>
          <div><b>Поставщик:</b> ${{esc(c.supplier)}}</div>
          <div><b>Сумма:</b> ${{esc(c.price)}}</div>
          <div class="small">${{esc(c.c_group)}} → ${{esc(c.s_group)}}</div>
        </div>`).join("")
    : "<div class='small'>Нет примеров</div>";

  const hint = !isGroup
    ? `<div class='small' style='margin-top:6px'>⬇ Двойной клик, чтобы раскрыть группы</div>` : "";

  panel.innerHTML = `
    <h2>${{esc(title)}}</h2>
    <div class="card"><div><b>Оборот:</b> ${{esc(weight)}}</div>${{hint}}</div>
    <div class="card"><h3>Куда идут деньги</h3>${{outH}}</div>
    <div class="card"><h3>Откуда приходят деньги</h3>${{inH}}</div>
    <div class="card"><h3>Примеры контрактов</h3>${{cH}}</div>`;
}}
</script>
"""
    content = content.replace("</head>", style_and_data + "\n</head>")

    click_script = """
<script>
setTimeout(function(){
  if(typeof network === "undefined") return;
  network.fit({animation:{duration:600,easingFunction:"easeInOutQuad"}});
  network.on("click", function(p){ if(p.nodes.length > 0) renderPanel(p.nodes[0]); });
  network.on("doubleClick", function(p){
    if(p.nodes.length > 0 && currentMode === "sections") switchToGroups(p.nodes[0]);
  });
}, 400);

function switchToSections(){ location.reload(); }

function switchToGroups(section){
  currentMode = "groups";
  currentSection = section;
  document.getElementById("mode-label").innerHTML =
    "Режим: <b>Группы ОКВЭД — " + esc(sectionLabels[section]||section) + "</b>";
  document.getElementById("back-btn").style.display = "inline-block";
  document.getElementById("hint-text").style.display = "none";

  const flows = groupFlowsData.filter(r => r.source_section === section || r.target_section === section);
  if(!flows.length){
    document.getElementById("sidepanel").innerHTML =
      "<h2>Нет данных</h2><div class='card'>В разделе " + esc(section) + " нет потоков.</div>";
    return;
  }

  const nodes = {}, edges = {};
  flows.forEach(r => {
    if(!nodes[r.source_group]) nodes[r.source_group] = {id:r.source_group,
      label:r.source_group+"\\n"+(r.source_group_name||""), section:r.source_section};
    if(!nodes[r.target_group]) nodes[r.target_group] = {id:r.target_group,
      label:r.target_group+"\\n"+(r.target_group_name||""), section:r.target_section};
    const key = r.source_group+"→"+r.target_group;
    if(!edges[key]) edges[key]={from:r.source_group,to:r.target_group,weight:0,src_sec:r.source_section};
    edges[key].weight += r.money_flow;
  });

  const nodeWeights = {};
  Object.values(edges).forEach(e => {
    nodeWeights[e.from] = (nodeWeights[e.from]||0) + e.weight;
    nodeWeights[e.to]   = (nodeWeights[e.to]||0)   + e.weight;
  });

  const maxW = Math.max(...Object.values(edges).map(e => e.weight));
  const allNodes = Object.values(nodes);
  const n = allNodes.length;
  const radius = Math.max(350, n * 40);

  const container = document.getElementById("mynetwork");
  const visNodes = new vis.DataSet(allNodes.map((nd, i) => {
    const angle = 2 * Math.PI * i / n;
    const col = sectionColors[nd.section] || "#aaa";
    const w = nodeWeights[nd.id] || 1;
    return { id:nd.id, label:nd.label, title:nd.id+" | Оборот: "+fmtM(w),
             x:radius*Math.cos(angle), y:radius*Math.sin(angle),
             color:col, size:Math.max(16,Math.min(50,8+Math.pow(w,0.12))),
             physics:false, borderWidth:2, font:{size:12,multi:true} };
  }));

  const visEdges = new vis.DataSet(Object.values(edges).map(e => ({
    from:e.from, to:e.to, value:e.weight,
    width: 1 + 8*(e.weight/maxW),
    color: hexToRgba(sectionColors[e.src_sec]||"#aaa", 0.4),
    title: e.from+" → "+e.to+" | "+fmtM(e.weight),
    arrows:"to", smooth:{type:"curvedCW",roundness:0.14},
  })));

  network = new vis.Network(container,
    {nodes:visNodes, edges:visEdges},
    {nodes:{shape:"dot",font:{size:13}}, edges:{smooth:{type:"curvedCW",roundness:0.14}},
     physics:false, interaction:{hover:true}});
  network.fit({animation:{duration:600,easingFunction:"easeInOutQuad"}});
  network.on("click", function(p){ if(p.nodes.length>0) renderPanel(p.nodes[0]); });
}

function fmtM(x){ return parseFloat(x).toLocaleString("ru-RU",{maximumFractionDigits:0})+" ₽"; }
function hexToRgba(hex,alpha){
  hex=hex.replace("#","");
  return "rgba("+parseInt(hex.slice(0,2),16)+","+parseInt(hex.slice(2,4),16)+","+parseInt(hex.slice(4,6),16)+","+alpha+")";
}
</script>
"""
    content = content.replace("</body>", click_script + "\n</body>")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(content)


def main():
    section_flows = pd.read_csv("sector_flows.csv")
    group_flows   = pd.read_csv("sector_flows_groups.csv")
    contracts     = pd.read_csv("contracts_with_sectors.csv")

    section_flows = section_flows[section_flows["money_flow"] > 0]
    group_flows   = group_flows[group_flows["money_flow"] > 0]

    G = build_section_graph(section_flows)

    node_weights = {}
    for node in G.nodes():
        node_weights[node] = (
            sum(d["weight"] for _, _, d in G.in_edges(node, data=True)) +
            sum(d["weight"] for _, _, d in G.out_edges(node, data=True))
        )

    net = Network(height="100vh", width="100%", directed=True, bgcolor="#ffffff", font_color="#222222")
    net.toggle_physics(False)

    nodes = list(G.nodes())
    n = len(nodes)
    radius = 520

    for i, node in enumerate(nodes):
        angle = 2 * math.pi * i / n
        x, y = radius * math.cos(angle), radius * math.sin(angle)
        color = SECTION_COLORS.get(node, "#aaa")
        size  = max(20, min(62, 10 + node_weights.get(node, 1) ** 0.12))
        label = SECTION_LABELS.get(node, node)
        net.add_node(node, label=label,
                     title=f"{label} | Оборот: {fmt_money(node_weights.get(node, 0))}",
                     x=x, y=y, physics=False, color=color, size=size,
                     borderWidth=2, font={"size": 13})

    max_w = max(d["weight"] for _, _, d in G.edges(data=True))
    for src, tgt, data in G.edges(data=True):
        w = data["weight"]
        col = SECTION_COLORS.get(src, "#aaa")
        net.add_edge(src, tgt, value=w, width=1 + 8 * (w / max_w),
                     color=hex_to_rgba(col, 0.40),
                     title=f"{src} → {tgt} | {fmt_money(w)}",
                     arrows="to", smooth={"type": "curvedCW", "roundness": 0.14})

    output_path = "sector_graph.html"
    net.write_html(output_path, notebook=False)

    details = build_details(section_flows, group_flows, contracts)

    group_weights = {}
    for grp in set(group_flows["source_group"]).union(group_flows["target_group"]):
        out_w = group_flows[group_flows["source_group"] == grp]["money_flow"].sum()
        in_w  = group_flows[group_flows["target_group"] == grp]["money_flow"].sum()
        group_weights[grp] = out_w + in_w

    gf_json = group_flows.to_dict(orient="records")

    inject_sidebar_and_logic(
        output_path, details, node_weights, group_weights,
        SECTION_LABELS, SECTION_COLORS, gf_json,
    )
    print(f"Сохранено: {output_path}")


if __name__ == "__main__":
    main()
