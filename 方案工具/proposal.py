#!/usr/bin/env python3
"""方案工具 · 客户方案配置（JSON）→ 合作方案 / 报价单（Markdown + 可打印 HTML）

用法（任意位置运行）：
  python3 proposal.py list                                  所有客户的方案一览
  python3 proposal.py new 客户名 [--项目 名] [--模板 两选项|清单] [--version v1]
                                                            建 客户/<客户名>/{01-需求,02-交流纪要,03-方案}，放入方案配置骨架
  python3 proposal.py build 客户/xx/03-方案/xx-v1.json       生成同名 .md 和 .html
  python3 proposal.py build --all                           重建全部
  python3 proposal.py ledger [--write]                      台账；--write 写到仓库根目录 台账.md

只用标准库。一份方案 = 一个 JSON：多个「选项」并排对照（幻游纪式），或一个选项的清单（松石式）。
费用行：{"名称","说明"?,"单价": 数字|null|[低,高],"单位": "月"|"次"|"条"|…,"期数"?: 月数,"数量"?: 个数}
  · 有「期数」= 固定期限（开发期 3 个月）；单位「月」无期数 = 按月持续；其他单位 = 一次性/按量
  · 单价 null = 待定（不计入合计，方案里标出来）；单价 0 = 含在其他项内
附件：[{"标题","说明"?,"条目":[...]}]，放交付范围、时间规划这类清单，排在正文最后。
"""

from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
CLIENTS = ROOT / "客户"
TEMPLATES = HERE / "模板"
ANCHORS = HERE / "定价锚与条款库.json"

DEFAULT_SELLER = {"名称": "杜炫明 Franklin Du"}


# ---------- 基础 ----------

def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        sys.exit(f"找不到文件：{path}")
    except json.JSONDecodeError as e:
        sys.exit(f"JSON 格式错误：{path}\n  {e}")


def _num(x) -> str:
    if isinstance(x, float) and not x.is_integer():
        return f"{x:,.2f}"
    return f"{int(x):,}"


def money(v, cur="¥") -> str:
    if v is None:
        return "待定"
    if isinstance(v, (list, tuple)) and len(v) == 2:
        return f"{cur}{_num(v[0])}–{_num(v[1])}"
    if isinstance(v, (int, float)):
        return f"{cur}{_num(v)}"
    return str(v)


def seller() -> dict:
    if ANCHORS.exists():
        return load_json(ANCHORS).get("报价方", DEFAULT_SELLER)
    return DEFAULT_SELLER


# ---------- 计算 ----------

def calc_option(opt: dict, cur: str) -> dict:
    """算一个选项的费用行、合计。"""
    rows, fixed_total, monthly_total, pending = [], 0, 0, []
    for r in opt.get("费用", []):
        price, unit = r.get("单价"), r.get("单位", "月")
        qty, periods = r.get("数量", 1), r.get("期数")
        priced = isinstance(price, (int, float))
        if price is None and qty:
            pending.append(r["名称"])
        if price == 0:
            text, subtotal = "含在其他项内", 0
        elif not priced:
            text = money(price, cur) + (f"/{unit}" if unit else "") + (f" × {periods} 个{unit}" if periods else "")
            subtotal = None
        elif qty == 0:
            text, subtotal = f"{money(price, cur)}/{unit}（按需，另计）", 0
        elif periods:
            subtotal = price * qty * periods
            text = f"{money(price, cur)}/{unit} × {periods} 个{unit}" + (f" × {qty}" if qty > 1 else "") + f" = {money(subtotal, cur)}"
            fixed_total += subtotal
        elif unit == "月":
            subtotal = price * qty
            text = f"{money(price, cur)}/月" + (f" × {qty} = {money(subtotal, cur)}/月" if qty > 1 else "")
            monthly_total += subtotal
        else:
            subtotal = price * qty
            text = f"{money(price, cur)}/{unit}" + (f" × {qty} = {money(subtotal, cur)}" if qty > 1 else "")
            if unit in ("次", "项", "个", "套"):
                fixed_total += subtotal
        rows.append({**r, "数量": qty, "小计": subtotal, "文本": text})
    return {
        "名称": opt.get("名称", "方案"),
        "维度": opt.get("维度", {}),
        "行": rows,
        "固定合计": fixed_total,
        "月度合计": monthly_total,
        "待定": pending,
        "付款": opt.get("付款", ""),
    }


def fee_lines(o: dict, cur: str) -> list[str]:
    """费用维度的多行文本（对照表用）。"""
    L = [f"{r['名称']}：{r['文本']}" for r in o["行"]]
    if o["固定合计"]:
        L.append(f"合计 {money(o['固定合计'], cur)}")
    if o["月度合计"]:
        L.append(f"另按月 {money(o['月度合计'], cur)}/月")
    if o["付款"]:
        L.append("付款：" + o["付款"])
    return L


