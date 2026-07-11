#!/usr/bin/env python3
"""스키마 JSON → 인터랙티브 ERD HTML.

사용: render_erd.py <schema.json> <out.html>

스키마 JSON 스펙:
{
  "title": "life-os-sample",
  "tables": [
    {
      "name": "sms_messages",
      "group": "collect|master|product|join|finance|view",
      "desc": "이 테이블이 뭐 하는 곳인지 (필수)",
      "columns": [
        {"name":"id","type":"uuid","pk":true},
        {"name":"content","type":"text","desc":"컬럼 설명"},
        {"name":"contact_id","type":"uuid","fk":"contacts","desc":"..."}
      ]
    }
  ],
  "agg": [["sms_messages","daily_synthesis"], ["daily_synthesis","weekly_synthesis"]]
}

- group: collect(수집) master(허브) product(생산성) join(N:M) finance(재무) view(뷰)
- pk / fk: 관계. fk 값은 대상 테이블 이름. fk가 자기 테이블이면 self(자기참조)로 자동 처리.
- type: text/select/numeric/ts/date/bool/uuid/bigint/text[] (ERD 표시용)
- agg: 실테이블→뷰 집계선(점선). 롤업(일→주→월→년)도 여기에.
"""
import json
import sys
import os

GG = {'collect': 'c', 'master': 'm', 'product': 'p', 'join': 'j', 'finance': 'f', 'view': 'v'}
# 그룹별 x열 (collect만 2열로 분산)
GX = {'master': 560, 'product': 820, 'join': 1080, 'finance': 1340, 'view': 1600}
COLLECT_X = [40, 300]
TEMPLATE = os.path.join(os.path.dirname(__file__), '..', 'templates', 'erd_template.html')


def col_to_cell(c):
    """스키마 컬럼 → ERD cols 항목 [name, type, role?, target?]"""
    name, typ = c['name'], c.get('type', 'text')
    if c.get('pk'):
        return [name, typ, 'pk']
    if c.get('fk'):
        return [name, 'uuid', 'fk', c['fk']]
    return [name, typ]


def build(schema):
    nodes, table_desc, desc = {}, {}, {}
    collect_i = 0
    for t in schema['tables']:
        name, group = t['name'], t['group']
        g = GG.get(group, 'c')
        if group == 'collect':
            x = COLLECT_X[collect_i % 2]
            collect_i += 1
        else:
            x = GX.get(group, 560)
        views = t.get('formula_count', 0)  # ƒ 배지용 (선택)
        node = {'x': x, 'y': 0, 'g': g, 'cols': [col_to_cell(c) for c in t['columns']]}
        if views:
            node['views'] = views
        nodes[name] = node
        if t.get('desc'):
            table_desc[name] = t['desc']
        for c in t['columns']:
            if c.get('desc'):
                desc[f"{name}.{c['name']}"] = c['desc']
    agg = schema.get('agg', [])
    return nodes, table_desc, desc, agg


def main():
    if len(sys.argv) < 3:
        print("사용: render_erd.py <schema.json> <out.html>", file=sys.stderr)
        sys.exit(1)
    schema = json.load(open(sys.argv[1], encoding='utf-8'))
    nodes, table_desc, desc, agg = build(schema)
    tpl = open(TEMPLATE, encoding='utf-8').read()
    title = schema.get('title', 'ERD')
    tpl = tpl.replace('__NODES__', json.dumps(nodes, ensure_ascii=False))
    tpl = tpl.replace('__TABLE_DESC__', json.dumps(table_desc, ensure_ascii=False))
    tpl = tpl.replace('__DESC__', json.dumps(desc, ensure_ascii=False))
    tpl = tpl.replace('__AGG__', json.dumps(agg, ensure_ascii=False))
    tpl = tpl.replace('__TITLE__', title)
    with open(sys.argv[2], 'w', encoding='utf-8') as f:
        f.write(tpl)
    # 요약
    groups = {}
    for t in schema['tables']:
        groups[t['group']] = groups.get(t['group'], 0) + 1
    ncols = sum(len(t['columns']) for t in schema['tables'])
    ndesc = len(desc)
    missing_tbl = [t['name'] for t in schema['tables'] if not t.get('desc')]
    print(f"✅ {sys.argv[2]}")
    print(f"   테이블 {len(schema['tables'])}개 {dict(groups)} · 컬럼 {ncols} · 집계선 {len(agg)}")
    print(f"   속성 설명 {ndesc}/{ncols}")
    if missing_tbl:
        print(f"   ⚠️ 역할 설명 누락 테이블: {missing_tbl}")


if __name__ == '__main__':
    main()
