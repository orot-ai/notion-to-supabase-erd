# notion-to-supabase-erd

Design a **normalized Supabase (Postgres) schema from your Notion databases**, and generate an
**interactive ERD** you can actually click around in.

It's a [Claude Code](https://claude.com/claude-code) skill plus two standalone Python scripts
(stdlib only, no dependencies). The deterministic parts — dumping Notion and rendering the ERD — are
scripts. The judgment part — deciding what's real data vs. a formula, what becomes a foreign key vs. a
join table — is done by the model, guided by `SKILL.md`.

## Why

Notion databases are full of formulas, rollups, and buttons. A table with "101 columns" usually has ~15
of real data — the rest is computed. Moving to Postgres means keeping the data, turning formulas into
views, and making relations explicit. This tool standardizes that, and gives you an ERD where:

- Tables are colored by layer (source / hub / derived / join / finance / view)
- **Foreign keys draw a line** from the FK column to the target's `id`
- **Many-to-many** shows as a join table; **aggregates** show as dashed lines into views
- Columns are **collapsible** (primary shown, the rest folded behind "▾ N more")
- **Click a table** for its role, **click a column** for its description
- Everything auto-lays-out with no overlap, and is a single self-contained HTML file

## Install (as a Claude Code skill)

```bash
git clone https://github.com/orot-ai/notion-to-supabase-erd ~/.claude/skills/notion-to-supabase-erd
```
Then in Claude Code: "migrate my Notion workspace to Supabase" / "build an ERD from these Notion DBs".

Or use the scripts directly (below).

## Use (standalone)

### 1. Get a Notion token and share your DBs
- Create an **internal integration**: https://www.notion.so/my-integrations → copy the token (`ntn_…`).
- Open each database → ••• → **Connections** → add your integration.

### 2. Dump
```bash
export NOTION_API_TOKEN=ntn_xxx
python3 scripts/dump_notion.py <db_id> [<db_id> ...] --out notion_raw.json
```
Database id is the 32-hex chunk in the DB URL: `notion.so/<workspace>/<DB_ID>?v=…`.

### 3. Design `schema.json`
Read `notion_raw.json` and write a normalized schema (this is where the model earns its keep — see
`SKILL.md` for the rules and `examples/sample.schema.json` for a full example).

### 4. Render
```bash
python3 scripts/render_erd.py schema.json erd.html
open erd.html
```
The run prints description coverage and warns about any table missing a role description.

## schema.json in one glance

```json
{
  "title": "my-project",
  "tables": [
    {"name":"contacts","group":"master","desc":"People/senders hub.","columns":[
      {"name":"id","type":"uuid","pk":true},
      {"name":"name","type":"text","desc":"Display name."}
    ]},
    {"name":"sms","group":"collect","desc":"Incoming texts.","columns":[
      {"name":"id","type":"uuid","pk":true},
      {"name":"body","type":"text","desc":"Message body."},
      {"name":"contact_id","type":"uuid","fk":"contacts","desc":"Sender."}
    ]}
  ],
  "agg": [["sms","daily_synthesis"]]
}
```

- **group**: `collect` · `master` · `product` · `join` · `finance` · `view`
- **pk / fk**: relationships. `fk` value is the target table name. FK to its own table = self-reference.
- **type**: `text` `select` `numeric` `ts` `date` `bool` `uuid` `bigint` `text[]`
- **agg**: `[from_table, to_view]` dashed aggregate edges (also for day→week→month→year rollups)

## Files

```
SKILL.md                     Workflow + normalization rules (read by Claude Code)
scripts/dump_notion.py       Notion property dump (stdlib, NOTION_API_TOKEN)
scripts/render_erd.py        schema.json → interactive erd.html
templates/erd_template.html  The ERD (data injected at render time)
examples/sample.schema.json      Full example (life-os): every relation type
examples/minimal.schema.json     Tiny example
```

## Requirements
- Python 3.9+ (stdlib only)
- A Notion internal integration token

## License
MIT
