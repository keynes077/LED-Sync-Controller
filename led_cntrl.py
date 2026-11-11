import sys, os, json, time, math, threading
from pathlib import Path
from collections import deque

from PySide6.QtCore import Qt, QTimer, Signal, QObject, QThread, QSize
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QBrush, QLinearGradient, QIcon, QAction, QPixmap
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QFrame, QLabel, QPushButton, QVBoxLayout,
    QHBoxLayout, QGridLayout, QStackedWidget, QComboBox, QSlider, QSpinBox,
    QCheckBox, QLineEdit, QColorDialog, QMessageBox, QProgressBar, QGroupBox,
    QFormLayout, QScrollArea, QSystemTrayIcon, QMenu
)

APP_NAME = "LED CNTRL"
APP_DIR = Path(os.getenv("APPDATA", str(Path.home()))) / "LED CNTRL"
OLD_APP_DIR = Path(os.getenv("APPDATA", str(Path.home()))) / "LED CNTRL"
CONFIG_PATH = APP_DIR / "settings.json"
DEFAULT_CONFIG = {
    "port": "", "baud": 115200, "led_count": 42, "pin": 2,
    "top": 15, "right": 8, "bottom": 11, "left": 8, "start_corner": "Bottom-right", "direction": "Counter-clockwise",
    "brightness": 75, "fps": 20, "smoothing": 35,
    "mode": "Screen Sync", "color": "#d6ad55",
    "sound_sensitivity": 55, "sound_reaction_speed": 65, "sound_bass_intensity": 75,
    "sound_min_brightness": 8, "sound_max_brightness": 100, "sound_palette": "Neon",
    "startup_animation": True, "launch_windows": False,
    "minimize_tray": True, "minimize_on_start": True, "restore_mode": True,
    "monitor": 0, "protocol": "csv_rgb", "theme": "Dark Gold", "auto_refresh_ports": True, "auto_reconnect": True, "port_refresh_seconds": 3,
    "ai_auto_brightness": True, "ai_scene_analysis": True, "ai_color_calibration": True,
    "white_balance_r": 1.15, "white_balance_g": 1.0, "white_balance_b": 0.82,
    "ai_profile": "Adaptive", "ai_last_scene": "Waiting for screen capture",
    "sample_top": 7, "sample_right": 7, "sample_bottom": 7, "sample_left": 7
}
GOLD = "#15c9a0"
BG = "#0b0b0d"
PANEL = "#141214"
PANEL2 = "#1b191b"
TEXT = "#f4f2f4"
MUTED = "#969096"
BORDER = "#292629"

def load_config():
    APP_DIR.mkdir(parents=True, exist_ok=True)
    # Migrate settings from the previous LED CNTRL name on first launch.
    if not CONFIG_PATH.exists() and (OLD_APP_DIR / "settings.json").exists():
        try:
            CONFIG_PATH.write_text((OLD_APP_DIR / "settings.json").read_text(encoding="utf-8"), encoding="utf-8")
        except Exception:
            pass
    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        return {**DEFAULT_CONFIG, **data}
    except Exception:
        return DEFAULT_CONFIG.copy()

def save_config(cfg):
    APP_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(cfg, indent=2), encoding="utf-8")


class PerimeterLayoutPreview(QWidget):
    """Visual monitor perimeter preview for custom LED edge counts and direction."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.counts = {"top": 15, "right": 8, "bottom": 11, "left": 8}
        self.start_corner = "Bottom-right"
        self.direction = "Counter-clockwise"
        self.setMinimumHeight(330)
        self.setMinimumWidth(480)

    def set_layout(self, counts, start_corner, direction):
        self.counts = dict(counts)
        self.start_corner = start_corner
        self.direction = direction
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), QColor("#0e0e11"))
        rect = self.rect().adjusted(24, 24, -24, -24)
        # Fit a wide monitor diagram into the available area.
        w = min(rect.width() * 0.72, rect.height() * 1.55)
        h = min(rect.height() * 0.56, w * 0.58)
        x = rect.center().x() - w / 2
        y = rect.center().y() - h / 2
        screen = __import__("PySide6.QtCore", fromlist=["QRectF"]).QRectF(x, y, w, h)
        p.setPen(QPen(QColor("#4b484d"), 2))
        p.setBrush(QColor("#17171b"))
        p.drawRoundedRect(screen, 12, 12)
        p.setPen(QPen(QColor("#29272d"), 1))
        p.drawRoundedRect(screen.adjusted(9, 9, -9, -9), 7, 7)
        p.setPen(QColor("#d7d2da"))
        p.setFont(QFont("Segoe UI", 11, QFont.Weight.DemiBold))
        p.drawText(screen, Qt.AlignmentFlag.AlignCenter, "SCREEN")
        p.setPen(QColor("#918b96"))
        p.setFont(QFont("Segoe UI", 8))
        p.drawText(12, 17, self.width()-24, 18, Qt.AlignmentFlag.AlignLeft, "CUSTOM PERIMETER LAYOUT")
        # LED dots are drawn around each side, matching the counts set in the controls.
        dot_r = 4.2
        dot_color = QColor("#19cba2")
        for side in ("top", "right", "bottom", "left"):
            n = max(0, int(self.counts.get(side, 0)))
            for i in range(n):
                t = (i + 0.5) / max(1, n)
                if side == "top":
                    cx, cy = screen.left() + t * screen.width(), screen.top() - 8
                elif side == "right":
                    cx, cy = screen.right() + 8, screen.top() + t * screen.height()
                elif side == "bottom":
                    cx, cy = screen.right() - t * screen.width(), screen.bottom() + 8
                else:
                    cx, cy = screen.left() - 8, screen.bottom() - t * screen.height()
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(dot_color)
                p.drawEllipse(__import__("PySide6.QtCore", fromlist=["QPointF"]).QPointF(cx, cy), dot_r, dot_r)
        p.setPen(QColor("#d8d2db"))
        p.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
        p.drawText(screen.left(), screen.top()-30, screen.width(), 18, Qt.AlignmentFlag.AlignCenter, f"TOP  ·  {self.counts.get('top',0)} LEDs")
        p.drawText(screen.right()+17, screen.top(), 105, screen.height(), Qt.AlignmentFlag.AlignVCenter, f"RIGHT\n{self.counts.get('right',0)} LEDs")
        p.drawText(screen.left(), screen.bottom()+17, screen.width(), 18, Qt.AlignmentFlag.AlignCenter, f"BOTTOM  ·  {self.counts.get('bottom',0)} LEDs")
        p.drawText(0, screen.top(), max(18, screen.left()-18), screen.height(), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight, f"LEFT\n{self.counts.get('left',0)} LEDs")
        p.setPen(QColor("#a49ca7"))
        p.setFont(QFont("Segoe UI", 8))
        p.drawText(20, self.height()-18, self.width()-40, 14, Qt.AlignmentFlag.AlignLeft,
                   f"Start: {self.start_corner}   •   Direction: {self.direction}")
        p.end()

class LedStripPreview(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(250)
        self.count = 42
        self.colors = [QColor("#292a2c") for _ in range(self.count)]
        self.setToolTip("Illustrative LED layout preview")
    def set_colors(self, colors):
        self.colors = colors
        self.update()
    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = self.rect().adjusted(16, 12, -16, -12)
        p.setPen(QPen(QColor(BORDER), 1))
        p.setBrush(QBrush(QColor("#141516")))
        p.drawRoundedRect(r, 18, 18)
        # screen-shaped center
        cx, cy = r.center().x(), r.center().y()
        screen = r.adjusted(80, 52, -80, -52)
        p.setPen(QPen(QColor("#45423a"), 1))
        p.setBrush(QBrush(QColor("#222326")))
        p.drawRoundedRect(screen, 10, 10)
        p.setPen(QColor(MUTED))
        p.setFont(QFont("Segoe UI", 10))
        p.drawText(screen, Qt.AlignmentFlag.AlignCenter, "SCREEN\nAMBIENT LIGHTING")
        pts = []
        left, right = r.left()+25, r.right()-25
        top, bottom = r.top()+25, r.bottom()-25
        # top left to top right, right down, bottom right to bottom left, left up
        for i in range(15):
            x = left + (right-left)*i/14
            pts.append((x, top))
        for i in range(8):
            y = top + (bottom-top)*(i+1)/9
            pts.append((right, y))
        for i in range(11):
            x = right - (right-left)*i/10
            pts.append((x, bottom))
        for i in range(8):
            y = bottom - (bottom-top)*(i+1)/9
            pts.append((left, y))
        for i, (x,y) in enumerate(pts[:len(self.colors)]):
            c = self.colors[i]
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(c))
            p.drawEllipse(int(x-5), int(y-5), 10, 10)
            if c.lightness() > 80:
                p.setPen(QPen(QColor(c.red(), c.green(), c.blue(), 70), 5))
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.drawEllipse(int(x-7), int(y-7), 14, 14)
        p.end()

class LightAreaCanvas(QWidget):
    """Canvas preview of the screen-sampling bands used by Screen Sync."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.areas = {"top":7,"right":7,"bottom":7,"left":7}
        self.setMinimumHeight(260)
        self.setMinimumWidth(420)
    def set_areas(self, areas):
        self.areas = dict(areas); self.update()
    def paintEvent(self, event):
        p=QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), QColor("#0e0e11"))
        from PySide6.QtCore import QRectF
        r=self.rect().adjusted(30,30,-30,-30)
        w=min(r.width()*.78,r.height()*1.55); h=min(r.height()*.70,w*.56)
        x=r.center().x()-w/2; y=r.center().y()-h/2; screen=QRectF(x,y,w,h)
        p.setPen(QPen(QColor("#77727b"),2)); p.setBrush(QColor("#17171b")); p.drawRoundedRect(screen,8,8)
        colors={"top":"#ffad45","right":"#38d9c4","bottom":"#aa78ff","left":"#42a5ff"}
        t=min(.35,max(.01,self.areas.get("top",7)/100)); rr=min(.35,max(.01,self.areas.get("right",7)/100)); b=min(.35,max(.01,self.areas.get("bottom",7)/100)); ll=min(.35,max(.01,self.areas.get("left",7)/100))
        bands={"top":QRectF(x,y,w,h*t),"right":QRectF(x+w*(1-rr),y,h*0+w*rr,h),"bottom":QRectF(x,y+h*(1-b),w,h*b),"left":QRectF(x,y,w*ll,h)}
        for side,band in bands.items():
            p.setPen(Qt.PenStyle.NoPen); p.setBrush(QColor(colors[side])); p.drawRoundedRect(band,4,4)
        p.setPen(QColor("#ffffff")); p.setFont(QFont("Segoe UI",10,QFont.Weight.DemiBold)); p.drawText(screen,Qt.AlignmentFlag.AlignCenter,"SCREEN\n\nColored bands = sampled areas")
        p.setPen(QColor("#c8c3cc")); p.setFont(QFont("Segoe UI",9))
        p.drawText(int(x),int(y-18),int(w),16,Qt.AlignmentFlag.AlignCenter,f"TOP  {self.areas.get('top',7)}%")
        p.drawText(int(x),int(y+h+4),int(w),16,Qt.AlignmentFlag.AlignCenter,f"BOTTOM  {self.areas.get('bottom',7)}%")
        p.drawText(2,int(y),max(20,int(x-6)),int(h),Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignVCenter,f"LEFT\n{self.areas.get('left',7)}%")
        p.drawText(int(x+w+6),int(y),max(20,self.width()-int(x+w)-8),int(h),Qt.AlignmentFlag.AlignLeft|Qt.AlignmentFlag.AlignVCenter,f"RIGHT\n{self.areas.get('right',7)}%")
        p.end()

class SerialController(QObject):
    status = Signal(str)
    frame_sent = Signal()
    def __init__(self):
        super().__init__()
        self.ser = None
        self.lock = threading.Lock()
    def ports(self):
        try:
            from serial.tools import list_ports
            return [(p.device, f"{p.device} — {p.description}") for p in list_ports.comports()]
        except Exception:
            return []
    def connect_port(self, port, baud=115200):
        try:
            import serial
            self.disconnect_port()
            self.ser = serial.Serial(port, baud, timeout=0.1, write_timeout=0.5)
            time.sleep(1.8)
            self.status.emit(f"Connected · {port}")
            return True
        except Exception as e:
            self.ser = None
            self.status.emit(f"Connection failed · {e}")
            return False
    def disconnect_port(self):
        try:
            if self.ser and self.ser.is_open: self.ser.close()
        except Exception:
            pass
        self.ser = None
    def send_rgb(self, colors):
        with self.lock:
            if not self.ser or not self.ser.is_open:
                return False
            try:
                flat = []
                for c in colors:
                    flat.extend([max(0,min(255,int(c.red()))), max(0,min(255,int(c.green()))), max(0,min(255,int(c.blue())))])
                self.ser.write((",".join(map(str, flat)) + "\n").encode("ascii"))
                self.frame_sent.emit()
                return True
            except Exception as e:
                self.status.emit(f"USB write error · {e}")
                return False

