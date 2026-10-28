"""Shared recognition and exports for CLI and GUI. Scores are heuristic, not probabilities."""
import csv
import json
from pathlib import Path
import numpy as np
import cv2
from . import detector, imageio, ranksuit


def recognize(path):
    image = imageio.imread(str(path))
    cards = detector.detect_cards(image)
    for card in cards:
        result = ranksuit.read_card(card.warped)
        card.rank, card.suit = result['rank'], result['suit']
        card.confidence, card.rot = result['score'], result['rot']
        card.accepted = result.get('accepted',False)
        card.oriented = cv2.resize(np.rot90(card.warped, card.rot).copy(),(210,294))
    annotated = image.copy()
    for i, card in enumerate(cards):
        annotated = detector.draw_results(annotated, [card],
            color=(0, 200, 0) if card.accepted else (0, 180, 255),
            label_fn=lambda _, c: '%d %s%s%s' % (i+1, c.rank or '?',
                (c.suit or '?').upper(), '' if c.accepted else ' CHECK'))
    return {'path': str(Path(path).resolve()), 'image': image,
            'annotated': annotated, 'cards': cards}


def records(result):
    return [dict(image=result['path'], index=i+1, rank=c.rank, suit=c.suit,
                 score=round(c.confidence, 4), accepted=c.accepted,
                 rotation=c.rot*90, quad=c.quad.tolist())
            for i, c in enumerate(result['cards'])]


def export(results, folder):
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    rows = []
    for i, result in enumerate(results):
        stem = '%03d_%s' % (i+1, Path(result['path']).stem)
        if not imageio.imwrite(str(folder / (stem+'_result.png')), result['annotated']):
            raise OSError('Failed to save annotated image')
        for j, card in enumerate(result['cards']):
            if not imageio.imwrite(str(folder / ('%s_card_%02d.png' % (stem,j+1))), card.oriented):
                raise OSError('Failed to save card image')
        rows.extend(records(result))
    with (folder/'results.csv').open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['image','index','rank','suit','score','accepted','rotation','quad'])
        writer.writeheader()
        writer.writerows(rows)
    (folder/'results.json').write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding='utf-8')
