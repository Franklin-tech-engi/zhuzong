// 幻游纪 · 简版报价 + 合作协议（草稿）→ .docx + .md
// 用法：NODE_PATH=<装了 docx 的 node_modules> node build_docx.js
// 内容改这里，改完重跑。⛔ 已发出的版本别改，复制一份改版本号。
const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, WidthType, AlignmentType,
  HeadingLevel, LevelFormat, BorderStyle, ShadingType, PageBreak,
} = require("docx");

const OUT = __dirname;
const FONT = "Microsoft YaHei";
const DATE = "2026 年 9 月 7 日";

// ---------- 内容 ----------
// Franklin 2026-09-07：别写太具体。只写清楚：大概交付时间、付款要求、赔偿条款。赔偿不含「质量退款」和「甲方逾期付款违约金」两条（Franklin 去掉）。暂不提「叠加开发」（Franklin 09-07）。
const 费用表 = {
  cols: [2400, 2800, 4160],
  rows: [
    ["项目", "费用", "说明"],
    ["开发月（第 1–2 个月）", "6,000 元/月 × 2 = 12,000 元", "换脸核心功能顺畅稳定；10 月 1 日前交付试用版"],
    ["维护月（第 3–6 个月）", "3,000 元/月 × 4 = 12,000 元", "维护、修正、小迭代"],
    ["6 个月合计", "24,000 元", "不含税"],
  ],
};

const 交付时间 = [
  "10 月 1 日前：交付可试用版本（换脸核心链路：选模板 → 传照片 → 生成 → 下载分享），供贵方内部及小范围试用。",
  "第 2 个月末（约 11 月上旬）：核心功能稳定，可支撑几百名用户使用；文旅页与基础后台上线。",
  "第 3 个月起：进入维护期，负责维护、修正与小迭代。",
  "贵方配合事项（账号、素材、资质、接口配额）延误的，节点相应顺延。",
];

const 付款 = [
  "签约当日支付 12,000 元（前两个开发月）。",
  "第 3 个月起，每月 1 日前支付当月维护费 3,000 元。",
  "费用不含税；阿里云、微信等平台费用及商用后的接口费由贵方承担，上线前内测接口费由我承担（封顶 1,000 元）。",
];

const 赔偿 = [
  "乙方延期：因乙方自身原因，交付节点逾期超过 7 日的，每逾期 1 日按该阶段费用的 1% 向甲方支付违约金，累计不超过该阶段费用的 20%。因甲方配合事项延误、第三方平台故障、政策变化或不可抗力导致的延期不计。",
  "甲方保证责任：因甲方提供的素材、样板视频版权、人脸信息处理、内容合规或经营资质问题引发的第三方索赔、平台处罚、监管处罚或诉讼，由甲方独自承担；乙方因此遭受损失的，甲方应予赔偿。",
  "责任上限：乙方对甲方的全部赔偿责任以乙方实际已收取的费用为限；不承担利润、商誉、数据、流量等间接损失。",
  "免责：阿里云、微信等第三方平台的故障、接口限制、配额不足、规则变化，以及不可抗力，不构成任何一方违约。",
];

const 报价简版 = [
  { t: "h1", text: "幻游纪小程序 · 报价" },
  { t: "meta", text: `${DATE} · 报价方：杜炫明 Franklin Du · 有效期至 2026 年 9 月 14 日` },
  { t: "h2", text: "一、费用" },
  { t: "table", ...费用表 },
  { t: "h2", text: "二、付款" },
  { t: "ul", items: 付款 },
  { t: "h2", text: "三、交付时间（大概）" },
  { t: "ul", items: 交付时间 },
  { t: "h2", text: "四、备选：按需开发" },
  { t: "p", text: "3,500 元/月，3 个月一签一付。只负责功能实现与上线，不对整体稳定性负责，不承诺上线日期。可随时转为上述方案，从转换当月起按上述条件执行。" },
  { t: "meta", text: "代码资产归贵方，从写第一行起代码仓库即在贵方名下。确定后据此签订《合作备忘录》。" },
];

const 协议 = [
  { t: "h1", text: "幻游纪小程序 合作备忘录" },
  { t: "meta", text: "草稿 · 2026 年 9 月" },
  { t: "p", text: "甲方（委托方）：____________________　联系人：__________" },
  { t: "p", text: "乙方（服务方）：杜炫明（Franklin Du）" },
  { t: "p", text: "乙方为甲方开发并维护「幻游纪」AI 换脸文旅电商微信小程序（以下简称「本软件」），合作期 6 个月，自签署日起算。双方就交付时间、付款与违约赔偿约定如下：" },
  { t: "h2", text: "一、交付时间" },
  { t: "ol", items: 交付时间 },
  { t: "h2", text: "二、费用与付款" },
  { t: "table", ...费用表 },
  { t: "ol", items: 付款 },
  { t: "h2", text: "三、违约责任与赔偿" },
  { t: "ol", items: 赔偿 },
  { t: "h2", text: "四、其他" },
  { t: "ol", items: [
    "本软件源代码归甲方所有，自乙方写入第一行代码起代码仓库即在甲方名下；不含甲方业务数据的通用技术组件，乙方保留复用权。",
    "任一方提前 15 日书面通知可终止；已付未服务部分按天折算退还，已完成的开发月费用不退；终止后 5 个工作日内乙方移交代码与账号权限。",
    "双方对彼此的商业信息与用户数据负保密义务。争议协商解决，协商不成提交乙方住所地人民法院。",
    "本备忘录一式两份，电子签署及扫描件与原件同等有效；未尽事宜以双方书面（含微信文字）确认为准。",
  ] },
  { t: "sig" },
];

