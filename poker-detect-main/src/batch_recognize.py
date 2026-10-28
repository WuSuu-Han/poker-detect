"""Batch recognition/export without a GUI."""
import argparse
import logging
from pathlib import Path
from cardlib.pipeline import recognize, export

def main():
    p=argparse.ArgumentParser(); p.add_argument('input'); p.add_argument('--output',default='output/batch')
    p.add_argument('--verbose',action='store_true'); args=p.parse_args()
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO)
    source=Path(args.input)
    paths=[source] if source.is_file() else sorted(x for x in source.iterdir() if x.suffix.lower() in {'.png','.jpg','.jpeg','.bmp','.tif','.tiff'})
    results=[]; failures=0
    for path in paths:
        try:
            results.append(recognize(path)); logging.info('%s: %d cards',path,len(results[-1]['cards']))
        except Exception:
            failures+=1; logging.exception('Failed: %s',path)
    export(results,args.output)
    if failures: raise SystemExit(1)

if __name__=='__main__': main()