class ScreenWorker(QThread):
    frame = Signal(list)
    status = Signal(str)

    def __init__(self, count, fps, smoothing, brightness, monitor=0,
                 top=15, right=8, bottom=11, left=8,
                 start_corner="Bottom-right", direction="Counter-clockwise",
                 ai_auto_brightness=True, ai_scene_analysis=True, ai_color_calibration=True,
                 white_balance=(1.15, 1.0, 0.82), ai_profile="Adaptive", sample_areas=None):
        super().__init__()
        self.count, self.fps = count, fps
        self.smoothing, self.brightness, self.monitor = smoothing, brightness, monitor
        self.edge_counts = {"top": int(top), "right": int(right),
                            "bottom": int(bottom), "left": int(left)}
        self.start_corner = start_corner
        self.direction = direction
        self.ai_auto_brightness = bool(ai_auto_brightness)
        self.ai_scene_analysis = bool(ai_scene_analysis)
        self.ai_color_calibration = bool(ai_color_calibration)
        self.white_balance = tuple(float(v) for v in white_balance)
        self.ai_profile = ai_profile
        self.sample_areas = sample_areas or {"top":7,"right":7,"bottom":7,"left":7}
        self.running = True
        self.previous = None

    def stop(self):
        self.running = False

    def run(self):
        try:
            import mss
            import numpy as np
            with mss.mss() as sct:
                monitors = sct.monitors
                mi = max(1, min(self.monitor + 1, len(monitors) - 1))
                mon = monitors[mi]
                while self.running:
                    start = time.time()
                    shot = np.array(sct.grab(mon))[:, :, :3]
                    h, w, _ = shot.shape
                    # Offline scene analysis: estimate screen luminance and classify the current scene.
                    # This is a lightweight local heuristic, not a cloud AI model.
                    sample = shot[::max(1, h//80), ::max(1, w//80), :].astype(np.float32)
                    screen_luma = float((sample[:, :, 0]*0.0722 + sample[:, :, 1]*0.7152 + sample[:, :, 2]*0.2126).mean())
                    if self.ai_scene_analysis:
                        self.last_scene = "Dark scene" if screen_luma < 55 else ("Bright scene" if screen_luma > 175 else "Balanced scene")
                    else:
                        self.last_scene = "Scene analysis off"
                    auto_gain = max(0.35, min(1.0, 0.35 + screen_luma / 255.0 * 0.65)) if self.ai_auto_brightness else 1.0
                    if self.ai_profile == "Movie":
                        auto_gain *= 0.88
                    elif self.ai_profile == "Gaming":
                        auto_gain = min(1.0, auto_gain * 1.08)
                    regions = {}

                    def split_horizontal(n, reverse=False, side="top"):
                        result = []
                        for i in range(n):
                            j = n - 1 - i if reverse else i
                            x0, x1 = int(w*j/max(1,n)), int(w*(j+1)/max(1,n))
                            thick=max(1,int(h*float(self.sample_areas.get(side,"7"))/100))
                            result.append(shot[:thick, x0:x1] if side == "top" else shot[-thick:, x0:x1])
                        return result

                    def split_vertical(n, side="right", reverse=False):
                        result = []
                        for i in range(n):
                            j = n - 1 - i if reverse else i
                            y0, y1 = int(h*j/max(1,n)), int(h*(j+1)/max(1,n))
                            if side == "right":
                                result.append(shot[y0:y1, -max(1,int(w*float(self.sample_areas.get("right",7))/100)):])
                            else:
                                result.append(shot[y0:y1, :max(1,int(w*float(self.sample_areas.get("left",7))/100))])
                        return result

                    # Each edge list follows the clockwise perimeter from its first corner.
                    regions["top"] = split_horizontal(self.edge_counts["top"], False)       # TL -> TR
                    regions["right"] = split_vertical(self.edge_counts["right"], "right", False) # TR -> BR
                    regions["bottom"] = split_horizontal(self.edge_counts["bottom"], True, "bottom")  # BR -> BL
                    regions["left"] = split_vertical(self.edge_counts["left"], "left", True) # BL -> TL

                    # Physical LED index 0 starts at the selected corner and advances in the selected direction.
                    perimeter = []
                    corners = {
                        "Top-left": ("top", 0, "cw"),
                        "Top-right": ("right", 0, "cw"),
                        "Bottom-right": ("bottom", 0, "cw"),
                        "Bottom-left": ("left", 0, "cw"),
                    }
                    clockwise = (self.direction == "Clockwise")
                    # Canonical clockwise order: top TL->TR, right TR->BR,
                    # bottom BR->BL, left BL->TL.
                    side_order = ["top", "right", "bottom", "left"] if clockwise else ["left", "bottom", "right", "top"]
                    start_corner = self.start_corner
                    # Rotate canonical perimeter so index 0 is at the requested corner.
                    corner_side = {"Top-left": "top", "Top-right": "right",
                                   "Bottom-right": "bottom", "Bottom-left": "left"}[start_corner]
                    # Start index within each clockwise side; reverse traversal uses the matching corner endpoint.
                    side_start = {
                        ("top", True): 0, ("right", True): 0, ("bottom", True): 0, ("left", True): 0,
                        ("top", False): -1, ("right", False): -1, ("bottom", False): -1, ("left", False): -1
                    }
                    # Build side sequence with correct per-edge direction for the selected traversal.
                    cw_side_order = ["top", "right", "bottom", "left"]
                    ccw_side_order = ["left", "bottom", "right", "top"]
                    order = cw_side_order if clockwise else ccw_side_order
                    # The corner is the boundary between two sides. Choose the side whose first point is that corner.
                    start_pos = {
                        ("Top-left", True): ("top", 0), ("Top-right", True): ("right", 0),
                        ("Bottom-right", True): ("bottom", 0), ("Bottom-left", True): ("left", 0),
                        ("Top-left", False): ("top", 0), ("Top-right", False): ("right", -1),
                        ("Bottom-right", False): ("bottom", -1), ("Bottom-left", False): ("left", -1),
                    }[(start_corner, clockwise)]
                    # Side arrays above are stored clockwise. Reverse them for counter-clockwise traversal.
                    ordered_sides = {}
                    for side, arr in regions.items():
                        ordered_sides[side] = arr if clockwise else list(reversed(arr))
                    # Rotate side order to start at the selected side; edge starts align at the chosen corner.
                    order = cw_side_order if clockwise else ccw_side_order
                    idx = order.index(start_pos[0])
                    order = order[idx:] + order[:idx]
                    for side in order:
                        arr = ordered_sides[side]
                        if side == start_pos[0] and start_pos[1] == -1:
                            arr = list(reversed(arr))
                        perimeter.extend(arr)

                    vals = []
                    for reg in perimeter[:self.count]:
                        if reg.size:
                            bgr = reg.reshape(-1, 3).mean(axis=0)
                            rgb = [int(bgr[2]), int(bgr[1]), int(bgr[0])]
                            luminance = 0.2126*rgb[0] + 0.7152*rgb[1] + 0.0722*rgb[2]
                            if luminance < 18:
                                rgb = [0, 0, 0]
                            else:
                                rgb = [int(v*self.brightness/100 * auto_gain) for v in rgb]
                                if self.ai_color_calibration:
                                    rgb = [max(0, min(255, int(rgb[0]*self.white_balance[0]))),
                                           max(0, min(255, int(rgb[1]*self.white_balance[1]))),
                                           max(0, min(255, int(rgb[2]*self.white_balance[2])))]
                        else:
                            rgb = [0, 0, 0]
                        vals.append(QColor(*rgb))
                    while len(vals) < self.count:
                        vals.append(QColor(0, 0, 0))
                    if self.previous and len(self.previous) == len(vals):
                        a = self.smoothing/100
                        vals = [QColor(int(old.red()*(1-a)+new.red()*a),
                                        int(old.green()*(1-a)+new.green()*a),
                                        int(old.blue()*(1-a)+new.blue()*a))
                                for old, new in zip(self.previous, vals)]
                    self.previous = vals
                    self.frame.emit(vals)
                    time.sleep(max(0, 1/max(1,self.fps) - (time.time()-start)))
        except Exception as e:
            self.status.emit(f"Screen capture unavailable: {e}")

class SoundSyncWorker(QThread):
    """Windows PC-output loopback audio analysis; local/offline FFT-based LED sync."""
    frame = Signal(list)
    status = Signal(str)

    def __init__(self, count, fps, brightness, sensitivity=55, reaction_speed=65,
                 bass_intensity=75, min_brightness=8, max_brightness=100,
                 palette="Neon", combined=False, monitor=0, top=15, right=8,
                 bottom=11, left=8, start_corner="Bottom-right", direction="Counter-clockwise",
                 smoothing=35, sample_areas=None):
        super().__init__()
        self.count, self.fps, self.brightness = count, max(5, fps), brightness
        self.sensitivity = max(1, min(100, sensitivity)) / 50.0
        self.reaction_speed = max(1, min(100, reaction_speed)) / 100.0
        self.bass_intensity = max(0, min(100, bass_intensity)) / 100.0
        self.min_brightness = max(0, min(100, min_brightness)) / 100.0
        self.max_brightness = max(self.min_brightness, min(100, max_brightness)) / 100.0
        self.palette, self.combined, self.monitor = palette, combined, monitor
        self.edge_counts = {"top": int(top), "right": int(right), "bottom": int(bottom), "left": int(left)}
        self.start_corner, self.direction = start_corner, direction
        self.smoothing = max(0, min(90, smoothing)) / 100.0
        self.sample_areas = sample_areas or {"top":7,"right":7,"bottom":7,"left":7}
        self.running = True
        self.envelope = 0.0
        self.prev = None
        self.combined_pulse = 0.0

    def stop(self):
        self.running = False

    def _screen_colors(self, shot, np):
        h, w, _ = shot.shape
        regions = {}
        def horizontal(n, reverse=False, side="top"):
            out=[]; thick=max(1,int((h if side in ("top","bottom") else w)*float(self.sample_areas.get(side,7))/100))
            for i in range(n):
                j=n-1-i if reverse else i; x0=int(w*j/max(1,n)); x1=int(w*(j+1)/max(1,n))
                out.append(shot[:thick,x0:x1] if side=="top" else shot[-thick:,x0:x1])
            return out
        def vertical(n, side, reverse=False):
            out=[]; thick=max(1,int(w*float(self.sample_areas.get(side,7))/100))
            for i in range(n):
                j=n-1-i if reverse else i; y0=int(h*j/max(1,n)); y1=int(h*(j+1)/max(1,n))
                out.append(shot[y0:y1,-thick:] if side=="right" else shot[y0:y1,:thick])
            return out
        regions["top"]=horizontal(self.edge_counts["top"],False,"top")
        regions["right"]=vertical(self.edge_counts["right"],False)
        regions["bottom"]=horizontal(self.edge_counts["bottom"],True,"bottom")
        regions["left"]=vertical(self.edge_counts["left"],True)
        cw=self.direction=="Clockwise"
        # Exact physical order used by this installation: LED 1 at bottom-right,
        # then travel left along the bottom, up the left, across the top, down right.
        if self.start_corner=="Bottom-right" and not cw:
            order=["bottom","left","top","right"]
            reverse_by_side={"bottom":False,"left":False,"top":False,"right":False}
        else:
            order=["top","right","bottom","left"] if cw else ["left","bottom","right","top"]
            corner_side={"Top-left":"top","Top-right":"right","Bottom-right":"bottom","Bottom-left":"left"}.get(self.start_corner,"bottom")
            if corner_side in order:
                k=order.index(corner_side); order=order[k:]+order[:k]
            reverse_by_side={side:(not cw) for side in order}
        vals=[]
        for side in order:
            arr=list(reversed(regions[side])) if reverse_by_side.get(side,False) else regions[side]
            for reg in arr:
                if reg.size:
                    bgr=reg.reshape(-1,3).mean(axis=0); vals.append([int(bgr[2]),int(bgr[1]),int(bgr[0])])
        return vals[:self.count]

    def run(self):
        try:
            import numpy as np
            import soundcard as sc
            speaker=sc.default_speaker()
            if speaker is None:
                raise RuntimeError("No default Windows audio output device was found.")
            mic=sc.get_microphone(id=str(speaker.name), include_loopback=True)
            self.status.emit(f"PC audio loopback active · {speaker.name}")
            screen_capture=None; monitor_rect=None
            if self.combined:
                try:
                    import mss
                    screen_capture=mss.mss(); mons=screen_capture.monitors
                    monitor_rect=mons[max(1,min(self.monitor+1,len(mons)-1))]
                except Exception as e:
                    self.status.emit(f"Combined mode: screen capture unavailable; using audio sync · {e}")
                    self.combined=False
            with mic.recorder(samplerate=44100, channels=2, blocksize=2048) as recorder:
                while self.running:
                    t0=time.time()
                    audio=recorder.record(numframes=2048)
                    if audio is None or len(audio)==0: continue
                    mono=np.asarray(audio,dtype=np.float32).mean(axis=1)
                    rms=float(np.sqrt(np.mean(mono*mono)))
                    target=min(1.0, rms*12.0*self.sensitivity)
                    self.envelope=self.envelope*(1-self.reaction_speed)+target*self.reaction_speed
                    spec=np.abs(np.fft.rfft(mono*np.hanning(len(mono))))
                    freqs=np.fft.rfftfreq(len(mono),1/44100)
                    bands=[]
                    for lo,hi in [(35,140),(140,500),(500,2000),(2000,6000),(6000,16000)]:
                        mask=(freqs>=lo)&(freqs<hi)
                        v=float(spec[mask].mean()) if mask.any() else 0.0
                        bands.append(v)
                    peak=max(bands)+1e-6
                    bands=[min(1.0,(v/peak)**0.7) for v in bands]
                    bands[0]=min(1.0,bands[0]*(0.5+self.bass_intensity*1.5))
                    # Combined mode uses audio only as a smooth brightness modulation.
                    # Screen RGB remains the color source; no audio palette is blended in.
                    spectral_energy=(bands[0]*0.40 + bands[1]*0.25 + bands[2]*0.20 + bands[3]*0.10 + bands[4]*0.05)
                    activity=min(1.0, rms * 18.0 * self.sensitivity)
                    pulse_target=min(1.0, 0.55*activity + 0.45*spectral_energy)
                    pulse_alpha=0.12 + self.reaction_speed*0.18
                    self.combined_pulse += (pulse_target-self.combined_pulse)*pulse_alpha
                    if self.palette=="Warm": palette=[(255,65,18),(255,150,20),(255,220,80),(255,90,50),(255,35,80)]
                    elif self.palette=="Cool": palette=[(40,90,255),(20,200,255),(80,255,220),(150,90,255),(230,80,255)]
                    else: palette=[(255,45,70),(255,130,30),(210,255,35),(20,230,160),(45,90,255)]
                    screen=[]
                    if self.combined and screen_capture is not None:
                        shot=np.asarray(screen_capture.grab(monitor_rect))[:,:,:3]
                        screen=self._screen_colors(shot,np)
                    out=[]
                    for i in range(self.count):
                        band_idx=min(4,int(i*5/max(1,self.count)))
                        level=max(self.min_brightness, min(self.max_brightness, bands[band_idx]*(0.45+self.envelope*1.8)))
                        level=min(1.0,level*self.brightness/100)
                        audio_rgb=palette[band_idx]
                        if self.combined and i<len(screen):
                            sr,sg,sb=screen[i]
                            # Screen-first combined mode: preserve sampled screen hue/color.
                            # Audio creates a medium-strength, smoothed brightness pulse only.
                            base=max(0.25, min(1.0, self.brightness/100))
                            pulse=0.78 + 0.32*self.combined_pulse
                            rgb=[int(c*base*pulse) for c in (sr,sg,sb)]
                        else:
                            rgb=[int(c*level) for c in audio_rgb]
                        out.append(QColor(*[max(0,min(255,v)) for v in rgb]))
                    if self.prev and len(self.prev)==len(out):
                        a=(0.22 if self.combined else max(0.15,self.reaction_speed))
                        out=[QColor(int(o.red()*(1-a)+n.red()*a),int(o.green()*(1-a)+n.green()*a),int(o.blue()*(1-a)+n.blue()*a)) for o,n in zip(self.prev,out)]
                    self.prev=out
                    self.frame.emit(out)
                    delay=max(0,1/self.fps-(time.time()-t0))
                    if delay: time.sleep(delay)
            if screen_capture is not None: screen_capture.close()
        except Exception as e:
            self.status.emit("Sound Sync unavailable · install soundcard and check Windows audio output permissions · " + str(e))


class VoiceCommandWorker(QThread):
    recognized = Signal(str)
    status = Signal(str)

    def __init__(self, model_path):
        super().__init__()
        self.model_path = str(model_path)

    def run(self):
        try:
            import json as json_module
            import sounddevice as sd
            from vosk import Model, KaldiRecognizer
            model = Model(self.model_path)
            recognizer = KaldiRecognizer(model, 16000)
            self.status.emit("Listening locally for one command…")
            with sd.RawInputStream(samplerate=16000, blocksize=8000, dtype="int16", channels=1) as stream:
                deadline = time.time() + 10
                while time.time() < deadline:
                    data, overflowed = stream.read(4000)
                    if recognizer.AcceptWaveform(bytes(data)):
                        result = json_module.loads(recognizer.Result())
                        text = result.get("text", "").strip()
                        if text:
                            self.recognized.emit(text)
                            self.status.emit(f"Heard: {text}")
                            return
                result = json_module.loads(recognizer.FinalResult())
                text = result.get("text", "").strip()
                if text:
                    self.recognized.emit(text)
                    self.status.emit(f"Heard: {text}")
                else:
                    self.status.emit("No command detected. Try again.")
        except Exception as exc:
            self.status.emit(f"Voice setup needed: {exc}")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.cfg = load_config()
        self.serial = SerialController()
        self.worker = None
        self.current_mode = "Idle"
        self.animation_timer = QTimer(self)
        self.animation_timer.timeout.connect(self.startup_step)
        self.anim_step = 0
        self.anim_passes = 0
        self.anim_running = False
        self.colors = [QColor("#18191a") for _ in range(int(self.cfg["led_count"]))]
        self.setWindowTitle("LED CNTRL")
        logo_path = Path(__file__).with_name("led_cntrl_logo.png")
        if logo_path.exists():
            self.setWindowIcon(QIcon(str(logo_path)))
        self.resize(1440, 900)
        self.setMinimumSize(1100, 700)
        self.setStyleSheet(self.stylesheet())
        self.build_ui()
        self.refresh_ports()
        self.serial.status.connect(self.set_status)
        self.port_refresh_timer = QTimer(self)
        self.port_refresh_timer.timeout.connect(self.auto_refresh_ports)
        self.port_refresh_timer.start(max(1000, int(self.cfg.get("port_refresh_seconds", 3)) * 1000))
        self.tray = None
        self._really_quit = False
        self.setup_tray()
        self.statusBar().setStyleSheet(f"color:{MUTED}; background:{BG}; border-top:1px solid {BORDER};")
        self.set_status("Ready · USB lighting controller")
        if self.cfg.get("startup_animation", True):
            QTimer.singleShot(1000, self.begin_startup_animation)
        if self.cfg.get("minimize_on_start", True) and self.tray:
            QTimer.singleShot(250, self.hide)

    def setup_tray(self):
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        self.tray = QSystemTrayIcon(self)
        self.tray.setToolTip("LED CNTRL — Created by Keynes")
        # Use a simple custom gold icon so the tray icon does not depend on external files.
        pix = QIcon()
        from PySide6.QtGui import QPixmap
        pm = QPixmap(64, 64)
        pm.fill(QColor("#151617"))
        painter = QPainter(pm)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor(GOLD), 4))
        painter.drawRoundedRect(8, 8, 48, 48, 12, 12)
        painter.setPen(QPen(QColor(GOLD), 5))
        painter.drawLine(20, 32, 44, 32)
        painter.drawLine(32, 20, 32, 44)
        painter.end()
        self.tray.setIcon(QIcon(pm))
        menu = QMenu()
        show_action = QAction("Open LED CNTRL", self)
        show_action.triggered.connect(self.show_from_tray)
        menu.addAction(show_action)
        menu.addSeparator()
        quit_action = QAction("Exit LED CNTRL", self)
        quit_action.triggered.connect(self.quit_application)
        menu.addAction(quit_action)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(lambda reason: self.show_from_tray() if reason == QSystemTrayIcon.ActivationReason.Trigger else None)
        self.tray.show()

    def show_from_tray(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def quit_application(self):
        self._really_quit = True
        if self.tray:
            self.tray.hide()
        self.close()

    def stylesheet(self):
        return f"""
        QWidget {{ background:{BG}; color:{TEXT}; font-family:'Segoe UI'; font-size:9pt; }}
        QMainWindow {{ background:#090a0c; }}
        QFrame#Sidebar {{ background:#100e10; border:1px solid #242124; border-radius:20px; }}
        QFrame#Card {{ background:{PANEL}; border:1px solid #252225; border-radius:18px; }}
        QLabel#Title {{ font-size:22pt; font-weight:650; }}
        QLabel#SubTitle {{ color:{MUTED}; font-size:8pt; }}
        QLabel#Section {{ color:{MUTED}; font-size:8pt; font-weight:600; letter-spacing:1px; }}
        QPushButton {{ background:#1b191b; color:{TEXT}; border:1px solid #292629; border-radius:9px; padding:8px 12px; }}
        QPushButton:hover {{ border:1px solid #277d6b; background:#202123; }}
        QPushButton#Primary {{ background:#0da982; color:#f8fffc; font-weight:700; border:0; }}
        QPushButton#Primary:hover {{ background:#17c69c; }}
        QPushButton#Nav {{ text-align:left; padding:10px 12px; background:transparent; border:1px solid transparent; color:#b9b4ba; border-radius:10px; }}
        QPushButton#Nav:checked {{ color:#f7f5f7; background:#1a211f; border:1px solid #176a58; }}
        QComboBox, QLineEdit, QSpinBox {{ background:#201d20; border:1px solid #302c30; border-radius:8px; padding:7px; min-height:18px; }}
        QSlider::groove:horizontal {{ height:4px; background:#373238; border-radius:2px; }}
        QSlider::handle:horizontal {{ background:{GOLD}; width:12px; margin:-4px 0; border-radius:6px; }}
        QCheckBox {{ spacing:8px; }}
        QCheckBox::indicator {{ width:16px; height:16px; }}
        QCheckBox::indicator:checked {{ background:{GOLD}; border:1px solid {GOLD}; }}
        QProgressBar {{ border:0; background:#343034; border-radius:3px; height:5px; text-align:center; }}
        QProgressBar::chunk {{ background:{GOLD}; border-radius:3px; }}
        QScrollArea {{ border:0; }}
        QStatusBar {{ color:{MUTED}; background:{BG}; border-top:1px solid {BORDER}; }}
        """
    def build_ui(self):
        root = QWidget()
        outer = QHBoxLayout(root); outer.setContentsMargins(0,0,0,0); outer.setSpacing(0)
        sidebar = QFrame(); sidebar.setObjectName("Sidebar"); sidebar.setFixedWidth(184)
        sv = QVBoxLayout(sidebar); sv.setContentsMargins(10,16,10,12); sv.setSpacing(5)
        logo_path = Path(__file__).with_name("led_cntrl_logo.png")
        brand = QLabel()
        brand.setAlignment(Qt.AlignmentFlag.AlignCenter)
        brand.setStyleSheet("padding:4px;")
        if logo_path.exists():
            brand.setPixmap(QPixmap(str(logo_path)).scaled(156, 118, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        else:
            brand.setText("LED CNTRL")
            brand.setStyleSheet(f"font-size:17pt;font-weight:700;color:{TEXT};padding:8px;")
        sv.addWidget(brand)
        by = QLabel("CREATED BY KEYNES"); by.setStyleSheet(f"font-size:8pt;letter-spacing:2px;color:{GOLD};padding:0 8px 18px;")
        sv.addWidget(by)
        self.nav_buttons = {}
        navs = [("Home","⌂"),("Screen Sync","◉"),("Sound Sync","♫"),("Effects","✧"),("LED Layout","▦"),("Light Calibration","▧"),("Profiles","▤"),("Devices","⌁"),("Settings","⚙")]
        for name, icon in navs:
            b = QPushButton(f"{icon}   {name}"); b.setObjectName("Nav"); b.setCheckable(True)
            b.clicked.connect(lambda checked=False, n=name: self.navigate(n))
            sv.addWidget(b); self.nav_buttons[name]=b
        sv.addStretch()
        footer = QLabel("USB SERIAL  •  OFFLINE READY"); footer.setStyleSheet(f"font-size:7pt;color:{MUTED};padding:8px;")
        sv.addWidget(footer)
        main = QWidget(); mv=QVBoxLayout(main); mv.setContentsMargins(22,18,22,16); mv.setSpacing(12)
        top = QHBoxLayout()
        titlebox=QVBoxLayout()
        self.page_title=QLabel("Home"); self.page_title.setObjectName("Title")
        self.page_sub=QLabel("Your lighting, perfectly in sync."); self.page_sub.setObjectName("SubTitle")
        titlebox.addWidget(self.page_title); titlebox.addWidget(self.page_sub)
        top.addLayout(titlebox); top.addStretch()
        self.connection_badge=QLabel("●  DISCONNECTED"); self.connection_badge.setStyleSheet(f"color:{GOLD};background:#27251e;border:1px solid #51452b;border-radius:12px;padding:9px 13px;")
        top.addWidget(self.connection_badge)
        mv.addLayout(top)
        self.pages=QStackedWidget()
        self.pages.addWidget(self.make_home())
        self.pages.addWidget(self.make_sync())
        self.pages.addWidget(self.make_sound_sync())
        self.pages.addWidget(self.make_effects())
        self.pages.addWidget(self.make_layout())
        self.pages.addWidget(self.make_calibration())
        self.pages.addWidget(self.make_profiles())
        self.pages.addWidget(self.make_devices())
        self.pages.addWidget(self.make_settings())
        mv.addWidget(self.pages,1)
        outer.addWidget(sidebar); outer.addWidget(main,1)
        self.setCentralWidget(root)
        self.navigate("Home")
    def card(self, title, subtitle=None):
        f=QFrame(); f.setObjectName("Card"); l=QVBoxLayout(f); l.setContentsMargins(18,16,18,16); l.setSpacing(10)
        t=QLabel(title); t.setStyleSheet("font-size:13pt;font-weight:650;")
        l.addWidget(t)
        if subtitle:
            s=QLabel(subtitle); s.setObjectName("SubTitle"); s.setWordWrap(True); l.addWidget(s)
        return f,l
    def make_home(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(12)

        # Header: PC name, page title, tooltip toggle and user area.
        header = QHBoxLayout()
        titlebox = QVBoxLayout()
        pcname = QLabel("PC Name")
        pcname.setStyleSheet(f"color:{MUTED};font-size:8pt;")
        title = QLabel("Home")
        title.setStyleSheet("font-size:21pt;font-weight:700;")
        titlebox.addWidget(pcname)
        titlebox.addWidget(title)
        header.addLayout(titlebox)
        header.addStretch()

        tooltip_card = QFrame()
        tooltip_card.setObjectName("Card")
        tooltip_row = QHBoxLayout(tooltip_card)
        tooltip_row.setContentsMargins(12, 7, 12, 7)
        tip_text = QVBoxLayout()
        tip_title = QLabel("Tooltip Mode")
        tip_title.setStyleSheet("font-size:9pt;font-weight:650;")
        tip_sub = QLabel("Turn it on if you don't understand how something works")
        tip_sub.setStyleSheet(f"color:{MUTED};font-size:7pt;")
        tip_text.addWidget(tip_title)
        tip_text.addWidget(tip_sub)
        tooltip_row.addLayout(tip_text)
        self.tooltip_toggle = QCheckBox()
        self.tooltip_toggle.setChecked(bool(self.cfg.get("tooltip_mode", False)))
        self.tooltip_toggle.toggled.connect(lambda v: self.cfg.update({"tooltip_mode": v}) or save_config(self.cfg))
        tooltip_row.addWidget(self.tooltip_toggle)
        header.addWidget(tooltip_card)

        user = QFrame()
        userrow = QHBoxLayout(user)
        userrow.setContentsMargins(10, 0, 0, 0)
        avatar = QLabel("K")
        avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        avatar.setFixedSize(34, 34)
        avatar.setStyleSheet("background:#5d3e52;border-radius:17px;font-size:13pt;font-weight:700;")
        usertext = QVBoxLayout()
        usertext.addWidget(QLabel("Keynes"))
        by = QLabel("Created by Keynes")
        by.setStyleSheet(f"color:{MUTED};font-size:7pt;")
        usertext.addWidget(by)
        userrow.addWidget(avatar)
        userrow.addLayout(usertext)
        header.addWidget(user)
        lay.addLayout(header)

        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(12)

        def card(title, subtitle=None, min_height=120):
            frame = QFrame()
            frame.setObjectName("Card")
            frame.setMinimumHeight(min_height)
            v = QVBoxLayout(frame)
            v.setContentsMargins(15, 13, 15, 13)
            v.setSpacing(7)
            lab = QLabel(title)
            lab.setStyleSheet("font-size:12pt;font-weight:700;")
            v.addWidget(lab)
            if subtitle:
                sub = QLabel(subtitle)
                sub.setStyleSheet(f"font-size:7pt;color:{MUTED};")
                sub.setWordWrap(True)
                v.addWidget(sub)
            return frame, v

        def status(parent_layout, text="Optimal", color=GOLD):
            lab = QLabel("●  " + text)
            lab.setStyleSheet(f"color:{color};font-size:9pt;font-weight:600;")
            parent_layout.addWidget(lab)
            return lab

        def bar(parent_layout, value=60):
            p = QProgressBar()
            p.setRange(0, 100)
            p.setValue(max(0, min(100, int(value))))
            p.setTextVisible(False)
            p.setFixedHeight(5)
            parent_layout.addWidget(p)
            return p

        # Large welcome card with abstract line art and actionable controls.
        welcome, wl = card("Welcome back", "LED CNTRL  •  LOCAL LIGHTING CONTROL", 260)
        welcome.setStyleSheet("QFrame#Card { background:#100e11; border:1px solid #252225; border-radius:18px; }")
        self.welcome_name = QLabel("Keynes")
        self.welcome_name.setStyleSheet("font-size:25pt;font-weight:750;")
        wl.addWidget(self.welcome_name)
        art = QLabel("╱╲  ╱╲  ╱╲  ╱╲  ╱╲\n╲╱╲╱╲╱╲╱╲╱╲╱")
        art.setAlignment(Qt.AlignmentFlag.AlignCenter)
        art.setMinimumHeight(58)
        art.setStyleSheet("color:#423047;font-size:17pt;font-weight:300;")
        wl.addWidget(art)
        self.home_connection = QLabel("●  USB controller status: checking")
        self.home_connection.setStyleSheet(f"color:{GOLD};font-weight:600;")
        wl.addWidget(self.home_connection)
        wl.addWidget(QLabel("Screen sync and addressable LED control"))
        self.preview = LedStripPreview()
        self.preview.setMaximumHeight(90)
        wl.addWidget(self.preview)
        welcome_actions = QHBoxLayout()
        mypc = QPushButton("My PC  ›")
        mypc.clicked.connect(lambda: self.navigate("Devices"))
        welcome_actions.addStretch()
        welcome_actions.addWidget(mypc)
        wl.addLayout(welcome_actions)
        grid.addWidget(welcome, 0, 0, 2, 1)

        # Processor, RAM and storage cards.
        processor, pl = card("Processor", "CPU usage and temperature", 145)
        self.cpu_metric = self.metric_tile("AMD / Intel CPU", "Reading system telemetry…")
        # Compact telemetry labels are placed directly in these cards.
        self.cpu_value = QLabel("Checking usage…")
        self.cpu_value.setStyleSheet("font-size:9pt;color:#e9e5e9;")
        pl.addWidget(self.cpu_value)
        status(pl, "Monitoring available")
        bar(pl, 58)
        grid.addWidget(processor, 0, 1)

        ram, rl = card("RAM", "System memory", 145)
        self.memory_metric = self.metric_tile("Memory", "Reading memory…")
        self.ram_value = QLabel("Checking memory…")
        self.ram_value.setStyleSheet("font-size:9pt;")
        rl.addWidget(self.ram_value)
        status(rl, "Available")
        bar(rl, 45)
        grid.addWidget(ram, 0, 2)

        storage, sl = card("Storage", "System drive", 145)
        self.storage_value = QLabel("Checking disk usage…")
        self.storage_value.setStyleSheet("font-size:9pt;")
        sl.addWidget(self.storage_value)
        status(sl, "Drive information")
        bar(sl, 55)
        grid.addWidget(storage, 0, 3)

        gpu, gl = card("Video Card", "GPU utilization and temperature", 145)
        self.gpu_metric = self.metric_tile("GPU", "Optional NVIDIA telemetry")
        self.gpu_value = QLabel("GPU telemetry unavailable until detected")
        self.gpu_value.setWordWrap(True)
        self.gpu_value.setStyleSheet("font-size:9pt;")
        gl.addWidget(self.gpu_value)
        status(gl, "GPU telemetry")
        bar(gl, 24)
        grid.addWidget(gpu, 1, 1)

        network, nl = card("Network", "Network interface status", 145)
        self.network_value = QLabel("Local application • USB serial")
        self.network_value.setStyleSheet("font-size:9pt;")
        nl.addWidget(self.network_value)
        status(nl, "No internet required")
        network_art = QLabel("▁▂▁▃▆▅▇▅▃▄▂▃▅▆▄▂▃▅")
        network_art.setAlignment(Qt.AlignmentFlag.AlignCenter)
        network_art.setStyleSheet("color:#b77de5;font-size:18pt;")
        nl.addWidget(network_art)
        grid.addWidget(network, 1, 2, 1, 2)

        analyzer, al = card("Performance Analyzer", "Screen-edge lighting tools", 118)
        status(al, "Ready")
        ab = QPushButton("Analyze  ›")
        ab.clicked.connect(lambda: self.navigate("Screen Sync"))
        al.addWidget(ab, 0, Qt.AlignmentFlag.AlignLeft)
        grid.addWidget(analyzer, 2, 0)

        optimize, ol = card("Optimization", "Lighting performance and responsiveness", 118)
        status(ol, "Lighting profile")
        ob = QPushButton("Optimize  ›")
        ob.clicked.connect(lambda: self.navigate("Effects"))
        ol.addWidget(ob, 0, Qt.AlignmentFlag.AlignLeft)
        grid.addWidget(optimize, 2, 1)

        health, hl = card("Health Center", "Troubleshooting and connection checks", 118)
        status(hl, "Diagnostics available")
        hb = QPushButton("Health  ›")
        hb.clicked.connect(lambda: self.navigate("Devices"))
        hl.addWidget(hb, 0, Qt.AlignmentFlag.AlignLeft)
        grid.addWidget(health, 3, 0)

        support, sul = card("24/7 Support", "Local help and troubleshooting", 118)
        status(sul, "Help available")
        sb = QPushButton("Support  ›")
        sb.clicked.connect(lambda: self.navigate("Devices"))
        sul.addWidget(sb, 0, Qt.AlignmentFlag.AlignLeft)
        grid.addWidget(support, 3, 1)

        settings, setl = card("Platform Settings", "GENERAL PREFERENCES", 250)
        self.notifications_toggle = QCheckBox("App notifications")
        self.notifications_toggle.setChecked(bool(self.cfg.get("notifications", True)))
        self.notifications_toggle.toggled.connect(lambda v: self.cfg.update({"notifications": v}) or save_config(self.cfg))
        self.launch_toggle = QCheckBox("Launch when Windows starts")
        self.launch_toggle.setChecked(bool(self.cfg.get("launch_windows", False)))
        self.launch_toggle.toggled.connect(lambda v: self.cfg.update({"launch_windows": v}) or save_config(self.cfg))
        self.tracking_toggle = QCheckBox("Real-time screen monitoring")
        self.tracking_toggle.setChecked(bool(self.cfg.get("screen_monitoring", True)))
        self.tracking_toggle.toggled.connect(lambda v: self.cfg.update({"screen_monitoring": v}) or save_config(self.cfg))
        self.logs_toggle = QCheckBox("Save diagnostic logs")
        self.logs_toggle.setChecked(bool(self.cfg.get("diagnostic_logs", False)))
        self.logs_toggle.toggled.connect(lambda v: self.cfg.update({"diagnostic_logs": v}) or save_config(self.cfg))
        for item in [self.notifications_toggle, self.launch_toggle, self.tracking_toggle, self.logs_toggle]:
            settings_layout = QHBoxLayout()
            settings_layout.addWidget(item)
            settings_layout.addStretch()
            setl.addLayout(settings_layout)
        all_settings = QPushButton("All Settings  ›")
        all_settings.clicked.connect(lambda: self.navigate("Settings"))
        setl.addStretch()
        setl.addWidget(all_settings)
        grid.addWidget(settings, 2, 2, 2, 2)

        # Keep the familiar lighting controls available below the reference-style dashboard.
        controls, cl = card("Lighting Control", "Choose mode, brightness and start or stop your LEDs", 145)
        row = QHBoxLayout()
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Screen Sync", "Sound Sync", "Screen + Sound", "Solid Colour", "Rainbow", "Breathing", "Gold Chase"])
        self.mode_combo.setCurrentText(self.cfg.get("mode", "Screen Sync"))
        self.mode_combo.currentTextChanged.connect(self.change_mode)
        row.addWidget(self.mode_combo, 2)
        choose = QPushButton("Choose colour")
        choose.clicked.connect(self.choose_color)
        row.addWidget(choose)
        cl.addLayout(row)
        self.bright_label = QLabel(f"Brightness  {self.cfg['brightness']}%")
        cl.addWidget(self.bright_label)
        self.brightness = QSlider(Qt.Orientation.Horizontal)
        self.brightness.setRange(1, 100)
        self.brightness.setValue(int(self.cfg["brightness"]))
        self.brightness.setToolTip("Brightness is applied live and saved automatically.")
        self.brightness.valueChanged.connect(self.brightness_changed)
        cl.addWidget(self.brightness)
        btnrow = QHBoxLayout()
        self.start_btn = QPushButton("▶  Start")
        self.start_btn.setObjectName("Primary")
        self.start_btn.clicked.connect(self.start_lighting)
        self.stop_btn = QPushButton("■  Lights off")
        self.stop_btn.clicked.connect(self.lights_off)
        btnrow.addWidget(self.start_btn)
        btnrow.addWidget(self.stop_btn)
        cl.addLayout(btnrow)
        self.active_effect = QLabel("●  Ready")
        self.active_effect.setStyleSheet(f"color:{MUTED};padding:4px;")
        cl.addWidget(self.active_effect)
        grid.addWidget(controls, 4, 0, 1, 4)

        # Offline AI lighting assistant: adaptive screen analysis, calibration, profiles and commands.
        ai_card, ail = card("AI Lighting Assistant", "Local adaptive lighting · no cloud account required")
        ai_row = QHBoxLayout()
        self.ai_auto_check = QCheckBox("Auto brightness")
        self.ai_auto_check.setChecked(bool(self.cfg.get("ai_auto_brightness", True)))
        self.ai_auto_check.toggled.connect(self.ai_settings_changed)
        ai_row.addWidget(self.ai_auto_check)
        self.ai_scene_check = QCheckBox("Scene analysis")
        self.ai_scene_check.setChecked(bool(self.cfg.get("ai_scene_analysis", True)))
        self.ai_scene_check.toggled.connect(self.ai_settings_changed)
        ai_row.addWidget(self.ai_scene_check)
        self.ai_calibration_check = QCheckBox("White-balance calibration")
        self.ai_calibration_check.setChecked(bool(self.cfg.get("ai_color_calibration", True)))
        self.ai_calibration_check.toggled.connect(self.ai_settings_changed)
        ai_row.addWidget(self.ai_calibration_check)
        ail.addLayout(ai_row)
        profile_row = QHBoxLayout()
        profile_row.addWidget(QLabel("Lighting profile"))
        self.ai_profile_combo = QComboBox()
        self.ai_profile_combo.addItems(["Adaptive", "Gaming", "Movie", "Neutral"])
        self.ai_profile_combo.setCurrentText(self.cfg.get("ai_profile", "Adaptive"))
        self.ai_profile_combo.currentTextChanged.connect(self.ai_settings_changed)
        profile_row.addWidget(self.ai_profile_combo)
        ail.addLayout(profile_row)
        wb_grid = QGridLayout()
        self.wb_sliders = {}
        for row_idx, (key, label, default) in enumerate((("white_balance_r", "Red balance", 1.15), ("white_balance_g", "Green balance", 1.0), ("white_balance_b", "Blue balance", 0.82))):
            wb_grid.addWidget(QLabel(label), row_idx, 0)
            slider = QSlider(Qt.Orientation.Horizontal); slider.setRange(50, 150)
            slider.setValue(int(float(self.cfg.get(key, default))*100))
            slider.valueChanged.connect(lambda _v: self.ai_settings_changed())
            self.wb_sliders[key] = slider
            wb_grid.addWidget(slider, row_idx, 1)
            value_label = QLabel(f"{slider.value()}%"); value_label.setMinimumWidth(42)
            slider.valueChanged.connect(lambda v, lbl=value_label: lbl.setText(f"{v}%"))
            wb_grid.addWidget(value_label, row_idx, 2)
        ail.addLayout(wb_grid)
        command_row = QHBoxLayout()
        self.ai_command = QLineEdit(); self.ai_command.setPlaceholderText("Try: brightness 45, gaming mode, movie mode, screen sync, white, lights off")
        self.ai_command.returnPressed.connect(self.run_ai_command)
        command_row.addWidget(self.ai_command, 1)
        cmd_btn = QPushButton("Run command"); cmd_btn.clicked.connect(self.run_ai_command); command_row.addWidget(cmd_btn)
        voice_btn = QPushButton("🎙 Voice command"); voice_btn.clicked.connect(self.start_voice_listening); command_row.addWidget(voice_btn)
        ail.addLayout(command_row)
        self.ai_status = QLabel(self.cfg.get("ai_last_scene", "Adaptive lighting ready")); self.ai_status.setObjectName("SubTitle")
        ail.addWidget(self.ai_status)
        grid.addWidget(ai_card, 5, 0, 1, 4)

        lay.addLayout(grid, 1)
        footer = QLabel("LED CNTRL  •  CREATED BY KEYNES  •  LOCAL USB CONTROL  •  OFFLINE READY")
        footer.setStyleSheet(f"color:#777078;font-size:7pt;letter-spacing:1px;padding:3px;")
        lay.addWidget(footer)

        self.op_mode = QLabel(self.cfg.get("mode", "Screen Sync"))
        self.port_overview = QLabel("USB serial · Configure your controller in Devices")
        self.metrics_timer = QTimer(self)
        self.metrics_timer.timeout.connect(self.update_metrics)
        self.metrics_timer.start(2500)
        self.update_metrics()
        dashboard_scroll = QScrollArea()
        dashboard_scroll.setWidgetResizable(True)
        dashboard_scroll.setFrameShape(QFrame.Shape.NoFrame)
        dashboard_scroll.setWidget(page)
        return dashboard_scroll

    def metric_tile(self, title, initial):
        f=QFrame(); f.setObjectName("Card"); l=QVBoxLayout(f); l.setContentsMargins(12,12,12,12)
        t=QLabel(title); t.setStyleSheet(f"color:{GOLD};font-size:9pt;font-weight:700;")
        v=QLabel(initial); v.setWordWrap(True); v.setStyleSheet("font-size:11pt;font-weight:600;")
        l.addWidget(t); l.addWidget(v); f.value_label=v
        return f

    def update_metrics(self):
        try:
            import psutil
            cpu=f"{psutil.cpu_percent(interval=None):.0f}% usage"
            mem=psutil.virtual_memory()
            memory=f"{mem.percent:.0f}% used  ·  {mem.used/(1024**3):.1f}/{mem.total/(1024**3):.1f} GB"
        except Exception:
            cpu="Telemetry unavailable"; memory="Telemetry unavailable"
        if hasattr(self, "cpu_value"): self.cpu_value.setText(cpu)
        if hasattr(self, "ram_value"): self.ram_value.setText(memory)
        gpu_text = self.nvidia_telemetry()
        if hasattr(self, "gpu_value"):
            self.gpu_value.setText(gpu_text or "GPU telemetry unavailable")
        try:
            import psutil
            root_path = os.getenv("SystemDrive", "C:") + "\\\\"
            usage = psutil.disk_usage(root_path)
            storage = f"{usage.percent:.0f}% used  ·  {usage.used/(1024**3):.0f}/{usage.total/(1024**3):.0f} GB"
            if hasattr(self, "storage_value"): self.storage_value.setText(storage)
        except Exception:
            if hasattr(self, "storage_value"): self.storage_value.setText("Storage telemetry unavailable")
        if hasattr(self, "cpu_metric"): self.cpu_metric.value_label.setText(cpu)
        if hasattr(self, "memory_metric"): self.memory_metric.value_label.setText(memory)
        if hasattr(self, "gpu_metric"): self.gpu_metric.value_label.setText(gpu_text or "NVIDIA telemetry unavailable")
        if hasattr(self, "fan_metric"): self.fan_metric.value_label.setText("Not available through standard API")

    def nvidia_telemetry(self):
        import shutil, subprocess
        exe=shutil.which("nvidia-smi")
        if not exe: return None
        try:
            # Hide the Windows console window created by nvidia-smi on each telemetry poll.
            creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
            startup_info = None
            if os.name == "nt" and hasattr(subprocess, "STARTUPINFO"):
                startup_info = subprocess.STARTUPINFO()
                startup_info.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startup_info.wShowWindow = 0
            out=subprocess.check_output(
                [exe, "--query-gpu=utilization.gpu,temperature.gpu", "--format=csv,noheader,nounits"],
                timeout=1, text=True, creationflags=creation_flags, startupinfo=startup_info
            ).strip()
            vals=[x.strip() for x in out.split(",")]
            if len(vals)>=2: return f"{vals[0]}% usage  ·  {vals[1]}°C"
        except Exception: pass
        return None

    def choose_color(self):
        color=QColorDialog.getColor(QColor(self.cfg.get("color",GOLD)),self,"Choose LED colour")
        if color.isValid():
            self.cfg["color"]=color.name()
            if self.mode_combo.currentText()=="Solid Colour": self.render_effect("Solid Colour")
    def make_sync(self):
        page=QWidget(); l=QVBoxLayout(page); l.setContentsMargins(0,0,0,0); l.setSpacing(14)
        c,cl=self.card("Screen Sync","Sample monitor-edge colors and stream them to your ESP32 over USB.")
        form=QFormLayout()
        self.monitor_combo=QComboBox()
        # Enumerate actual displays through MSS. MSS index 0 is the virtual desktop;
        # indices 1..N are individual monitors. Store a zero-based physical index.
        try:
            import mss
            with mss.mss() as display_probe:
                detected = display_probe.monitors[1:]
            for display_index, display in enumerate(detected):
                label = f"Display {display_index + 1}  ·  {display['width']} × {display['height']}"
                self.monitor_combo.addItem(label, display_index)
        except Exception as exc:
            self.monitor_combo.addItem("Primary display (detection unavailable)", 0)
        if self.monitor_combo.count() == 0:
            self.monitor_combo.addItem("Primary display", 0)
        saved_monitor = int(self.cfg.get("monitor", 0))
        saved_item = self.monitor_combo.findData(saved_monitor)
        self.monitor_combo.setCurrentIndex(saved_item if saved_item >= 0 else 0)
        self.monitor_combo.currentIndexChanged.connect(self.on_monitor_changed)
        form.addRow("Capture monitor",self.monitor_combo)
        self.fps_spin=QSpinBox(); self.fps_spin.setRange(5,30); self.fps_spin.setValue(int(self.cfg["fps"])); form.addRow("Update rate (FPS)",self.fps_spin)
        self.smooth_slider=QSlider(Qt.Orientation.Horizontal); self.smooth_slider.setRange(0,90); self.smooth_slider.setValue(int(self.cfg["smoothing"])); form.addRow("Color smoothing",self.smooth_slider)
        cl.addLayout(form)
        b=QPushButton("Start Screen Sync"); b.setObjectName("Primary"); b.clicked.connect(lambda: (self.mode_combo.setCurrentText("Screen Sync"),self.start_lighting()))
        cl.addWidget(b); l.addWidget(c); l.addStretch(); return page
    def on_monitor_changed(self, index):
        """Persist the selected physical display and restart active screen capture."""
        if index < 0 or not hasattr(self, "monitor_combo"):
            return
        selected = self.monitor_combo.currentData()
        if selected is None:
            selected = index
        self.cfg["monitor"] = int(selected)
        save_config(self.cfg)
        # A worker takes a snapshot of the monitor at startup, so restart it to
        # switch the real capture source (including combined Screen + Sound mode).
        if self.current_mode in ("Screen Sync", "Screen + Sound") and self.worker and self.worker.isRunning():
            self.start_lighting()
        self.set_status(f"Capture display set to {self.monitor_combo.currentText()}")

    def make_sound_sync(self):
        page=QWidget(); l=QVBoxLayout(page); l.setContentsMargins(0,0,0,0); l.setSpacing(14)
        c,cl=self.card("PC Audio Smart Sync","Captures Windows output audio locally (games, YouTube, music and movies). No microphone or internet required.")
        form=QFormLayout()
        self.sound_sensitivity=QSlider(Qt.Orientation.Horizontal); self.sound_sensitivity.setRange(1,100); self.sound_sensitivity.setValue(int(self.cfg.get("sound_sensitivity",55))); form.addRow("Sensitivity",self.sound_sensitivity)
        self.sound_bass=QSlider(Qt.Orientation.Horizontal); self.sound_bass.setRange(0,100); self.sound_bass.setValue(int(self.cfg.get("sound_bass_intensity",75))); form.addRow("Bass intensity",self.sound_bass)
        self.sound_speed=QSlider(Qt.Orientation.Horizontal); self.sound_speed.setRange(1,100); self.sound_speed.setValue(int(self.cfg.get("sound_reaction_speed",65))); form.addRow("Reaction speed",self.sound_speed)
        self.sound_min=QSlider(Qt.Orientation.Horizontal); self.sound_min.setRange(0,50); self.sound_min.setValue(int(self.cfg.get("sound_min_brightness",8))); form.addRow("Minimum brightness",self.sound_min)
        self.sound_max=QSlider(Qt.Orientation.Horizontal); self.sound_max.setRange(10,100); self.sound_max.setValue(int(self.cfg.get("sound_max_brightness",100))); form.addRow("Maximum brightness",self.sound_max)
        self.sound_palette=QComboBox(); self.sound_palette.addItems(["Neon","Warm","Cool"]); self.sound_palette.setCurrentText(self.cfg.get("sound_palette","Neon")); form.addRow("Color palette",self.sound_palette)
        for control in (self.sound_sensitivity,self.sound_bass,self.sound_speed,self.sound_min,self.sound_max):
            control.valueChanged.connect(self.persist_sound_settings)
        self.sound_palette.currentTextChanged.connect(self.persist_sound_settings)
        cl.addLayout(form)
        row=QHBoxLayout(); b=QPushButton("Start Sound Sync"); b.setObjectName("Primary"); b.clicked.connect(lambda: (self.mode_combo.setCurrentText("Sound Sync"),self.start_lighting())); row.addWidget(b)
        b2=QPushButton("Start Screen + Sound"); b2.clicked.connect(lambda: (self.mode_combo.setCurrentText("Screen + Sound"),self.start_lighting())); row.addWidget(b2); cl.addLayout(row)
        save=QPushButton("Save Sound Settings"); save.clicked.connect(self.save_sound_settings); cl.addWidget(save)
        note=QLabel("Smart Sync combines low-frequency bass, mids, highs and overall audio energy. If loopback capture fails, install the requirements again and check the selected Windows output device."); note.setObjectName("SubTitle"); note.setWordWrap(True); cl.addWidget(note)
        l.addWidget(c); l.addStretch(); return page

    def persist_sound_settings(self, *_args):
        if not all(hasattr(self, name) for name in ("sound_sensitivity","sound_bass","sound_speed","sound_min","sound_max","sound_palette")):
            return
        self.cfg.update({"sound_sensitivity":self.sound_sensitivity.value(),"sound_bass_intensity":self.sound_bass.value(),"sound_reaction_speed":self.sound_speed.value(),"sound_min_brightness":self.sound_min.value(),"sound_max_brightness":max(self.sound_min.value(),self.sound_max.value()),"sound_palette":self.sound_palette.currentText()})
        save_config(self.cfg)

    def save_sound_settings(self):
        self.persist_sound_settings()
        self.set_status("Sound Sync preferences saved")
        QMessageBox.information(self,"Sound settings saved","Your Sound Sync preferences have been saved.")

    def make_effects(self):
        page=QWidget(); l=QVBoxLayout(page); l.setContentsMargins(0,0,0,0); grid=QGridLayout(); grid.setSpacing(14)
        effects=[("Screen Sync","Match your monitor edge colors"),("Sound Sync","React to PC audio: bass, beats and spectrum"),("Screen + Sound","Combine screen colors with audio energy"),("Solid Colour","One precise color across the strip"),("Rainbow","A moving spectrum"),("Breathing","Soft pulsing light"),("Gold Chase","Brand-inspired traveling gold glow")]
        for i,(name,desc) in enumerate(effects):
            c,cl=self.card(name,desc); b=QPushButton("Activate effect"); b.clicked.connect(lambda checked=False,n=name:self.activate_effect(n)); cl.addWidget(b); grid.addWidget(c,i//2,i%2)
        l.addLayout(grid); l.addStretch(); return page
    def make_layout(self):
        page = QWidget()
        outer = QVBoxLayout(page)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(12)

        card, cl = self.card(
            "Custom LED layout",
            "Arrange your own monitor perimeter. Set the number of LEDs on each edge, choose the first LED corner and strip direction, then save."
        )
        grid = QGridLayout()
        grid.setHorizontalSpacing(18)
        grid.setVerticalSpacing(10)

        self.count_spin = QSpinBox()
        self.count_spin.setRange(1, 600)
        self.count_spin.setValue(int(self.cfg["led_count"]))
        self.top_spin = QSpinBox()
        self.top_spin.setRange(0, 600)
        self.top_spin.setValue(int(self.cfg["top"]))
        self.right_spin = QSpinBox()
        self.right_spin.setRange(0, 600)
        self.right_spin.setValue(int(self.cfg["right"]))
        self.bottom_spin = QSpinBox()
        self.bottom_spin.setRange(0, 600)
        self.bottom_spin.setValue(int(self.cfg["bottom"]))
        self.left_spin = QSpinBox()
        self.left_spin.setRange(0, 600)
        self.left_spin.setValue(int(self.cfg["left"]))
        self.pin_spin = QSpinBox()
        self.pin_spin.setRange(0, 48)
        self.pin_spin.setValue(int(self.cfg["pin"]))

        self.start_corner_combo = QComboBox()
        self.start_corner_combo.addItems(["Top-left", "Top-right", "Bottom-right", "Bottom-left"])
        self.start_corner_combo.setCurrentText(self.cfg.get("start_corner", "Bottom-right"))
        self.direction_combo = QComboBox()
        self.direction_combo.addItems(["Clockwise", "Counter-clockwise"])
        self.direction_combo.setCurrentText(self.cfg.get("direction", "Counter-clockwise"))

        controls = QFrame()
        controls.setObjectName("Card")
        form = QFormLayout(controls)
        form.setContentsMargins(16, 16, 16, 16)
        form.setSpacing(10)
        form.addRow("Total LEDs", self.count_spin)
        form.addRow("Top edge", self.top_spin)
        form.addRow("Right edge", self.right_spin)
        form.addRow("Bottom edge", self.bottom_spin)
        form.addRow("Left edge", self.left_spin)
        form.addRow("First LED corner", self.start_corner_combo)
        form.addRow("Strip direction", self.direction_combo)
        form.addRow("Firmware data pin (reference)", self.pin_spin)
        grid.addWidget(controls, 0, 0)

        self.layout_diagram = PerimeterLayoutPreview()
        grid.addWidget(self.layout_diagram, 0, 1)
        for spin in [self.count_spin, self.top_spin, self.right_spin, self.bottom_spin, self.left_spin]:
            spin.valueChanged.connect(self.refresh_layout_diagram)
        self.start_corner_combo.currentTextChanged.connect(self.refresh_layout_diagram)
        self.direction_combo.currentTextChanged.connect(self.refresh_layout_diagram)
        cl.addLayout(grid)

        self.layout_total_label = QLabel()
        self.layout_total_label.setStyleSheet(f"color:{MUTED};padding:4px;")
        cl.addWidget(self.layout_total_label)
        buttons = QHBoxLayout()
        save = QPushButton("Save layout")
        save.setObjectName("Primary")
        save.clicked.connect(self.save_layout)
        reset = QPushButton("Reset to 42 LEDs")
        reset.clicked.connect(self.reset_layout)
        buttons.addWidget(save)
        buttons.addWidget(reset)
        buttons.addStretch()
        cl.addLayout(buttons)
        outer.addWidget(card)
        outer.addStretch()
        self.refresh_layout_diagram()
        return page

    def refresh_layout_diagram(self, *_):
        if not hasattr(self, "layout_diagram"):
            return
        counts = {
            "top": self.top_spin.value(),
            "right": self.right_spin.value(),
            "bottom": self.bottom_spin.value(),
            "left": self.left_spin.value(),
        }
        total = sum(counts.values())
        declared = self.count_spin.value()
        self.layout_diagram.set_layout(counts, self.start_corner_combo.currentText(), self.direction_combo.currentText())
        ok = total == declared
        color = GOLD if ok else "#f06b6b"
        self.layout_total_label.setText(f"Edge total: {total} LEDs  /  Total LEDs setting: {declared}  —  " +
                                        ("Ready to save" if ok else f"Mismatch: adjust by {declared-total:+d} LEDs"))
        self.layout_total_label.setStyleSheet(f"color:{color};padding:4px;")

    def reset_layout(self):
        self.count_spin.setValue(42)
        self.top_spin.setValue(15)
        self.right_spin.setValue(8)
        self.bottom_spin.setValue(11)
        self.left_spin.setValue(8)
        self.start_corner_combo.setCurrentText("Bottom-right")
        self.direction_combo.setCurrentText("Counter-clockwise")
        self.refresh_layout_diagram()

    def make_calibration(self):
        page=QWidget(); outer=QVBoxLayout(page); outer.setContentsMargins(0,0,0,0); outer.setSpacing(12)
        card,cl=self.card("Light Area Calibration","Set the percentage of each screen edge sampled for the corresponding LED zone. The colored canvas updates live; save to apply to Screen Sync.")
        self.light_canvas=LightAreaCanvas(); cl.addWidget(self.light_canvas)
        grid=QGridLayout(); self.area_sliders={}
        for row,side in enumerate(("top","right","bottom","left")):
            label=QLabel(side.title()+" sampling area"); label.setMinimumWidth(145)
            slider=QSlider(Qt.Orientation.Horizontal); slider.setRange(1,30); slider.setValue(int(self.cfg.get("sample_"+side,7)))
            value=QLabel(f"{slider.value()}%"); value.setMinimumWidth(40)
            slider.valueChanged.connect(lambda v,s=side,l=value: (l.setText(f"{v}%"), self.update_area_canvas()))
            grid.addWidget(label,row,0); grid.addWidget(slider,row,1); grid.addWidget(value,row,2); self.area_sliders[side]=slider
        cl.addLayout(grid); self.update_area_canvas()
        buttons=QHBoxLayout(); save=QPushButton("Save & Apply Calibration"); save.setObjectName("Primary"); save.clicked.connect(self.save_calibration); buttons.addWidget(save)
        reset=QPushButton("Reset to 7%"); reset.clicked.connect(lambda: [self.area_sliders[s].setValue(7) for s in self.area_sliders]); buttons.addWidget(reset); cl.addLayout(buttons)
        note=QLabel("Tip: 5–10% is a good starting point. Larger areas blend more of the screen; smaller areas react closer to the edges. These settings are persisted and used by the Screen Sync capture worker."); note.setObjectName("SubTitle"); note.setWordWrap(True); cl.addWidget(note)
        outer.addWidget(card); outer.addStretch(); return page
    def update_area_canvas(self):
        if hasattr(self,"light_canvas"):
            self.light_canvas.set_areas({s:self.area_sliders[s].value() for s in self.area_sliders})
    def save_calibration(self):
        for side,slider in self.area_sliders.items(): self.cfg["sample_"+side]=slider.value()
        save_config(self.cfg)
        if getattr(self,"current_mode","")=="Screen Sync" and self.serial.ser and self.serial.ser.is_open:
            self.start_lighting()
        QMessageBox.information(self,"Calibration saved","Screen sampling areas saved. They will be used by Screen Sync now and on future launches.")

    def make_profiles(self):
        page=QWidget(); l=QVBoxLayout(page); l.setContentsMargins(0,0,0,0)
        c,cl=self.card("Lighting profiles","Save your current mode, brightness, layout, and startup preferences.")
        self.profile_name=QLineEdit("My setup"); self.profile_name.setPlaceholderText("Profile name"); cl.addWidget(self.profile_name)
        row=QHBoxLayout(); b=QPushButton("Save profile"); b.setObjectName("Primary"); b.clicked.connect(self.save_profile); row.addWidget(b)
        b2=QPushButton("Load profile"); b2.clicked.connect(self.load_profile); row.addWidget(b2)
        b3=QPushButton("Export settings"); b3.clicked.connect(self.export_settings); row.addWidget(b3)
        cl.addLayout(row); self.profile_status=QLabel("Profiles are stored locally."); self.profile_status.setObjectName("SubTitle"); cl.addWidget(self.profile_status)
        l.addWidget(c); l.addStretch(); return page
    def make_devices(self):
        page=QWidget(); l=QVBoxLayout(page); l.setContentsMargins(0,0,0,0)
        c,cl=self.card("USB device","Connect to an ESP32 running compatible LED CNTRL serial firmware.")
        form=QFormLayout()
        self.port_combo=QComboBox(); form.addRow("Serial port",self.port_combo)
        refresh=QPushButton("Refresh ports now"); refresh.clicked.connect(self.refresh_ports); form.addRow("",refresh)
        self.baud_combo=QComboBox(); self.baud_combo.addItems(["115200","230400","57600","9600"]); self.baud_combo.setCurrentText(str(self.cfg["baud"])); form.addRow("Baud rate",self.baud_combo)
        cl.addLayout(form)
        row=QHBoxLayout(); self.connect_btn=QPushButton("Connect"); self.connect_btn.setObjectName("Primary"); self.connect_btn.clicked.connect(self.connect_device)
        self.disconnect_btn=QPushButton("Disconnect"); self.disconnect_btn.clicked.connect(self.disconnect_device)
        row.addWidget(self.connect_btn); row.addWidget(self.disconnect_btn); cl.addLayout(row)
        self.device_status=QLabel("Disconnected"); self.device_status.setWordWrap(True); cl.addWidget(self.device_status)
        proto=QLabel("Protocol: newline-terminated comma-separated RGB values (R,G,B repeated for each LED). Firmware LED count/order must match the saved layout.")
        proto.setObjectName("SubTitle"); proto.setWordWrap(True); cl.addWidget(proto)
        l.addWidget(c); l.addStretch(); return page
    def make_settings(self):
        page=QWidget(); l=QVBoxLayout(page); l.setContentsMargins(0,0,0,0); l.setSpacing(14)
        c,cl=self.card("Application preferences","Configure startup behavior and your preferred experience.")
        self.autostart_check=QCheckBox("Start LED CNTRL when Windows starts"); self.autostart_check.setChecked(bool(self.cfg["launch_windows"])); cl.addWidget(self.autostart_check)
        self.minimize_start_check=QCheckBox("Minimize to system tray on startup"); self.minimize_start_check.setChecked(bool(self.cfg.get("minimize_on_start", True))); cl.addWidget(self.minimize_start_check)
        self.tray_check=QCheckBox("Minimize to system tray when closing"); self.tray_check.setChecked(bool(self.cfg["minimize_tray"])); cl.addWidget(self.tray_check)
        self.animation_check=QCheckBox("Play two-pass gold LED startup animation"); self.animation_check.setChecked(bool(self.cfg["startup_animation"])); cl.addWidget(self.animation_check)
        self.restore_check=QCheckBox("Restore previous lighting mode after startup animation"); self.restore_check.setChecked(bool(self.cfg["restore_mode"])); cl.addWidget(self.restore_check)
        self.auto_refresh_check=QCheckBox("Automatically refresh USB/COM ports"); self.auto_refresh_check.setChecked(bool(self.cfg.get("auto_refresh_ports", True))); cl.addWidget(self.auto_refresh_check)
        self.auto_reconnect_check=QCheckBox("Automatically reconnect to the last selected port"); self.auto_reconnect_check.setChecked(bool(self.cfg.get("auto_reconnect", True))); cl.addWidget(self.auto_reconnect_check)
        b=QPushButton("Save settings"); b.setObjectName("Primary"); b.clicked.connect(self.save_settings); cl.addWidget(b)
        info=QLabel("Offline-first: lighting control runs locally. Screen Sync requires the optional capture dependencies; online access is not required.")
        info.setObjectName("SubTitle"); info.setWordWrap(True); cl.addWidget(info)
        l.addWidget(c); l.addStretch(); return page
    def navigate(self,name):
        names=["Home","Screen Sync","Sound Sync","Effects","LED Layout","Light Calibration","Profiles","Devices","Settings"]
        idx=names.index(name)
        self.pages.setCurrentIndex(idx); self.page_title.setText(name)
        subs={"Home":"Your lighting, perfectly in sync.","Screen Sync":"Bring the colors on your display to life.","Sound Sync":"Make your LEDs react to PC audio in real time.","Effects":"Choose a lighting style for your space.","LED Layout":"Configure your physical LED perimeter.","Light Calibration":"Adjust the screen areas sampled by each LED edge.","Profiles":"Keep your favorite setups one click away.","Devices":"Manage USB-connected controllers.","Settings":"Make LED CNTRL work your way."}
        self.page_sub.setText(subs[name])
        for n,b in self.nav_buttons.items(): b.setChecked(n==name)
    def set_status(self,msg):
        self.statusBar().showMessage(msg)
        if "Connected" in msg and "failed" not in msg.lower():
            self.connection_badge.setText("●  CONNECTED"); self.connection_badge.setStyleSheet(f"color:#a9d18e;background:#1e2a20;border:1px solid #3a5a3b;border-radius:12px;padding:9px 13px;")
            self.home_connection.setText("ESP32 connected"); self.home_connection.setStyleSheet("font-size:12pt;color:#a9d18e;")
        elif "Disconnected" in msg or "failed" in msg.lower():
            self.connection_badge.setText("●  DISCONNECTED"); self.connection_badge.setStyleSheet(f"color:{GOLD};background:#27251e;border:1px solid #51452b;border-radius:12px;padding:9px 13px;")
            self.home_connection.setText("ESP32 not connected"); self.home_connection.setStyleSheet(f"font-size:12pt;color:{MUTED};")
        if hasattr(self,"device_status"): self.device_status.setText(msg)
    def auto_refresh_ports(self):
        """Refresh the port list without disrupting an active serial connection."""
        if not self.cfg.get("auto_refresh_ports", True):
            return
        if self.serial.ser and getattr(self.serial.ser, "is_open", False):
            return
        if hasattr(self, "port_combo"):
            old = self.port_combo.currentData()
            available = [p for p, _ in self.serial.ports()]
            if old not in available or not available:
                self.refresh_ports()
            # If a previously selected device returns, reconnect only when enabled.
            wanted = self.cfg.get("port", "")
            if wanted and wanted in available and self.cfg.get("auto_reconnect", True):
                self.connect_saved_port(wanted)

    def connect_saved_port(self, port):
        try:
            baud = int(self.cfg.get("baud", 115200))
            if self.serial.connect_port(port, baud):
                if hasattr(self, "port_combo"):
                    idx = self.port_combo.findData(port)
                    if idx >= 0:
                        self.port_combo.setCurrentIndex(idx)
                self.port_overview.setText(f"{port} · {baud} baud")
                if self.cfg.get("startup_animation", True):
                    self.begin_startup_animation()
        except Exception as exc:
            self.set_status(f"Auto-reconnect failed · {exc}")

    def refresh_ports(self):
        if not hasattr(self,"port_combo"): return
        previous=self.cfg.get("port","")
        self.port_combo.clear()
        ports=self.serial.ports()
        if not ports: self.port_combo.addItem("No serial ports found","")
        else:
            for p,label in ports: self.port_combo.addItem(label,p)
        idx=self.port_combo.findData(previous)
        if idx>=0: self.port_combo.setCurrentIndex(idx)
    def connect_device(self):
        port=self.port_combo.currentData()
        if not port:
            QMessageBox.warning(self,"No serial port","Connect the ESP32 over USB and refresh the port list.")
            return
        ok=self.serial.connect_port(port,int(self.baud_combo.currentText()))
        if ok:
            self.cfg["port"]=port; self.cfg["baud"]=int(self.baud_combo.currentText()); save_config(self.cfg)
            self.port_overview.setText(f"{port} · {self.cfg['baud']} baud")
            if self.cfg.get("startup_animation"): self.begin_startup_animation()
    def disconnect_device(self):
        self.stop_worker(); self.serial.disconnect_port(); self.set_status("Disconnected")
    def begin_startup_animation(self):
        if not self.serial.ser or not self.serial.ser.is_open:
            self.set_status("Startup animation waiting · connect ESP32 to run on physical LEDs")
            return
        self.stop_worker()
        self.anim_step=0; self.anim_passes=0; self.anim_running=True
        self.current_mode="Startup Animation"; self.active_effect.setText("●  Gold brand animation · 0/2 passes")
        self.animation_timer.start(35)
        self.set_status("Running two-pass gold startup animation")
    def startup_step(self):
        n=int(self.cfg["led_count"])
        if n<1: return
        colors=[QColor("#100f0c") for _ in range(n)]
        head=self.anim_step % n
        for tail in range(7):
            idx=(head-tail)%n
            intensity=max(0,255-tail*32)
            colors[idx]=QColor(intensity, int(intensity*.72), int(intensity*.30))
        self.send_frame(colors)
        self.anim_step += 1
        if self.anim_step % n == 0:
            self.anim_passes += 1
            self.active_effect.setText(f"●  Gold brand animation · {min(2,self.anim_passes)}/2 passes")
            if self.anim_passes >= 2:
                self.animation_timer.stop(); self.anim_running=False
                self.set_status("Startup animation complete")
                if self.cfg.get("restore_mode",True):
                    QTimer.singleShot(120, self.start_lighting)
                else: self.current_mode="Idle"
    def ai_settings_changed(self, *_args):
        self.cfg["ai_auto_brightness"] = bool(self.ai_auto_check.isChecked())
        self.cfg["ai_scene_analysis"] = bool(self.ai_scene_check.isChecked())
        self.cfg["ai_color_calibration"] = bool(self.ai_calibration_check.isChecked())
        self.cfg["ai_profile"] = self.ai_profile_combo.currentText()
        for key, slider in self.wb_sliders.items():
            self.cfg[key] = slider.value() / 100.0
        save_config(self.cfg)
        if self.worker and self.worker.isRunning():
            self.worker.ai_auto_brightness = self.cfg["ai_auto_brightness"]
            self.worker.ai_scene_analysis = self.cfg["ai_scene_analysis"]
            self.worker.ai_color_calibration = self.cfg["ai_color_calibration"]
            self.worker.white_balance = (self.cfg["white_balance_r"], self.cfg["white_balance_g"], self.cfg["white_balance_b"])
            self.worker.ai_profile = self.cfg["ai_profile"]
        if hasattr(self, "ai_status"):
            self.ai_status.setText("AI settings saved · applied live where supported")

    def run_ai_command(self):
        command = self.ai_command.text().strip().lower()
        if not command:
            return
        try:
            if command in ("lights off", "turn off", "off", "stop"):
                self.lights_off()
            elif command in ("screen sync", "sync", "ambilight"):
                self.mode_combo.setCurrentText("Screen Sync"); self.start_lighting()
            elif command in ("white", "pure white", "set white"):
                self.cfg["color"] = "#ffffff"; self.mode_combo.setCurrentText("Solid Colour"); self.start_lighting()
            elif command in ("red", "blue", "green", "purple", "cyan", "yellow"):
                colors = {"red":"#ff0000", "blue":"#0000ff", "green":"#00ff00", "purple":"#8000ff", "cyan":"#00ffff", "yellow":"#ffff00"}
                self.cfg["color"] = colors[command]; self.mode_combo.setCurrentText("Solid Colour"); self.start_lighting()
            elif "gaming" in command:
                self.ai_profile_combo.setCurrentText("Gaming"); self.mode_combo.setCurrentText("Screen Sync"); self.start_lighting()
            elif "movie" in command or "cinema" in command:
                self.ai_profile_combo.setCurrentText("Movie"); self.mode_combo.setCurrentText("Screen Sync"); self.start_lighting()
            elif "adaptive" in command:
                self.ai_profile_combo.setCurrentText("Adaptive"); self.mode_combo.setCurrentText("Screen Sync"); self.start_lighting()
            elif command.startswith("brightness"):
                digits = "".join(ch for ch in command if ch.isdigit())
                if not digits: raise ValueError("Try 'brightness 45'.")
                value = max(1, min(100, int(digits))); self.brightness.setValue(value)
            elif command in ("reset white balance", "white balance reset", "reset calibration"):
                for key, value in (("white_balance_r",115),("white_balance_g",100),("white_balance_b",82)):
                    self.wb_sliders[key].setValue(value)
            else:
                raise ValueError("Command not recognized. Try brightness 45, gaming mode, movie mode, screen sync, white, or lights off.")
            self.ai_command.clear()
            self.ai_status.setText(f"Assistant applied: {command}")
            save_config(self.cfg)
        except Exception as exc:
            QMessageBox.information(self, "Lighting assistant", str(exc))

    def start_voice_listening(self):
        model_path = APP_DIR / "vosk-model"
        if not model_path.exists():
            QMessageBox.information(self, "Offline voice control setup",
                "To enable fully offline voice recognition:\n\n"
                "1. Install the optional packages: pip install vosk sounddevice\n"
                "2. Download and extract an English Vosk speech model.\n"
                "3. Rename the extracted model folder to 'vosk-model' and place it here:\n\n"
                + str(APP_DIR) + "\n\nThen click Voice command again. The app does not upload audio.")
            return
        self.voice_worker = VoiceCommandWorker(model_path)
        self.voice_worker.status.connect(self.set_ai_status)
        self.voice_worker.recognized.connect(self.accept_voice_command)
        self.voice_worker.start()

    def set_ai_status(self, message):
        if hasattr(self, "ai_status"):
            self.ai_status.setText(message)
        self.set_status(message)

    def accept_voice_command(self, command):
        if hasattr(self, "ai_command"):
            self.ai_command.setText(command)
            self.run_ai_command()

    def brightness_changed(self, value):
        # Persist the brightness immediately so it survives closing/restarting LED CNTRL.
        value = max(1, min(100, int(value)))
        self.cfg["brightness"] = value
        self.bright_label.setText(f"Brightness  {value}%")
        save_config(self.cfg)

        # Apply changes live in Screen Sync without restarting the capture worker.
        if self.current_mode == "Screen Sync" and self.worker and self.worker.isRunning():
            self.worker.brightness = value
        elif self.current_mode not in ("Startup Animation", "Idle"):
            self.render_effect(self.current_mode)
    def change_mode(self,mode):
        self.cfg["mode"]=mode
        if mode and self.current_mode not in ("Startup Animation",): self.current_mode=mode
    def activate_effect(self,name):
        self.mode_combo.setCurrentText(name)
        self.current_mode=name
        self.start_lighting()
    def start_lighting(self):
        if not self.serial.ser or not self.serial.ser.is_open:
            self.navigate("Devices")
            QMessageBox.information(self,"Connect your ESP32","Connect the ESP32 over USB before starting lighting.")
            return
        self.stop_worker()
        mode=self.mode_combo.currentText()
        self.current_mode=mode
        self.active_effect.setText(f"●  {mode} active")
        if mode=="Screen Sync":
            self.worker=ScreenWorker(int(self.cfg["led_count"]), int(getattr(self,"fps_spin",None).value() if hasattr(self,"fps_spin") else self.cfg["fps"]), int(getattr(self,"smooth_slider",None).value() if hasattr(self,"smooth_slider") else self.cfg["smoothing"]), int(self.cfg["brightness"]), int(self.cfg.get("monitor",0)), top=self.cfg.get("top",15), right=self.cfg.get("right",8), bottom=self.cfg.get("bottom",11), left=self.cfg.get("left",8), start_corner=self.cfg.get("start_corner","Bottom-right"), direction=self.cfg.get("direction","Counter-clockwise"), ai_auto_brightness=self.cfg.get("ai_auto_brightness",True), ai_scene_analysis=self.cfg.get("ai_scene_analysis",True), ai_color_calibration=self.cfg.get("ai_color_calibration",True), white_balance=(self.cfg.get("white_balance_r",1.15),self.cfg.get("white_balance_g",1.0),self.cfg.get("white_balance_b",0.82)), ai_profile=self.cfg.get("ai_profile","Adaptive"), sample_areas={side:int(self.cfg.get("sample_"+side,7)) for side in ("top","right","bottom","left")})
            self.worker.frame.connect(self.send_frame); self.worker.status.connect(self.set_status); self.worker.start()
        elif mode in ("Sound Sync", "Screen + Sound"):
            self.cfg.update({"sound_sensitivity":self.sound_sensitivity.value() if hasattr(self,"sound_sensitivity") else self.cfg.get("sound_sensitivity",55),
                "sound_bass_intensity":self.sound_bass.value() if hasattr(self,"sound_bass") else self.cfg.get("sound_bass_intensity",75),
                "sound_reaction_speed":self.sound_speed.value() if hasattr(self,"sound_speed") else self.cfg.get("sound_reaction_speed",65),
                "sound_min_brightness":self.sound_min.value() if hasattr(self,"sound_min") else self.cfg.get("sound_min_brightness",8),
                "sound_max_brightness":self.sound_max.value() if hasattr(self,"sound_max") else self.cfg.get("sound_max_brightness",100),
                "sound_palette":self.sound_palette.currentText() if hasattr(self,"sound_palette") else self.cfg.get("sound_palette","Neon")})
            save_config(self.cfg)
            self.worker=SoundSyncWorker(int(self.cfg["led_count"]), int(self.cfg.get("fps",20)), int(self.cfg["brightness"]),
                sensitivity=self.cfg.get("sound_sensitivity",55), reaction_speed=self.cfg.get("sound_reaction_speed",65),
                bass_intensity=self.cfg.get("sound_bass_intensity",75), min_brightness=self.cfg.get("sound_min_brightness",8),
                max_brightness=self.cfg.get("sound_max_brightness",100), palette=self.cfg.get("sound_palette","Neon"),
                combined=(mode=="Screen + Sound"), monitor=int(self.cfg.get("monitor",0)), top=self.cfg.get("top",15),
                right=self.cfg.get("right",8), bottom=self.cfg.get("bottom",11), left=self.cfg.get("left",8),
                start_corner=self.cfg.get("start_corner","Bottom-right"), direction=self.cfg.get("direction","Counter-clockwise"),
                smoothing=self.cfg.get("smoothing",35), sample_areas={side:int(self.cfg.get("sample_"+side,7)) for side in ("top","right","bottom","left")})
            self.worker.frame.connect(self.send_frame); self.worker.status.connect(self.set_status); self.worker.start()
        else:
            self.effect_timer=QTimer(self); self.effect_phase=0
            self.effect_timer.timeout.connect(lambda:self.render_effect(mode))
            self.effect_timer.start(max(25,int(1000/max(5,int(self.cfg["fps"])))))
            self.render_effect(mode)
        save_config(self.cfg)
        self.set_status(f"Lighting active · {mode}")
    def stop_worker(self):
        if self.worker and self.worker.isRunning():
            self.worker.stop(); self.worker.wait(1200)
        self.worker=None
        if hasattr(self,"effect_timer") and self.effect_timer.isActive(): self.effect_timer.stop()
        self.animation_timer.stop(); self.anim_running=False
    def render_effect(self,mode):
        n=int(self.cfg["led_count"]); phase=getattr(self,"effect_phase",0); self.effect_phase=phase+1
        bright=int(self.cfg["brightness"])/100
        out=[]
        if mode=="Solid Colour":
            col=QColor(self.cfg.get("color",GOLD))
            out=[QColor(int(col.red()*bright),int(col.green()*bright),int(col.blue()*bright)) for _ in range(n)]
        elif mode=="Breathing":
            k=(math.sin(phase*.09)+1)/2
            out=[QColor(int(214*bright*k),int(173*bright*k),int(85*bright*k)) for _ in range(n)]
        elif mode=="Gold Chase":
            head=phase%n
            for i in range(n):
                d=(head-i)%n; k=max(0,1-d/8)*bright
                out.append(QColor(int(214*k),int(173*k),int(85*k)))
        else: # Rainbow
            for i in range(n):
                h=((i/max(1,n))+phase*.006)%1
                c=QColor.fromHsvF(h,.88,.95*bright)
                out.append(c)
        self.send_frame(out)
    def send_frame(self,colors):
        if not colors: return
        self.colors=colors
        self.preview.set_colors(colors)
        self.serial.send_rgb(colors)
    def lights_off(self):
        self.stop_worker()
        self.current_mode="Idle"
        self.colors=[QColor("#000000") for _ in range(int(self.cfg["led_count"]))]
        self.send_frame(self.colors)
        self.active_effect.setText("●  Lights off")
        self.set_status("Lights off")
    def save_layout(self):
        total = sum([self.top_spin.value(), self.right_spin.value(), self.bottom_spin.value(), self.left_spin.value()])
        if total != self.count_spin.value():
            QMessageBox.warning(self, "LED count mismatch",
                                f"Your edge counts add up to {total}, but Total LEDs is {self.count_spin.value()}. Make them match before saving.")
            return
        self.cfg.update({
            "led_count": self.count_spin.value(),
            "top": self.top_spin.value(),
            "right": self.right_spin.value(),
            "bottom": self.bottom_spin.value(),
            "left": self.left_spin.value(),
            "pin": self.pin_spin.value(),
            "start_corner": self.start_corner_combo.currentText(),
            "direction": self.direction_combo.currentText(),
        })
        self.colors = [QColor("#202124") for _ in range(self.cfg["led_count"])]
        if hasattr(self, "preview"):
            self.preview.count = self.cfg["led_count"]
            self.preview.set_colors(self.colors)
        save_config(self.cfg)
        # Apply the new mapping immediately if Screen Sync is currently running.
        if getattr(self, "current_mode", "") == "Screen Sync" and self.serial.ser and self.serial.ser.is_open:
            self.start_lighting()
        QMessageBox.information(self, "Layout saved",
                                "Layout saved and Screen Sync restarted with the new edge counts and direction. The ESP32 firmware must support the same total LED count.")
    def save_profile(self):
        name=self.profile_name.text().strip() or "My setup"
        path=APP_DIR / "profiles"; path.mkdir(parents=True,exist_ok=True)
        (path/(name.replace("/","_").replace("\\","_")+".json")).write_text(json.dumps(self.cfg,indent=2),encoding="utf-8")
        self.profile_status.setText(f"Saved profile: {name}")
    def load_profile(self):
        path=APP_DIR/"profiles"
        if not path.exists():
            QMessageBox.information(self,"No profiles","Save a profile first."); return
        files=sorted(path.glob("*.json"))
        if not files:
            QMessageBox.information(self,"No profiles","Save a profile first."); return
        from PySide6.QtWidgets import QInputDialog
        names=[f.stem for f in files]
        name,ok=QInputDialog.getItem(self,"Load profile","Choose profile",names,0,False)
        if ok and name:
            self.cfg.update(json.loads((path/(name+".json")).read_text(encoding="utf-8")))
            save_config(self.cfg); self.profile_status.setText(f"Loaded profile: {name}")
            self.brightness.setValue(int(self.cfg["brightness"])); self.mode_combo.setCurrentText(self.cfg["mode"])
    def export_settings(self):
        from PySide6.QtWidgets import QFileDialog
        path,_=QFileDialog.getSaveFileName(self,"Export settings","led-cntrl-settings.json","JSON files (*.json)")
        if path: Path(path).write_text(json.dumps(self.cfg,indent=2),encoding="utf-8")
    def save_settings(self):
        self.cfg["launch_windows"]=self.autostart_check.isChecked()
        self.cfg["minimize_on_start"]=self.minimize_start_check.isChecked()
        self.cfg["minimize_tray"]=self.tray_check.isChecked()
        self.cfg["startup_animation"]=self.animation_check.isChecked()
        self.cfg["restore_mode"]=self.restore_check.isChecked()
        self.cfg["auto_refresh_ports"]=self.auto_refresh_check.isChecked()
        self.cfg["auto_reconnect"]=self.auto_reconnect_check.isChecked()
        save_config(self.cfg)
        self.set_autostart(self.cfg["launch_windows"])
        QMessageBox.information(self,"Settings saved","Your preferences have been saved.")
    def set_autostart(self, enabled):
        """Create/remove a per-user Windows Startup shortcut."""
        try:
            startup = Path(os.getenv("APPDATA", str(Path.home()))) / "Microsoft/Windows/Start Menu/Programs/Startup"
            startup.mkdir(parents=True, exist_ok=True)
            shortcut = startup / "LED CNTRL.lnk"
            if not enabled:
                if shortcut.exists():
                    shortcut.unlink()
                self.set_status("Windows startup disabled")
                return

            import win32com.client
            shell = win32com.client.Dispatch("WScript.Shell")
            sc = shell.CreateShortCut(str(shortcut))
            if getattr(sys, "frozen", False):
                sc.Targetpath = str(Path(sys.executable).resolve())
                sc.Arguments = ""
                sc.WorkingDirectory = str(Path(sys.executable).resolve().parent)
            else:
                sc.Targetpath = str(Path(sys.executable).resolve())
                sc.Arguments = '"' + str(Path(__file__).resolve()) + '"'
                sc.WorkingDirectory = str(Path(__file__).resolve().parent)
            sc.Description = "Start LED CNTRL with Windows"
            sc.save()
            self.set_status("LED CNTRL will start with Windows")
        except Exception as e:
            self.set_status(f"Could not update Windows startup shortcut: {e}")

    def closeEvent(self,event):
        save_config(self.cfg)
        if self.cfg.get("minimize_tray", True) and self.tray and self.tray.isVisible() and not self._really_quit:
            # Closing the window hides it; lighting and USB control continue running.
            self.hide()
            self.tray.showMessage(
                "LED CNTRL",
                "Still running in the system tray. Choose Exit LED CNTRL to stop lighting control.",
                QSystemTrayIcon.MessageIcon.Information,
                2500
            )
            event.ignore()
            return
        self.stop_worker()
        self.serial.disconnect_port()
        if self.tray:
            self.tray.hide()
        event.accept()

def main():
    app=QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName("Keynes")
    w=MainWindow(); w.show()
    sys.exit(app.exec())

if __name__=="__main__":
    main()
