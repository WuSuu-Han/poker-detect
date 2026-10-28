"""Synthetic sample regression. Multiset counts are NOT detection precision/recall."""
import argparse
from collections import Counter
import json
from pathlib import Path
import platform
import cv2
import numpy as np
from cardlib import imageio, detector, ranksuit
from robustness_test import degrade, TRUTH


def rotate_bound(image,angle):
    h,w=image.shape[:2]; m=cv2.getRotationMatrix2D((w/2,h/2),angle,1)
    c,s=abs(m[0,0]),abs(m[0,1]); nw=int(np.ceil(h*s+w*c)); nh=int(np.ceil(h*c+w*s))
    m[0,2]+=(nw-w)/2; m[1,2]+=(nh-h)/2
    return cv2.warpAffine(image,m,(nw,nh),borderValue=(60,60,60)),m


def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--image',default=str(Path(__file__).resolve().parents[1]/'data/cards_sample.jpg'))
    parser.add_argument('--output',default='output/benchmark.json'); args=parser.parse_args()
    image=imageio.imread(args.image); scenarios=degrade(image)
    legacy_count=len(scenarios)
    scenarios += [('rotate_bound_%d'%a,rotate_bound(image,a)[0]) for a in [15,30,45,60,75,90,180,270]]
    rows=[]
    for name,img in scenarios:
        codes=[]
        for c in detector.detect_cards(img):
            r=ranksuit.read_card(c.warped)
            codes.append(str(r['rank'])+(r['suit'] or '?').upper())
        hits=sum((Counter(codes)&Counter(TRUTH)).values())
        rows.append(dict(scenario=name,detected=len(codes),multiset_correct=hits,truth=len(TRUTH),predictions=codes))
    report=dict(scope='Single sample synthetic regression; no independent real-photo verification. Multiset counts do not measure localization precision.',
        versions=dict(python=platform.python_version(),opencv=cv2.__version__,numpy=np.__version__),
        legacy_correct=sum(r['multiset_correct'] for r in rows[:legacy_count]),legacy_total=legacy_count*len(TRUTH),
        real_photos_verified=False,scenarios=rows)
    path=Path(args.output); path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    lines=['# Synthetic regression','','Real-camera verification: PENDING.','','| Scenario | Detected | Multiset correct |','|---|---:|---:|']
    lines+=['| %s | %d | %d/%d |'%(r['scenario'],r['detected'],r['multiset_correct'],r['truth']) for r in rows]
    lines+=['','Multiset matching ignores position. Use evaluate.py with independently annotated quads for precision, recall and accuracy.',
            'Legacy rotation20 keeps the original canvas and crops corners; rotate_bound scenarios preserve the full canvas.']
    path.with_suffix('.md').write_text('\n'.join(lines),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=True))

if __name__=='__main__': main()
