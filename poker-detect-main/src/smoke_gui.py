"""GUI event-loop integration test, run in a temporary project copy."""
import time
from pathlib import Path
import tempfile
import tkinter as tk
from gui import App
from cardlib.pipeline import export

root=tk.Tk(); root.withdraw(); app=App(root)
def wait_done():
    deadline=time.monotonic()+30
    while app.busy and time.monotonic()<deadline:
        root.update(); time.sleep(.01)
    assert not app.busy,'GUI worker did not finish'
wait_done()
app.start([Path(__file__).resolve().parents[1]/'data/cards_sample.jpg'])
wait_done()
assert len(app.results)==1 and len(app.results[0]['cards'])==8
assert len(app.card_frame.winfo_children())==8
with tempfile.TemporaryDirectory() as folder:
    export(app.results,folder)
    assert len(list(Path(folder).glob('*_card_*.png')))==8
    assert (Path(folder)/'results.json').is_file()
root.destroy()
print('GUI warmup, background recognition, card widgets and export: PASS')