def resolve(spec: dict, path: Path) -> dict:
    cur = spec.get("币种", "¥")
    opts = [calc_option(o, cur) for o in spec.get("选项", [])]
    if not opts:
        sys.exit(f"{path.name} 没有「选项」")
    dims = spec.get("维度顺序")
    if not dims:
        dims = []
        for o in opts:
            for k in o["维度"]:
                if k not in dims:
                    dims.append(k)
        if "费用" not in dims:
            dims.append("费用")
    date = dt.date.fromisoformat(spec["日期"]) if spec.get("日期") else dt.date.today()
    return {
        "路径": path,
        "客户": spec.get("客户", path.parent.parent.name),
        "项目": spec.get("项目", ""),
        "联系人": spec.get("联系人", ""),
        "版本": spec.get("版本", "v1"),
        "日期": date,
        "状态": spec.get("状态", "草稿"),
        "标题": spec.get("标题") or f"{spec.get('项目') or spec.get('客户', '')} 合作方案",
        "导语": spec.get("导语", ""),
        "报价方": spec.get("报价方") or seller(),
        "币种": cur,
        "选项": opts,
        "维度顺序": dims,
        "共同前提": spec.get("共同前提", []),
        "怎么选": spec.get("怎么选", []),
        "费用相关说明": spec.get("费用相关说明", []),
        "附言": spec.get("附言", ""),
        "附件": spec.get("附件", []),
    }


# ---------- Markdown ----------

def md_cell(s: str) -> str:
    return s.replace("|", "｜").replace("\n", "<br>")


def render_md(q: dict) -> str:
    cur = q["币种"]
    L = [f"# {q['标题']}", ""]
    meta = f"{q['日期'].strftime('%Y 年 %m 月')} · {q['版本']}"
    if q["导语"]:
        meta += f" · {q['导语']}"
    L += [meta, ""]

    if len(q["选项"]) > 1:
        L.append("| | " + " | ".join(o["名称"] for o in q["选项"]) + " |")
        L.append("|---|" + "---|" * len(q["选项"]))
        for d in q["维度顺序"]:
            cells = []
            for o in q["选项"]:
                v = "<br>".join(fee_lines(o, cur)) if d == "费用" else md_cell(str(o["维度"].get(d, "—")))
                cells.append(v)
            L.append(f"| **{d}** | " + " | ".join(cells) + " |")
        L.append("")
    else:
        o = q["选项"][0]
        if o["维度"]:
            L += ["| | |", "|---|---|"]
            L += [f"| **{k}** | {md_cell(str(v))} |" for k, v in o["维度"].items()]
            L.append("")
        L += [f"## {o['名称']}", "", "| # | 项目 | 说明 | 费用 |", "|---|---|---|---|"]
        for i, r in enumerate(o["行"], 1):
            L.append(f"| {i} | {r['名称']} | {md_cell(r.get('说明', ''))} | {r['文本']} |")
        L.append("")
        L += ["| 合计 | |", "|---|---|"]
        if o["固定合计"]:
            L.append(f"| **一次性 / 固定期合计** | **{money(o['固定合计'], cur)}** |")
        if o["月度合计"]:
            L.append(f"| **月度合计** | **{money(o['月度合计'], cur)}/月** |")
        if o["待定"]:
            L.append(f"| 待定（未计入） | {'、'.join(o['待定'])} |")
        if o["付款"]:
            L.append(f"| 付款 | {o['付款']} |")
        L.append("")

    for title, key, numbered in (("共同前提", "共同前提", False), ("怎么选", "怎么选", False), ("费用相关说明", "费用相关说明", True)):
        items = q[key]
        if items:
            L += [f"## {title}", ""]
            L += [(f"{i}. {t}" if numbered else f"- {t}") for i, t in enumerate(items, 1)]
            L.append("")
    if q["附言"]:
        L += ["## 附言", "", q["附言"], ""]
    for att in q["附件"]:
        L += [f"## {att['标题']}", ""]
        if att.get("说明"):
            L += [att["说明"], ""]
        L += [f"- {t}" for t in att.get("条目", [])]
        L.append("")
    L += ["---", "", f"{q['报价方'].get('名称', '')} · {q['日期'].isoformat()}", ""]
    return "\n".join(L)


# ---------- HTML ----------

