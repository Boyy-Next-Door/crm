"""Data import helpers for CRM.

Provides CSV templates (English fieldnames — the format Frappe's Data
Importer can parse directly) plus a Chinese-language reference sheet
that documents each field's meaning, whether it's required, and any
valid values.

Why not Chinese CSV headers directly? Frappe's importer matches header
columns against fieldname first, then against label. CRM DocType labels
are English, so a Chinese-headered CSV would fail to match any column.
The pragmatic answer for a bilingual admin is: keep the CSV headers
English (import-safe), and hand out a Chinese cheatsheet.
"""

import csv
import io
import zipfile
from typing import Any

import frappe
from frappe import _


# The four DocTypes CRM's frontend DataImport page supports.
# Values are (title_zh, sample_rows). Sample rows use plausible Chinese
# data so an admin can see immediately what shape the import expects.
SUPPORTED_DOCTYPES: dict[str, dict[str, Any]] = {
	"CRM Lead": {
		"title_zh": "客户线索",
		"sample_rows": [
			{
				"first_name": "张",
				"last_name": "三",
				"email": "zhangsan@example.com",
				"mobile_no": "13800138000",
				"organization": "北京示例科技有限公司",
				"job_title": "销售总监",
				"industry": "Technology",
				"source": "Website",
				"status": "New",
				"no_of_employees": "51-200",
				"annual_revenue": "5000000",
				"territory": "",
				"lead_owner": "",
			},
			{
				"first_name": "李",
				"last_name": "四",
				"email": "lisi@example.com",
				"mobile_no": "13800138001",
				"organization": "上海示范贸易有限公司",
				"job_title": "采购经理",
				"industry": "Retail",
				"source": "Existing Customer",
				"status": "Contacted",
				"no_of_employees": "11-50",
				"annual_revenue": "2000000",
				"territory": "",
				"lead_owner": "",
			},
			{
				"first_name": "王",
				"last_name": "五",
				"email": "wangwu@example.com",
				"mobile_no": "13800138002",
				"organization": "深圳测试信息技术有限公司",
				"job_title": "CTO",
				"industry": "Technology",
				"source": "Referral",
				"status": "Nurture",
				"no_of_employees": "1-10",
				"annual_revenue": "",
				"territory": "",
				"lead_owner": "",
			},
		],
	},
	"CRM Deal": {
		"title_zh": "商机",
		"sample_rows": [
			{
				"organization": "北京示例科技有限公司",
				"annual_revenue": "1200000",
				"close_date": "2026-12-31",
				"probability": "60",
				"status": "Qualification",
				"industry": "Technology",
				"source": "Website",
				"territory": "",
				"deal_owner": "",
			},
			{
				"organization": "上海示范贸易有限公司",
				"annual_revenue": "500000",
				"close_date": "2026-11-15",
				"probability": "30",
				"status": "Demo/Making",
				"industry": "Retail",
				"source": "Existing Customer",
				"territory": "",
				"deal_owner": "",
			},
		],
	},
	"Contact": {
		"title_zh": "联系人",
		"sample_rows": [
			{
				"first_name": "赵",
				"last_name": "六",
				"email_id": "zhaoliu@example.com",
				"mobile_no": "13800138003",
				"company_name": "北京示例科技有限公司",
				"designation": "总经理",
				"gender": "Male",
			},
		],
	},
	"CRM Organization": {
		"title_zh": "组织",
		"sample_rows": [
			{
				"organization_name": "北京示例科技有限公司",
				"website": "https://example.com",
				"industry": "Technology",
				"no_of_employees": "51-200",
				"annual_revenue": "10000000",
				"territory": "",
			},
			{
				"organization_name": "上海示范贸易有限公司",
				"website": "https://demo.com",
				"industry": "Retail",
				"no_of_employees": "11-50",
				"annual_revenue": "3000000",
				"territory": "",
			},
		],
	},
}


def _get_field_info(doctype: str, fieldname: str) -> dict[str, str]:
	"""Return a small dict describing a field for the Chinese cheatsheet.

	Reads the DocType's meta so field labels, types, and required flags
	stay in sync with reality — no hard-coded schema to drift.
	"""
	try:
		meta = frappe.get_meta(doctype)
		df = meta.get_field(fieldname)
		if not df:
			return {"label": fieldname, "type": "-", "required": "", "options": ""}
		return {
			"label": _(df.label) if df.label else fieldname,
			"type": df.fieldtype or "-",
			"required": "是" if df.reqd else "",
			"options": df.options or "",
		}
	except Exception:
		return {"label": fieldname, "type": "-", "required": "", "options": ""}


def _build_csv(doctype: str) -> str:
	"""Return a CSV string for a single doctype (English header + samples)."""
	spec = SUPPORTED_DOCTYPES.get(doctype)
	if not spec:
		frappe.throw(_("Unsupported doctype: {0}").format(doctype))

	sample_rows = spec["sample_rows"]
	# Header comes from the union of keys in samples, preserving first-row order.
	fieldnames: list[str] = []
	seen: set[str] = set()
	for row in sample_rows:
		for k in row.keys():
			if k not in seen:
				seen.add(k)
				fieldnames.append(k)

	buf = io.StringIO()
	writer = csv.DictWriter(buf, fieldnames=fieldnames)
	writer.writeheader()
	for row in sample_rows:
		writer.writerow(row)
	return buf.getvalue()


