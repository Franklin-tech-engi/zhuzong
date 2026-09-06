#!/usr/bin/env python3
"""报价工具 · 价格表 + 报价单配置 → 报价单（Markdown / HTML）

用法（在本目录或任意位置运行）：
  python3 quote.py list                       看价格表
  python3 quote.py new 客户名 [--version v1]   新建报价单配置 → 报价单/客户名-v1.json（含全部项目，删掉不要的）
  python3 quote.py build 报价单/xxx.json       生成同名 .md 和 .html
  python3 quote.py build --all                重建 报价单/ 下所有配置
  python3 quote.py ledger [--write]           所有报价单一览；--write 写入 报价单/台账.md

只用标准库。价格数字的唯一正本是 价格表.json；报价单配置只做勾选和按客户覆盖。
"""

from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CATALOG_PATH = HERE / "价格表.json"
QUOTES_DIR = HERE / "报价单"

BILLING_LABEL = {
    "monthly": "按月",
    "one_time": "一次性",
    "per_unit": "按量",
    "reimburse": "实报实销",
    "quote": "另议",
}


# ---------- 基础 ----------

def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        sys.exit(f"找不到文件：{path}")
    except json.JSONDecodeError as e:
        sys.exit(f"JSON 格式错误：{path}\n  {e}")


def fmt_money(v, cur: str = "¥") -> str:
    """None → 待定；[a, b] → ¥a–b；数字 → ¥1,234。"""
    if v is None:
        return "待定"
    if isinstance(v, (list, tuple)) and len(v) == 2:
        return f"{cur}{_num(v[0])}–{_num(v[1])}"
    if isinstance(v, (int, float)):
        return f"{cur}{_num(v)}"
    return str(v)


def _num(x) -> str:
    if isinstance(x, float) and not x.is_integer():
        return f"{x:,.2f}"
    return f"{int(x):,}"


def parse_date(s: str | None) -> dt.date:
    if not s:
        return dt.date.today()
    return dt.date.fromisoformat(s)


# ---------- 计算 ----------

def resolve(catalog: dict, spec: dict) -> dict:
    """把报价单配置和价格表合并，算出每行小计和合计。"""
    by_id = {it["id"]: it for it in catalog["项目"]}
    cur = catalog.get("币种", "¥")
    rows = []
    for sel in spec.get("项目", []):
        base = by_id.get(sel.get("id"))
        if base is None and "名称" not in sel:
            sys.exit(f"价格表里没有 id={sel.get('id')!r}，又没给「名称」——先去 价格表.json 登记")
        item = dict(base or {})
        item.update({k: v for k, v in sel.items() if k != "id"})
        item["id"] = sel.get("id", item.get("名称"))

        qty = item.get("数量", 1)
        price = item.get("单价")
        billing = item.get("计费", "monthly")
        fixed = isinstance(price, (int, float)) and billing in ("monthly", "one_time", "per_unit")
        subtotal = price * qty if fixed else None
        rows.append({
            "id": item["id"],
            "名称": item.get("名称", item["id"]),
            "说明": item.get("说明", ""),
            "备注": item.get("备注", ""),
            "单价": price,
            "单价文本": _price_text(price, item.get("单位"), cur),
            "数量": qty,
            "计费": billing,
            "计费文本": BILLING_LABEL.get(billing, billing),
            "小计": subtotal,
            "小计文本": _subtotal_text(price, qty, billing, subtotal, cur),
        })

    monthly = sum(r["小计"] for r in rows if r["计费"] == "monthly" and r["小计"] is not None)
    one_time = sum(r["小计"] for r in rows if r["计费"] == "one_time" and r["小计"] is not None)
    for d in spec.get("优惠", []):
        amt = d.get("金额", 0) or 0
        if d.get("作用于", "monthly") == "one_time":
            one_time -= amt
        else:
            monthly -= amt
    pending = [r["名称"] for r in rows if r["数量"] and r["计费"] in ("monthly", "one_time") and r["单价"] is None]

    date = parse_date(spec.get("日期"))
    days = spec.get("有效期天数")
    valid_until = date + dt.timedelta(days=days) if days else None

    return {
        "客户": spec.get("客户", ""),
        "联系人": spec.get("联系人", ""),
        "版本": spec.get("版本", "v1"),
        "日期": date,
        "有效期天数": days,
        "有效期至": valid_until,
        "状态": spec.get("状态", "草稿"),
        "报价方": catalog.get("报价方", {}),
        "币种": cur,
        "行": rows,
        "优惠": spec.get("优惠", []),
        "月度合计": monthly,
        "一次性合计": one_time,
        "待定项": pending,
        "实报实销": catalog.get("实报实销", []),
        "通用条款": catalog.get("通用条款", []),
        "附言": spec.get("附言", ""),
    }


