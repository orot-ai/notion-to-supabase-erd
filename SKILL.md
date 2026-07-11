---
name: notion-to-supabase-erd
version: 1.0.0
description: "Design a normalized Supabase (Postgres) schema from one or more Notion databases and generate an interactive ERD. Dumps Notion properties → you design a normalized schema.json (drop formulas, relation→FK, many-to-many→join table, aggregates→view) → renders a self-contained HTML ERD with collapsible columns, relation lines, and per-table / per-column descriptions. Use when asked to migrate Notion to Supabase, build an ERD from Notion, or design a schema for a Notion workspace."
metadata:
  requires:
    bins: []
---

# notion-to-supabase-erd

Standardizes the "Notion → Supabase" migration: **normalized schema design + interactive ERD**.
Deterministic steps (dump, render) are scripts; the judgment step (normalization, descriptions) is done by the model.

## Pipeline

```
1) dump_notion.py    Dump every Notion property → notion_raw.json      [script]
2) (design)          Read raw, write normalized schema.json           [model — the core step]
3) render_erd.py     schema.json → erd.html (interactive)             [script]
4) review            Check coverage → show ERD → refine
```

## 1. Dump

```bash
export NOTION_API_TOKEN=ntn_xxx     # Notion internal integration token
python3 scripts/dump_notion.py <db_id> [<db_id> ...] --out notion_raw.json
```
Share each database with your integration first (••• → Connections). Output records every
property with type, relation target, select options, and `is_calc` (formula/rollup/button).

## 2. Design the schema (the important step — done by the model)

Read `notion_raw.json` and write `schema.json` following these rules.

**Required (do not skip):**
- **Every table gets a `desc`** (what this table is for). No blanks.
- **Every column gets a `desc`.** Only `id`/pk may be omitted (auto-described). Write one even for obvious ones.
- **Map every relationship:**
  - Notion relation (1:N) → a `"fk":"target_table"` column.
  - Many-to-many (both sides multiple; e.g. multi_select projects) → a **join table** (`group:"join"`, two fk columns).
  - Points at itself (parent / prev-next / related) → set fk target to its own table (rendered as self-reference).
  - Several sources aggregated by date (daily digest / monthly report) → a **view** (`group:"view"`) plus `agg` edges.

**Transform:**
- `is_calc` columns (formula/rollup/button) are **not stored** — express them as views / generated columns / app logic (via `agg` or a view table).
- select/multi_select/status → type `select`.
- Notion type → ERD type: `text` / `select` / `numeric` / `ts` / `date` / `bool` / `uuid` / `bigint` / `text[]`.
- Keep only `id` (pk) from system columns; drop created_at/updated_at/external_id for a clean node.
- If reports split into day/week/month/year, create `daily/weekly/monthly/yearly_synthesis` views with rollup `agg` (sources→daily, daily→weekly→monthly→yearly).

**Groups (6):** `collect` (sources) · `master` (hubs) · `product` (derived) · `join` (N:M) · `finance` · `view`.

### schema.json spec
```json
{
  "title": "my-project",
  "tables": [
    {"name":"sms","group":"collect","desc":"Incoming text messages...","columns":[
      {"name":"id","type":"uuid","pk":true},
      {"name":"body","type":"text","desc":"Cleaned message body."},
      {"name":"contact_id","type":"uuid","fk":"contacts","desc":"Who sent it."}
    ]},
    {"name":"task_projects","group":"join","desc":"task↔project N:M.","columns":[
      {"name":"task_id","type":"uuid","fk":"tasks"},
      {"name":"project_id","type":"uuid","fk":"projects"}]},
    {"name":"daily_synthesis","group":"view","desc":"[view] Daily rollup.","columns":[
      {"name":"note_date","type":"date"},{"name":"sms_count","type":"numeric","desc":"Texts that day."}]}
  ],
  "agg": [["sms","daily_synthesis"], ["daily_synthesis","weekly_synthesis"]]
}
```
See `examples/sample.schema.json` for a full example covering every relation type.

## 3. Render

```bash
python3 scripts/render_erd.py schema.json erd.html
```
Self-contained HTML: auto column layout (no overlap), collapsible columns (primary shown, rest folded),
relation lines (FK solid · join · self-reference · aggregate dashed), sky-blue highlight, click-a-table
for its role, click-a-column for its description. The run logs **description coverage** and **missing table
roles** — fill gaps in schema.json and re-render.

## 4. Review
- Fix low coverage / missing warnings.
- Show the ERD to the user, refine relations & descriptions.
- Once confirmed, turn schema.json into DDL (create table) and apply to Supabase.

`schema.json` becomes the single source of truth for DDL, migrations, and docs.
