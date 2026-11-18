import math
import random
import time
import tkinter as tk
from collections import deque
from tkinter import ttk

# EcoGrow HMI - Simulador educativo de riego automatizado (versión visual mejorada)
# Requiere únicamente Python 3 y Tkinter.

BG = "#0b1220"
HEADER = "#0e1929"
PANEL = "#111c2e"
PANEL2 = "#17243a"
BORDER = "#263750"
TEXT = "#e7eef8"
MUTED = "#91a3ba"
GREEN = "#29c58a"
BLUE = "#39a9e8"
AMBER = "#f5b942"
RED = "#ef6464"
FONT = "Segoe UI"


# ----------------------------------------------------------------------
# Utilidades de color y dibujo
# ----------------------------------------------------------------------
def _rgb(c):
  c = c.lstrip("#")
  return tuple(int(c[i : i + 2], 16) for i in (0, 2, 4))


def mix(a, b, t):
  """Mezcla dos colores hex. t=0 -> a, t=1 -> b."""
  t = max(0.0, min(1.0, t))
  ra, rb = _rgb(a), _rgb(b)
  return "#%02x%02x%02x" % tuple(int(ra[i] + (rb[i] - ra[i]) * t) for i in range(3))


def clamp(v, lo, hi):
  return max(lo, min(hi, v))


def rrect(c, x1, y1, x2, y2, r=10, **kw):
  """Rectángulo redondeado."""
  pts = [
      x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r,
      x2, y2 - r, x2, y2, x2 - r, y2, x1 + r, y2,
      x1, y2, x1, y2 - r, x1, y1 + r, x1, y1,
  ]
  return c.create_polygon(pts, smooth=True, **kw)


def vgrad(c, x1, y1, x2, y2, c1, c2, steps=24):
  """Degradado vertical hecho con franjas."""
  for i in range(steps):
    ya = y1 + (y2 - y1) * i / steps
    yb = y1 + (y2 - y1) * (i + 1) / steps + 1
    c.create_rectangle(
        x1, ya, x2, yb, fill=mix(c1, c2, i / max(1, steps - 1)), outline=""
    )