CSS = """
body{font-family:-apple-system,"PingFang SC","Hiragino Sans GB","Microsoft YaHei","Noto Sans CJK SC",sans-serif;
     color:#1a1a1a;background:#fff;max-width:900px;margin:32px auto;padding:0 24px;line-height:1.65}
h1{font-size:24px;margin:0 0 4px}
h2{font-size:17px;margin:28px 0 8px}
.sub{color:#666;margin-bottom:20px;font-size:14px}
table{border-collapse:collapse;width:100%;margin:8px 0 16px;font-size:14px}
th,td{border:1px solid #ddd;padding:9px 11px;vertical-align:top;text-align:left}
th{background:#f4f4f4;font-weight:600}
.cmp td:first-child{width:96px;font-weight:600;background:#fafafa;white-space:nowrap}
.cmp th{font-size:15px}
.fee div{margin:1px 0}
.fee .tot{font-weight:700;margin-top:4px}
.fee .pend{color:#a05a00}
td.num{text-align:right;white-space:nowrap}
.total td{font-weight:700;background:#fffbe6}
.note{color:#444;font-size:13px}
ul,ol{padding-left:22px;font-size:14px;color:#333}
li{margin:4px 0}
.foot{margin-top:36px;color:#666;font-size:13px;border-top:1px solid #ddd;padding-top:8px}
@media print{body{margin:0;max-width:none}h2{page-break-after:avoid}}
"""


def fee_html(o: dict, cur: str) -> str:
    e = html.escape
    parts = [f"<div>{e(r['名称'])}：{e(r['文本'])}</div>" for r in o["行"]]
    if o["固定合计"]:
        parts.append(f"<div class='tot'>合计 {money(o['固定合计'], cur)}</div>")
    if o["月度合计"]:
        parts.append(f"<div class='tot'>另按月 {money(o['月度合计'], cur)}/月</div>")
    if o["付款"]:
        parts.append(f"<div>付款：{e(o['付款'])}</div>")
    return "<div class='fee'>" + "".join(parts) + "</div>"


def render_html(q: dict) -> str:
    e = html.escape
    cur = q["币种"]
    H = ["<!doctype html><html lang='zh-CN'><head><meta charset='utf-8'>",
         f"<title>{e(q['标题'])} {e(q['版本'])}</title><style>{CSS}</style></head><body>",
         f"<h1>{e(q['标题'])}</h1>"]
    sub = f"{q['日期'].strftime('%Y 年 %m 月')} · {e(q['版本'])}" + (f" · {e(q['导语'])}" if q["导语"] else "")
    H.append(f"<div class='sub'>{sub}</div>")

    if len(q["选项"]) > 1:
        H.append("<table class='cmp'><tr><th></th>" + "".join(f"<th>{e(o['名称'])}</th>" for o in q["选项"]) + "</tr>")
        for d in q["维度顺序"]:
            cells = []
            for o in q["选项"]:
                cells.append(fee_html(o, cur) if d == "费用" else e(str(o["维度"].get(d, "—"))).replace("\n", "<br>"))
            H.append(f"<tr><td>{e(d)}</td>" + "".join(f"<td>{c}</td>" for c in cells) + "</tr>")
        H.append("</table>")
    else:
        o = q["选项"][0]
        if o["维度"]:
            H.append("<table class='cmp'>" + "".join(
                f"<tr><td>{e(k)}</td><td>{e(str(v)).replace(chr(10), '<br>')}</td></tr>" for k, v in o["维度"].items()) + "</table>")
        H.append(f"<h2>{e(o['名称'])}</h2><table><tr><th>#</th><th>项目</th><th>说明</th><th class='num'>费用</th></tr>")
        for i, r in enumerate(o["行"], 1):
            H.append(f"<tr><td>{i}</td><td>{e(r['名称'])}</td><td class='note'>{e(r.get('说明', ''))}</td><td class='num'>{e(r['文本'])}</td></tr>")
        H.append("</table><table>")
        if o["固定合计"]:
            H.append(f"<tr class='total'><td>一次性 / 固定期合计</td><td class='num'>{money(o['固定合计'], cur)}</td></tr>")
        if o["月度合计"]:
            H.append(f"<tr class='total'><td>月度合计</td><td class='num'>{money(o['月度合计'], cur)}/月</td></tr>")
        if o["待定"]:
            H.append(f"<tr><td>待定（未计入）</td><td>{e('、'.join(o['待定']))}</td></tr>")
        if o["付款"]:
            H.append(f"<tr><td>付款</td><td>{e(o['付款'])}</td></tr>")
        H.append("</table>")

    for title, key, tag in (("共同前提", "共同前提", "ul"), ("怎么选", "怎么选", "ul"), ("费用相关说明", "费用相关说明", "ol")):
        if q[key]:
            H.append(f"<h2>{title}</h2><{tag}>" + "".join(f"<li>{e(t)}</li>" for t in q[key]) + f"</{tag}>")
    if q["附言"]:
        H.append(f"<h2>附言</h2><p class='note'>{e(q['附言'])}</p>")
    for att in q["附件"]:
        H.append(f"<h2>{e(att['标题'])}</h2>")
        if att.get("说明"):
            H.append(f"<p class='note'>{e(att['说明'])}</p>")
        H.append("<ul>" + "".join(f"<li>{e(t)}</li>" for t in att.get("条目", [])) + "</ul>")
    H.append(f"<div class='foot'>{e(q['报价方'].get('名称', ''))} · {q['日期'].isoformat()}</div></body></html>")
    return "\n".join(H)


