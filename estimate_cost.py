"""Offline token-cost estimator for Argolink Claude Opus 5.5."""
from __future__ import annotations
import json, sys
from decimal import Decimal
from pathlib import Path
PRICES={"input":Decimal('4'),"output":Decimal('20'),"cached_input":Decimal('0.2'),"cache_write":Decimal('5')}

def estimate(usage:dict)->dict:
    total=Decimal('0'); parts={}
    for key,price_key in [('input_tokens','input'),('output_tokens','output'),('cached_input_tokens','cached_input'),('cache_write_tokens','cache_write')]:
        tokens=int(usage.get(key,0)); amount=(Decimal(tokens)/Decimal(1_000_000))*PRICES[price_key]; parts[price_key]=amount; total+=amount
    return {'model':'claude-opus-5-5','currency':'USD','breakdown':{k:str(v.quantize(Decimal('0.000001'))) for k,v in parts.items()},'total':str(total.quantize(Decimal('0.000001')))}

if __name__=='__main__':
    if len(sys.argv)!=2: raise SystemExit('usage: python estimate_cost.py usage.json')
    print(json.dumps(estimate(json.loads(Path(sys.argv[1]).read_text())),indent=2))