// ---------- 渲染：Markdown ----------
function toMd(doc) {
  const L = [];
  for (const b of doc) {
    if (b.t === "h1") L.push(`# ${b.text}`, "");
    else if (b.t === "h2") L.push(`## ${b.text}`, "");
    else if (b.t === "meta") L.push(`*${b.text}*`, "");
    else if (b.t === "p") L.push(b.text, "");
    else if (b.t === "ul") L.push(...b.items.map((x) => `- ${x}`), "");
    else if (b.t === "ol") L.push(...b.items.map((x, i) => `${i + 1}. ${x}`), "");
    else if (b.t === "table") {
      L.push("| " + b.rows[0].join(" | ") + " |", "|" + b.rows[0].map(() => "---").join("|") + "|");
      L.push(...b.rows.slice(1).map((r) => "| " + r.join(" | ") + " |"), "");
    } else if (b.t === "sig") L.push("", "甲方（盖章/签字）：____________________　日期：__________", "", "乙方（签字）：____________________　日期：__________", "");
    else if (b.t === "pagebreak") L.push("---", "");
  }
  return L.join("\n");
}

// ---------- 渲染：docx ----------
let olCount = 0;
function toDocx(doc) {
  const numbering = { config: [
    { reference: "bullets", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 560, hanging: 280 } } } }] },
  ] };
  const children = [];
  const run = (text, opt = {}) => new TextRun({ text, font: FONT, size: 21, ...opt });
  for (const b of doc) {
    if (b.t === "h1") children.push(new Paragraph({ heading: HeadingLevel.HEADING_1, spacing: { after: 120 }, children: [run(b.text, { size: 32, bold: true })] }));
    else if (b.t === "h2") children.push(new Paragraph({ heading: HeadingLevel.HEADING_2, spacing: { before: 280, after: 100 }, children: [run(b.text, { size: 24, bold: true })] }));
    else if (b.t === "meta") children.push(new Paragraph({ spacing: { after: 200 }, children: [run(b.text, { size: 19, color: "666666" })] }));
    else if (b.t === "p") children.push(new Paragraph({ spacing: { after: 120, line: 320 }, children: [run(b.text)] }));
    else if (b.t === "ul") for (const x of b.items) children.push(new Paragraph({ numbering: { reference: "bullets", level: 0 }, spacing: { after: 80, line: 320 }, children: [run(x)] }));
    else if (b.t === "ol") {
      const ref = `ol${++olCount}`;
      numbering.config.push({ reference: ref, levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 560, hanging: 360 } } } }] });
      for (const x of b.items) children.push(new Paragraph({ numbering: { reference: ref, level: 0 }, spacing: { after: 80, line: 320 }, children: [run(x)] }));
    } else if (b.t === "table") {
      const border = { style: BorderStyle.SINGLE, size: 4, color: "BBBBBB" };
      const borders = { top: border, bottom: border, left: border, right: border };
      const rows = b.rows.map((r, ri) => new TableRow({
        tableHeader: ri === 0,
        children: r.map((c, ci) => new TableCell({
          width: { size: b.cols[ci], type: WidthType.DXA }, borders,
          shading: ri === 0 ? { type: ShadingType.CLEAR, fill: "F2F2F2", color: "auto" } : undefined,
          margins: { top: 80, bottom: 80, left: 100, right: 100 },
          children: [new Paragraph({ children: [run(c, { size: 19, bold: ri === 0 || (ri === b.rows.length - 1 && ci < 2) })] })],
        })),
      }));
      children.push(new Table({ rows, columnWidths: b.cols, width: { size: b.cols.reduce((a, c) => a + c, 0), type: WidthType.DXA } }));
      children.push(new Paragraph({ spacing: { after: 120 }, children: [] }));
    } else if (b.t === "sig") {
      children.push(new Paragraph({ spacing: { before: 600, after: 300 }, children: [run("甲方（盖章/签字）：____________________　日期：__________")] }));
      children.push(new Paragraph({ spacing: { after: 300 }, children: [run("乙方（签字）：____________________　日期：__________")] }));
    } else if (b.t === "pagebreak") children.push(new Paragraph({ children: [new PageBreak()] }));
  }
  return new Document({
    numbering,
    styles: { default: { document: { run: { font: FONT, size: 21 } } } },
    sections: [{ properties: { page: { margin: { top: 1300, bottom: 1300, left: 1400, right: 1400 } } }, children }],
  });
}

async function emit(name, doc) {
  fs.writeFileSync(path.join(OUT, `${name}.md`), toMd(doc), "utf8");
  const buf = await Packer.toBuffer(toDocx(doc));
  fs.writeFileSync(path.join(OUT, `${name}.docx`), buf);
  console.log("✓", name + ".docx", name + ".md");
}

(async () => {
  await emit("幻游纪-报价-简版", 报价简版);
  await emit("幻游纪-合作备忘录-草稿", 协议);
})();
