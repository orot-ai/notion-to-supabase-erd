#!/usr/bin/env python3
"""Dump all properties of one or more Notion databases → JSON.

This JSON is the *input* for normalized schema design. It records every property
with its type, relation target, select options, and whether it's a computed
property (formula/rollup/button) so you can decide what to keep vs. drop.

Usage:
  export NOTION_API_TOKEN=ntn_xxx           # Notion internal integration token
  python3 dump_notion.py <db_id> [<db_id> ...] [--out raw.json]

- Works with the current Notion API (2025-09-03, data_sources aware).
- Pure stdlib. No dependencies.
- Share each database with your integration first (••• → Connections).
"""
import json
import os
import sys
import urllib.request
import urllib.error

TOKEN = os.environ.get('NOTION_API_TOKEN')
NOTION_VERSION = '2025-09-03'
CALC_TYPES = {'formula', 'rollup', 'button'}


def api(method, path):
    req = urllib.request.Request('https://api.notion.com/v1/' + path, method=method)
    req.add_header('Authorization', 'Bearer ' + TOKEN)
    req.add_header('Notion-Version', NOTION_VERSION)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def db_props(dbid):
    """Return (title, properties) — data_sources aware."""
    r = api('GET', f'databases/{dbid}')
    title = ''.join(t.get('plain_text', '') for t in r.get('title', []))
    props = r.get('properties')
    if not props:
        srcs = r.get('data_sources') or []
        if srcs:
            r2 = api('GET', f"data_sources/{srcs[0]['id']}")
            if not title:
                title = ''.join(t.get('plain_text', '') for t in r2.get('title', []))
            props = r2.get('properties') or {}
    return title, (props or {})


def parse_prop(pname, p):
    t = p.get('type', '?')
    item = {'name': pname, 'type': t}
    if t == 'relation':
        item['relation_db'] = (p.get('relation', {}).get('database_id', '') or '').replace('-', '')
    elif t in ('select', 'multi_select', 'status'):
        item['options'] = [o['name'] for o in p.get(t, {}).get('options', [])]
    elif t in CALC_TYPES:
        item['is_calc'] = True
    return item


def dump_db(dbid):
    title, props = db_props(dbid)
    cols = [parse_prop(n, p) for n, p in props.items()]
    return {
        'id': dbid.replace('-', ''),
        'title': title,
        'columns': cols,
        'total': len(cols),
        'calc_count': sum(1 for c in cols if c.get('is_calc')),
    }


def main():
    if not TOKEN:
        sys.exit("Set NOTION_API_TOKEN (Notion internal integration token).")
    args = sys.argv[1:]
    out_path = None
    if '--out' in args:
        i = args.index('--out')
        out_path, args = args[i + 1], args[:i] + args[i + 2:]
    if not args:
        sys.exit(__doc__)

    result = {}
    for dbid in args:
        try:
            result[dbid.replace('-', '')] = dump_db(dbid)
        except urllib.error.HTTPError as e:
            result[dbid] = {'error': f'HTTP {e.code}: {e.reason}'}
        except Exception as e:
            result[dbid] = {'error': str(e)[:120]}

    # map relation target ids → titles when both were dumped
    id2title = {v['id']: v.get('title', '') for v in result.values() if 'id' in v}
    for v in result.values():
        for c in v.get('columns', []):
            rid = c.get('relation_db')
            if rid and rid in id2title:
                c['relation_to'] = id2title[rid]

    text = json.dumps(result, ensure_ascii=False, indent=1)
    if out_path:
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(text)
        print(f"✓ {out_path}  ({len(result)} DB)")
        for k, v in result.items():
            if 'total' in v:
                print(f"  {v['title'] or k}: {v['total']} cols ({v['calc_count']} computed)")
            else:
                print(f"  {k}: {v['error']}")
    else:
        print(text)


if __name__ == '__main__':
    main()
