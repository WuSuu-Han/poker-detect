"""Create ground truth by clicking four corners clockwise and entering rank+suit."""
import argparse
import json
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, simpledialog, messagebox
from PIL import Image, ImageTk, ImageOps


def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--output',default='data/real_photos.json')
    args=parser.parse_args(); output=Path(args.output).resolve()
    data=json.loads(output.read_text(encoding='utf-8')) if output.exists() else dict(schema_version=1,images=[])
    root=tk.Tk(); root.title('独立标注：四个角按顺时针点击，右键撤销；完成后保存本图')
    state=dict(points=[],cards=[],path=None,scale=1.,photo=None)
    canvas=tk.Canvas(root,width=1100,height=700,bg='#444'); canvas.pack()
    def open_image():
        p=filedialog.askopenfilename()
        if not p: return
        im=ImageOps.exif_transpose(Image.open(p)).convert('RGB')
        original=im.size; im.thumbnail((1100,700)); state.update(path=Path(p).resolve(),scale=original[0]/im.width,points=[],cards=[])
        state['photo']=ImageTk.PhotoImage(im); canvas.delete('all'); canvas.create_image(0,0,anchor='nw',image=state['photo'])
    def click(e):
        if not state['path']: return
        points=state['points']; points.append((e.x,e.y)); canvas.create_oval(e.x-3,e.y-3,e.x+3,e.y+3,fill='red',tags='point')
        if len(points)==4:
            label=simpledialog.askstring('牌面标签','输入点数和花色，如 10h、As、Qc、7d（s黑桃 h红桃 d方块 c梅花）')
            if label:
                rank,suit=label[:-1].upper(),label[-1].lower()
                if rank in ['A','2','3','4','5','6','7','8','9','10','J','Q','K'] and suit in 'shdc':
                    state['cards'].append(dict(rank=rank,suit=suit,quad=[[x*state['scale'],y*state['scale']] for x,y in points]))
                    canvas.create_polygon(*[v for p in points for v in p],outline='lime',fill='',width=2)
                    canvas.create_text(*points[0],text=label,fill='yellow',anchor='sw')
                else: messagebox.showerror('错误','标签格式错误，请重新标注这张牌。')
            points.clear(); canvas.delete('point')
    def undo(e=None):
        state['points'].clear(); canvas.delete('point')
    def save():
        if not state['path']: return
        import os
        file=os.path.relpath(state['path'],output.parent).replace('\\','/')
        old=next((i for i in data['images'] if i['file']==file),None)
        if old and not messagebox.askyesno('覆盖','该图片已有标注，是否覆盖？'): return
        item=dict(file=file,photo_id=file,source='real',split='test',cards=state['cards'].copy())
        data['images']=[i for i in data['images'] if i['file']!=file]+[item]
        output.parent.mkdir(parents=True,exist_ok=True)
        output.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
        messagebox.showinfo('已保存','本图 %d 张牌。下一张图片请点击打开。'%len(item['cards']))
    canvas.bind('<Button-1>',click); canvas.bind('<Button-3>',undo)
    for title,cmd in [('打开图片',open_image),('撤销当前四点',undo),('保存本图',save)]: tk.Button(root,text=title,command=cmd).pack(side='left')
    root.mainloop()

if __name__=='__main__': main()
