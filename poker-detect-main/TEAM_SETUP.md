# 队友环境配置与协作指南

适用项目：扑克牌检测与识别。记录日期：2026-10-27。

首次配置请从项目根目录操作，即能看到 `src/`、`data/`、`requirements-lock.txt` 和 `run_gui.cmd` 的目录。不要照搬其他队友的电脑绝对路径。

项目功能与未完成任务见 [项目完成情况](PROJECT_STATUS.md)。

## 一、需要准备的环境

项目已有验证记录的环境如下；这些是现有项目记录，本次编写文档未重新安装验证。

| 组件 | 已验证版本／说明 |
| --- | --- |
| 操作系统 | Windows；项目附带的 CMD 启动器仅适用于 Windows |
| Python | 3.14.7；优先选择与现有验证记录一致的版本及 64 位解释器 |
| OpenCV Python 发行包 | `opencv-python==5.0.0.93`；运行时 `cv2.__version__` 为 `5.0.0` |
| NumPy | `2.5.4` |
| Pillow | `13.0.0` |
| Tkinter／Tcl-Tk | GUI 所需，由 Python 安装程序提供；现有记录为 Tk 9 |
| Git | 命令行 Git 或 GitHub Desktop 均可，用于团队协作 |

精确依赖见 `requirements-lock.txt`；`requirements.txt` 是较宽松的版本范围，不等同于已验证的组合。

当前功能不要求 GPU、CUDA、深度学习框架或额外训练模型。通常使用已有 `templates.npz`，不需要另外安装 Cambria 字体。

若无法获得锁定版本，或安装器提示没有对应发行包，请保留完整报错并与团队核对版本。不要静默替换依赖后继续使用旧的测试结论；替换环境后需要重新记录测试结果。

## 二、获取项目

如果使用 GitHub Desktop：克隆团队仓库，然后在 VS Code 中打开仓库文件夹。

如果使用 Git：从团队 GitHub 页面复制实际仓库地址，再执行：

```powershell
# 将下一行中的地址替换为团队仓库的真实地址。
git clone https://github.com/OWNER/REPOSITORY.git
# 切换到克隆生成的实际文件夹；名称以仓库为准。
cd REPOSITORY
```

确认仓库内包含 `src/cardlib/templates.npz`、`data/cards_sample.jpg` 和 `requirements-lock.txt`。缺文件时先检查拉取是否完整，不要立即修改识别代码。

## 三、创建每个人自己的虚拟环境

安装 Python 时保留 Tcl/Tk 支持。先查看本机 Python，再创建环境：

```powershell
py --list
py -3.14 --version
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
```

`py -3.14` 选择本机安装的 3.14 系列，实际补丁版本以 `--version` 输出为准，不会自动安装 3.14.7。没有 `py` 启动器时，可用已安装 Python 的完整路径创建环境。

无需激活也能使用 `.venv\Scripts\python.exe`，因此不必为激活脚本修改 PowerShell 执行策略。不要复制队友的 `.venv`，它包含与创建机器有关的路径，应在自己电脑上重新创建。

## 四、检查环境与 VS Code 解释器

```powershell
.\.venv\Scripts\python.exe --version
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -c "import cv2, numpy, PIL; print('OpenCV:', cv2.__version__); print('NumPy:', numpy.__version__); print('Pillow:', PIL.__version__)"
.\.venv\Scripts\python.exe -m tkinter
```

最后一条应打开 Tk 测试窗口，检查后关闭。若 `tkinter` 不可用，应通过 Python 安装程序补充 Tcl/Tk 支持，不能把它当作普通第三方库通过 `pip install tkinter` 解决。

VS Code 中按 `Ctrl+Shift+P`，执行 `Python: Select Interpreter`，选择当前仓库的 `.venv\Scripts\python.exe`。终端运行与编辑器解释器应指向同一项目环境。

## 五、启动软件

### GUI

推荐双击项目根目录的 `run_gui.cmd`，或在 PowerShell 中执行：

```powershell
.\run_gui.cmd
```

也可直接运行：

```powershell
.\.venv\Scripts\python.exe src/gui.py
```

界面预加载模板后，选择 `data/cards_sample.jpg`。已有测试记录为检出 8 张、整牌标签正确 8 张；队友本机结果应实际核对，不能仅凭界面启动成功就认为识别通过。

GUI 可导出 CSV、JSON、标注原图和单张摆正牌图。CHECK 是人工核对提示，匹配分数不是正确概率。

### 命令行与已有测试

以下使用项目自带的 Windows 启动器，从项目根目录执行：

