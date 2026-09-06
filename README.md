# zhuzong

Franklin 的商务工具仓库。目前有一个工具：

## 报价工具（`报价工具/`）

把「价格表」和「这个客户勾了哪些项」分开管，一条命令生成可发送的报价单。

- `价格表.json`：所有服务项和单价，唯一正本
- `报价单/<客户>-<版本>.json`：每份报价单的配置（勾选项、数量、按客户覆盖）
- `quote.py`：生成 Markdown 和 HTML 报价单，并维护台账

```bash
cd 报价工具
python3 quote.py list                          # 看价格表
python3 quote.py new 某客户                     # 新建配置
python3 quote.py build 报价单/某客户-v1.json     # 生成 .md / .html
python3 quote.py ledger --write                # 报价台账
```

HTML 版在浏览器里打开后「打印 → 存为 PDF」即可发给客户。只依赖 Python 3 标准库。

详细规则见 `CLAUDE.md`。
