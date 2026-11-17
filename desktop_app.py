"""Starts the spaceXBot desktop window. This is the file the Windows .exe is built from.
  spacexbot-desktop.exe                    opens the window
  spacexbot-desktop.exe --selftest FILE    opens nothing; checks everything needed is inside the .exe and writes the result to FILE
Run from source instead:  python -m desktop.gui"""
import sys

CHECKS = ('tkinter', 'requests', 'MetaTrader5', 'desktop.config', 'desktop.client', 'desktop.broker', 'desktop.engine', 'desktop.presenter', 'desktop.gui')

def selftest(path):
    """Used by the build to prove the finished .exe contains its parts. Returns 0 (all good) or 1."""
    out, ok = [], True
    for name in CHECKS:
        try: __import__(name); out.append('ok   ' + name)
        except Exception as e: ok = False; out.append('FAIL %s: %s: %s' % (name, e.__class__.__name__, e))
    try:
        import tkinter
        r = tkinter.Tk(); r.withdraw(); r.destroy(); out.append('ok   a window can be created')
    except Exception as e: ok = False; out.append('FAIL window: %s: %s' % (e.__class__.__name__, e))
    out.append('SELFTEST ' + ('PASS' if ok else 'FAIL'))
    try:
        with open(path, 'w', encoding='utf-8') as f: f.write('\n'.join(out) + '\n')
    except OSError: return 1
    return 0 if ok else 1

def alert(text):
    """A plain Windows message box. There is no console in the .exe, so this is the only way to tell the person something."""
    try:
        import ctypes; ctypes.windll.user32.MessageBoxW(0, text, 'spaceXBot desktop', 0x10)
    except Exception: pass

def main(argv=None, window=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) >= 2 and argv[0] == '--selftest': return selftest(argv[1])
    try:
        if window is None:
            from desktop.gui import main as window
        rc = window()
    except Exception as e:
        rc = 1
        try:
            from desktop import config
            import os; os.makedirs(config.home(), exist_ok=True)
            with open(os.path.join(config.home(), 'crash.log'), 'a', encoding='utf-8') as f: f.write('launcher: %s: %s\n' % (e.__class__.__name__, e))
        except Exception: pass
    if rc:
        alert('spaceXBot desktop could not open its window.\n\nDetails were saved in the folder .spacexbot in your user folder (file crash.log). '
              'Send that file to support.')
    return rc

if __name__ == '__main__': sys.exit(main())
