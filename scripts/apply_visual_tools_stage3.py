#!/usr/bin/env python3
"""Embed the local figure/table viewer into standalone M01–M16 modules."""
from pathlib import Path
import re
ROOT=Path(__file__).resolve().parents[1]
def main():
 css=(ROOT/'scripts/templates/visual-tools-stage3.css').read_text();js=(ROOT/'scripts/templates/visual-tools-stage3.js').read_text()
 for n in range(1,17):
  p=next((ROOT/'module_v1').glob(f'M{n:02}_*'));s=p.read_text()
  s=re.sub(r'\n/\* V3_VISUAL_TOOLS:.*?/\* END_V3_VISUAL_CSS \*/\n','',s,flags=re.S)
  s=re.sub(r'\n<script data-visual-tools="3">.*?</script>\n','',s,flags=re.S)
  s=re.sub(r'\n*\s*</style>','\n</style>',s,count=1)
  s=re.sub(r'\n*\s*</body>','\n</body>',s,count=1)
  s=s.replace('</style>',css+'\n/* END_V3_VISUAL_CSS */\n</style>',1)
  s=s.replace('</body>','<script data-visual-tools="3">\n'+js+'\n</script>\n</body>',1)
  p.write_text(s)
if __name__=='__main__':main()