def _build_readme_html() -> str:
	"""Render a bilingual field reference for all supported doctypes."""
	sections: list[str] = []
	for doctype, spec in SUPPORTED_DOCTYPES.items():
		# Pull column names from the first sample row (they define the
		# CSV header in _build_csv, so this stays consistent).
		fieldnames = list(spec["sample_rows"][0].keys()) if spec["sample_rows"] else []

		rows_html = []
		for fn in fieldnames:
			info = _get_field_info(doctype, fn)
			rows_html.append(
				"<tr>"
				f"<td><code>{fn}</code></td>"
				f"<td>{info['label']}</td>"
				f"<td>{info['type']}</td>"
				f"<td>{info['required']}</td>"
				f"<td>{info['options']}</td>"
				"</tr>"
			)

		sections.append(
			f"<h2>{spec['title_zh']} <small style='color:#888'>({doctype})</small></h2>"
			"<table>"
			"<thead><tr>"
			"<th>字段名（CSV 列名）</th>"
			"<th>中文含义</th>"
			"<th>类型</th>"
			"<th>是否必填</th>"
			"<th>可选值/关联表</th>"
			"</tr></thead>"
			f"<tbody>{''.join(rows_html)}</tbody>"
			"</table>"
		)

	return f"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8">
<title>Frappe CRM 数据导入 字段说明</title>
<style>
body {{ font-family: -apple-system, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif; max-width: 1000px; margin: 2em auto; padding: 0 1em; color: #222; }}
h1 {{ border-bottom: 2px solid #333; padding-bottom: 0.3em; }}
h2 {{ margin-top: 2em; color: #2563eb; }}
table {{ width: 100%; border-collapse: collapse; margin: 1em 0; font-size: 14px; }}
th, td {{ border: 1px solid #ddd; padding: 6px 10px; text-align: left; vertical-align: top; }}
th {{ background: #f5f5f5; font-weight: 600; }}
code {{ background: #f0f0f0; padding: 2px 6px; border-radius: 3px; font-family: "SF Mono", Consolas, monospace; }}
.tip {{ background: #fff8e1; border-left: 4px solid #f59e0b; padding: 12px 16px; margin: 1em 0; }}
</style>
</head>
<body>
<h1>Frappe CRM 数据导入 - 字段说明</h1>

<div class="tip">
<strong>使用说明：</strong>
<ol>
  <li>本压缩包中每个 <code>.csv</code> 文件对应 CRM 的一种数据类型，可分别导入</li>
  <li>CSV 文件的<strong>首行必须保留原样</strong>（英文列名，Frappe 用这个匹配字段）</li>
  <li>示例行（第 2 行开始）为参考数据，导入前请<strong>删除示例并填入真实数据</strong></li>
  <li>关联字段（如 <code>industry</code>、<code>source</code>）填的值必须<strong>已存在于对应表中</strong>；若不存在会导入失败</li>
  <li>推荐先用 5 - 10 条真实数据试导，确认字段匹配无误后再上传大表格</li>
  <li>建议依次导入：<strong>组织 → 联系人 → 线索 → 商机</strong>（有依赖关系时避免报错）</li>
</ol>
</div>

{''.join(sections)}

<div class="tip">
<strong>常见问题：</strong>
<ul>
  <li><strong>报错 "Could not find X: Y"</strong>：说明关联的记录不存在。比如线索里 organization="XX" 但组织表没这条，先建组织再导线索</li>
  <li><strong>手机号/邮箱重复</strong>：Frappe 默认允许重复，除非你自定义了唯一性校验</li>
  <li><strong>日期格式</strong>：一律用 <code>YYYY-MM-DD</code>（如 <code>2026-12-31</code>），Excel 别自动改成 <code>12/31/2026</code></li>
  <li><strong>数字里带千分位</strong>：<code>1,000,000</code> 会失败，改成 <code>1000000</code></li>
  <li><strong>状态/来源/行业等下拉值</strong>：以 CRM 里现有的选项为准，可先在 UI 上手工建一条看下拉里有哪些值</li>
</ul>
</div>

</body>
</html>
"""


@frappe.whitelist()
def download_template(doctype: str):
	"""Download a single-doctype CSV template."""
	frappe.only_for(["System Manager", "Sales Manager"], True)

	if doctype not in SUPPORTED_DOCTYPES:
		frappe.throw(_("Unsupported doctype: {0}").format(doctype))

	csv_str = _build_csv(doctype)
	filename = f"{doctype.replace(' ', '_').lower()}_template.csv"

	frappe.local.response.filename = filename
	# UTF-8 BOM so Excel opens it as UTF-8 (otherwise Chinese in sample data
	# shows up as garbage on Windows).
	frappe.local.response.filecontent = ("﻿" + csv_str).encode("utf-8")
	frappe.local.response.type = "download"


@frappe.whitelist()
def download_all_templates_zip():
	"""Bundle every supported CSV template plus a Chinese README into a zip."""
	frappe.only_for(["System Manager", "Sales Manager"], True)

	buf = io.BytesIO()
	with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
		for doctype in SUPPORTED_DOCTYPES:
			csv_str = _build_csv(doctype)
			filename = f"{doctype.replace(' ', '_').lower()}_template.csv"
			# BOM here too so Excel plays nice.
			zf.writestr(filename, "﻿" + csv_str)

		zf.writestr("字段说明_README.html", _build_readme_html())

	frappe.local.response.filename = "crm_import_templates.zip"
	frappe.local.response.filecontent = buf.getvalue()
	frappe.local.response.type = "download"