def _price_text(price, unit, cur) -> str:
    if price == 0:
        return "含在其他项内"
    return fmt_money(price, cur) + (f"/{unit}" if unit and price is not None else "")


def _subtotal_text(price, qty, billing, subtotal, cur) -> str:
    if billing == "quote":
        return "另议"
    if billing == "reimburse":
        return "实报实销"
    if price is None:
        return "待定"
    if qty == 0:
        return "—"
    if subtotal == 0:
        return "含在其他项内"
    label = {"monthly": "/月", "one_time": "", "per_unit": "（按量结算）"}.get(billing, "")
    return fmt_money(subtotal, cur) + label


# ---------- 输出：Markdown ----------

def render_md(q: dict) -> str:
    cur = q["币种"]
    L = [f"# 报价单 · {q['客户']}", ""]
    L += ["| | |", "|---|---|",
          f"| 客户 | {q['客户']} |",
          f"| 联系人 | {q['联系人'] or '—'} |",
          f"| 报价方 | {q['报价方'].get('名称', '')} |",
          f"| 版本 | {q['版本']} |",
          f"| 日期 | {q['日期'].isoformat()} |"]
    if q["有效期至"]:
        L.append(f"| 有效期 | {q['有效期天数']} 天（至 {q['有效期至'].isoformat()}） |")
    L += [f"| 状态 | {q['状态']} |", ""]

    L += ["## 报价明细", "",
          "| # | 项目 | 说明 | 单价 | 数量 | 计费 | 小计 |",
          "|---|---|---|---|---|---|---|"]
    for i, r in enumerate(q["行"], 1):
        desc = r["说明"]
        if r["备注"]:
            desc = (desc + "<br>" if desc else "") + f"**{r['备注']}**"
        L.append(f"| {i} | {r['名称']} | {desc} | {r['单价文本']} | {r['数量']} | {r['计费文本']} | {r['小计文本']} |")
    L.append("")

    L += ["## 费用合计", "", "| 项 | 金额 |", "|---|---|"]
    for d in q["优惠"]:
        L.append(f"| 优惠 · {d.get('名称', '')} | −{fmt_money(d.get('金额', 0), cur)} |")
    L.append(f"| **月度合计** | **{fmt_money(q['月度合计'], cur)}/月** |")
    L.append(f"| **一次性合计** | **{fmt_money(q['一次性合计'], cur)}** |")
    for x in q["实报实销"]:
        L.append(f"| {x['名称']} | 实报实销，随月结算 |")
    if q["待定项"]:
        L.append(f"| 待定项（未计入合计） | {'、'.join(q['待定项'])} |")
    L.append("")

    if q["实报实销"]:
        L += ["## 实报实销项", ""]
        L += [f"- **{x['名称']}**：{x['说明']}" for x in q["实报实销"]]
        L.append("")
    if q["通用条款"]:
        L += ["## 通用条款", ""]
        L += [f"{i}. {t}" for i, t in enumerate(q["通用条款"], 1)]
        L.append("")
    if q["附言"]:
        L += ["## 附言", "", q["附言"], ""]

    L += ["---", "",
          f"**客户确认（{q['联系人'] or q['客户']}）：** ____________________　日期：__________", "",
          f"**报价方（{q['报价方'].get('名称', '')}）：** ____________________　日期：__________", ""]
    return "\n".join(L)


# ---------- 输出：HTML ----------

CSS = """
body{font-family:-apple-system,"PingFang SC","Hiragino Sans GB","Microsoft YaHei","Noto Sans CJK SC",sans-serif;
     color:#1a1a1a;background:#fff;max-width:880px;margin:32px auto;padding:0 24px;line-height:1.6}
h1{font-size:26px;margin:0 0 4px}
.sub{color:#666;margin-bottom:24px}
table{border-collapse:collapse;width:100%;margin:8px 0 24px;font-size:14px}
th,td{border:1px solid #ddd;padding:8px 10px;vertical-align:top;text-align:left}
th{background:#f4f4f4;font-weight:600}
td.num,th.num{text-align:right;white-space:nowrap}
td.nw,th.nw{white-space:nowrap}
.meta td:first-child{width:90px;color:#666;background:#fafafa}
.note{color:#444;font-size:13px}
.remark{display:block;font-weight:600;color:#7a4b00;margin-top:2px}
.total td{font-weight:700;background:#fffbe6}
.terms{font-size:13px;color:#444}
.sig{display:flex;gap:40px;margin-top:40px;font-size:14px}
.sig div{flex:1;border-top:1px solid #999;padding-top:6px}
@media print{body{margin:0;max-width:none}}
"""


