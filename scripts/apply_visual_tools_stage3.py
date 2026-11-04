#!/usr/bin/env python3
"""Embed the local viewer into selected standalone modules (default M01–M16)."""
from pathlib import Path
import argparse,re
ROOT=Path(__file__).resolve().parents[1]
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--modules',type=int,nargs='+',default=list(range(1,17)));args=parser.parse_args()
 if any(n<1 or n>37 for n in args.modules):parser.error('module numbers must be 1..37')
 css=(ROOT/'scripts/templates/visual-tools-stage3.css').read_text();js=(ROOT/'scripts/templates/visual-tools-stage3.js').read_text()
 for n in args.modules:
  p=next((ROOT/'module_v1').glob(f'M{n:02}_*'));s=p.read_text()
  s=re.sub(r'\n/\* V3_VISUAL_TOOLS:.*?/\* END_V3_VISUAL_CSS \*/\n','',s,flags=re.S)
  s=re.sub(r'\n<script data-visual-tools="3">.*?</script>\n','',s,flags=re.S)
  s=re.sub(r'\n*\s*</style>','\n</style>',s,count=1)
  s=re.sub(r'\n*\s*</body>','\n</body>',s,count=1)
  s=s.replace('</style>',css+'\n/* END_V3_VISUAL_CSS */\n</style>',1)
  s=s.replace('</body>','<script data-visual-tools="3">\n'+js+'\n</script>\n</body>',1)
  p.write_text(s)
if __name__=='__main__':main()
