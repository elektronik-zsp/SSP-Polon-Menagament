"""CommandFIRE SSP Serwis Manager 2.5.2: native Win32 panel + system tray, pure stdlib.

No Tkinter, .NET, PowerShell, pywin32 or network packages required.
The panel only controls the already authenticated local launcher / HTTP service.
"""
from __future__ import annotations

import ctypes
from ctypes import wintypes
import os
from pathlib import Path
import sys
import threading
import traceback

sys.path.insert(0, str(Path(__file__).resolve().parent))  # -I removes the script directory
import launcher


WINDOW_CLASS = 'SSPPolonManagerWindow_' + launcher.IDENTITY
WINDOW_TITLE = 'CommandFIRE SSP Serwis — Menedżer programu'
POLL_INTERVAL_MS = 15_000
ICON_PATH = Path(__file__).resolve().parents[1] / 'favicon.ico'


def snapshot():
    """Read-only health snapshot, safe to call in a worker thread."""
    try:
        configured_port = launcher.read_port()
        state = launcher.read_state()
        running = launcher.request_control(state) if state else None
        if running:
            problem = launcher.check_database(state['port'], state['token'], timeout=2)
            return {
                'running': True,
                'port': state['port'],
                'version': str(running.get('version', '?')),
                'editors': running.get('localEditors', 0),
                'database_error': problem,
                'message': 'Baza sieciowa: dostępna' if not problem else 'Baza sieciowa: BRAK DOSTĘPU',
            }
        if not launcher.available(configured_port):
            detail = 'Port jest zajęty przez inną aplikację lub starszą wersję CommandFIRE SSP Serwis.'
        else:
            detail = 'Serwer nie jest uruchomiony.'
        return {'running': False, 'port': configured_port,
                'message': 'Baza: nie sprawdzano (serwer wyłączony)', 'detail': detail}
    except Exception as exc:
        return {'running': False, 'message': 'Nie udało się sprawdzić stanu.', 'detail': str(exc)}


def execute_action(action):
    """Serialize with the CLI and return errors for the GUI."""
    with launcher.launcher_lock():
        if action == 'start':
            launcher.start()
        elif action == 'stop':
            launcher.stop(announce=False)
        else:
            raise ValueError('Nieznane działanie')


def _write_error():
    try:
        launcher.STATE_DIR.mkdir(parents=True, exist_ok=True)
        with (launcher.STATE_DIR / 'manager.log').open('a', encoding='utf-8') as stream:
            stream.write(traceback.format_exc() + '\n')
    except OSError:
        pass


