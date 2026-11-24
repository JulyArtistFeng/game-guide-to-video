"""Read-only plan contract checks. Not a media renderer or a semantic quality judge."""
import argparse, hashlib, json, math, re
from pathlib import Path

SKILL = 'game-guide-to-video'
class ContractError(ValueError): pass
def need(condition, message):
    if not condition: raise ContractError(message)
def text(value, label):
    need(isinstance(value,str) and bool(value.strip()), label+' must be nonempty text')
    return value
def num(value, label, positive=False):
    need(isinstance(value,(int,float)) and not isinstance(value,bool) and math.isfinite(value),label+' must be a finite number')
    need(value>0 if positive else value>=0,label+' is out of range')
    return value
def rows(value,label):
    need(isinstance(value,list) and bool(value),label+' must be a nonempty list')
    need(all(isinstance(v,dict) for v in value),label+' entries must be objects')
    return value
def ids(value,label):
    result={}
    for row in rows(value,label):
        key=text(row.get('id'),label+' id');need(key not in result,'duplicate '+label+' id: '+key);result[key]=row
    return result
def span(row,limit,start='start',end='end'):
    a=num(row.get(start),start);b=num(row.get(end),end)
    need(a<b and b<=limit+0.001,'invalid/out-of-range interval '+start+'/'+end)
    return a,b
def cover(items,total):
    intervals=sorted(span(row,total) for row in rows(items,'timeline'))
    cursor=0.0
    for a,b in intervals:
        need(a<=cursor+0.001,'timeline has an uncovered gap at '+str(cursor))
        cursor=max(cursor,b)
    need(cursor>=total-0.001,'timeline does not cover output end')
def cover_window(items,start,end):
    intervals=[]
    for row in items:
        a=max(start,row['start']);b=min(end,row['end'])
        if b>a:intervals.append({'start':a-start,'end':b-start})
    cover(intervals,end-start)
def source_clip(row,source_duration):
    a,b=span(row,source_duration,'source_in','source_out')
    speed=num(row.get('speed',1),'speed',True)
    expected=(b-a)/speed
    need(abs((row['end']-row['start'])-expected)<=0.05,'clip output duration does not match source interval/speed')
    return a,b

def check_role(d,base,check_files):
    text(d.get('source_document'),'source_document');text(d.get('game_version'),'game_version')
    duration=num(d.get('output_duration'),'output_duration',True)
    cues=ids(d.get('narration'),'narration');shots=rows(d.get('shots'),'shots');cover(shots,duration)
    for shot in shots:
        need(shot.get('kind') in ['gameplay','screenshot','diagram','generated_atmosphere','title'],'declare shot identity')
        text(shot.get('source_ref'),'shot source_ref')
        if shot['kind'] in ['gameplay','screenshot']:need(shot.get('game_version')==d['game_version'],'gameplay shot version differs from source guide')
    for cue in cues.values():
        a,b=span(cue,duration);text(cue.get('text'),'narration text')
        if cue.get('claim_kind')=='mechanic':
            text(cue.get('source_ref'),'mechanic source document location')
            supporting=[s for s in shots if s['kind'] in ['gameplay','screenshot'] or (s['kind']=='diagram' and s.get('verified_against_source') is True and isinstance(s.get('illustration_label'),str) and bool(s['illustration_label'].strip()))]
            cover_window(supporting,a,b)


def inspect_plan(data,base=None,check_files=False):
    try:
        need(isinstance(data,dict),'plan must be an object')
        need(data.get('skill')==SKILL,'plan belongs to a different skill')
        check_role(data,Path(base or '.'),check_files)
        errors=[]
    except (ContractError,KeyError,TypeError,ValueError,OSError,AttributeError) as exc:
        errors=[str(exc)]
    return {'skill':SKILL,'contract_valid':not errors,'errors':errors,'scope':'declared plan and optional file fingerprints only','quality':'requires role-specific human/semantic and rendered-output review; no tools, media generation or external services executed'}
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('plan',type=Path)
    # No external media/service inspection is claimed by this checker.
    args=p.parse_args()
    try:
        data=json.loads(args.plan.read_text(encoding='utf-8'))
        result=inspect_plan(data,args.plan.resolve().parent,False)
        print(json.dumps(result,ensure_ascii=False,indent=2))
        return 0 if result['contract_valid'] else 1
    except (OSError,ValueError) as exc:
        print(json.dumps({'contract_valid':False,'errors':[str(exc)]},ensure_ascii=False));return 2
if __name__=='__main__': raise SystemExit(main())