def render_html(q: dict) -> str:
    e = html.escape
    cur = q["币种"]
    H = [f"<!doctype html><html lang='zh-CN'><head><meta charset='utf-8'>",
         f"<title>报价单 · {e(q['客户'])} {e(q['版本'])}</title><style>{CSS}</style></head><body>",
         f"<h1>报价单 · {e(q['客户'])}</h1>",
         f"<div class='sub'>{e(q['版本'])} · {q['日期'].isoformat()} · {e(q['状态'])}</div>"]

    H.append("<table class='meta'>")
    H.append(f"<tr><td>客户</td><td>{e(q['客户'])}</td></tr>")
    H.append(f"<tr><td>联系人</td><td>{e(q['联系人'] or '—')}</td></tr>")
    H.append(f"<tr><td>报价方</td><td>{e(q['报价方'].get('名称', ''))}</td></tr>")
    if q["有效期至"]:
        H.append(f"<tr><td>有效期</td><td>{q['有效期天数']} 天（至 {q['有效期至'].isoformat()}）</td></tr>")
    H.append("</table>")

    H.append("<h2>报价明细</h2><table><tr><th>#</th><th>项目</th><th>说明</th>"
             "<th class='num'>单价</th><th class='num'>数量</th><th class='nw'>计费</th><th class='num'>小计</th></tr>")
    for i, r in enumerate(q["行"], 1):
        desc = f"<span class='note'>{e(r['说明'])}</span>"
        if r["备注"]:
            desc += f"<span class='remark'>{e(r['备注'])}</span>"
        H.append(f"<tr><td>{i}</td><td>{e(r['名称'])}</td><td>{desc}</td>"
                 f"<td class='num'>{e(r['单价文本'])}</td><td class='num'>{r['数量']}</td>"
                 f"<td class='nw'>{e(r['计费文本'])}</td><td class='num'>{e(r['小计文本'])}</td></tr>")
    H.append("</table>")

    H.append("<h2>费用合计</h2><table>")
    for d in q["优惠"]:
        H.append(f"<tr><td>优惠 · {e(d.get('名称', ''))}</td><td class='num'>−{fmt_money(d.get('金额', 0), cur)}</td></tr>")
    H.append(f"<tr class='total'><td>月度合计</td><td class='num'>{fmt_money(q['月度合计'], cur)}/月</td></tr>")
    H.append(f"<tr class='total'><td>一次性合计</td><td class='num'>{fmt_money(q['一次性合计'], cur)}</td></tr>")
    for x in q["实报实销"]:
        H.append(f"<tr><td>{e(x['名称'])}</td><td class='num'>实报实销，随月结算</td></tr>")
    if q["待定项"]:
        H.append(f"<tr><td>待定项（未计入合计）</td><td>{e('、'.join(q['待定项']))}</td></tr>")
    H.append("</table>")

    if q["实报实销"]:
        H.append("<h2>实报实销项</h2><ul class='terms'>")
        H += [f"<li><b>{e(x['名称'])}</b>：{e(x['说明'])}</li>" for x in q["实报实销"]]
        H.append("</ul>")
    if q["通用条款"]:
        H.append("<h2>通用条款</h2><ol class='terms'>")
        H += [f"<li>{e(t)}</li>" for t in q["通用条款"]]
        H.append("</ol>")
    if q["附言"]:
        H.append(f"<h2>附言</h2><p class='terms'>{e(q['附言'])}</p>")

    H.append("<div class='sig'>"
             f"<div>客户确认（{e(q['联系人'] or q['客户'])}）　日期：</div>"
             f"<div>报价方（{e(q['报价方'].get('名称', ''))}）　日期：</div></div>")
    H.append("</body></html>")
    return "\n".join(H)


# ---------- 命令 ----------