def path_dots(c, pts, now, color, speed=70, gap=26, r=3):
  """Puntos que viajan a lo largo de una polilínea (flujo de agua / corriente)."""
  segs, total = [], 0
  for a, b in zip(pts, pts[1:]):
    length = math.hypot(b[0] - a[0], b[1] - a[1])
    segs.append((a, b, length))
    total += length
  if total <= 0:
    return
  for k in range(int(total // gap)):
    d = (now * speed + k * gap) % total
    for a, b, length in segs:
      if d <= length and length > 0:
        x = a[0] + (b[0] - a[0]) * d / length
        y = a[1] + (b[1] - a[1]) * d / length
        c.create_oval(x - r, y - r, x + r, y + r, fill=color, outline="")
        break
      d -= length


def flat(pts):
  return [v for p in pts for v in p]


# ----------------------------------------------------------------------
class EcoGrow:

  STATUS = {
      "idle": ("●  SISTEMA EN ESPERA", AMBER),
      "run": ("●  SIMULACIÓN EN MARCHA", GREEN),
      "pause": ("●  SIMULACIÓN PAUSADA", AMBER),
      "reset": ("●  SISTEMA REINICIADO", AMBER),
  }

  def __init__(self, root):
    self.root = root
    root.title("EcoGrow | Sistema de monitoreo de invernadero")
    root.geometry("1280x820")
    root.minsize(1050, 720)
    root.configure(bg=BG)

    self.humidity = tk.DoubleVar(value=34)
    self.temperature = tk.DoubleVar(value=24.5)
    self.on_limit = tk.DoubleVar(value=40)
    self.off_limit = tk.DoubleVar(value=60)
    self.pump_on = False
    self.running = False
    self.status_key = "idle"
    self.tank_level = 0.8
    self.last_tick = time.time()
    self.history_h = deque([34] * 36, maxlen=60)
    self.history_t = deque([24.5] * 36, maxlen=60)

    # Elementos decorativos con posiciones fijas
    rnd = random.Random(7)
    self.stars = [(rnd.random(), rnd.random(), rnd.random() * 6) for _ in range(55)]
    self.soil_dots = [(rnd.random(), rnd.random()) for _ in range(70)]
    self.clouds = [(0.10, 48, 1.0, 6), (0.45, 32, 0.8, 4), (0.78, 72, 1.2, 8)]

    self._style()
    self._build()
    self.update_all()
    self.animate()
    self.render()

  # ------------------------------------------------------------------
  def _style(self):
    style = ttk.Style()
    style.theme_use("clam")

  def panel(self, parent, title, subtitle=None):
    frame = tk.Frame(parent, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
    head = tk.Frame(frame, bg=PANEL)
    head.pack(fill="x", padx=15, pady=(12, 8))
    tk.Frame(head, bg=GREEN, width=3, height=14).pack(side="left", padx=(0, 8))
    tk.Label(
        head, text=title.upper(), bg=PANEL, fg=TEXT, font=(FONT, 10, "bold")
    ).pack(side="left")
    if subtitle:
      tk.Label(head, text=subtitle, bg=PANEL, fg=MUTED, font=(FONT, 8)).pack(
          side="right"
      )
    return frame

  # ------------------------------------------------------------------
  def _build(self):
    header = tk.Frame(self.root, bg=HEADER, height=68)
    header.pack(fill="x")
    header.pack_propagate(False)
    brand = tk.Frame(header, bg=HEADER)
    brand.pack(side="left", padx=22, pady=10)
    logo = tk.Canvas(brand, width=40, height=40, bg=HEADER, highlightthickness=0)
    logo.pack(side="left", padx=(0, 12))
    logo.create_oval(2, 2, 38, 38, fill="#12392f", outline=GREEN, width=2)
    logo.create_polygon(
        20, 8, 31, 22, 20, 33, 9, 22, fill=GREEN, outline="", smooth=False
    )
    logo.create_line(20, 14, 20, 32, fill="#0b1220", width=2)
    titles = tk.Frame(brand, bg=HEADER)
    titles.pack(side="left")
    tk.Label(
        titles, text="ECOGROW", fg=TEXT, bg=HEADER, font=(FONT, 15, "bold")
    ).pack(anchor="w")
    tk.Label(
        titles,
        text="GREENHOUSE CONTROL SYSTEM  /  HMI",
        fg=MUTED,
        bg=HEADER,
        font=(FONT, 8),
    ).pack(anchor="w")

    right_head = tk.Frame(header, bg=HEADER)
    right_head.pack(side="right", padx=24)
    self.header_status = tk.Label(
        right_head, text="", bg=HEADER, fg=AMBER, font=(FONT, 9, "bold")
    )
    self.header_status.pack(anchor="e")
    self.clock_label = tk.Label(
        right_head, text="", bg=HEADER, fg=MUTED, font=(FONT, 8)
    )
    self.clock_label.pack(anchor="e")
    tk.Frame(self.root, bg=GREEN, height=2).pack(fill="x")

    body = tk.Frame(self.root, bg=BG)
    body.pack(fill="both", expand=True, padx=16, pady=14)
    left = tk.Frame(body, bg=BG)
    left.pack(side="left", fill="both", expand=True, padx=(0, 12))
    right = tk.Frame(body, bg=BG, width=310)
    right.pack(side="right", fill="y")
    right.pack_propagate(False)

    # Tarjetas de resumen
    cards = tk.Frame(left, bg=BG)
    cards.pack(fill="x", pady=(0, 12))
    self.metric_h = self.metric_card(cards, "HUMEDAD DEL SUELO", "34.0", "%", BLUE)
    self.metric_t = self.metric_card(cards, "TEMPERATURA AMBIENTE", "24.5", "°C", AMBER)
    self.metric_p = self.metric_card(cards, "BOMBA DE RIEGO", "OFF", "", GREEN)
    self.metric_h.pack(side="left", fill="x", expand=True, padx=(0, 8))
    self.metric_t.pack(side="left", fill="x", expand=True, padx=4)
    self.metric_p.pack(side="left", fill="x", expand=True, padx=(8, 0))

    # Esquema visual
    schematic = self.panel(left, "Vista del proceso", "DIAGRAMA DEL INVERNADERO")
    schematic.pack(fill="both", expand=True, pady=(0, 12))
    self.diagram = tk.Canvas(
        schematic, bg="#0d1828", height=330, highlightthickness=0
    )
    self.diagram.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    # Gráficos
    charts = tk.Frame(left, bg=BG)
    charts.pack(fill="x")
    p1 = self.panel(charts, "Humedad del suelo", "HISTORIAL")
    p2 = self.panel(charts, "Temperatura", "HISTORIAL")
    p1.pack(side="left", fill="both", expand=True, padx=(0, 6))
    p2.pack(side="left", fill="both", expand=True, padx=(6, 0))
    self.chart_h = tk.Canvas(p1, bg=PANEL, height=130, highlightthickness=0)
    self.chart_t = tk.Canvas(p2, bg=PANEL, height=130, highlightthickness=0)
    self.chart_h.pack(fill="x", padx=8, pady=(0, 8))
    self.chart_t.pack(fill="x", padx=8, pady=(0, 8))
    self.chart_h.bind("<Configure>", lambda e: self.update_charts())
    self.chart_t.bind("<Configure>", lambda e: self.update_charts())

    # Controles laterales
    controls = self.panel(right, "Panel de experimentos", "AJUSTES EN VIVO")
    controls.pack(fill="x", pady=(0, 10))
    self.slider_block(controls, "Humedad simulada", self.humidity, 0, 100, "%", BLUE)
    self.slider_block(controls, "Temperatura simulada", self.temperature, 0, 50, "°C", AMBER)
    self.slider_block(controls, "Activar bomba en", self.on_limit, 5, 80, "%", GREEN)
    self.slider_block(controls, "Detener bomba en", self.off_limit, 20, 100, "%", GREEN)

    self.temp_effect_label = tk.Label(
        controls,
        text="EFECTO TÉRMICO: NORMAL",
        bg=PANEL,
        fg=AMBER,
        font=(FONT, 8, "bold"),
        justify="left",
        wraplength=265,
    )
    self.temp_effect_label.pack(anchor="w", padx=13, pady=(4, 12))

    actions = self.panel(right, "Control de simulación")
    actions.pack(fill="x", pady=(0, 10))
    btnrow = tk.Frame(actions, bg=PANEL)
    btnrow.pack(fill="x", padx=12, pady=(0, 12))
    self.make_button(btnrow, "▶  INICIAR", GREEN, self.start).pack(fill="x", pady=3)
    self.make_button(btnrow, "⏸  PAUSAR", AMBER, self.pause).pack(fill="x", pady=3)
    self.make_button(btnrow, "↺  REINICIAR", "#5d7896", self.reset).pack(fill="x", pady=3)

    status = self.panel(right, "Estado de componentes")
    status.pack(fill="both", expand=True)
    self.component_labels = {}
    for name, key in [
        ("Sensor de humedad", "sensor"),
        ("Sensor de temperatura", "temp"),
        ("Relé de control", "relay"),
        ("Bomba de agua", "pump"),
        ("Alimentación solar", "solar"),
    ]:
      row = tk.Frame(status, bg=PANEL2)
      row.pack(fill="x", padx=12, pady=3)
      tk.Label(row, text=name, bg=PANEL2, fg=MUTED, font=(FONT, 9)).pack(
          side="left", padx=8, pady=6
      )
      lab = tk.Label(row, text="● ACTIVO", bg=PANEL2, fg=GREEN, font=(FONT, 8, "bold"))
      lab.pack(side="right", padx=8)
      self.component_labels[key] = lab

    tk.Label(
        self.root,
        text="SIMULACIÓN EDUCATIVA  •  Sensores, panel solar, relé y bomba virtuales",
        bg=HEADER,
        fg=MUTED,
        font=(FONT, 8),
        pady=7,
    ).pack(fill="x")

  # ------------------------------------------------------------------
  def metric_card(self, parent, label, value, unit, color):
    f = tk.Frame(parent, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
    tk.Frame(f, bg=color, height=3).pack(fill="x")
    tk.Label(f, text=label, bg=PANEL, fg=MUTED, font=(FONT, 8, "bold")).pack(
        anchor="w", padx=14, pady=(10, 2)
    )
    line = tk.Frame(f, bg=PANEL)
    line.pack(anchor="w", padx=14)
    val = tk.Label(line, text=value, bg=PANEL, fg=color, font=(FONT, 24, "bold"))
    val.pack(side="left")
    tk.Label(line, text=unit, bg=PANEL, fg=MUTED, font=(FONT, 10)).pack(
        side="left", padx=5, pady=(8, 0)
    )
    bar = tk.Canvas(f, height=8, bg=PANEL, highlightthickness=0)
    bar.pack(fill="x", padx=14, pady=(4, 4))
    sub = tk.Label(f, text="", bg=PANEL, fg=MUTED, font=(FONT, 8))
    sub.pack(anchor="w", padx=14, pady=(0, 10))
    f.value_label = val
    f.bar = bar
    f.sub = sub
    f.frac, f.color = 0, color
    bar.bind("<Configure>", lambda e, card=f: self.draw_bar(card))
    return f

  def set_bar(self, card, frac, color, sub=None):
    card.frac, card.color = clamp(frac, 0, 1), color
    if sub is not None:
      card.sub.config(text=sub)
    self.draw_bar(card)

  def draw_bar(self, card):
    b = card.bar
    b.delete("all")
    w = max(b.winfo_width(), 60)
    rrect(b, 0, 1, w, 7, r=3, fill=BORDER, outline="")
    if card.frac > 0.01:
      rrect(b, 0, 1, max(8, w * card.frac), 7, r=3, fill=card.color, outline="")

  def slider_block(self, parent, label, var, low, high, unit, color):
    box = tk.Frame(parent, bg=PANEL)
    box.pack(fill="x", padx=13, pady=5)
    top = tk.Frame(box, bg=PANEL)
    top.pack(fill="x")
    tk.Label(top, text=label, bg=PANEL, fg=MUTED, font=(FONT, 9)).pack(side="left")
    value = tk.Label(
        top, text=f"{var.get():.1f} {unit}", bg=PANEL, fg=color, font=(FONT, 9, "bold")
    )
    value.pack(side="right")
    # La etiqueta se actualiza también cuando el código cambia la variable (reset, simulación)
    var.trace_add(
        "write", lambda *a: value.config(text=f"{var.get():.1f} {unit}")
    )
    scale = tk.Scale(
        box,
        variable=var,
        from_=low,
        to=high,
        orient="horizontal",
        showvalue=False,
        resolution=0.5,
        bg=PANEL,
        fg=TEXT,
        troughcolor=BORDER,
        activebackground=color,
        highlightthickness=0,
        bd=0,
        sliderlength=20,
        width=12,
        sliderrelief="flat",
        command=lambda v: self.update_all(),
        length=250,
    )
    scale.pack(fill="x")
    return scale

  def make_button(self, parent, text, color, command):
    hover = mix(color, "#ffffff", 0.18)
    b = tk.Button(
        parent,
        text=text,
        command=command,
        bg=color,
        fg="#07111e",
        activebackground=hover,
        activeforeground="#07111e",
        relief="flat",
        bd=0,
        cursor="hand2",
        font=(FONT, 9, "bold"),
        pady=9,
    )
    b.bind("<Enter>", lambda e: b.config(bg=hover))
    b.bind("<Leave>", lambda e: b.config(bg=color))
    return b

  # ------------------------------------------------------------------
  def start(self):
    self.running = True
    self.status_key = "run"
    self.last_tick = time.time()
    self.update_all()

  def pause(self):
    self.running = False
    self.status_key = "pause"
    self.update_all()

  def reset(self):
    self.running = False
    self.status_key = "reset"
    self.humidity.set(34)
    self.temperature.set(24.5)
    self.on_limit.set(40)
    self.off_limit.set(60)
    self.pump_on = False
    self.tank_level = 0.8
    self.history_h.clear()
    self.history_t.clear()
    self.history_h.extend([34] * 36)
    self.history_t.extend([24.5] * 36)
    self.update_all()

  # ------------------------------------------------------------------
  def update_all(self):
    h, t = self.humidity.get(), self.temperature.get()
    low, high = self.on_limit.get(), self.off_limit.get()
    if high <= low:
      self.pump_on = False
      self.header_status.config(text="⚠  REVISA LOS LÍMITES", fg=RED)
    else:
      text, color = self.STATUS[self.status_key]
      self.header_status.config(text=text, fg=color)
      if h <= low:
        self.pump_on = True
      elif h >= high:
        self.pump_on = False

    self.metric_h.value_label.config(text=f"{h:.1f}")
    self.metric_t.value_label.config(text=f"{t:.1f}")

    evaporation = self.evaporation_rate(t)
    if t < 25:
      thermal_state = "BAJA"
    elif t < 30:
      thermal_state = "MODERADA"
    elif t < 40:
      thermal_state = "ALTA"
    elif t < 45:
      thermal_state = "MUY ALTA"
    else:
      thermal_state = "EXTREMA"

    self.temp_effect_label.config(
        text=(
            f"EFECTO TÉRMICO: {thermal_state}  |  SECADO:"
            f" {evaporation:.1f}%/h\nCada actualización equivale a 5 min"
        ),
        fg=AMBER if t < 30 else RED,
    )

    self.metric_p.value_label.config(
        text="ON" if self.pump_on else "OFF", fg=GREEN if self.pump_on else MUTED
    )

    # Barras de las tarjetas
    h_color = RED if h <= low else BLUE
    self.set_bar(self.metric_h, h / 100, h_color, f"Umbrales: {low:.0f}%  –  {high:.0f}%")
    t_color = AMBER if t < 30 else RED
    self.set_bar(self.metric_t, t / 50, t_color, f"Evaporación: {evaporation:.1f} %/h")
    self.set_bar(
        self.metric_p,
        1.0 if self.pump_on else 0.0,
        GREEN,
        "Relé activado · regando" if self.pump_on else "Relé en espera",
    )

    self.component_labels["sensor"].config(text="● ACTIVO", fg=GREEN)
    self.component_labels["temp"].config(text="● ACTIVO", fg=GREEN)
    self.component_labels["relay"].config(
        text="● ACTIVADO" if self.pump_on else "● EN ESPERA",
        fg=GREEN if self.pump_on else MUTED,
    )
    self.component_labels["pump"].config(
        text="● ENCENDIDA" if self.pump_on else "● APAGADA",
        fg=GREEN if self.pump_on else MUTED,
    )
    self.component_labels["solar"].config(text="● DISPONIBLE", fg=AMBER)

    self.update_charts()

  def update_charts(self):
    self.draw_chart(
        self.chart_h, self.history_h, BLUE, 0, 100, "%",
        [(self.on_limit.get(), RED), (self.off_limit.get(), GREEN)],
    )
    self.draw_chart(self.chart_t, self.history_t, AMBER, 0, 50, "°C")

  # ------------------------------------------------------------------
  # DIAGRAMA PRINCIPAL
  # ------------------------------------------------------------------
  def draw_diagram(self):
    c = self.diagram
    c.delete("all")
    w = max(c.winfo_width(), 600)
    h = max(c.winfo_height(), 300)
    now = time.time()
    hv, tv = self.humidity.get(), self.temperature.get()
    low, high = self.on_limit.get(), self.off_limit.get()
    heat = clamp((tv - 20) / 30, 0, 1)
    ground_y = h - 46

    # ---------------- Cielo ----------------
    vgrad(c, 0, 0, w, ground_y, "#07101f", mix("#1b4a63", "#5a3a4a", heat * 0.6), 30)
    for sx, sy, ph in self.stars:
      x, y = sx * w, sy * ground_y * 0.55
      tw = (math.sin(now * 2 + ph) + 1) / 2
      c.create_oval(x, y, x + 2, y + 2, fill=mix("#294a66", "#d8ecff", tw), outline="")

    # Sol (su color se calienta con la temperatura)
    sunx, suny = 105, 62
    sun_col = mix("#ffd76a", "#ff6a3d", heat)
    for r, k in [(50, 0.08), (40, 0.16), (31, 0.30)]:
      c.create_oval(
          sunx - r, suny - r, sunx + r, suny + r,
          fill=mix("#16324a", sun_col, k), outline="",
      )
    for i in range(12):
      a = now * 0.3 + i * math.pi / 6
      c.create_line(
          sunx + math.cos(a) * 26, suny + math.sin(a) * 26,
          sunx + math.cos(a) * 38, suny + math.sin(a) * 38,
          fill=mix("#16324a", sun_col, 0.7), width=2,
      )
    pulse = 18 + math.sin(now * 2) * 1.2
    c.create_oval(
        sunx - pulse, suny - pulse, sunx + pulse, suny + pulse, fill=sun_col, outline=""
    )

    # Nubes
    for xf, cy, s, spd in self.clouds:
      x = (xf * w + now * spd) % (w + 240) - 120
      for dx1, dy1, dx2, dy2 in [(-28, -8, 4, 10), (-12, -16, 22, 8), (8, -6, 36, 10)]:
        c.create_oval(
            x + dx1 * s, cy + dy1 * s, x + dx2 * s, cy + dy2 * s,
            fill="#27526e", outline="",
        )

    # Colinas y suelo
    c.create_polygon(
        0, ground_y, 0, ground_y - 30, w * 0.15, ground_y - 48, w * 0.35, ground_y - 24,
        w * 0.6, ground_y - 56, w * 0.85, ground_y - 26, w, ground_y - 40, w, ground_y,
        smooth=True, fill="#0f3a3a", outline="",
    )
    c.create_polygon(
        0, ground_y, 0, ground_y - 14, w * 0.25, ground_y - 26, w * 0.5, ground_y - 12,
        w * 0.78, ground_y - 28, w, ground_y - 14, w, ground_y,
        smooth=True, fill="#14503f", outline="",
    )
    vgrad(c, 0, ground_y, w, h, "#1a4a35", "#0a1a17", 8)
    c.create_line(0, ground_y, w, ground_y, fill="#2f7a55", width=2)

    # ---------------- Geometría del invernadero ----------------
    margin = max(170, int(w * 0.2))
    gx1, gx2 = margin, w - margin
    cx = (gx1 + gx2) // 2
    gy1 = 56
    wall_top = gy1 + 55
    gy2 = ground_y
    bed_y = gy2 - 44
    pipe_y = bed_y - 20

    c.create_oval(gx1 - 12, gy2 - 8, gx2 + 12, gy2 + 10, fill="#08130f", outline="")

    # Pared trasera (se tiñe de rojizo con el calor)
    back_top = mix("#14384a", "#5a2a2a", clamp((tv - 32) / 18, 0, 1))
    vgrad(c, gx1, wall_top, gx2, gy2, back_top, "#0f2a38", 16)
    c.create_polygon(
        gx1, wall_top, cx, gy1, gx2, wall_top, fill=mix(back_top, "#2a6580", 0.25), outline=""
    )

    # Reflejos de cristal
    for k in range(4):
      x = gx1 + (gx2 - gx1) * (0.12 + k * 0.22)
      c.create_line(x + 30, wall_top + 10, x - 20, gy2 - 10, fill="#1b4a60", width=7)
      c.create_line(x + 46, wall_top + 10, x - 4, gy2 - 10, fill="#1b4a60", width=2)

    # Efecto de calor
    if tv >= 32:
      amp = 2 + (tv - 32) / 3
      for k in range(3):
        y0 = wall_top + 34 + k * 24
        pts = []
        for x in range(gx1 + 20, gx2 - 20, 14):
          pts.extend((x, y0 + math.sin(now * 3 + x * 0.05 + k) * amp))
        c.create_line(*pts, smooth=True, fill=mix(back_top, "#ff7a59", 0.45), width=2)

    # ---------------- Cables de control (detrás de la planta) ----------------
    relay_x1, relay_x2 = gx1 + 34, gx1 + 100
    relay_cy = wall_top + 28
    sens_x = gx2 - 110
    sens_head_y = bed_y - 62
    led_on = GREEN if self.pump_on else "#41556f"
    wire_sensor = mix("#7a6a3a", AMBER, 0.6 if self.running else 0.3)
    # sensor -> relé
    c.create_line(
        sens_x, sens_head_y - 12, sens_x, relay_cy, relay_x2, relay_cy,
        fill=wire_sensor, width=2, dash=(5, 3),
    )
    # relé -> bomba (se calcula con la posición de la bomba más abajo)
    px, py = 68, ground_y - 126
    c.create_line(
        relay_x1, relay_cy, gx1 - 24, relay_cy, gx1 - 24, py - 44, px, py - 44, px, py - 24,
        fill=GREEN if self.pump_on else "#41556f", width=2, dash=(5, 3),
    )

    # ---------------- Bancal ----------------
    bx1, bx2 = gx1 + 45, gx2 - 45
    soil = mix("#7a5a3c", "#2b1c15", hv / 100)
    rrect(c, bx1 - 4, bed_y - 4, bx2 + 4, gy2 - 8, r=6, fill="#8a6a48", outline="#a98557", width=1)
    c.create_rectangle(bx1, bed_y, bx2, gy2 - 12, fill=soil, outline="")
    c.create_rectangle(bx1, bed_y, bx2, bed_y + 6, fill=mix(soil, "#ffffff", 0.10), outline="")
    for rx, ry in self.soil_dots:
      x = bx1 + rx * (bx2 - bx1)
      y = bed_y + 9 + ry * (gy2 - 12 - bed_y - 12)
      c.create_oval(x, y, x + 3, y + 2, fill=mix(soil, "#000000", 0.30), outline="")
      if hv > 55 and ry > 0.5:
        c.create_oval(x + 6, y, x + 8, y + 2, fill=mix(soil, "#7dd3fc", 0.45), outline="")
    c.create_text(
        cx, gy2 - 24, text=f"HUMEDAD {hv:.0f}%",
        fill=mix(soil, "#ffffff", 0.6), font=(FONT, 8, "bold"),
    )

    # ---------------- Goteo ----------------
    pipe_col = "#38bdf8" if self.pump_on else "#64748b"
    c.create_line(gx1 + 14, pipe_y, gx2 - 60, pipe_y, fill="#0a1522", width=9, capstyle="round")
    c.create_line(gx1 + 14, pipe_y, gx2 - 60, pipe_y, fill=pipe_col, width=5, capstyle="round")
    c.create_line(gx1 + 14, pipe_y - 1, gx2 - 60, pipe_y - 1, fill=mix(pipe_col, "#ffffff", 0.4), width=1)
    emitters = list(range(gx1 + 80, gx2 - 70, 55))
    for dx in emitters:
      c.create_rectangle(dx - 3, pipe_y + 3, dx + 3, pipe_y + 9, fill="#94a3b8", outline="")

    # ---------------- Planta ----------------
    health = clamp(hv / 50, 0, 1) * (1.0 if tv < 40 else 0.6)
    self.draw_plant(c, cx, bed_y, health, now)

    # Insignia de estado de la planta
    if hv <= low:
      badge, bcol = "ESTRÉS HÍDRICO", RED
    elif tv >= 40:
      badge, bcol = "ESTRÉS TÉRMICO", RED
    elif hv >= high:
      badge, bcol = "SUELO HIDRATADO", BLUE
    else:
      badge, bcol = "PLANTA ÓPTIMA", GREEN
    by = gy1 + 28
    rrect(c, cx - 62, by - 11, cx + 62, by + 11, r=8, fill=mix("#0b1a28", bcol, 0.18), outline=bcol)
    c.create_text(cx, by, text=badge, fill=bcol, font=(FONT, 8, "bold"))

    # Gotas de riego
    if self.pump_on:
      for i, dx in enumerate(emitters):
        for d in range(2):
          prog = (now * 1.8 + i * 0.37 + d * 0.5) % 1
          y = pipe_y + 9 + prog * (bed_y - pipe_y - 9)
          c.create_oval(dx - 2, y, dx + 2, y + 7, fill="#7dd3fc", outline="")
          if prog > 0.88:
            c.create_oval(dx - 7, bed_y - 2, dx + 7, bed_y + 2, outline="#7dd3fc")

    # ---------------- Estructura del invernadero (marco por delante) ----------------
    frame_col = "#4fb8a8"
    for i in range(1, 8):
      x = gx1 + (gx2 - gx1) * i / 8
      c.create_line(x, wall_top, x, gy2, fill="#2f6f86", width=1)
      c.create_line(cx, gy1, x, wall_top, fill="#2f6f86", width=1)
    c.create_polygon(gx1, wall_top, cx, gy1, gx2, wall_top, fill="", outline=frame_col, width=3)
    c.create_rectangle(gx1, wall_top, gx2, gy2, outline=frame_col, width=3)
    c.create_oval(cx - 4, gy1 - 4, cx + 4, gy1 + 4, fill=frame_col, outline="")

    # ---------------- Tanque ----------------
    tx, ty = px - 38, ground_y - 74
    rrect(c, tx, ty, tx + 76, ground_y, r=10, fill="#0f2233", outline="#38bdf8", width=2)
    lvl_top = ty + 8 + (1 - self.tank_level) * 58
    wave = [tx + 5, ty + 66]
    for x in range(tx + 5, tx + 72, 6):
      wave.extend((x, lvl_top + math.sin(now * 2 + x * 0.2) * 1.6))
    wave.extend((tx + 71, ty + 66))
    c.create_polygon(wave, fill="#1b86c9", outline="")
    c.create_line(tx + 9, ty + 12, tx + 9, ty + 58, fill="#4fb4ec", width=2)
    c.create_text(px, ty + 34, text=f"{self.tank_level * 100:.0f}%", fill=TEXT, font=(FONT, 9, "bold"))
    c.create_text(px, ground_y + 14, text="TANQUE", fill="#94a3b8", font=(FONT, 7, "bold"))

    # ---------------- Tubería principal ----------------
    seg_a = [(px, ty), (px, py + 24)]
    seg_b = [(px + 24, py), (gx1 + 14, py), (gx1 + 14, pipe_y)]
    for seg in (seg_a, seg_b):
      c.create_line(*flat(seg), fill="#0a1522", width=9, capstyle="round", joinstyle="round")
      c.create_line(*flat(seg), fill=pipe_col, width=5, capstyle="round", joinstyle="round")
    c.create_rectangle(gx1 - 3, py - 8, gx1 + 3, py + 8, fill="#94a3b8", outline="")
    if self.pump_on:
      path_dots(c, seg_a, now, "#bae6fd", gap=24)
      path_dots(c, seg_b + [(gx2 - 60, pipe_y)], now, "#bae6fd", gap=24)

    # ---------------- Bomba ----------------
    pump_bg = "#064e3b" if self.pump_on else "#111c2e"
    pump_border = "#22c55e" if self.pump_on else "#64748b"
    if self.pump_on:
      c.create_oval(px - 30, py - 30, px + 30, py + 30, outline=mix("#0d1828", GREEN, 0.35), width=3)
    c.create_oval(px - 24, py - 24, px + 24, py + 24, fill=pump_bg, outline=pump_border, width=3)
    if self.pump_on:
      a0 = now * 8
      for k in range(3):
        a = a0 + k * 2 * math.pi / 3
        c.create_line(px, py, px + math.cos(a) * 15, py + math.sin(a) * 15,
                      fill="#86efac", width=3, capstyle="round")
      c.create_oval(px - 3, py - 3, px + 3, py + 3, fill="#064e3b", outline="")
    else:
      c.create_text(px, py, text="P", fill=TEXT, font=(FONT, 13, "bold"))
    c.create_text(px + 30, py + 14, text="BOMBA", fill="#94a3b8", font=(FONT, 7, "bold"), anchor="w")

    # ---------------- Relé ----------------
    rrect(c, relay_x1, relay_cy - 16, relay_x2, relay_cy + 16, r=6,
          fill="#1b2a3d", outline=GREEN if self.pump_on else "#41556f", width=2)
    c.create_text(relay_x1 + 24, relay_cy, text="RELÉ", fill=TEXT, font=(FONT, 8, "bold"))
    c.create_oval(relay_x2 - 14, relay_cy - 5, relay_x2 - 6, relay_cy + 3, fill=led_on, outline="")

    # ---------------- Sensor de humedad ----------------
    c.create_line(sens_x - 5, sens_head_y + 12, sens_x - 5, bed_y + 22, fill="#cbd5e1", width=2)
    c.create_line(sens_x + 5, sens_head_y + 12, sens_x + 5, bed_y + 22, fill="#cbd5e1", width=2)
    rrect(c, sens_x - 20, sens_head_y - 12, sens_x + 20, sens_head_y + 12, r=5,
          fill="#1e293b", outline="#38bdf8", width=2)
    c.create_text(sens_x, sens_head_y, text=f"{hv:.0f}%", fill=TEXT, font=(FONT, 9, "bold"))
    led = RED if hv <= low else GREEN
    c.create_oval(sens_x + 12, sens_head_y - 20, sens_x + 18, sens_head_y - 14, fill=led, outline="")
    c.create_text(sens_x, sens_head_y - 26, text="SENSOR", fill="#94a3b8", font=(FONT, 7, "bold"))

    # ---------------- Panel solar ----------------
    spx, spy = w - 95, 40
    c.create_line(spx - 6, spy + 40, spx - 6, ground_y, fill="#64748b", width=4)
    c.create_oval(spx - 60, spy - 14, spx + 52, spy + 48, outline=mix("#16324a", sun_col, 0.12))
    c.create_polygon(
        spx - 45, spy, spx + 48, spy, spx + 36, spy + 38, spx - 55, spy + 38,
        fill="#0f2942", outline="#38bdf8", width=2,
    )
    for i in range(1, 4):
      xx = spx - 55 + i * 24
      c.create_line(xx, spy + 2, xx - 10, spy + 36, fill="#2b7fb0", width=1)
    c.create_line(spx - 50, spy + 19, spx + 42, spy + 19, fill="#2b7fb0", width=1)
    shine = (now * 0.6) % 1.6 - 0.3
    sxp = spx - 50 + shine * 90
    if spx - 50 < sxp < spx + 40:
      c.create_line(sxp, spy + 3, sxp - 9, spy + 35, fill="#7dd3fc", width=2)
    c.create_text(spx - 4, spy + 56, text="PANEL SOLAR", fill="#94a3b8", font=(FONT, 7, "bold"))
    # Línea de energía hasta el invernadero
    power = [(spx - 6, ground_y + 10), (gx2, ground_y + 10)]
    c.create_line(*flat(power), fill="#6b5a2a", width=2, dash=(4, 3))
    path_dots(c, power, now, AMBER, speed=45, gap=30, r=2)

    c.create_text(
        w // 2, h - 12,
        text="ZONA DE CULTIVO  •  SISTEMA DE RIEGO AUTOMATIZADO",
        fill="#64748b", font=(FONT, 8, "bold"),
    )

  # ------------------------------------------------------------------
  # ------------------------------------------------------------------
  # PLANTA
  # ------------------------------------------------------------------
  def draw_leaf(self, c, bx, by, ang, length, width, col, vein):
    """Hoja con forma de gota, nervadura central y venas laterales."""
    ca, sa = math.cos(ang), math.sin(ang)
    left, rightp = [], []
    n = 8
    for k in range(n + 1):
      t = k / n
      prof = width * math.sin(math.pi * t ** 0.85) * (1 - 0.25 * t)
      ax, ay = bx + ca * length * t, by + sa * length * t
      left.append((ax - sa * prof, ay + ca * prof))
      rightp.append((ax + sa * prof, ay - ca * prof))
    poly = left + rightp[::-1]
    c.create_polygon(flat(poly), smooth=True, fill=col, outline=mix(col, "#ffffff", 0.25))
    c.create_line(bx, by, bx + ca * length * 0.92, by + sa * length * 0.92, fill=vein, width=1)
    for t in (0.3, 0.5, 0.7):
      ax, ay = bx + ca * length * t, by + sa * length * t
      for s in (-1, 1):
        c.create_line(
            ax, ay,
            ax + (ca * 0.6 - s * sa) * width * 0.8,
            ay + (sa * 0.6 + s * ca) * width * 0.8,
            fill=vein,
        )

  def draw_plant(self, c, cx, bed_y, health, now):
    droop = 1 - health
    sway = math.sin(now * 1.5) * 3
    stem_col = mix("#8a7a3a", "#2f9e4f", health)
    dark_leaf = mix("#8a6b2a", "#168a4a", health)
    light_leaf = mix("#b9a23e", "#34d27b", health)
    vein = mix(dark_leaf, "#ffffff", 0.35)

    # Montículo de tierra en la base
    c.create_oval(cx - 26, bed_y - 5, cx + 26, bed_y + 9,
                  fill=mix("#2b1c15", "#52392e", 0.4), outline="")

    # Tallo curvo (curva de Bézier cuadrática)
    top_x = cx + sway * 0.8
    top_y = bed_y - 104 + droop * 26
    ctrl_x, ctrl_y = cx - 12 + sway * 0.3, bed_y - 52
    stem = []
    for k in range(11):
      t = k / 10
      x = (1 - t) ** 2 * cx + 2 * (1 - t) * t * ctrl_x + t ** 2 * top_x
      y = (1 - t) ** 2 * bed_y + 2 * (1 - t) * t * ctrl_y + t ** 2 * top_y
      stem.append((x, y))
    c.create_line(*flat(stem), fill=mix(stem_col, "#000000", 0.35), width=8,
                  smooth=True, capstyle="round")
    c.create_line(*flat(stem), fill=stem_col, width=5, smooth=True, capstyle="round")
    c.create_line(*flat(stem), fill=mix(stem_col, "#ffffff", 0.3), width=1, smooth=True)

    # Hojas alternas a lo largo del tallo
    for i in range(6):
      t = 0.22 + i * 0.13
      idx = min(10, int(t * 10))
      bx, by = stem[idx]
      side = -1 if i % 2 == 0 else 1
      elev = math.radians(58 - i * 4) * health - math.radians(55) * droop
      elev += math.radians(math.sin(now * 1.5 + i) * 3)
      ang = math.atan2(-math.sin(elev), side * math.cos(elev))
      length = (48 - i * 4) * (0.8 + 0.2 * health)
      col = light_leaf if i % 2 else dark_leaf
      self.draw_leaf(c, bx, by, ang, length, 11 - i * 0.6, col, vein)

    # Corona de hojas en la punta
    for da in (-100, -78, -122):
      ang = math.radians(da) + math.radians(droop * 25 * (1 if da > -100 else -1))
      self.draw_leaf(c, top_x, top_y, ang, 24, 8, light_leaf, vein)

    # Flores amarillas (planta con humedad media) o tomates (planta sana)
    if 0.35 < health <= 0.85:
      for fx, fy in [(top_x - 9, top_y + 6), (top_x + 10, top_y + 14)]:
        for k in range(5):
          a = k * 2 * math.pi / 5 + now * 0.2
          c.create_oval(fx + math.cos(a) * 4 - 3, fy + math.sin(a) * 4 - 3,
                        fx + math.cos(a) * 4 + 3, fy + math.sin(a) * 4 + 3,
                        fill="#fde047", outline="")
        c.create_oval(fx - 2, fy - 2, fx + 2, fy + 2, fill="#f59e0b", outline="")
    elif health > 0.85:
      for t, side in [(0.40, 1), (0.55, -1), (0.30, -1)]:
        bx, by = stem[int(t * 10)]
        fx = bx + side * 17 + sway * 0.3
        fy = by + 15
        c.create_line(bx, by, bx + side * 8, by + 2, fx, fy - 7,
                      fill="#2f9e4f", width=2, smooth=True)
        c.create_oval(fx - 8, fy - 7, fx + 8, fy + 8, fill="#dc2626", outline="#fca5a5")
        c.create_oval(fx - 4, fy - 4, fx - 1, fy - 1, fill="#fecaca", outline="")
        c.create_polygon(fx - 6, fy - 6, fx, fy - 9, fx + 6, fy - 6, fx, fy - 3,
                         fill="#16a34a", outline="")

  def draw_chart(self, canvas, values, color, low, high, unit, thresholds=None):
    canvas.delete("all")
    w = max(canvas.winfo_width(), 250)
    h = max(canvas.winfo_height(), 120)
    left, right, top, bottom = 34, w - 12, 10, h - 22

    def ypos(v):
      return bottom - (clamp(v, low, high) - low) / (high - low) * (bottom - top)

    for i in range(5):
      y = top + (bottom - top) * i / 4
      canvas.create_line(left, y, right, y, fill="#1d2d45")
      label = high - (high - low) * i / 4
      canvas.create_text(left - 6, y, text=f"{label:.0f}", fill=MUTED, anchor="e", font=(FONT, 7))

    for val, col in thresholds or []:
      canvas.create_line(left, ypos(val), right, ypos(val), fill=col, dash=(5, 4))

    vals = list(values)
    pts = []
    for i, v in enumerate(vals):
      x = left + (right - left) * i / max(1, len(vals) - 1)
      pts.extend((x, ypos(v)))
    if len(pts) >= 4:
      canvas.create_polygon(
          [left, bottom] + pts + [right, bottom], fill=mix(PANEL, color, 0.20), outline=""
      )
      canvas.create_line(*pts, fill=color, width=2, smooth=True)
      canvas.create_oval(pts[-2] - 8, pts[-1] - 8, pts[-2] + 8, pts[-1] + 8,
                         fill=mix(PANEL, color, 0.25), outline="")
      canvas.create_oval(pts[-2] - 3, pts[-1] - 3, pts[-2] + 3, pts[-1] + 3,
                         fill=color, outline="")
    if vals:
      canvas.create_text(right, h - 6, text=f"ACTUAL: {vals[-1]:.1f}{unit}", fill=color,
                         anchor="e", font=(FONT, 8, "bold"))
    canvas.create_text(left, h - 6, text=unit, fill=MUTED, anchor="w", font=(FONT, 7))

  def evaporation_rate(self, temperature):
    puntos = [
        (10, 0.15), (20, 0.30), (25, 0.50), (30, 0.80),
        (35, 1.20), (40, 2.50), (45, 4.00), (50, 6.00),
    ]
    if temperature <= puntos[0][0]:
      return puntos[0][1]
    if temperature >= puntos[-1][0]:
      return puntos[-1][1]
    for i in range(len(puntos) - 1):
      t1, r1 = puntos[i]
      t2, r2 = puntos[i + 1]
      if t1 <= temperature <= t2:
        proporcion = (temperature - t1) / (t2 - t1)
        return r1 + (r2 - r1) * proporcion
    return puntos[-1][1]

  # ------------------------------------------------------------------
  def animate(self):
    """Paso de simulación (cada 500 ms)."""
    self.clock_label.config(text=time.strftime("%d/%m/%Y   %H:%M:%S"))
    if self.running:
      h = self.humidity.get()
      drying_per_hour = self.evaporation_rate(self.temperature.get())
      drying_this_tick = drying_per_hour * (5 / 60)
      if self.pump_on:
        h = min(100, h + 0.70 - drying_this_tick * 0.25)
        self.tank_level = max(0.12, self.tank_level - 0.004)
      else:
        h = max(0, h - drying_this_tick)
        self.tank_level = min(1.0, self.tank_level + 0.0015)
      self.humidity.set(round(h, 1))
      self.history_h.append(h)
      self.history_t.append(self.temperature.get())
      self.update_all()
    self.root.after(500, self.animate)

  def render(self):
    """Bucle de animación visual (~16 fps): gotas, flujo, nubes, hélice..."""
    self.draw_diagram()
    self.root.after(60, self.render)


if __name__ == "__main__":
  root = tk.Tk()
  app = EcoGrow(root)
  root.mainloop()