# zhuzong

Franklin 的商务线：给客户出合作方案和报价。

- `方案工具/怎么出方案.md`：定价逻辑、方案结构、发出前检查清单（核心）
- `方案工具/proposal.py`：方案 JSON → Markdown + 可打印 HTML
- `客户/<客户>/`：01-需求 / 02-交流纪要 / 03-方案
- `台账.md`：所有方案一览

```bash
python3 方案工具/proposal.py new 某客户 --模板 两选项
python3 方案工具/proposal.py build --all
python3 方案工具/proposal.py ledger --write
```

只依赖 Python 3 标准库。规则见 `CLAUDE.md`。