def cmd_list(catalog: dict, _args) -> None:
    cur = catalog.get("币种", "¥")
    print(f"价格表 · {catalog.get('报价方', {}).get('名称', '')}\n")
    print(f"{'id':<22}{'项目':<28}{'单价':<16}{'计费':<8}")
    print("-" * 74)
    for it in catalog["项目"]:
        price = _price_text(it.get("单价"), it.get("单位"), cur)
        print(f"{it['id']:<22}{it['名称']:<28}{price:<16}{BILLING_LABEL.get(it.get('计费', ''), it.get('计费', '')):<8}")
    if catalog.get("实报实销"):
        print("\n实报实销：" + "；".join(x["名称"] for x in catalog["实报实销"]))


def cmd_new(catalog: dict, args) -> None:
    QUOTES_DIR.mkdir(exist_ok=True)
    path = QUOTES_DIR / f"{args.客户名}-{args.version}.json"
    if path.exists():
        sys.exit(f"已存在：{path}（要出新版就换 --version）")
    spec = {
        "_说明": "id 对应 价格表.json 的项目；数量/单价/说明/名称 可在这里按客户覆盖；不要的行直接删。",
        "客户": args.客户名,
        "联系人": "",
        "版本": args.version,
        "日期": dt.date.today().isoformat(),
        "有效期天数": 30,
        "状态": "草稿",
        "项目": [{"id": it["id"], "数量": 1} for it in catalog["项目"]],
        "优惠": [],
        "附言": "",
    }
    path.write_text(json.dumps(spec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"已新建 {path.relative_to(HERE)}，删掉不要的项目、填联系人，然后 build")


def build_one(catalog: dict, spec_path: Path) -> dict:
    q = resolve(catalog, load_json(spec_path))
    md = spec_path.with_suffix(".md")
    hp = spec_path.with_suffix(".html")
    md.write_text(render_md(q), encoding="utf-8")
    hp.write_text(render_html(q), encoding="utf-8")
    print(f"✓ {spec_path.name} → {md.name}, {hp.name}   月度 {fmt_money(q['月度合计'], q['币种'])}  一次性 {fmt_money(q['一次性合计'], q['币种'])}"
          + (f"  待定：{'、'.join(q['待定项'])}" if q["待定项"] else ""))
    return q


def cmd_build(catalog: dict, args) -> None:
    if args.all:
        paths = sorted(QUOTES_DIR.glob("*.json"))
        if not paths:
            sys.exit(f"{QUOTES_DIR} 下没有报价单配置")
    else:
        if not args.spec:
            sys.exit("要么给配置文件路径，要么 --all")
        paths = [Path(args.spec)]
    for p in paths:
        build_one(catalog, p)


def cmd_ledger(catalog: dict, args) -> None:
    rows = []
    for p in sorted(QUOTES_DIR.glob("*.json")):
        q = resolve(catalog, load_json(p))
        rows.append((q["日期"].isoformat(), q["客户"], q["版本"], q["状态"],
                     fmt_money(q["月度合计"], q["币种"]) + "/月", fmt_money(q["一次性合计"], q["币种"]),
                     "、".join(q["待定项"]) or "—", p.name))
    rows.sort(reverse=True)
    lines = ["| 日期 | 客户 | 版本 | 状态 | 月度 | 一次性 | 待定项 | 配置 |",
             "|---|---|---|---|---|---|---|---|"]
    lines += ["| " + " | ".join(r) + " |" for r in rows]
    text = "\n".join(lines)
    print(text)
    if args.write:
        out = QUOTES_DIR / "台账.md"
        out.write_text("# 报价台账（由 quote.py ledger --write 生成，⛔别手改）\n\n" + text + "\n", encoding="utf-8")
        print(f"\n已写入 {out.relative_to(HERE)}")


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list", help="看价格表")
    p_new = sub.add_parser("new", help="新建报价单配置")
    p_new.add_argument("客户名")
    p_new.add_argument("--version", default="v1")
    p_build = sub.add_parser("build", help="生成报价单 .md/.html")
    p_build.add_argument("spec", nargs="?")
    p_build.add_argument("--all", action="store_true")
    p_ledger = sub.add_parser("ledger", help="所有报价单一览")
    p_ledger.add_argument("--write", action="store_true")
    args = ap.parse_args(argv)

    catalog = load_json(CATALOG_PATH)
    {"list": cmd_list, "new": cmd_new, "build": cmd_build, "ledger": cmd_ledger}[args.cmd](catalog, args)


if __name__ == "__main__":
    main()
