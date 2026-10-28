import tempfile
import unittest
from pathlib import Path
import json
import cv2
import numpy as np
from evaluate import match, iou, load_manifest, evaluate
from benchmark import rotate_bound
from cardlib import ranksuit, imageio
from cardlib.pipeline import recognize, export


class ToolsTest(unittest.TestCase):
    def test_assignment_avoids_greedy_miss(self):
        pairs=match(np.array([[.9,.7],[.8,.1]]))
        self.assertEqual({(i,j) for i,j,_ in pairs},{(0,1),(1,0)})

    def test_geometry(self):
        q=[[0,0],[10,0],[10,10],[0,10]]
        self.assertAlmostEqual(iou(q,q),1.)
        self.assertEqual(iou(q,[[20,20],[30,20],[30,30],[20,30]]),0.)
        im=np.zeros((60,100,3),np.uint8)
        rot,m=rotate_bound(im,45)
        xy=np.array([[0,0,1],[100,0,1],[100,60,1],[0,60,1]])@m.T
        self.assertTrue((xy>=-1).all()); self.assertTrue((xy[:,0]<=rot.shape[1]+1).all())

    def test_cache_without_fonts(self):
        old=ranksuit._FONT_DIR
        try:
            ranksuit._RANK_TPL.clear(); ranksuit._SUIT_TPL.clear(); ranksuit._FONT_DIR='missing-font-folder'
            self.assertEqual(len(ranksuit.rank_templates()),13)
            self.assertEqual(len(ranksuit.suit_templates()),4)
        finally: ranksuit._FONT_DIR=old

    def test_empty_scene_export_and_evaluation(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder); imageio.imwrite(str(p/'empty.png'),np.zeros((400,600,3),np.uint8))
            result=recognize(p/'empty.png'); self.assertEqual(len(result['cards']),0)
            export([result],p/'out'); self.assertTrue((p/'out/results.csv').is_file())
            manifest=dict(schema_version=1,images=[dict(file='empty.png',photo_id='one',source='real',cards=[])])
            (p/'truth.json').write_text(json.dumps(manifest),encoding='utf-8')
            report=evaluate(p/'truth.json'); self.assertEqual(report['counts']['predicted'],0)

    def test_failure_keys(self):
        r=ranksuit.read_card(np.full((294,210,3),255,np.uint8))
        self.assertIsNone(r['rank']); self.assertIn('suit_dist',r); self.assertIn('rank_dist',r)

    def test_manifest_rejects_split_leakage(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)
            for name in ['a.png','b.png']:
                imageio.imwrite(str(p/name),np.zeros((40,40,3),np.uint8))
            manifest=dict(schema_version=1,images=[dict(file=f,photo_id='same-original',source='synthetic',split=split,cards=[])
                for f,split in [('a.png','train'),('b.png','test')]])
            (p/'truth.json').write_text(json.dumps(manifest),encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'crosses dataset splits'):
                load_manifest(p/'truth.json')

if __name__=='__main__': unittest.main()