if os.name == 'nt':
    from ctypes import WINFUNCTYPE

    user32 = ctypes.WinDLL('user32', use_last_error=True)
    shell32 = ctypes.WinDLL('shell32', use_last_error=True)
    kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
    gdi32 = ctypes.WinDLL('gdi32', use_last_error=True)
    LRESULT = ctypes.c_ssize_t
    WNDPROC = WINFUNCTYPE(LRESULT, wintypes.HWND, wintypes.UINT,
                          wintypes.WPARAM, wintypes.LPARAM)

    # HCURSOR is not exported by ctypes.wintypes in CPython builds.
    # Win32 HCURSOR and HANDLE have the same underlying pointer representation.
    HCURSOR = getattr(wintypes, 'HCURSOR', wintypes.HANDLE)

    class WNDCLASSW(ctypes.Structure):
        _fields_ = [
            ('style', wintypes.UINT), ('lpfnWndProc', WNDPROC),
            ('cbClsExtra', ctypes.c_int), ('cbWndExtra', ctypes.c_int),
            ('hInstance', wintypes.HINSTANCE), ('hIcon', wintypes.HICON),
            ('hCursor', HCURSOR), ('hbrBackground', wintypes.HBRUSH),
            ('lpszMenuName', wintypes.LPCWSTR), ('lpszClassName', wintypes.LPCWSTR),
        ]

    class POINT(ctypes.Structure):
        _fields_ = [('x', wintypes.LONG), ('y', wintypes.LONG)]

    class MSG(ctypes.Structure):
        _fields_ = [('hwnd', wintypes.HWND), ('message', wintypes.UINT),
                    ('wParam', wintypes.WPARAM), ('lParam', wintypes.LPARAM),
                    ('time', wintypes.DWORD), ('pt', POINT), ('lPrivate', wintypes.DWORD)]

    class GUID(ctypes.Structure):
        _fields_ = [('Data1', wintypes.DWORD), ('Data2', wintypes.WORD),
                    ('Data3', wintypes.WORD), ('Data4', ctypes.c_ubyte * 8)]

    class NOTIFYICONDATAW(ctypes.Structure):
        _fields_ = [
            ('cbSize', wintypes.DWORD), ('hWnd', wintypes.HWND),
            ('uID', wintypes.UINT), ('uFlags', wintypes.UINT),
            ('uCallbackMessage', wintypes.UINT), ('hIcon', wintypes.HICON),
            ('szTip', wintypes.WCHAR * 128),
            ('dwState', wintypes.DWORD), ('dwStateMask', wintypes.DWORD),
            ('szInfo', wintypes.WCHAR * 256), ('uVersion', wintypes.UINT),
            ('szInfoTitle', wintypes.WCHAR * 64), ('dwInfoFlags', wintypes.DWORD),
            ('guidItem', GUID), ('hBalloonIcon', wintypes.HICON),
        ]

    user32.MessageBoxW.argtypes = [wintypes.HWND, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.UINT]
    user32.MessageBoxW.restype = ctypes.c_int
    user32.RegisterClassW.argtypes = [ctypes.POINTER(WNDCLASSW)]
    user32.RegisterClassW.restype = wintypes.ATOM
    user32.CreateWindowExW.argtypes = [wintypes.DWORD, wintypes.LPCWSTR, wintypes.LPCWSTR,
        wintypes.DWORD, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
        wintypes.HWND, wintypes.HMENU, wintypes.HINSTANCE, ctypes.c_void_p]
    user32.CreateWindowExW.restype = wintypes.HWND
    user32.DefWindowProcW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
    user32.DefWindowProcW.restype = LRESULT
    user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
    user32.SetForegroundWindow.argtypes = [wintypes.HWND]
    user32.SetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPCWSTR]
    user32.EnableWindow.argtypes = [wintypes.HWND, wintypes.BOOL]
    user32.SendMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
    user32.SendMessageW.restype = LRESULT
    user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
    user32.PostMessageW.restype = wintypes.BOOL
    user32.LoadIconW.argtypes = [wintypes.HINSTANCE, wintypes.LPCWSTR]
    user32.LoadIconW.restype = wintypes.HICON
    user32.LoadImageW.argtypes = [wintypes.HINSTANCE, wintypes.LPCWSTR, wintypes.UINT,
                                  ctypes.c_int, ctypes.c_int, wintypes.UINT]
    user32.LoadImageW.restype = wintypes.HICON
    user32.DestroyIcon.argtypes = [wintypes.HICON]
    user32.DestroyIcon.restype = wintypes.BOOL
    user32.LoadCursorW.argtypes = [wintypes.HINSTANCE, wintypes.LPCWSTR]
    user32.LoadCursorW.restype = HCURSOR
    user32.GetSysColorBrush.argtypes = [ctypes.c_int]
    user32.GetSysColorBrush.restype = wintypes.HBRUSH
    user32.SetTimer.argtypes = [wintypes.HWND, ctypes.c_size_t, wintypes.UINT, ctypes.c_void_p]
    user32.SetTimer.restype = ctypes.c_size_t
    user32.KillTimer.argtypes = [wintypes.HWND, ctypes.c_size_t]
    user32.FindWindowW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR]
    user32.FindWindowW.restype = wintypes.HWND
    user32.RegisterWindowMessageW.argtypes = [wintypes.LPCWSTR]
    user32.RegisterWindowMessageW.restype = wintypes.UINT
    user32.GetMessageW.argtypes = [ctypes.POINTER(MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT]
    user32.GetMessageW.restype = ctypes.c_int
    user32.TranslateMessage.argtypes = [ctypes.POINTER(MSG)]
    user32.DispatchMessageW.argtypes = [ctypes.POINTER(MSG)]
    user32.CreatePopupMenu.restype = wintypes.HMENU
    user32.AppendMenuW.argtypes = [wintypes.HMENU, wintypes.UINT, ctypes.c_size_t, wintypes.LPCWSTR]
    user32.TrackPopupMenu.argtypes = [wintypes.HMENU, wintypes.UINT, ctypes.c_int, ctypes.c_int,
                                      ctypes.c_int, wintypes.HWND, ctypes.c_void_p]
    user32.TrackPopupMenu.restype = wintypes.UINT
    user32.DestroyMenu.argtypes = [wintypes.HMENU]
    user32.GetCursorPos.argtypes = [ctypes.POINTER(POINT)]
    user32.DestroyWindow.argtypes = [wintypes.HWND]
    shell32.Shell_NotifyIconW.argtypes = [wintypes.DWORD, ctypes.POINTER(NOTIFYICONDATAW)]
    shell32.Shell_NotifyIconW.restype = wintypes.BOOL
    kernel32.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
    kernel32.CreateMutexW.restype = wintypes.HANDLE
    kernel32.GetLastError.restype = wintypes.DWORD
    kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
    kernel32.GetModuleHandleW.restype = wintypes.HMODULE
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    gdi32.GetStockObject.argtypes = [ctypes.c_int]
    gdi32.GetStockObject.restype = wintypes.HGDIOBJ

    WS_OVERLAPPEDWINDOW = 0x00CF0000
    WS_VISIBLE = 0x10000000
    WS_CHILD = 0x40000000
    WS_TABSTOP = 0x00010000
    BS_PUSHBUTTON = 0
    WS_EX_APPWINDOW = 0x00040000
    CW_USEDEFAULT = -2147483648
    SW_SHOW = 5
    SW_HIDE = 0
    SW_RESTORE = 9
    WM_DESTROY = 0x0002
    WM_CLOSE = 0x0010
    WM_SIZE = 0x0005
    WM_COMMAND = 0x0111
    WM_TIMER = 0x0113
    WM_SETFONT = 0x0030
    WM_SETICON = 0x0080
    IMAGE_ICON = 1
    ICON_SMALL = 0
    ICON_BIG = 1
    LR_LOADFROMFILE = 0x0010
    WM_NULL = 0
    WM_LBUTTONUP = 0x0202
    WM_LBUTTONDBLCLK = 0x0203
    WM_RBUTTONUP = 0x0205
    SIZE_MINIMIZED = 1
    WM_APP = 0x8000
    MSG_TRAY = WM_APP + 1
    MSG_WORKER = WM_APP + 2
    MSG_SHOW = WM_APP + 3
    NIF_MESSAGE = 0x01
    NIF_ICON = 0x02
    NIF_TIP = 0x04
    NIM_ADD = 0
    NIM_MODIFY = 1
    NIM_DELETE = 2
    TPM_RIGHTBUTTON = 0x0002
    TPM_RETURNCMD = 0x0100
    MF_STRING = 0
    MF_SEPARATOR = 0x800
    MB_OK = 0
    MB_ICONWARNING = 0x30
    MB_YESNO = 4
    ID_START = 101
    ID_STOP = 102
    ID_BROWSER = 103
    ID_TRAY = 104
    ID_EXIT = 105
    TIMER_STATUS = 1


    def _resource(number):
        return ctypes.cast(ctypes.c_void_p(number), wintypes.LPCWSTR)


    def load_app_icon(size):
        # Portable location, independent from the VBS working directory.
        # Loaded as an owned HICON, which must be destroyed on shutdown.
        if ICON_PATH.is_file():
            return user32.LoadImageW(None, str(ICON_PATH), IMAGE_ICON, size, size, LR_LOADFROMFILE)
        return None


    class Manager:
        def __init__(self):
            self.hwnd = None
            self.controls = {}
            self.tray = None
            self.tray_added = False
            self.busy = False
            self.checking = False
            self.pending = []
            self.pending_lock = threading.Lock()
            self.callback = WNDPROC(self.wndproc)  # Win32 must keep function pointer alive
            self.instance = kernel32.GetModuleHandleW(None)
            self.taskbar_created = user32.RegisterWindowMessageW('TaskbarCreated')
            self.icon_big_owned = load_app_icon(32)
            self.icon_small_owned = load_app_icon(16)
            self.icon_big = self.icon_big_owned or user32.LoadIconW(None, _resource(32512))
            self.icon_small = self.icon_small_owned or self.icon_big

        def log(self, title, message, warning=False):
            user32.MessageBoxW(self.hwnd, str(message), title, MB_OK | (MB_ICONWARNING if warning else 0x40))

        def make_child(self, control_class, text, ident, x, y, w, h, button=False):
            control = user32.CreateWindowExW(0, control_class, text,
                WS_VISIBLE | WS_CHILD | (WS_TABSTOP if button else 0) | (BS_PUSHBUTTON if button else 0),
                x, y, w, h, self.hwnd, ctypes.c_void_p(ident) if ident else None,
                self.instance, None)
            if not control:
                raise ctypes.WinError(ctypes.get_last_error())
            self.controls[ident] = control
            font = gdi32.GetStockObject(17)  # DEFAULT_GUI_FONT
            user32.SendMessageW(control, WM_SETFONT, font, 1)
            return control

        def make_window(self):
            wc = WNDCLASSW()
            wc.lpfnWndProc = self.callback
            wc.hInstance = self.instance
            wc.hIcon = self.icon_big
            wc.hCursor = user32.LoadCursorW(None, _resource(32512))
            wc.hbrBackground = user32.GetSysColorBrush(15)
            wc.lpszClassName = WINDOW_CLASS
            if not user32.RegisterClassW(ctypes.byref(wc)):
                err = ctypes.get_last_error()
                if err != 1410:  # Class already exists within this process
                    raise ctypes.WinError(err)
            self.hwnd = user32.CreateWindowExW(WS_EX_APPWINDOW, WINDOW_CLASS, WINDOW_TITLE,
                WS_OVERLAPPEDWINDOW, CW_USEDEFAULT, CW_USEDEFAULT, 510, 338,
                None, None, self.instance, None)
            if not self.hwnd:
                raise ctypes.WinError(ctypes.get_last_error())
            # Set both title-bar / Alt+Tab icon and small shell/tray icon.
            user32.SendMessageW(self.hwnd, WM_SETICON, ICON_BIG, self.icon_big)
            user32.SendMessageW(self.hwnd, WM_SETICON, ICON_SMALL, self.icon_small)
            self.make_child('STATIC', 'CommandFIRE SSP Serwis — panel sterowania', 1, 20, 17, 445, 23)
            self.make_child('STATIC', 'Stan: sprawdzanie...', 2, 20, 56, 455, 27)
            self.make_child('STATIC', 'Baza: sprawdzanie...', 3, 20, 89, 460, 24)
            self.make_child('STATIC', 'Uruchomiony lokalnie; wspólna baza pozostaje na dysku sieciowym.', 4,
                            20, 122, 465, 23)
            self.make_child('BUTTON', 'Uruchom', ID_START, 20, 162, 143, 39, True)
            self.make_child('BUTTON', 'Zatrzymaj', ID_STOP, 176, 162, 143, 39, True)
            self.make_child('BUTTON', 'Otwórz panel', ID_BROWSER, 332, 162, 143, 39, True)
            self.make_child('BUTTON', 'Minimalizuj do tray', ID_TRAY, 20, 216, 455, 33, True)
            self.make_child('STATIC', 'X ukrywa menedżer w tray — serwer nadal działa. Zatrzymaj go przyciskiem.',
                            5, 20, 262, 466, 25)
            self.show_tray()
            user32.SetTimer(self.hwnd, TIMER_STATUS, POLL_INTERVAL_MS, None)
            # A VBS launcher may request SW_HIDE through STARTUPINFO. Windows
            # ignores the first ShowWindow(nCmdShow) in that case, honoring
            # STARTUPINFO instead. A second explicit call opens the panel.
            user32.ShowWindow(self.hwnd, SW_SHOW)
            user32.ShowWindow(self.hwnd, SW_RESTORE)
            user32.SetForegroundWindow(self.hwnd)
            self.refresh()

        def show_tray(self):
            nid = NOTIFYICONDATAW()
            nid.cbSize = ctypes.sizeof(nid)
            nid.hWnd = self.hwnd
            nid.uID = 1
            nid.uFlags = NIF_MESSAGE | NIF_ICON | NIF_TIP
            nid.uCallbackMessage = MSG_TRAY
            nid.hIcon = self.icon_small
            nid.szTip = 'CommandFIRE SSP Serwis — menedżer'
            self.tray = nid
            self.tray_added = bool(shell32.Shell_NotifyIconW(NIM_ADD, ctypes.byref(nid)))
            if not self.tray_added:
                user32.SetWindowTextW(self.controls[5],
                   'Nie można utworzyć ikony tray. Okno będzie minimalizowane na pasek zadań.')

        def update_tray(self, tip):
            if self.tray_added and self.tray:
                self.tray.szTip = tip[:127]
                shell32.Shell_NotifyIconW(NIM_MODIFY, ctypes.byref(self.tray))

        def restore(self):
            user32.ShowWindow(self.hwnd, SW_RESTORE)
            user32.ShowWindow(self.hwnd, SW_SHOW)
            user32.SetForegroundWindow(self.hwnd)

        def hide(self):
            if self.tray_added:
                user32.ShowWindow(self.hwnd, SW_HIDE)
            else:
                # Tray may be disabled by policy or unavailable after an Explorer crash.
                user32.ShowWindow(self.hwnd, 6)  # SW_MINIMIZE, recoverable from taskbar

        def queue_message(self, *value):
            with self.pending_lock:
                self.pending.append(value)
            if self.hwnd:
                user32.PostMessageW(self.hwnd, MSG_WORKER, 0, 0)

        def refresh(self):
            if self.checking:
                return
            self.checking = True

            def work():
                result = snapshot()
                self.queue_message('status', result)
            threading.Thread(target=work, daemon=True, name='ssp-status').start()

        def perform(self, action):
            if self.busy:
                return
            self.busy = True
            for ident in (ID_START, ID_STOP):
                user32.EnableWindow(self.controls[ident], False)
            user32.SetWindowTextW(self.controls[2],
                                  'Stan: ' + ('uruchamianie...' if action == 'start' else 'zatrzymywanie...'))
            def work():
                try:
                    execute_action(action)
                    self.queue_message('operation', action, None)
                except Exception as exc:
                    self.queue_message('operation', action, str(exc))
            threading.Thread(target=work, daemon=True, name='ssp-' + action).start()

        def apply_status(self, status):
            if self.busy:
                return
            online = status.get('running', False)
            message = ('Stan: URUCHOMIONY' if online else 'Stan: ZATRZYMANY')
            if online:
                message += '   |   ' + str(status['port']) + '   |   ' + status['version']
                if status.get('editors'):
                    message += f'   |   Edycje: {status["editors"]}'
            user32.SetWindowTextW(self.controls[2], message)
            user32.SetWindowTextW(self.controls[3], status.get('message', 'Brak danych'))
            if status.get('detail'):
                user32.SetWindowTextW(self.controls[4], status['detail'][:95])
            elif status.get('database_error'):
                user32.SetWindowTextW(self.controls[4],
                   ('Błąd: ' + str(status['database_error']))[:95])
            else:
                user32.SetWindowTextW(self.controls[4],
                    'Aplikacja działa lokalnie. Edycja rekordów jest blokowana we wspólnej bazie.')
            user32.EnableWindow(self.controls[ID_START], not online)
            user32.EnableWindow(self.controls[ID_STOP], online)
            user32.EnableWindow(self.controls[ID_BROWSER], online)
            self.update_tray('CommandFIRE SSP Serwis — ' + ('działa' if online else 'zatrzymany') +
                             (' / błąd bazy' if status.get('database_error') else ''))

        def process_queue(self):
            with self.pending_lock:
                jobs = self.pending[:]
                self.pending.clear()
            for kind, *items in jobs:
                if kind == 'status':
                    self.checking = False
                    self.apply_status(items[0])
                elif kind == 'operation':
                    action, err = items
                    self.busy = False
                    if err:
                        self.log('Nie udało się wykonać polecenia', err, warning=True)
                    self.refresh()

        def open_panel(self):
            state = launcher.read_state()
            if state and launcher.request_control(state):
                launcher.browser(state['port'])
            else:
                self.log('CommandFIRE SSP Serwis', 'Serwer nie jest uruchomiony. Kliknij Uruchom.', True)

        def tray_menu(self):
            menu = user32.CreatePopupMenu()
            if not menu:
                return
            user32.AppendMenuW(menu, MF_STRING, MSG_SHOW, 'Pokaż okno')
            user32.AppendMenuW(menu, MF_STRING, ID_BROWSER, 'Otwórz panel WWW')
            user32.AppendMenuW(menu, MF_SEPARATOR, 0, None)
            user32.AppendMenuW(menu, MF_STRING, ID_START, 'Uruchom serwer')
            user32.AppendMenuW(menu, MF_STRING, ID_STOP, 'Zatrzymaj serwer')
            user32.AppendMenuW(menu, MF_SEPARATOR, 0, None)
            user32.AppendMenuW(menu, MF_STRING, ID_EXIT, 'Zamknij menedżer (serwer bez zmian)')
            point = POINT()
            user32.GetCursorPos(ctypes.byref(point))
            user32.SetForegroundWindow(self.hwnd)
            command = user32.TrackPopupMenu(menu, TPM_RIGHTBUTTON | TPM_RETURNCMD,
                                            point.x, point.y, 0, self.hwnd, None)
            user32.DestroyMenu(menu)
            user32.PostMessageW(self.hwnd, WM_NULL, 0, 0)
            if command:
                self.command(command)

        def command(self, ident):
            if ident == MSG_SHOW:
                self.restore()
            elif ident == ID_START:
                self.perform('start')
            elif ident == ID_STOP:
                self.perform('stop')
            elif ident == ID_BROWSER:
                self.open_panel()
            elif ident == ID_TRAY:
                self.hide()
            elif ident == ID_EXIT:
                if self.busy:
                    self.log('CommandFIRE SSP Serwis', 'Najpierw zakończ uruchamianie lub zatrzymywanie.', True)
                    return
                state = launcher.read_state()
                if state and launcher.request_control(state):
                    result = user32.MessageBoxW(self.hwnd,
                       'Serwer nadal działa w tle. Zamknięcie menedżera go nie zatrzyma.\n\n'
                       'Czy zamknąć tylko okno menedżera?', WINDOW_TITLE, MB_YESNO | MB_ICONWARNING)
                    if result != 6:
                        return
                user32.DestroyWindow(self.hwnd)

        def wndproc(self, hwnd, msg, wparam, lparam):
            try:
                if msg == WM_COMMAND:
                    self.command(int(wparam) & 0xffff)
                    return 0
                if msg == WM_CLOSE:
                    self.hide()
                    return 0
                if msg == WM_SIZE and int(wparam) == SIZE_MINIMIZED:
                    if self.tray_added:
                        user32.ShowWindow(hwnd, SW_HIDE)
                    return 0
                if msg == MSG_TRAY:
                    if int(lparam) in (WM_LBUTTONUP, WM_LBUTTONDBLCLK):
                        self.restore()
                    elif int(lparam) == WM_RBUTTONUP:
                        self.tray_menu()
                    return 0
                if msg == MSG_SHOW:
                    self.restore()
                    return 0
                if msg == MSG_WORKER:
                    self.process_queue()
                    return 0
                if msg == WM_TIMER and int(wparam) == TIMER_STATUS:
                    self.refresh()
                    return 0
                if msg == self.taskbar_created:
                    self.show_tray()
                    return 0
                if msg == WM_DESTROY:
                    user32.KillTimer(hwnd, TIMER_STATUS)
                    if self.tray_added:
                        shell32.Shell_NotifyIconW(NIM_DELETE, ctypes.byref(self.tray))
                        self.tray_added = False
                    for handle in (self.icon_big_owned, self.icon_small_owned):
                        if handle:
                            user32.DestroyIcon(handle)
                    user32.PostQuitMessage(0)
                    return 0
            except Exception:
                _write_error()
            return user32.DefWindowProcW(hwnd, msg, wparam, lparam)

        def run(self):
            self.make_window()
            message = MSG()
            while True:
                outcome = user32.GetMessageW(ctypes.byref(message), None, 0, 0)
                if outcome == 0:
                    break
                if outcome < 0:
                    raise ctypes.WinError(ctypes.get_last_error())
                user32.TranslateMessage(ctypes.byref(message))
                user32.DispatchMessageW(ctypes.byref(message))


def main():
    if os.name != 'nt':
        print('Panel zarządzania jest przeznaczony dla systemu Windows 10/11.')
        raise SystemExit(2)
    mutex = kernel32.CreateMutexW(None, False, 'Local\\SSPPolonManager_' + launcher.IDENTITY)
    if not mutex:
        raise ctypes.WinError(ctypes.get_last_error())
    duplicate = ctypes.get_last_error() == 183  # ERROR_ALREADY_EXISTS
    try:
        if duplicate:
            old = user32.FindWindowW(WINDOW_CLASS, None)
            if old:
                user32.PostMessageW(old, MSG_SHOW, 0, 0)
            else:
                user32.MessageBoxW(None,
                   'Menedżer już się uruchamia. Odszukaj jego ikonę w zasobniku systemowym.',
                   WINDOW_TITLE, 0x40)
            return
        manager = Manager()
        manager.run()
    except Exception as exc:
        _write_error()
        if not os.environ.get('SSP_MANAGER_BOOTSTRAP'):
            user32.MessageBoxW(None, 'Nie można uruchomić menedżera:\n' + str(exc) +
                '\n\nDziennik: ' + str(launcher.STATE_DIR / 'manager.log'), WINDOW_TITLE, 0x10)
        raise
    finally:
        kernel32.CloseHandle(mutex)


if __name__ == '__main__':
    main()
