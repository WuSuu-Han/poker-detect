"""Tk GUI. All widget operations stay on the main thread."""
import queue
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from PIL import Image, ImageTk
from cardlib import ranksuit
from cardlib.pipeline import recognize, export


class App:
    def __init__(self, root):
        self.root, self.events = root, queue.Queue()
        self.results, self.photos = [], []
        self.busy = False
        root.title('扑克牌点数与花色识别')
        root.geometry('1160x760')
        toolbar = ttk.Frame(root); toolbar.pack(fill='x', padx=8, pady=8)
        self.buttons = []
        for title, command in [('选择图片', self.open_images), ('选择文件夹', self.open_folder),
                               ('导出结果', self.save)]:
            b = ttk.Button(toolbar, text=title, command=command)
            b.pack(side='left', padx=4); self.buttons.append(b)
        self.status = tk.StringVar(value='正在预加载模板…')
        ttk.Label(toolbar, textvariable=self.status).pack(side='left', padx=12)
        ttk.Label(root, text='分数为启发式匹配分数，并非正确概率；黄色 CHECK 表示需要人工核对。').pack(anchor='w', padx=12)
        pane = ttk.Panedwindow(root, orient='horizontal'); pane.pack(fill='both', expand=True)
        left = ttk.Frame(pane); right = ttk.Frame(pane)
        pane.add(left, weight=3); pane.add(right, weight=2)
        self.files = ttk.Combobox(left, state='readonly'); self.files.pack(fill='x', padx=8, pady=6)
        self.files.bind('<<ComboboxSelected>>', lambda e: self.show(self.files.current()))
        self.preview = ttk.Label(left, anchor='center'); self.preview.pack(fill='both', expand=True)
        canvas = tk.Canvas(right, highlightthickness=0)
        scroll = ttk.Scrollbar(right, orient='vertical', command=canvas.yview)
        scroll.pack(side='right', fill='y'); canvas.pack(side='left', fill='both', expand=True)
        canvas.configure(yscrollcommand=scroll.set)
        self.card_frame = ttk.Frame(canvas)
        canvas.create_window((0,0), window=self.card_frame, anchor='nw')
        self.card_frame.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        self.set_busy(True)
        threading.Thread(target=self.warmup, daemon=True).start()
        root.after(100, self.poll)

    def set_busy(self, value):
        self.busy = value
        for b in self.buttons: b.configure(state='disabled' if value else 'normal')

    def warmup(self):
        try:
            if not ranksuit.rank_templates() or not ranksuit.suit_templates():
                raise RuntimeError('没有可用模板；请恢复 cardlib/templates.npz 或安装所需字体。')
            self.events.put(('ready', None))
        except Exception as e: self.events.put(('fatal', str(e)))

    def open_images(self):
        paths = filedialog.askopenfilenames(filetypes=[('图片','*.jpg *.jpeg *.png *.bmp *.tif *.tiff'), ('全部','*.*')])
        if paths: self.start(paths)

    def open_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            paths = sorted(p for p in Path(folder).iterdir() if p.suffix.lower() in {'.jpg','.jpeg','.png','.bmp','.tif','.tiff'})
            if paths: self.start(paths)
            else: messagebox.showinfo('提示','文件夹内没有支持的图片。')

    def start(self, paths):
        if self.busy: return
        self.set_busy(True); self.results = []; self.files.set('')
        self.status.set('正在识别…')
        threading.Thread(target=self.work, args=(list(paths),), daemon=True).start()

    def work(self, paths):
        for path in paths:
            try: self.events.put(('result', recognize(path)))
            except Exception as e: self.events.put(('error', '%s: %s' % (path,e)))
        self.events.put(('done',None))

    def poll(self):
        try:
            while True:
                kind, value = self.events.get_nowait()
                if kind == 'result':
                    self.results.append(value)
                    self.files['values'] = [Path(r['path']).name for r in self.results]
                    self.files.current(len(self.results)-1); self.show(len(self.results)-1)
                elif kind in ('ready','done'):
                    self.set_busy(False)
                    self.status.set('就绪' if kind=='ready' else '已处理 %d 张图片' % len(self.results))
                elif kind in ('error','fatal'):
                    if kind=='fatal': self.status.set('模板加载失败')
                    messagebox.showerror('处理失败', value)
        except queue.Empty: pass
        self.root.after(100,self.poll)

    def photo(self, bgr, size):
        im = Image.fromarray(bgr[:,:,::-1]); im.thumbnail(size)
        p = ImageTk.PhotoImage(im); self.photos.append(p); return p

    def show(self, index):
        if index < 0 or index >= len(self.results): return
        self.photos.clear()
        for w in self.card_frame.winfo_children(): w.destroy()
        result = self.results[index]
        self.preview.configure(image=self.photo(result['annotated'],(660,580)))
        if not result['cards']: ttk.Label(self.card_frame,text='未检测到牌，请检查背景、光照或拍摄距离。').pack()
        names = {'s':'黑桃','h':'红桃','c':'梅花','d':'方块'}
        for i,c in enumerate(result['cards']):
            row = ttk.Frame(self.card_frame); row.pack(fill='x',pady=6)
            ttk.Label(row,image=self.photo(c.oriented,(115,170))).pack(side='left')
            text = '#%d  %s %s\n匹配分数 %.3f\n%s' % (i+1,c.rank or '?',names.get(c.suit,'?'),c.confidence,'已接受' if c.accepted else '需要核对 CHECK')
            tk.Label(row,text=text,justify='left',fg='darkgreen' if c.accepted else '#ad6500').pack(side='left',padx=8)

    def save(self):
        if not self.results: return messagebox.showinfo('提示','请先识别图片。')
        folder = filedialog.askdirectory()
        if folder:
            try:
                export(self.results,folder); self.status.set('已导出 CSV、JSON、标注图和摆正牌图')
            except Exception as e: messagebox.showerror('导出失败',str(e))


def main():
    root = tk.Tk(); App(root); root.mainloop()

if __name__ == '__main__': main()
