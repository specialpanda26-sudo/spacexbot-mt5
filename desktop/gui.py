"""The spaceXBot desktop window (Windows). Run:  python -m desktop.gui     (the .exe starts here too).
This file is deliberately thin: it only draws boxes and forwards clicks. All the logic is in presenter.py, which is tested without a screen."""
import os, sys, time, traceback
from . import config
from .presenter import Presenter

COLOURS = {'ok': '#0a7d33', 'warn': '#a15c00', 'bad': '#c0262d', 'idle': '#555555'}
MAX_LOG_LINES = 500

def crash_log(text):
    """Last-resort record next to the settings, so a crash can be reported."""
    try:
        os.makedirs(config.home(), exist_ok=True)
        with open(os.path.join(config.home(), 'crash.log'), 'a', encoding='utf-8') as f: f.write('%s\n%s\n' % (time.strftime('%Y-%m-%d %H:%M:%S'), text))
    except OSError: pass

class Window:
    """Implements the 'ui' the Presenter talks to."""
    def __init__(self):
        import tkinter as tk
        from tkinter import ttk, messagebox
        self.tk, self.ttk, self.mb = tk, ttk, messagebox
        self.root = tk.Tk(); self.root.title('spaceXBot desktop'); self.root.minsize(620, 520)
        try:                                                                  # sharper text on high-resolution screens
            import ctypes; ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception: pass
        self.v = {'server_url': tk.StringVar(), 'key': tk.StringVar(), 'suffix': tk.StringVar(), 'allow_live': tk.BooleanVar(value=False)}
        self.show_key = tk.BooleanVar(value=False)
        f = ttk.Frame(self.root, padding=12); f.pack(fill='both', expand=True); f.columnconfigure(1, weight=1); f.rowconfigure(8, weight=1)
        ttk.Label(f, text='Server address').grid(row=0, column=0, sticky='w', pady=3)
        self.e_url = ttk.Entry(f, textvariable=self.v['server_url']); self.e_url.grid(row=0, column=1, columnspan=2, sticky='ew')
        ttk.Label(f, text='https://your-name.onrender.com (copy it from your browser)', foreground='#666').grid(row=1, column=1, columnspan=2, sticky='w')
        ttk.Label(f, text='Personal key').grid(row=2, column=0, sticky='w', pady=3)
        self.e_key = ttk.Entry(f, textvariable=self.v['key'], show='*'); self.e_key.grid(row=2, column=1, sticky='ew')
        self.c_show = ttk.Checkbutton(f, text='Show', variable=self.show_key, command=self._toggle_key); self.c_show.grid(row=2, column=2, padx=(6, 0))
        ttk.Label(f, text='Symbol suffix').grid(row=3, column=0, sticky='w', pady=3)
        self.e_suf = ttk.Entry(f, textvariable=self.v['suffix'], width=12); self.e_suf.grid(row=3, column=1, sticky='w')
        ttk.Label(f, text='Usually empty. Some brokers add letters, e.g. .r or m', foreground='#666').grid(row=4, column=1, columnspan=2, sticky='w')
        self.c_live = tk.Checkbutton(f, text='Allow REAL-money accounts (leave off to stay demo-only)', variable=self.v['allow_live'], fg='#c0262d')
        self.c_live.grid(row=5, column=0, columnspan=3, sticky='w', pady=(6, 2))
        self.btn = ttk.Button(f, text='Start', command=lambda: self._safe(self.p.toggle)); self.btn.grid(row=6, column=0, columnspan=3, sticky='ew', pady=8, ipady=6)
        self.status = tk.Label(f, text='', anchor='w', justify='left', font=('Segoe UI', 11, 'bold'), wraplength=580); self.status.grid(row=7, column=0, columnspan=3, sticky='ew')
        box = ttk.Frame(f); box.grid(row=8, column=0, columnspan=3, sticky='nsew', pady=(6, 0)); box.rowconfigure(1, weight=1); box.columnconfigure(0, weight=1)
        self.advice = tk.Label(box, text='', anchor='w', justify='left', wraplength=580, fg='#333'); self.advice.grid(row=0, column=0, columnspan=2, sticky='ew', pady=(0, 4))
        self.log = tk.Text(box, height=12, wrap='word', state='disabled', font=('Consolas', 9)); self.log.grid(row=1, column=0, sticky='nsew')
        sb = ttk.Scrollbar(box, command=self.log.yview); sb.grid(row=1, column=1, sticky='ns'); self.log.configure(yscrollcommand=sb.set)
        ttk.Label(f, text='Not financial advice. Nothing here is proven profitable. You can lose money. Keep MetaTrader 5 open.', foreground='#666').grid(row=9, column=0, columnspan=3, sticky='w', pady=(6, 0))
        self.p = Presenter(self)
        self.root.report_callback_exception = self._on_error                  # a bug in a click must not kill the window
        self.root.protocol('WM_DELETE_WINDOW', self._close)
        self.p.load(); self._loop()

    # ---- the interface the Presenter uses ----
    def get_form(self): return {k: v.get() for k, v in self.v.items()}
    def set_form(self, d):
        for k, v in d.items():
            if k in self.v: self.v[k].set(v)
    def set_status(self, text, colour): self.status.configure(text=text, fg=COLOURS.get(colour, '#555555'))
    def set_advice(self, text): self.advice.configure(text=text)
    def set_button(self, text, enabled): self.btn.configure(text=text, state='normal' if enabled else 'disabled')
    def set_fields_enabled(self, on):
        for w in (self.e_url, self.e_key, self.e_suf): w.configure(state='normal' if on else 'disabled')
        self.c_live.configure(state='normal' if on else 'disabled')
    def confirm(self, text): return bool(self.mb.askyesno('Real money', text, icon='warning', default='no'))
    def append_log(self, line):
        self.log.configure(state='normal'); self.log.insert('end', line + '\n')
        n = int(self.log.index('end-1c').split('.')[0])
        if n > MAX_LOG_LINES: self.log.delete('1.0', '%d.0' % (n - MAX_LOG_LINES))
        self.log.see('end'); self.log.configure(state='disabled')

    # ---- plumbing ----
    def _toggle_key(self): self.e_key.configure(show='' if self.show_key.get() else '*')
    def _safe(self, fn):
        try: fn()
        except Exception: self._on_error(*sys.exc_info())
    def _on_error(self, exc, val, tb):
        text = ''.join(traceback.format_exception(exc, val, tb)); crash_log(text)
        try: self.append_log('Internal problem (the window is still running): %s: %s' % (exc.__name__, val))
        except Exception: pass
    def _loop(self):
        self._safe(self.p.pump); self.root.after(300, self._loop)
    def _close(self):
        try: self.p.close()
        except Exception: pass
        self.root.destroy()
    def run(self): self.root.mainloop()

def main():
    try: Window().run(); return 0
    except Exception:
        crash_log(traceback.format_exc()); return 1

if __name__ == '__main__': sys.exit(main())