# ---------- 命令 ----------

def all_specs() -> list[Path]:
    return sorted(CLIENTS.glob("*/03-方案/*.json"))


def rel(p: Path) -> str:
    try:
        return str(p.resolve().relative_to(ROOT))
    except ValueError:
        return str(p)


def summary(q: dict) -> str:
    parts = []
    for o in q["选项"]:
        s = o["名称"]
        bits = []
        if o["固定合计"]:
            bits.append(money(o["固定合计"], q["币种"]))
        if o["月度合计"]:
            bits.append(money(o["月度合计"], q["币种"]) + "/月")
        if o["待定"]:
            bits.append("待定:" + "、".join(o["待定"]))
        parts.append(s + "＝" + (" + ".join(bits) if bits else "—"))
    return "；".join(parts)


def cmd_list(_a) -> None:
    for p in all_specs():
        q = resolve(load_json(p), p)
        print(f"{q['日期']}  {q['客户']:<10}{q['版本']:<5}{q['状态']:<24}{summary(q)}")
    if not all_specs():
        print("还没有方案。python3 proposal.py new 客户名")


def cmd_new(a) -> None:
    tpl = TEMPLATES / f"{a.模板}.json"
    if not tpl.exists():
        sys.exit(f"没有模板 {tpl}；可选：{', '.join(p.stem for p in TEMPLATES.glob('*.json'))}")
    base = CLIENTS / a.客户名
    for sub in ("01-需求", "02-交流纪要", "03-方案"):
        (base / sub).mkdir(parents=True, exist_ok=True)
    out = base / "03-方案" / f"{a.客户名}-合作方案-{a.version}.json"
    if out.exists():
        sys.exit(f"已存在：{out}（出新版换 --version）")
    spec = load_json(tpl)
    spec.update({"客户": a.客户名, "项目": a.项目 or a.客户名, "版本": a.version, "日期": dt.date.today().isoformat(), "状态": "草稿"})
    out.write_text(json.dumps(spec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    memo = TEMPLATES / "交流纪要.md"
    if memo.exists():
        shutil.copy(memo, base / "02-交流纪要" / "模板-交流纪要.md")
    print(f"已建 {rel(base)}/，方案骨架 {rel(out)}。把需求文档放进 01-需求，聊完填 02-交流纪要，改好方案后 build")


def build_one(p: Path) -> dict:
    q = resolve(load_json(p), p)
    p.with_suffix(".md").write_text(render_md(q), encoding="utf-8")
    p.with_suffix(".html").write_text(render_html(q), encoding="utf-8")
    print(f"✓ {rel(p)}  →  {summary(q)}")
    return q


def cmd_build(a) -> None:
    paths = all_specs() if a.all else ([Path(a.spec).resolve()] if a.spec else None)
    if not paths:
        sys.exit("给配置路径，或 --all")
    for p in paths:
        build_one(p)


def cmd_ledger(a) -> None:
    rows = []
    for p in all_specs():
        q = resolve(load_json(p), p)
        rows.append((q["日期"].isoformat(), q["客户"], q["项目"], q["版本"], q["状态"], summary(q), rel(p)))
    rows.sort(reverse=True)
    lines = ["| 日期 | 客户 | 项目 | 版本 | 状态 | 金额 | 配置 |", "|---|---|---|---|---|---|---|"]
    lines += ["| " + " | ".join(r) + " |" for r in rows]
    text = "\n".join(lines)
    print(text)
    if a.write:
        out = ROOT / "台账.md"
        out.write_text("# 方案台账（`python3 方案工具/proposal.py ledger --write` 生成，⛔别手改）\n\n" + text + "\n", encoding="utf-8")
        print(f"\n已写入 {rel(out)}")


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list")
    p_new = sub.add_parser("new")
    p_new.add_argument("客户名")
    p_new.add_argument("--项目", default="")
    p_new.add_argument("--模板", default="两选项")
    p_new.add_argument("--version", default="v1")
    p_build = sub.add_parser("build")
    p_build.add_argument("spec", nargs="?")
    p_build.add_argument("--all", action="store_true")
    p_ledger = sub.add_parser("ledger")
    p_ledger.add_argument("--write", action="store_true")
    a = ap.parse_args(argv)
    {"list": cmd_list, "new": cmd_new, "build": cmd_build, "ledger": cmd_ledger}[a.cmd](a)


if __name__ == "__main__":
    main()
