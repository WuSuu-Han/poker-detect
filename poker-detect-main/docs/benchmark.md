# Synthetic regression

Real-camera verification: PENDING.

| Scenario | Detected | Multiset correct |
|---|---:|---:|
| 原图 | 8 | 8/8 |
| 暗光 45% | 8 | 8/8 |
| 过曝 1.35 | 8 | 8/8 |
| 模糊 7x7 | 8 | 6/8 |
| JPEG q20 | 8 | 8/8 |
| 旋转 20° | 8 | 6/8 |
| 透视 | 8 | 8/8 |
| rotate_bound_15 | 8 | 8/8 |
| rotate_bound_30 | 8 | 8/8 |
| rotate_bound_45 | 8 | 8/8 |
| rotate_bound_60 | 8 | 8/8 |
| rotate_bound_75 | 8 | 8/8 |
| rotate_bound_90 | 8 | 6/8 |
| rotate_bound_180 | 8 | 8/8 |
| rotate_bound_270 | 8 | 8/8 |

Multiset matching ignores position. Use evaluate.py with independently annotated quads for precision, recall and accuracy.
Legacy rotation20 keeps the original canvas and crops corners; rotate_bound scenarios preserve the full canvas.