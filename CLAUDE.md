# zhuzong · 项目入口

> Franklin 自己的商务工具仓库。第一个工具是**报价工具**：给客户出报价单。
> 建于 2026-09-06。本目录是 git 仓库，收工时提交一次。
> ⛔ 这里放的是 Franklin 对客户的**服务报价**（内容代运营、AI 应用开发等），不是客户商品的售价。

## 目录

| 目录 | 是什么 |
|---|---|
| `报价工具/价格表.json` | ⭐报价数字的唯一正本。改价只改这里 |
| `报价工具/报价单/<客户>-<版本>.json` | 每份报价单一个配置：勾选项目、数量、按客户覆盖单价/说明 |
| `报价工具/报价单/<客户>-<版本>.md / .html` | 由 quote.py 生成，⛔别手改，改配置重新 build |
| `报价工具/报价单/台账.md` | `quote.py ledger --write` 生成的报价一览 |
| `报价工具/quote.py` | 生成脚本，只用 Python 标准库 |

## 怎么用

```bash
cd 报价工具
python3 quote.py list                 # 看价格表
python3 quote.py new 客户名            # 新建 报价单/客户名-v1.json，删掉不要的项目、填联系人
python3 quote.py build 报价单/客户名-v1.json   # 生成 .md + .html（浏览器打开 .html 可直接打印成 PDF）
python3 quote.py build --all          # 重建全部
python3 quote.py ledger --write       # 更新台账
```

## 规矩

1. ⛔ **报价单发给客户前，Franklin 亲口说「发」**。agent 只出稿，不发。
2. 数字只从 `价格表.json` 来。要给某个客户特价，在该客户的配置里覆盖「单价」，⛔别改价格表。
3. 一份报价改了内容就出新版本（v1 → v2），⛔别覆盖旧版本文件，旧版留作记录。
4. 「状态」字段手动维护：草稿 → 已发出 → 已收款 / 已作废。
5. 松石公主的报价 v2 是种子数据，数字与 `songshi-princess/产品与代码/服务协议-松石公主.md` 附件 A 一致；条款改动两边要同步。

## 收工

- 有报价单变动就跑一次 `python3 quote.py build --all && python3 quote.py ledger --write`
- `git add -A && git commit` 一次
