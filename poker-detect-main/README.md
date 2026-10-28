# 扑克牌检测与识别

沿用原项目的 HSV 分割、形态学、凸包四角、透视变换和字体模板倒角距离匹配。保留五个原实验脚本，新增 Tkinter GUI、批量导出、人工标注和独立评测工具。

## 运行 GUI

在本项目目录中：

```powershell
.\.venv\Scripts\python.exe src/gui.py
```

推荐双击 `run_gui.cmd`。本机测试中虚拟环境内的 Python 可读文件，但写文件被系统拒绝；这个启动脚本使用虚拟环境配置中的基础 Python，并加载同一虚拟环境的依赖。它不修改虚拟环境。直接运行若遇 PermissionError，可使用此入口。本机 PowerShell 限制未签名脚本，使用 CMD 入口无需调整执行策略。

选择图片或文件夹后，左侧显示检测框，右侧显示摆正牌面、点数、花色、匹配分数。识别线程通过队列向主线程回传结果。黄色 CHECK 表示结果需要核对；分数不是经过校准的正确概率。导出包含 CSV、JSON、标注原图和单张牌图。

## 批量与合成回归

以下 `python` 使用你的项目解释器；本机可用 `.\run_python.cmd` 替代，例如 `.\run_python.cmd src/benchmark.py --output output/benchmark.json`。

```powershell
python src/batch_recognize.py data --output output/batch
python src/benchmark.py --output output/benchmark.json
python src/robustness_test.py
python src/test_tools.py
```

`benchmark.py` 自动生成 JSON 和 Markdown，保留原七场景，并加入不裁切画布的 15/30/45/60/75/90/180/270 度旋转。原脚本的 20 度旋转会裁掉部分图像，报告单独保留它以便历史比较。

**这些是单张示例图的合成回归。多重集合匹配不验证检测位置，不能称为定位精确率。** 实际数值见 `docs/benchmark.md`，不在说明中手写固定表格。

## 真实多角度照片：待完成

目前用户未提供真实多角度拍摄照片，`data/real_photos.json` 因而为空。软件和评测入口已提供，不能据此声称正式题目的“多个角度拍照均准确识别”已经验收。

建议收集 20～50 张独立照片，涵盖平面旋转、不同俯拍角度、距离和桌面、光照条件，保留失败图片。每张照片在标注工具中按顺时针点击牌面四角，输入如 `10h`、`As`，点击“保存本图”；没有牌的负样本也可保存零张标注。

```powershell
python src/annotate.py --output data/real_photos.json
python src/evaluate.py data/real_photos.json --output output/real_evaluation.json
```

标注应由人根据原图独立完成，不能把检测输出当作真值。四角须按圆周顺序，花色 `s/h/d/c` 分别为黑桃、红桃、方块、梅花。路径相对 JSON 所在文件夹。示例条目结构：

```json
{"schema_version":1,"images":[{"file":"photos/photo01.jpg","photo_id":"photo01","source":"real","split":"test","angle_degrees":45,"cards":[{"rank":"A","suit":"s","quad":[[10,10],[110,10],[110,150],[10,150]]}]}]}
```

四点只是格式示例，不是已有图片的标注。一次原始拍摄的不同派生图使用相同 photo_id，禁止分配到不同 split。工具检查路径、重复文件、标签、凸四边形和 photo_id 跨集合泄漏。

评测按 IoU≥0.5 的一对一最大匹配统计 precision、recall、F1、点数／花色／整牌准确率、覆盖率、拒识率和已接受结果准确率；漏检计入准确率分母。误检中被接受的预测计入已接受结果准确率分母。输出逐图匹配 IoU 与混淆计数。无样本或无分母的指标为 N/A，不自动算成 100%。

## 识别修改

- Cambria TTC 回退保留；随项目提供 `src/cardlib/templates.npz`，没有 Windows 字体也可读取缓存。缺缓存和字体时明确报错。
- 各方向在同一识别坐标中切索引；透视牌短边横放；合并点数块时同步更新左边界。
- 索引粘连时尝试行投影谷值切分。10 参与模板匹配，双字符结构作为辅助证据。
- 中央重复花色对正倒方向分别匹配后投票，6/9 在可靠计数时作辅助修正；不代表所有字体和遮挡都适用。
- 匹配分数结合点数和花色距离，点数前两名差距参与 CHECK 提示，阈值尚未由独立实拍验证集校准。
- 白度相对阈值增加上限，防止超过 255；修正粘连牌腐蚀次数；诊断输出使用实际选中的阈值组。

## 环境与边界

本次验证：Python 3.14.7、OpenCV 5.0.0（发行包 5.0.0.93）、NumPy 2.5.4、Pillow 13.0.0、Tk 9。锁定版本见 requirements-lock.txt；Tk 由 Python 安装程序提供。

原图 8 张牌的识别仍须通过回归。模糊、裁切、部分旋转仍可能出错；浅色桌面、重叠、强反光、其他牌面字体没有完成真实照片验证。阈值封顶不等于解决白牌白桌分割。腐蚀分离修正也不等于已验证遮挡识别。项目没有宣称所有拍摄环境准确。