```powershell
# 识别示例图并导出。
.\run_python.cmd src/batch_recognize.py data/cards_sample.jpg --output output/batch

# 原实验脚本。
.\run_python.cmd src/env_check.py
.\run_python.cmd src/image_basics.py
.\run_python.cmd src/card_detection.py
.\run_python.cmd src/card_recognize.py

# 原七场景与扩展合成回归。
.\run_python.cmd src/robustness_test.py
.\run_python.cmd src/benchmark.py --output output/benchmark.json

# 单元测试和 GUI 流程验证。
.\run_python.cmd src/test_tools.py
.\run_python.cmd src/smoke_gui.py
```

`run_python.cmd` 从本机 `.venv/pyvenv.cfg` 读取基础 Python 路径，并加载本机虚拟环境依赖，不需要手工填写原开发者的路径。它要求该虚拟环境和对应基础 Python 都存在。

已有记录：6 项单元测试通过、GUI 流程验证通过、原七场景合计 52/56。报告包含合成图片，不能用来声称真实多角度拍摄准确率已达标。

## 六、后续真实照片标注与评测

准备实拍照片后：

```powershell
.\run_python.cmd src/annotate.py --output data/real_photos.json
.\run_python.cmd src/evaluate.py data/real_photos.json --output output/real_evaluation.json
```

操作要点：

1. 每张牌按顺时针依次点击四个角，输入点数和花色，例如 `As`、`10h`、`Qc`。
2. 花色 `s/h/d/c` 分别为黑桃、红桃、方块、梅花。
3. 点击“保存本图”后再切换图片；没有牌的负样本可以保存零张牌。
4. JSON 内图片路径相对 JSON 所在目录；移动图片后应同步维护路径。
5. 使用自己的照片建立独立标注，不用识别输出充当正确答案。
6. 同一拍摄照片的派生图使用相同 `photo_id`，不得跨训练／测试集合。

当前 `data/real_photos.json` 为空，评测显示 N/A 是正常情况，不代表 0 张样本全部识别成功。

## 七、常见问题

| 现象 | 处理方法 |
| --- | --- |
| `ModuleNotFoundError: cv2/numpy/PIL` | 检查 VS Code 解释器；使用 `.venv\Scripts\python.exe -m pip` 安装，避免装到其他 Python |
| 提示不存在 `.venv/pyvenv.cfg` | 在仓库根目录重新创建 `.venv`，不要复制其他电脑的环境 |
| CMD 找不到基础 Python | 原 Python 可能已移动或卸载；用现有 Python 重建项目环境 |
| 缺少字体／模板 | 优先恢复仓库中的 `src/cardlib/templates.npz`；缓存和系统字体都不可用时会明确报错 |
| `PermissionError` 或导出失败 | 确认目标目录可写；尝试 `run_gui.cmd`／`run_python.cmd`，并检查安全软件提示，不要一开始就改算法 |
| PowerShell 不允许运行激活脚本 | 使用解释器完整路径或 CMD 启动器，无需修改执行策略 |
| 找不到图片 | 从项目根目录运行，或使用带引号的完整图片路径 |
| 能启动但牌识别错误 | 记录原图、环境、预测结果和报告；背景、模糊、裁切和旋转均可能影响结果 |

本项目目前只记录了 Windows 环境的验证情况。其他系统上的 Tk、依赖安装和脚本入口需另行验证；CMD 文件不能直接用于 Linux／macOS。

## 八、团队 GitHub 提交流程

项目已忽略 `.venv/`、`output/`、`backups/`、`scratch/`、Python 缓存等目录。提交源码、模板缓存、必要示例与标注、说明文档及团队选择共享的报告。

如果本机已经是团队 Git 仓库，可按下面的流程只提交这两份文档；分支名称可自行调整：

```powershell
git status
git switch -c docs/project-status-and-setup
git add PROJECT_STATUS.md TEAM_SETUP.md
git diff --cached --stat
git diff --cached --name-only
```

确认暂存区只有本次希望提交的文件，再提交：

```powershell
git commit -m "docs: add project status and teammate setup guide"
git push -u origin docs/project-status-and-setup
```

然后在 GitHub 创建 Pull Request，请队友检查并合并。若暂存区原本已有其他文件，先核对清楚，不要直接把它们一起提交。

如果下载的是 ZIP、运行 `git status` 提示不是仓库，先克隆团队真实仓库，再把需要共享的项目文件复制进去，按上面的流程提交。已有源码尚未同步到团队仓库时，还需另外检查并提交源码和资源；上面的 `git add` 只会暂存两份新增文档。

不建议直接 `git add .` 后盲目提交。若 `.venv` 等文件以前已被跟踪，单靠 `.gitignore` 不会把它们移出版本控制，应先与团队确认处理方式。