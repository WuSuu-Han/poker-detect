"""Evaluate an independently annotated dataset; never infer truth from predictions."""
import argparse
from collections import Counter
import json
from pathlib import Path
import platform
import cv2
import numpy as np
from cardlib.pipeline import recognize


def iou(a,b):
    a = cv2.convexHull(np.asarray(a,np.float32)).reshape(-1,2)
    b = cv2.convexHull(np.asarray(b,np.float32)).reshape(-1,2)
    intersection,_ = cv2.intersectConvexConvex(a,b)
    union = cv2.contourArea(a)+cv2.contourArea(b)-intersection
    return float(intersection/union) if union>0 else 0.


def match(matrix, threshold=.5):
    """Maximum-cardinality then maximum-IoU bipartite matching, residual augmenting paths."""
    n,m = matrix.shape
    size = n+m+2; source=size-2; sink=size-1
    graph=[[] for _ in range(size)]
    def edge(u,v,cost):
        graph[u].append([v,len(graph[v]),1,cost])
        graph[v].append([u,len(graph[u])-1,0,-cost])
    for i in range(n): edge(source,i,0)
    for j in range(m): edge(n+j,sink,0)
    for i in range(n):
        for j in range(m):
            if matrix[i,j]>=threshold: edge(i,n+j,-float(matrix[i,j]))
    while True:
        dist=[float('inf')]*size; previous=[None]*size; dist[source]=0
        for _ in range(size-1):
            changed=False
            for u in range(size):
                for k,e in enumerate(graph[u]):
                    if e[2] and dist[u]+e[3]<dist[e[0]]-1e-12:
                        dist[e[0]]=dist[u]+e[3]; previous[e[0]]=(u,k); changed=True
            if not changed: break
        if previous[sink] is None: break
        v=sink
        while v!=source:
            u,k=previous[v]; e=graph[u][k]; e[2]=0; graph[v][e[1]][2]=1; v=u
    return [(i,e[0]-n,float(matrix[i,e[0]-n])) for i in range(n)
            for e in graph[i] if n<=e[0]<n+m and e[2]==0]


def load_manifest(path):
    path=Path(path); data=json.loads(path.read_text(encoding='utf-8-sig'))
    if data.get('schema_version')!=1: raise ValueError('Expected schema_version: 1')
    splits={}; seen=set()
    for item in data['images']:
        key=item['file']; photo=item['photo_id']; split=item.get('split','test')
        if key in seen: raise ValueError('Duplicate image: '+key)
        seen.add(key)
        if photo in splits and splits[photo]!=split: raise ValueError('photo_id crosses dataset splits: '+photo)
        splits[photo]=split
        if item.get('source') not in ('real','sample','synthetic'): raise ValueError('Invalid source')
        if not (path.parent/key).is_file(): raise FileNotFoundError(path.parent/key)
        for card in item['cards']:
            q=np.asarray(card['quad'],np.float32)
            if q.shape!=(4,2) or not np.isfinite(q).all() or not cv2.isContourConvex(q) or cv2.contourArea(q)<=1:
                raise ValueError('quad must be four convex boundary points in circular order')
            if card['rank'] not in ['A','2','3','4','5','6','7','8','9','10','J','Q','K'] or card['suit'] not in 'shdc' or len(card['suit'])!=1:
                raise ValueError('Invalid rank/suit')
    return data


def evaluate(path):
    data=load_manifest(path); rows=[]; counts=Counter(); confusion=Counter()
    for item in data['images']:
        result=recognize(Path(path).parent/item['file']); cards=result['cards']; truth=item['cards']
        matrix=np.zeros((len(truth),len(cards)))
        for i,t in enumerate(truth):
            for j,c in enumerate(cards): matrix[i,j]=iou(t['quad'],c.quad)
        pairs=match(matrix); counts.update(truth=len(truth),predicted=len(cards),matched=len(pairs),
                                          accepted=sum(c.accepted for c in cards))
        matched=[]
        for i,j,overlap in pairs:
            t,c=truth[i],cards[j]; rank=t['rank']==c.rank; suit=t['suit']==c.suit
            counts.update(rank_correct=int(rank),suit_correct=int(suit),full_correct=int(rank and suit),
                          accepted_correct=int(c.accepted and rank and suit))
            confusion[(t['rank']+t['suit'],str(c.rank)+str(c.suit))]+=1
            matched.append(dict(truth_index=i,prediction_index=j,iou=overlap,rank_correct=rank,suit_correct=suit))
        rows.append(dict(file=item['file'],source=item['source'],photo_id=item['photo_id'],
                         truth=len(truth),predicted=len(cards),matches=matched))
    safe=lambda a,b: a/b if b else None
    p=safe(counts['matched'],counts['predicted']); r=safe(counts['matched'],counts['truth'])
    return dict(schema_version=1,scope='Only annotated images; synthetic variants are not independent real photos.',
        real_photo_count=len({i['photo_id'] for i in data['images'] if i['source']=='real'}),
        versions=dict(python=platform.python_version(),opencv=cv2.__version__,numpy=np.__version__),
        counts=dict(counts),metrics=dict(precision=p,recall=r,f1=2*counts['matched']/(counts['truth']+counts['predicted']) if counts['truth']+counts['predicted'] else None,
        rank_accuracy=safe(counts['rank_correct'],counts['truth']),suit_accuracy=safe(counts['suit_correct'],counts['truth']),
        full_accuracy=safe(counts['full_correct'],counts['truth']),coverage=safe(counts['accepted'],counts['predicted']),
        unknown_rate=safe(counts['predicted']-counts['accepted'],counts['predicted']),
        accepted_accuracy=safe(counts['accepted_correct'],counts['accepted'])),
        confusion=[dict(truth=a,predicted=b,count=n) for (a,b),n in confusion.items()],images=rows)


def main():
    parser=argparse.ArgumentParser(); parser.add_argument('manifest'); parser.add_argument('--output',default='output/evaluation.json')
    args=parser.parse_args(); report=evaluate(args.manifest)
    out=Path(args.output); out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    lines=['# Dataset evaluation','', 'Real photos: %d'%report['real_photo_count'],'', '| Metric | Value |','|---|---|']
    for name,value in report['metrics'].items(): lines.append('| %s | %s |'%(name,'N/A' if value is None else '%.4f'%value))
    lines+=['','No real-camera acceptance claim until an independent real-photo dataset is evaluated.',
            'Accuracy includes missed cards. Coverage uses all predictions; unmatched accepted detections count against accepted accuracy.',
            'Scores are uncalibrated. No generalization confidence interval is inferred from synthetic copies.']
    out.with_suffix('.md').write_text('\n'.join(lines),encoding='utf-8'); print(json.dumps(report['metrics'],ensure_ascii=False))

if __name__=='__main__': main()
