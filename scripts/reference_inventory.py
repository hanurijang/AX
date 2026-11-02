#!/usr/bin/env python3
"""참고자료 메타데이터·번호·URL 형식 검사와 목록 추출. 외부 요청 없음.
실행: python scripts/reference_inventory.py [--output ref/review-p24/inventory.csv]
URL 접속·자료 본문 일치·출처 권리를 검증하는 도구가 아니다.
"""
import argparse
import csv
from datetime import date
import fnmatch
import json
from pathlib import Path
import re
import subprocess
from urllib.parse import urlparse

ROOT=Path(__file__).resolve().parents[1]


def js_array(source, name):
    array=re.search(r'var '+name+r'=(\[.*?\n\]);',source,re.S)[1]
    return json.loads(subprocess.check_output(['node','-e','console.log(JSON.stringify('+array+'))'],text=True))


def collect():
    policy_path=Path('/etc/codex/network-policy.json')
    policy=json.loads(policy_path.read_text()) if policy_path.exists() else {}
    network=policy.get('http_network_policy',{})
    hosts=[row['host'] for row in network.get('egress_rules',[])]
    rows=[];metadata={}
    for path in sorted((ROOT/'module_v1').glob('M*.html')):
        source=path.read_text();refs=js_array(source,'REFS')
        numbers=[row['n'] for row in refs]
        assert numbers==list(range(1,len(refs)+1)),path
        for term in js_array(source,'GLOSSARY'):
            if len(term)>4 and term[4]:assert term[4] in numbers,(path,term)
        for row in refs:
            assert row['title'].strip() and row['org'].strip(),row
            assert date.fromisoformat(row['date'][:10])<=date.today(),row
            url=urlparse(row['url']);assert url.scheme=='https' and url.hostname and not re.search(r'\s',row['url']),row
            if url.hostname=='doi.org':assert re.fullmatch(r'/10\.\d{4,9}/\S+',url.path),row
            key=(row['title'],row['org']);assert row['url'] not in metadata or metadata[row['url']]==key,row
            metadata[row['url']]=key
            # This describes local policy only, never the remote site's health.
            excluded=network.get('type')=='restricted' and not any(fnmatch.fnmatch(url.hostname,h) for h in hosts)
            status='미실행: 환경 HTTP 허용 목록 밖' if excluded else '미실행: 외부 확인 별도'
            rows.append(dict(module=int(path.name[1:3]),**row,external_verification=status))
    assert len({row['module'] for row in rows})==37
    return rows


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'ref/review-p24/inventory.csv')
    args=parser.parse_args();rows=collect();args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=['module','n','title','org','url','date','external_verification'])
        writer.writeheader();writer.writerows(rows)
    print(json.dumps(dict(modules=37,references=len(rows),unique_urls=len({r['url'] for r in rows}),external_requests=0),ensure_ascii=False))


if __name__=='__main__':main()
