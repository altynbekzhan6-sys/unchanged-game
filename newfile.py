import random, math, struct, wave, os, tempfile, json
from kivy.app import App
from kivy.uix.widget import Widget
from kivy.clock import Clock
from kivy.graphics import Color, Rectangle, Ellipse, Line
from kivy.core.text import Label as CoreLabel
from kivy.core.audio import SoundLoader
from kivy.core.image import Image as CoreImage

def make_snd(kind):
    try:
        sr = 22050
        dur = 0.08 if kind in ("hit", "buy") else (0.13 if kind in ("shoot", "melee", "rel") else (0.35 if kind == "boom" else 0.4))
        n = int(sr * dur)
        path = os.path.join(tempfile.gettempdir(), f"uk_{kind}.wav")
        with wave.open(path, "wb") as wf:
            wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(sr)
            frames = bytearray()
            for i in range(n):
                t = i / sr
                env = max(0.0, 1.0 - t / dur)
                if kind == "shoot":
                    v = (random.uniform(-1, 1) * 0.7 + math.sin(2 * math.pi * (280 - 180 * t / dur) * t) * 0.3) * env
                elif kind == "boom":
                    v = (random.uniform(-1, 1) * 0.85 + math.sin(2 * math.pi * (110 - 70 * t / dur) * t) * 0.4) * env
                elif kind == "melee":
                    v = math.sin(2 * math.pi * (420 - 300 * t / dur) * t) * env * 0.8
                elif kind == "hit":
                    v = math.sin(2 * math.pi * 680 * t) * env * 0.6
                elif kind == "buy":
                    f = 580 if t < dur * 0.5 else 880
                    v = math.sin(2 * math.pi * f * t) * env * 0.6
                elif kind == "rel":
                    v = (1.0 if math.sin(2 * math.pi * 320 * t) > 0 else -1.0) * env * 0.35
                else:
                    v = math.sin(2 * math.pi * (520 if int(t * 14) % 2 == 0 else 360) * t) * env * 0.7
                frames += struct.pack("<h", int(max(-1, min(1, v)) * 20000))
            wf.writeframes(frames)
        return SoundLoader.load(path)
    except Exception:
        return None

class GameWidget(Widget):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.W = 0
        self.H = 0
        self.state = "MENU"
        self.weapons = [
            {"n": "Пистолет", "d": 15, "cd": 18, "m": 12, "s": 1},
            {"n": "Автомат",  "d": 22, "cd": 9,  "m": 30, "s": 1},
            {"n": "Дробовик", "d": 18, "cd": 32, "m": 8,  "s": 3},
        ]
        self.snds = {k: make_snd(k) for k in ("shoot", "melee", "hit", "buy", "rel", "alarm", "boom")}
        self.tex_cache = {}
        self.anims = {"idle": [], "move": [], "run": [], "shot": []}
        self.anim_t = 0.0
        self.is_moving = False

        base_dir = os.path.dirname(os.path.abspath(__file__))
        save_dir = base_dir
        try:
            app = App.get_running_app()
            if app:
                save_dir = app.user_data_dir
        except Exception:
            save_dir = base_dir
        self.hud_file = os.path.join(save_dir, "hud_layout.json")
        self.hud_pos = {}
        self.drag_btn = None
        self.drag_off = (0, 0)
        try:
            sp_path = os.path.join(base_dir, "soldier_clean.png")
            if os.path.exists(sp_path):
                cimg = CoreImage(sp_path, keep_data=True)
                stex = cimg.texture
                stex.mag_filter = 'nearest'
                sw, sh = stex.size
                
                # Точные координаты каждого ряда и каждого солдата под твой спрайт-лист
                # Формат: (имя_анимации, y_от_верха_в_долях, высота_в_долях, [(x_старт, x_конец), ...])
                sheet_map = [
                    ("idle", 0.05, 0.14, [
                        (0.155, 0.230), (0.260, 0.335), (0.365, 0.440),
                        (0.470, 0.545), (0.575, 0.650), (0.680, 0.755), (0.785, 0.860)
                    ]),
                    ("move", 0.24, 0.14, [
                        (0.155, 0.215), (0.260, 0.320), (0.365, 0.425), (0.475, 0.535),
                        (0.580, 0.640), (0.685, 0.745), (0.790, 0.850), (0.895, 0.960)
                    ]),
                    ("run", 0.43, 0.14, [
                        (0.150, 0.205), (0.250, 0.305), (0.365, 0.420),
                        (0.470, 0.525), (0.570, 0.625), (0.680, 0.735)
                    ]),
                    ("shot", 0.60, 0.14, [
                        (0.155, 0.240), (0.260, 0.345), (0.365, 0.455), (0.470, 0.560)
                    ]),
                ]
                for name, top_y, h_frac, cols in sheet_map:
                    ry = sh * (1.0 - top_y - h_frac)
                    rh = sh * h_frac
                    for x0, x1 in cols:
                        rx = sw * x0
                        rw = sw * (x1 - x0)
                        reg = stex.get_region(rx, ry, rw, rh)
                        self.anims[name].append(reg)
        except Exception as e:
            print("Спрайт солдата:", e)

        self.furry_anims = {
            "white":   {"idle": [], "run": [], "attack": []},
            "dark":    {"idle": [], "run": [], "attack": []},
            "grabber": {"idle": [], "run": [], "attack": []},
        }
        try:
            for kind in ("white", "dark", "grabber"):
                fp = os.path.join(base_dir, f"furry_{kind}.png")
                if os.path.exists(fp):
                    ftex = CoreImage(fp).texture
                    ftex.mag_filter = 'nearest'
                    for r_i, sname in enumerate(("idle", "run", "attack")):
                        for step in range(4):
                            reg = ftex.get_region(step * 60, (2 - r_i) * 60, 60, 60)
                            self.furry_anims[kind][sname].append(reg)
        except Exception as e:
            print("Спрайты врагов:", e)

        self.fingers = {}
        self.bind(size=self.on_resize)
        Clock.schedule_interval(self.update, 1.0 / 60.0)
    def play_s(self, k):
        s = self.snds.get(k)
        if s:
            try: s.stop(); s.play()
            except Exception: pass

    def spawn_fx(self, cx, cy, col, count=12, spd=7.0, sz=7):
        if len(self.particles) > 140:
            del self.particles[:count]
        for _ in range(count):
            ang = random.uniform(0, math.pi * 2)
            v = random.uniform(1.5, spd)
            self.particles.append({
                "x": cx, "y": cy,
                "vx": math.cos(ang) * v,
                "vy": math.sin(ang) * v + 2.5,
                "c": col,
                "life": random.randint(18, 34),
                "max": 34,
                "sz": random.uniform(sz * 0.6, sz * 1.3)
            })

    def trigger_death(self, killer_kind):
        self.state = "OVER"
        self.grabber = None
        # 85% шанс превратиться в фурри того цвета, кто убил; 15% шанс пасть как человек и кровоточить
        if random.random() < 0.85:
            self.death_mode = "TF_DARK" if killer_kind in ("dark", "grabber") else "TF_WHITE"
            self.tf_x = self.px
            self.tf_y = self.py
            self.tf_dir = 1 if self.right else -1
            self.spawn_fx(self.px + self.p_sz * 0.5, self.py + self.p_sz * 0.5, (0.6, 0.2, 0.9), 22, 8.0, 8)
        else:
            self.death_mode = "BLEED"
            self.bleed_t = 0
            self.spawn_fx(self.px + self.p_sz * 0.5, self.py + 12, (0.95, 0.1, 0.1), 25, 8.5, 8)

    def on_resize(self, *args):
        w, h = self.width, self.height
        if w < 10 or h < 10: return
        first = (self.W == 0)
        self.W, self.H = w, h
        self.f1_y, self.f2_y, self.lift_w = h * 0.22, h * 0.58, w * 0.11
        self.lift_x = w - self.lift_w - 10
        self.lad_x = w - self.lift_w - 85
        self.evac_x = w * 0.25
        self.p_sz = h * 0.11
        self.gen_r = (w * 0.5 - 35, self.f1_y, 70, 65)
        self.tab_r = (w * 0.22, self.f2_y + 16, 44, 52)
        bs = h * 0.15
        by = h * 0.025
        self.b_l = (25, by, bs, bs)
        self.b_r = (35 + bs, by, bs, bs)
        self.b_j = (w - bs - 25, by, bs, bs)
        self.b_f = (w - bs * 2 - 40, by, bs, bs)
        self.b_mel = (w - bs * 2 - 40, by + bs + 6, bs, bs * 0.52)
        self.b_rel = (w - bs * 3 - 55, by, bs, bs)
        self.b_grn = (w - bs * 3 - 55, by + bs + 6, bs, bs * 0.52)
        self.b_act = (w * 0.5 - bs * 1.1, by, bs * 2.2, bs)
        self.b_rep = (w * 0.5 - bs * 1.1, by + bs + 6, bs * 2.2, bs * 0.52)
        self.b_bomb = (25, by + bs + 6, bs * 2.1, bs * 0.52)
        self.b_pause = (w - 65, h - 58, 50, 44)

        bw, bh = w * 0.34, h * 0.11
        self.b_play = (w * 0.5 - bw * 0.5, h * 0.44, bw, bh)
        self.b_hud  = (w * 0.5 - bw * 0.5, h * 0.30, bw, bh)
        self.b_exit = (w * 0.5 - bw * 0.5, h * 0.16, bw, bh)

        self.b_hud_save  = (w * 0.5 + 10, h - 65, 160, 48)
        self.b_hud_reset = (w * 0.5 - 170, h - 65, 160, 48)

        for k in ("b_l", "b_r", "b_j", "b_f", "b_mel", "b_rel", "b_grn", "b_act", "b_rep", "b_bomb"):
            if k in self.hud_pos:
                _, _, rw, rh = getattr(self, k)
                nx, ny = self.hud_pos[k]
                setattr(self, k, (nx * w, ny * h, rw, rh))

        mw, mh = w * 0.68, h * 0.72
        mx, my = (w - mw) * 0.5, (h - mh) * 0.5
        self.m_r = (mx, my, mw, mh)
        oh = mh * 0.13
        self.o1 = (mx + 30, my + mh - 55 - oh, mw - 60, oh)
        self.o2 = (mx + 30, my + mh - 63 - oh * 2, mw - 60, oh)
        self.o3 = (mx + 30, my + mh - 71 - oh * 3, mw - 60, oh)
        self.o4 = (mx + 30, my + mh - 79 - oh * 4, mw - 60, oh)
        self.o5 = (mx + 30, my + mh - 87 - oh * 5, mw - 60, oh)
        self.o6 = (mx + 30, my + mh - 95 - oh * 6, mw - 60, oh)
        self.cl_b = (mx + mw - 65, my + mh - 65, 50, 50)
        if first:
            self.reset()
            self.state = "MENU"

    def reset(self):
        w, h = self.W, self.H
        self.px, self.py = w * 0.5 - 80, self.f1_y
        self.bx, self.by = w * 0.5 - 25, self.f2_y
        self.carry_bomb = False
        self.hp, self.coins, self.kills = 100, 0, 0
        self.spd_l, self.vamp_l, self.ammo_l, self.dmg_l = 0, 0, 0, 0
        self.w_idx, self.ammo, self.reserve, self.rel_t, self.scd, self.muz_t, self.mel_t, self.mel_cd = 0, 12, 48, 0, 0, 0, 0, 0
        self.nades = 2
        self.bomb_hp, self.gen_hp, self.timer, self.heli_x, self.rotor = 200, 250, 10 * 3600, -250, 0
        self.heli_ready, self.heli_fly = False, False
        self.heli_y = h * 0.78
        self.saved_names = []
        self.lift_y, self.lift_ty, self.lift_top = self.f1_y, self.f1_y, False
        self.vy, self.on_g, self.right = 0, True, True
        self.bullets, self.enemies, self.bars, self.turrets, self.allies = [], [], [], [], []
        self.grenades, self.particles, self.corpses = [], [], []
        self.ammo_pads = [
            {"x": w * 0.16, "y": self.f1_y, "cd": 0, "nade": False},
            {"x": w * 0.64, "y": self.f2_y, "cd": 0, "nade": True},
        ]
        self.grabber = None
        self.grab_prog = 0
        self.grab_last = ""
        self.death_mode = None
        self.last_hit_kind = "white"
        self.tf_x, self.tf_y, self.tf_dir, self.bleed_t = 0, 0, 1, 0
        self.sp_t = 0
        self.state = "PLAY"

    def txt_tex(self, text, size):
        key = (text, int(size))
        if key not in self.tex_cache:
            if len(self.tex_cache) > 160: self.tex_cache.clear()
            lbl = CoreLabel(text=text, font_size=max(14, int(size)))
            lbl.refresh()
            self.tex_cache[key] = lbl.texture
        return self.tex_cache[key]

    def draw_txt(self, text, cx, cy, size, col=(1, 1, 1, 1), center=True):
        tex = self.txt_tex(text, size)
        Color(*col)
        x = cx - tex.width * 0.5 if center else cx
        y = cy - tex.height * 0.5 if center else cy
        Rectangle(texture=tex, pos=(x, y), size=tex.size)

    def in_r(self, r, x, y, pad=0):
        rx, ry, rw, rh = r
        return (rx - pad) <= x <= (rx + rw + pad) and (ry - pad) <= y <= (ry + rh + pad)

    def box_ov(self, a, b, pad=0):
        ax, ay, aw, ah = a
        bx, by, bw, bh = b
        return (ax - pad) < (bx + bw + pad) and (ax + aw + pad) > (bx - pad) and (ay - pad) < (by + bh + pad) and (ay + ah + pad) > (by - pad)

    def start_rel(self):
        if self.grabber: return
        max_m = self.weapons[self.w_idx]["m"] + self.ammo_l * 6
        if self.rel_t == 0 and self.ammo < max_m and self.reserve > 0:
            self.rel_t = 60; self.play_s("rel")

    def throw_nade(self):
        if self.grabber or self.nades <= 0: return
        self.nades -= 1
        self.play_s("melee")
        dx = 1 if self.right else -1
        nx = self.px + (self.p_sz if self.right else 0)
        ny = self.py + self.p_sz * 0.65
        self.grenades.append({"x": nx, "y": ny, "vx": 13 * dx, "vy": 13, "t": 120})

    def shoot(self):
        if self.grabber or self.rel_t > 0 or self.scd > 0: return
        if self.ammo <= 0:
            if self.reserve > 0: self.start_rel()
            return
        w = self.weapons[self.w_idx]
        self.ammo -= 1; self.scd = w["cd"]; self.muz_t = 5; self.anim_t = 0.0; self.play_s("shoot")
        dx = 1 if self.right else -1
        tx = self.px + self.p_sz * 1.25 if self.right else self.px - self.p_sz * 0.25
        ty = self.py + self.p_sz * 0.74
        spread = (0,) if w["s"] == 1 else (-3, 0, 3)
        for dy in spread:
            self.bullets.append({"x": tx, "y": ty, "vx": 22 * dx, "vy": dy, "d": w["d"] + self.dmg_l * 5})
        if self.ammo == 0 and self.reserve > 0: self.start_rel()

    def do_melee(self):
        if self.grabber or self.mel_cd > 0: return
        self.mel_t = 10; self.mel_cd = 24; self.play_s("melee")
        dx = 1 if self.right else -1
        hx = self.px + self.p_sz - 10 if self.right else self.px - 75
        hr = (hx, self.py - 10, 85, self.p_sz + 20)
        for e in self.enemies:
            if self.box_ov(hr, (e["x"], e["y"], e["w"], e["h"])):
                e["hp"] -= 30 + self.dmg_l * 5; self.play_s("hit")
                self.spawn_fx(e["x"] + e["w"] * 0.5, e["y"] + e["h"] * 0.5, (0.95, 0.15, 0.15), 6, 4.5, 5)
                e["x"] = max(0, min(self.W - e["w"], e["x"] + 110 * dx))
                e["vy"] = 7; e["g"] = False

    def on_touch_down(self, touch):
        if self.state == "EDIT_HUD":
            for k in ("b_l", "b_r", "b_j", "b_f", "b_mel", "b_rel", "b_grn", "b_act", "b_rep", "b_bomb"):
                rx, ry, rw, rh = getattr(self, k)
                if self.in_r((rx, ry, rw, rh), touch.x, touch.y, 6):
                    self.drag_btn = k
                    self.drag_off = (touch.x - rx, touch.y - ry)
                    return True
        self.fingers[touch.uid] = (touch.x, touch.y)
        self.handle_tap(touch.x, touch.y)
        return True

    def on_touch_move(self, touch):
        if self.state == "EDIT_HUD" and self.drag_btn:
            _, _, rw, rh = getattr(self, self.drag_btn)
            nx = max(0, min(self.W - rw, touch.x - self.drag_off[0]))
            ny = max(0, min(self.H - rh, touch.y - self.drag_off[1]))
            setattr(self, self.drag_btn, (nx, ny, rw, rh))
            return True

    def on_touch_up(self, touch):
        if self.state == "EDIT_HUD" and self.drag_btn:
            rx, ry, _, _ = getattr(self, self.drag_btn)
            self.hud_pos[self.drag_btn] = [rx / float(self.W), ry / float(self.H)]
            self.drag_btn = None
            return True
        self.fingers.pop(touch.uid, None)
        return True

    def handle_tap(self, x, y):
        st = self.state
        if st == "MENU":
            if self.in_r(self.b_play, x, y): self.play_s("buy"); self.reset()
            elif self.in_r(self.b_exit, x, y): App.get_running_app().stop()
            return
        if st == "PAUSE":
            if self.in_r(self.b_play, x, y): self.play_s("buy"); self.state = "PLAY"
            elif self.in_r(self.b_hud, x, y): self.play_s("buy"); self.state = "EDIT_HUD"
            elif self.in_r(self.b_exit, x, y): self.state = "MENU"
            return
        if st == "EDIT_HUD":
            if self.in_r(self.b_hud_reset, x, y):
                self.hud_pos.clear()
                if os.path.exists(self.hud_file):
                    try: os.remove(self.hud_file)
                    except Exception: pass
                self.on_resize()
                self.play_s("buy")
            elif self.in_r(self.b_hud_save, x, y):
                try:
                    with open(self.hud_file, "w", encoding="utf-8") as f:
                        json.dump(self.hud_pos, f)
                except Exception: pass
                self.play_s("buy")
                self.state = "PAUSE"
            return
        if st in ("OVER", "WIN"):
            self.reset(); return
        if st in ("SHOP", "BUFF"):
            if self.in_r(self.cl_b, x, y): self.state = "PLAY"; return
            if st == "SHOP":
                if self.in_r(self.o1, x, y) and self.coins >= 30 and self.hp < 100:
                    self.coins -= 30; self.hp = min(100, self.hp + 40); self.play_s("buy")
                elif self.in_r(self.o2, x, y) and self.coins >= 40:
                    self.coins -= 40; self.play_s("buy")
                    bx = self.px + self.p_sz + 15 if self.right else self.px - 35
                    self.bars.append({"x": bx, "y": self.py, "w": 22, "h": 55, "hp": 120})
                elif self.in_r(self.o3, x, y) and self.w_idx < 2:
                    c = 100 if self.w_idx == 0 else 200
                    if self.coins >= c:
                        self.coins -= c; self.w_idx += 1
                        max_m = self.weapons[self.w_idx]["m"] + self.ammo_l * 6
                        self.ammo = max_m
                        self.reserve += max_m * 3
                        self.rel_t = 0; self.play_s("buy")
                elif self.in_r(self.o4, x, y) and self.coins >= 80:
                    self.coins -= 80; self.play_s("buy")
                    self.turrets.append({"x": self.px + self.p_sz * 0.5 - 15, "y": self.py, "w": 30, "h": 35, "cd": 0, "hp": 100})
                elif self.in_r(self.o5, x, y) and self.coins >= 90 and not any(a["role"] == "eng" for a in self.allies):
                    self.coins -= 90; self.play_s("buy")
                    self.allies.append({"role": "eng", "n": "Инженер", "x": self.px, "y": self.py, "hp": 100, "max": 100, "cd": 0, "vy": 0, "on_g": True})
                elif self.in_r(self.o6, x, y) and self.coins >= 100 and not any(a["role"] == "med" for a in self.allies):
                    self.coins -= 100; self.play_s("buy")
                    self.allies.append({"role": "med", "n": "Медик", "x": self.px, "y": self.py, "hp": 90, "max": 90, "cd": 0, "vy": 0, "on_g": True})
            else:
                if self.in_r(self.o1, x, y) and self.coins >= 50 and self.spd_l < 4:
                    self.coins -= 50; self.spd_l += 1; self.play_s("buy")
                elif self.in_r(self.o2, x, y) and self.coins >= 70 and self.vamp_l < 4:
                    self.coins -= 70; self.vamp_l += 1; self.play_s("buy")
                elif self.in_r(self.o3, x, y) and self.coins >= 60 and self.ammo_l < 4:
                    self.coins -= 60; self.ammo_l += 1
                    self.ammo = self.weapons[self.w_idx]["m"] + self.ammo_l * 6
                    self.reserve += 30; self.play_s("buy")
                elif self.in_r(self.o4, x, y) and self.coins >= 80 and self.dmg_l < 4:
                    self.coins -= 80; self.dmg_l += 1; self.play_s("buy")
            return

        if st == "PLAY":
            if self.in_r(self.b_pause, x, y): self.state = "PAUSE"; return

            if self.grabber:
                side = "L" if self.in_r(self.b_l, x, y, 10) else ("R" if self.in_r(self.b_r, x, y, 10) else "")
                if side and side != self.grab_last:
                    self.grab_last = side
                    self.grab_prog += 1
                    self.play_s("hit")
                    if self.grab_prog >= 6:
                        g_enemy = self.grabber
                        self.grabber = None
                        self.grab_prog = 0
                        self.mel_t = 12
                        self.play_s("melee")
                        dx = 1 if (g_enemy["x"] >= self.px) else -1
                        self.right = (dx > 0)
                        if g_enemy in self.enemies:
                            g_enemy["hp"] -= 45 + self.dmg_l * 10
                            g_enemy["x"] = max(0, min(self.W - g_enemy["w"], g_enemy["x"] + 150 * dx))
                            g_enemy["vy"] = 10; g_enemy["g"] = False
                        self.spawn_fx(self.px + self.p_sz * 0.5, self.py + self.p_sz * 0.5, (1.0, 0.85, 0.2), 14, 7.0, 7)
                return

            if self.in_r(self.b_mel, x, y): self.do_melee()
            if self.in_r(self.b_rel, x, y): self.start_rel()
            if self.in_r(self.b_grn, x, y): self.throw_nade()
            pwr = self.gen_hp > 0
            if not pwr and self.in_r(self.b_bomb, x, y):
                if self.carry_bomb:
                    self.carry_bomb = False
                    self.bx = self.px + self.p_sz * 0.5 - 25
                    self.by = self.f2_y if self.py >= self.f2_y - 10 else self.f1_y
                    self.play_s("buy")
                elif self.box_ov((self.px, self.py, self.p_sz, self.p_sz), (self.bx, self.by, 50, 45), 25):
                    self.carry_bomb = True; self.play_s("buy")

            ntab = self.box_ov((self.px, self.py, self.p_sz, self.p_sz), self.tab_r, 30)
            nlift = abs((self.px + self.p_sz * 0.5) - (self.lift_x + self.lift_w * 0.5)) < self.lift_w
            if pwr and self.in_r(self.tab_r, x, y, 25): self.state = "BUFF"
            if pwr and self.in_r(self.b_act, x, y):
                if nlift:
                    self.lift_top = not self.lift_top
                    self.lift_ty = self.f2_y if self.lift_top else self.f1_y
                else:
                    self.state = "BUFF" if ntab else "SHOP"
            if pwr and self.in_r(self.b_rep, x, y) and self.coins >= 20:
                dmg_t = [t for t in self.turrets if t["hp"] < 100]
                if dmg_t:
                    nt = min(dmg_t, key=lambda t: abs(t["x"] - self.px))
                    self.coins -= 20; nt["hp"] = min(100, nt["hp"] + 60); self.play_s("buy")

    def update(self, dt):
        if self.W < 10 or self.H < 10: return
        W, H = self.W, self.H
        pwr = self.gen_hp > 0
        if not pwr and self.state in ("SHOP", "BUFF"): self.state = "PLAY"

        if self.state == "OVER":
            self.anim_t += dt
            for pt in self.particles[:]:
                pt["x"] += pt["vx"]; pt["y"] += pt["vy"]; pt["vy"] -= 0.35; pt["life"] -= 1
                if pt["life"] <= 0: self.particles.remove(pt)
            if self.death_mode in ("TF_DARK", "TF_WHITE"):
                self.tf_x += 2.5 * self.tf_dir
                if self.tf_x < 20: self.tf_x = 20; self.tf_dir = 1
                elif self.tf_x > W - self.p_sz - 20: self.tf_x = W - self.p_sz - 20; self.tf_dir = -1
            elif self.death_mode == "BLEED":
                self.bleed_t += 1
                if self.bleed_t % 6 == 0 and self.bleed_t < 180:
                    self.spawn_fx(self.px + self.p_sz * 0.5, self.py + 10, (0.9, 0.08, 0.08), 3, 3.5, 5)
            self.render()
            return

        if self.state == "PLAY":
            if self.grabber and self.grabber not in self.enemies:
                self.grabber = None

            ml = mr = up_hold = False
            if not self.grabber:
                for fx, fy in self.fingers.values():
                    if self.in_r(self.b_l, fx, fy): ml = True
                    if self.in_r(self.b_r, fx, fy): mr = True
                    if self.in_r(self.b_j, fx, fy): up_hold = True
                    if self.in_r(self.b_f, fx, fy): self.shoot()

            on_lad = (not pwr) and (not self.grabber) and abs((self.px + self.p_sz * 0.5) - (self.lad_x + 22)) < 38
            if on_lad and up_hold:
                self.py = min(self.f2_y, self.py + 8)
                self.vy = 0; self.on_g = True
            elif up_hold and self.on_g:
                self.vy = 21; self.on_g = False

            if pwr:
                if self.lift_y < self.lift_ty: self.lift_y = min(self.lift_ty, self.lift_y + 6)
                elif self.lift_y > self.lift_ty: self.lift_y = max(self.lift_ty, self.lift_y - 6)

            spd = 10 + self.spd_l * 2
            if not self.grabber:
                if ml: self.px -= spd; self.right = False
                if mr: self.px += spd; self.right = True
            self.anim_t += dt
            self.is_moving = (ml or mr) and self.on_g and not self.grabber
            self.px = max(0, min(W - self.p_sz, self.px))

            if not (on_lad and up_hold):
                pb = self.py; self.vy -= 1.1; self.py += self.vy; self.on_g = False
                for plat_y, pl_x, pl_w in ((self.f1_y, -500, W * 3), (self.f2_y, 0, W - self.lift_w - 20), (self.lift_y, self.lift_x, self.lift_w)):
                    if self.vy <= 0 and pb >= plat_y - 14 and self.py <= plat_y and (self.px + self.p_sz) > pl_x and self.px < (pl_x + pl_w):
                        self.py = plat_y; self.vy = 0; self.on_g = True

            if self.carry_bomb:
                self.bx = self.px + (self.p_sz * 0.5 - 25)
                self.by = self.py + 12

            if self.scd > 0: self.scd -= 1
            if self.muz_t > 0: self.muz_t -= 1
            if self.mel_t > 0: self.mel_t -= 1
            if self.mel_cd > 0: self.mel_cd -= 1
            if self.rel_t > 0:
                self.rel_t -= 1
                if self.rel_t == 0:
                    max_m = self.weapons[self.w_idx]["m"] + self.ammo_l * 6
                    need = max_m - self.ammo
                    take = min(need, self.reserve)
                    self.ammo += take
                    self.reserve -= take

            for pt in self.particles[:]:
                pt["x"] += pt["vx"]
                pt["y"] += pt["vy"]
                pt["vy"] -= 0.35
                pt["life"] -= 1
                if pt["life"] <= 0:
                    self.particles.remove(pt)

            for c in self.corpses[:]:
                c["t"] -= 1
                if c["t"] % 8 == 0:
                    self.spawn_fx(c["x"] + c["w"] * 0.5, c["y"] + 8, (0.85, 0.08, 0.08), 2, 2.5, 4)
                if c["t"] <= 0:
                    self.corpses.remove(c)

            for g in self.grenades[:]:
                gb = g["y"]
                g["vy"] -= 0.85
                g["x"] += g["vx"]
                g["y"] += g["vy"]
                if g["x"] < 10: g["x"] = 10; g["vx"] *= -0.55
                elif g["x"] > W - 20: g["x"] = W - 20; g["vx"] *= -0.55
                for plat_y, pl_x, pl_w in ((self.f1_y, -500, W * 3), (self.f2_y, 0, W - self.lift_w - 20)):
                    if g["vy"] <= 0 and gb >= plat_y - 14 and g["y"] <= plat_y and g["x"] > pl_x and g["x"] < (pl_x + pl_w):
                        g["y"] = plat_y
                        g["vy"] = -g["vy"] * 0.42
                        g["vx"] *= 0.72
                g["t"] -= 1
                if g["t"] <= 0:
                    self.play_s("boom")
                    self.spawn_fx(g["x"], g["y"] + 8, (1.0, 0.55, 0.1), 22, 11.0, 10)
                    self.spawn_fx(g["x"], g["y"] + 8, (1.0, 0.9, 0.3), 10, 7.0, 6)
                    for e in self.enemies:
                        dist = math.hypot((e["x"] + e["w"] * 0.5) - g["x"], (e["y"] + e["h"] * 0.5) - g["y"])
                        if dist < 175:
                            e["hp"] -= 95 + self.dmg_l * 15
                            e["vy"] = 11; e["g"] = False
                    self.grenades.remove(g)

            for pad in self.ammo_pads:
                if pad["cd"] > 0:
                    pad["cd"] -= 1
                else:
                    if self.box_ov((self.px, self.py, self.p_sz, self.p_sz), (pad["x"], pad["y"], 36, 26), 10):
                        add_ammo = self.weapons[self.w_idx]["m"] + self.ammo_l * 6
                        self.reserve += add_ammo
                        if pad["nade"]: self.nades = min(5, self.nades + 1)
                        pad["cd"] = 600
                        self.play_s("buy")
                        self.spawn_fx(pad["x"] + 18, pad["y"] + 14, (0.3, 0.9, 0.4), 8, 5.0, 6)

            if self.timer > 0:
                self.timer -= 1
            else:
                self.rotor += 1
                if not self.heli_fly:
                    if self.heli_x < self.evac_x - 85:
                        self.heli_x += 7
                    else:
                        self.heli_ready = True
                else:
                    self.heli_y += 6
                    if self.heli_y > H + 120:
                        self.state = "WIN"

            for a in self.allies[:]:
                if a["cd"] > 0: a["cd"] -= 1
                a_2nd = a["y"] >= self.f2_y - 10
                if self.heli_ready:
                    if not a_2nd:
                        climb_x = self.lift_x + self.lift_w * 0.5 if pwr else self.lad_x + 22
                        if abs((a["x"] + self.p_sz * 0.5) - climb_x) > 12:
                            a["x"] += 5 if climb_x > (a["x"] + self.p_sz * 0.5) else -5
                        else:
                            a["y"] = min(self.f2_y, a["y"] + 6)
                    else:
                        if abs((a["x"] + self.p_sz * 0.5) - self.evac_x) > 18:
                            a["x"] += 5 if self.evac_x > (a["x"] + self.p_sz * 0.5) else -5
                elif a["role"] == "eng":
                    targets = []
                    for bar in self.bars:
                        if bar["hp"] < 120:
                            targets.append((bar["x"], bar["y"] >= self.f2_y - 10, bar, "bar"))
                    for t in self.turrets:
                        if t["hp"] < 100:
                            targets.append((t["x"], t["y"] >= self.f2_y - 10, t, "tur"))
                    if pwr and self.gen_hp < 250:
                        targets.append((self.gen_r + 35, False, None, "gen"))
                    if targets:
                        same_t = [it for it in targets if it == a_2nd]
                        tx, t_2nd, obj, kind = min(same_t or targets, key=lambda item: abs(item - a["x"]))
                        if t_2nd != a_2nd:
                            shaft_x = self.lift_x + self.lift_w * 0.5 if pwr else self.lad_x + 22
                            if abs((a["x"] + self.p_sz * 0.5) - shaft_x) > 15:
                                a["x"] += 4.5 if shaft_x > (a["x"] + self.p_sz * 0.5) else -4.5
                            else:
                                a["y"] = self.f2_y if t_2nd else self.f1_y
                        elif abs((a["x"] + self.p_sz * 0.5) - tx) > 35:
                            a["x"] += 4.5 if tx > (a["x"] + self.p_sz * 0.5) else -4.5
                        elif a["cd"] == 0:
                            a["cd"] = 90; self.play_s("buy")
                            if kind == "bar": obj["hp"] = min(120, obj["hp"] + 35)
                            elif kind == "tur": obj["hp"] = min(100, obj["hp"] + 30)
                            elif kind == "gen": self.gen_hp = min(250, self.gen_hp + 25)
                else:
                    p_2nd = self.py >= self.f2_y - 10
                    if p_2nd == a_2nd:
                        tx = self.px - 45 if self.right else self.px + self.p_sz + 10
                        if abs(a["x"] - tx) > 25:
                            a["x"] += 5 if tx > a["x"] else -5
                    if a["cd"] == 0:
                        healed = False
                        if p_2nd == a_2nd and self.hp < 100 and abs(a["x"] - self.px) < 140:
                            self.hp = min(100, self.hp + 15); healed = True
                        for other in self.allies:
                            if other is not a and (other["y"] >= self.f2_y - 10) == a_2nd and other["hp"] < other["max"] and abs(a["x"] - other["x"]) < 140:
                                other["hp"] = min(other["max"], other["hp"] + 15); healed = True
                        if healed:
                            a["cd"] = 150; self.play_s("buy")
                a["x"] = max(0, min(W - self.p_sz, a["x"]))

            if self.heli_ready and not self.heli_fly and not self.grabber:
                p_at_evac = (self.py >= self.f2_y - 10) and abs((self.px + self.p_sz * 0.5) - self.evac_x) < 55
                allies_ready = all((a["y"] >= self.f2_y - 10) and abs((a["x"] + self.p_sz * 0.5) - self.evac_x) < 65 for a in self.allies)
                if p_at_evac and allies_ready:
                    self.saved_names = ["СОЛДАТ"] + [a["n"].upper() for a in self.allies]
                    self.heli_fly = True
                    self.play_s("buy")

            self.sp_t += 1
            if self.sp_t >= max(45, 115 - self.kills * 2) and not self.heli_fly and len(self.enemies) < 22:
                self.sp_t = 0; es = H * 0.11
                on_top = True if (self.heli_ready or not pwr) else (random.random() < 0.35)
                ex = -es if (on_top or random.random() < 0.5) else W + es
                ey = self.f2_y if on_top else self.f1_y
                mhp = min(140, 40 + (self.kills // 10) * 10)
                ekind = random.choice(("white", "white", "dark", "dark", "grabber"))
                espd = random.randint(5, 8) if ekind == "grabber" else random.randint(4, 7)
                self.enemies.append({"x": ex, "y": ey, "w": es, "h": es, "hp": mhp, "max": mhp, "s": espd, "vy": 0, "g": True, "cd": 0, "kind": ekind, "moving": True})

            for t in self.turrets:
                if t["cd"] > 0: t["cd"] -= 1
                else:
                    same_fl = [e for e in self.enemies if abs(e["y"] - t["y"]) < 120]
                    if same_fl:
                        trg = min(same_fl, key=lambda e: abs(e["x"] - t["x"]))
                        dx = 1 if trg["x"] > t["x"] else -1
                        self.bullets.append({"x": t["x"] + 15, "y": t["y"] + 22, "vx": 20 * dx, "vy": 0, "d": 15})
                        t["cd"] = 35; self.play_s("shoot")

            for b in self.bullets[:]:
                b["x"] += b["vx"]; b["y"] += b["vy"]
                if b["x"] < -20 or b["x"] > W + 20: self.bullets.remove(b)

            for e in self.enemies[:]:
                if e["cd"] > 0: e["cd"] -= 1
                e_2nd = e["y"] >= self.f2_y - 10
                p_2nd = self.py >= self.f2_y - 10
                b_2nd = self.by >= self.f2_y - 10

                if e is self.grabber:
                    e["moving"] = False
                    e["x"] = self.px + (self.p_sz * 0.35 if self.right else -self.p_sz * 0.35)
                    e["y"] = self.py
                    if e["cd"] == 0:
                        self.hp -= 12
                        self.last_hit_kind = e["kind"]
                        e["cd"] = 45
                        self.play_s("hit")
                        self.spawn_fx(self.px + self.p_sz * 0.5, self.py + self.p_sz * 0.5, (0.95, 0.15, 0.15), 5, 4.0, 5)
                    continue

                chase_p = False
                if e_2nd:
                    if p_2nd and self.on_g: tx = self.px + self.p_sz * 0.5; chase_p = True
                    elif b_2nd and not self.carry_bomb: tx = self.bx + 25
                    else: tx = self.px + self.p_sz * 0.5; chase_p = True
                else:
                    if not p_2nd and self.on_g: tx = self.px + self.p_sz * 0.5; chase_p = True
                    elif pwr: tx = self.gen_r[0] + 35
                    elif not b_2nd and not self.carry_bomb: tx = self.bx + 25
                    else: tx = self.px + self.p_sz * 0.5; chase_p = True

                if e["g"] and e_2nd and random.random() < 0.018:
                    e["vy"] = 20; e["g"] = False

                blk = False
                for bar in self.bars[:]:
                    if self.box_ov((e["x"], e["y"], e["w"], e["h"]), (bar["x"], bar["y"], bar["w"], bar["h"])):
                        blk = True
                        if e["cd"] == 0:
                            bar["hp"] -= 25; e["cd"] = 51
                            if bar["hp"] <= 0: self.bars.remove(bar)
                        break
                for t in self.turrets[:]:
                    if self.box_ov((e["x"], e["y"], e["w"], e["h"]), (t["x"], t["y"], t["w"], t["h"])):
                        blk = True
                        if e["cd"] == 0:
                            t["hp"] -= 25; e["cd"] = 51
                            if t["hp"] <= 0: self.turrets.remove(t)
                        break
                if chase_p and abs((self.px + self.p_sz * 0.5) - (e["x"] + e["w"] * 0.5)) < self.p_sz * 0.85:
                    blk = True
                e["moving"] = not blk
                if not blk:
                    e["x"] += e["s"] * (1 if tx > (e["x"] + e["w"] * 0.5) else -1)

                eb = e["y"]; e["vy"] -= 1.1; e["y"] += e["vy"]; e["g"] = False
                if e["vy"] > 0 and (e["y"] + e["h"]) >= self.f2_y - 16 and e["y"] < self.f2_y and e["x"] < (W - self.lift_w - 20):
                    e["y"] = self.f2_y - 16 - e["h"]; e["vy"] = 0
                for plat_y, pl_x, pl_w in ((self.f1_y, -500, W * 3), (self.f2_y, 0, W - self.lift_w - 20)):
                    if e["vy"] <= 0 and eb >= plat_y - 14 and e["y"] <= plat_y and (e["x"] + e["w"]) > pl_x and e["x"] < (pl_x + pl_w):
                        e["y"] = plat_y; e["vy"] = 0; e["g"] = True

                for b in self.bullets[:]:
                    if self.box_ov((e["x"], e["y"], e["w"], e["h"]), (b["x"], b["y"], 15, 6)):
                        e["hp"] -= b["d"]; self.play_s("hit")
                        self.spawn_fx(b["x"], b["y"], (1.0, 0.85, 0.2), 4, 4.0, 4)
                        self.bullets.remove(b); break

                if e["hp"] <= 0:
                    self.spawn_fx(e["x"] + e["w"] * 0.5, e["y"] + e["h"] * 0.5, (0.95, 0.1, 0.1), 16, 7.5, 7)
                    self.corpses.append({
                        "x": e["x"], "y": self.f2_y if e_2nd else self.f1_y,
                        "w": e["w"], "h": e["h"],
                        "kind": e["kind"], "t": 120,
                        "dir": 1 if (self.px >= e["x"]) else -1
                    })
                    self.enemies.remove(e); self.coins += 10; self.kills += 1
                    if self.kills % 15 == 0 and self.nades < 5: self.nades += 1
                    if self.vamp_l > 0: self.hp = min(100, self.hp + self.vamp_l * 4)
                    continue

                if e["cd"] == 0:
                    hit_a = None
                    for a in self.allies:
                        if self.box_ov((e["x"], e["y"], e["w"], e["h"]), (a["x"], a["y"], self.p_sz, self.p_sz), 6):
                            hit_a = a; break
                    if hit_a:
                        hit_a["hp"] -= 15; e["cd"] = 51; self.play_s("hit")
                        if hit_a["hp"] <= 0:
                            self.spawn_fx(hit_a["x"] + self.p_sz * 0.5, hit_a["y"] + self.p_sz * 0.5, (1.0, 0.15, 0.15), 16, 7.0, 8)
                            self.allies.remove(hit_a)
                    elif e_2nd == p_2nd and self.box_ov((e["x"], e["y"], e["w"], e["h"]), (self.px, self.py, self.p_sz, self.p_sz), 8):
                        if e["kind"] == "grabber" and self.grabber is None:
                            self.grabber = e
                            self.grab_prog = 0
                            self.grab_last = ""
                            e["cd"] = 45
                            self.play_s("alarm")
                        else:
                            self.hp -= 15; e["cd"] = 51; self.play_s("hit")
                            self.last_hit_kind = e["kind"]
                            self.spawn_fx(self.px + self.p_sz * 0.5, self.py + self.p_sz * 0.5, (0.95, 0.15, 0.15), 6, 5.0, 6)
                    elif not self.carry_bomb and e_2nd == b_2nd and self.box_ov((e["x"], e["y"], e["w"], e["h"]), (self.bx, self.by, 50, 45)):
                        self.bomb_hp -= 12; e["cd"] = 51
                    elif not e_2nd and pwr and self.box_ov((e["x"], e["y"], e["w"], e["h"]), self.gen_r):
                        self.gen_hp = max(0, self.gen_hp - 15); e["cd"] = 51
                        if self.gen_hp == 0: self.play_s("alarm")

            if self.hp <= 0:
                self.trigger_death(self.last_hit_kind)
            elif self.bomb_hp <= 0:
                self.state = "OVER"
                self.death_mode = "BOMB"
                self.spawn_fx(self.bx + 25, self.by + 20, (1.0, 0.5, 0.1), 30, 12.0, 11)

        self.render()
    def render(self):
        W, H = self.W, self.H
        pwr = self.gen_hp > 0
        self.canvas.clear()
        with self.canvas:
            Color(*(0.11, 0.12, 0.15) if pwr else (0.05, 0.06, 0.08))
            Rectangle(pos=(0, 0), size=(W, H))
            Color(*(0.16, 0.17, 0.20) if pwr else (0.08, 0.09, 0.11))
            Rectangle(pos=(40, self.f1_y), size=(W - 80, H - self.f1_y - 30))

            for wx in range(120, int(W - 220), 260):
                for wy in (H * 0.35, H * 0.72):
                    Color(*(0.07, 0.09, 0.13) if pwr else (0.04, 0.05, 0.07))
                    Rectangle(pos=(wx, wy), size=(110, 90))

            if not pwr:
                Color(0.85, 0.65, 0.15)
                Rectangle(pos=(self.lad_x, self.f1_y), size=(6, self.f2_y - self.f1_y + 40))
                Rectangle(pos=(self.lad_x + 38, self.f1_y), size=(6, self.f2_y - self.f1_y + 40))
                for ry in range(int(self.f1_y + 18), int(self.f2_y + 35), 24):
                    Rectangle(pos=(self.lad_x, ry), size=(44, 5))

            Color(0.08, 0.08, 0.10)
            Rectangle(pos=(self.lift_x - 5, self.f1_y), size=(self.lift_w + 10, H - self.f1_y - 30))
            Color(*(0.71, 0.59, 0.20) if pwr else (0.32, 0.28, 0.16))
            Rectangle(pos=(self.lift_x, self.lift_y - 16), size=(self.lift_w, 16))
            Color(0.29, 0.31, 0.33)
            Rectangle(pos=(-500, 0), size=(W * 3, self.f1_y))
            Color(0.33, 0.35, 0.37)
            Rectangle(pos=(0, self.f2_y - 16), size=(W - self.lift_w - 20, 16))

            for pad in self.ammo_pads:
                Color(0.25, 0.28, 0.32)
                Rectangle(pos=(pad["x"] - 4, pad["y"]), size=(44, 5))
                if pad["cd"] == 0:
                    Color(0.18, 0.58, 0.28)
                    Rectangle(pos=(pad["x"], pad["y"] + 5), size=(36, 24))
                    Color(0.95, 0.85, 0.25)
                    Rectangle(pos=(pad["x"] + 6, pad["y"] + 13), size=(24, 8))
                    self.draw_txt("ПАТРОНЫ" + ("+ГРН" if pad["nade"] else ""), pad["x"] + 18, pad["y"] + 38, H * 0.024, (0.4, 1, 0.5, 1))
                else:
                    Color(0.3, 0.35, 0.3, 0.4)
                    Line(rectangle=(pad["x"], pad["y"] + 5, 36, 24), width=1.2)
                    self.draw_txt(f"{pad['cd'] // 60 + 1}с", pad["x"] + 18, pad["y"] + 18, H * 0.024, (0.6, 0.6, 0.6, 0.8))

            for t in self.turrets:
                Color(0.43, 0.47, 0.51)
                Rectangle(pos=(t["x"], t["y"]), size=(30, 35))
                Color(0.24, 0.86, 0.35)
                Rectangle(pos=(t["x"], t["y"] + 40), size=(30 * max(0, t["hp"]) / 100.0, 5))

            gx, gy, gw, gh = self.gen_r
            Color(*(0.22, 0.25, 0.29) if pwr else (0.14, 0.14, 0.16))
            Rectangle(pos=(gx, gy), size=(gw, gh))
            Color(*(0.16, 0.78, 1.0) if pwr else (0.35, 0.12, 0.12))
            Rectangle(pos=(gx + 12, gy + 12), size=(gw - 24, gh - 24))
            Color(0.24, 0.86, 0.35)
            Rectangle(pos=(gx - 5, gy + gh + 8), size=(80 * max(0, self.gen_hp) / 250.0, 7))
            self.draw_txt("ГЕНЕРАТОР" if pwr else "СЛОМАН", gx + gw * 0.5, gy + gh + 28, H * 0.032, (0.4, 0.86, 1, 1) if pwr else (1, 0.3, 0.3, 1))

            tx, ty, tw, th = self.tab_r
            Color(0.12, 0.14, 0.18)
            Rectangle(pos=(tx, ty), size=(tw, th))
            Color(*(0.0, 0.82, 1.0) if pwr else (0.18, 0.20, 0.22))
            Rectangle(pos=(tx + 4, ty + 7), size=(tw - 8, th - 14))
            self.draw_txt("БАФФЫ" if pwr else "OFFLINE", tx + tw * 0.5, ty + th + 16, H * 0.032, (0, 0.86, 1, 1) if pwr else (0.5, 0.5, 0.5, 1))

            Color(0.20, 0.22, 0.24)
            Rectangle(pos=(self.bx, self.by), size=(50, 45))
            Color(1.0, 0.2, 0.2)
            Ellipse(pos=(self.bx + 15, self.by + 12), size=(20, 20))
            Color(0.24, 0.86, 0.35)
            Rectangle(pos=(self.bx - 15, self.by + 55), size=(80 * max(0, self.bomb_hp) / 200.0, 8))
            if self.state in ("MENU", "PAUSE"):
                Color(0.04, 0.05, 0.07, 0.82)
                Rectangle(pos=(0, 0), size=(W, H))
                self.draw_txt("UNCHANGED" if self.state == "MENU" else "ПАУЗА", W * 0.5, H * 0.76, H * 0.10, (0, 0.85, 1, 1))
                sub = "v2.2 | ТРУПЫ, ТРАНСФУР И ХВАТАТЕЛИ" if self.state == "MENU" else f"УБИТО: {self.kills}  |  МОНЕТЫ: {self.coins}"
                self.draw_txt(sub, W * 0.5, H * 0.63, H * 0.038, (0.7, 0.75, 0.82, 1))
                if self.state == "MENU":
                    self.draw_txt("DEV: altynbekzhan6-sys | TG: Hunter yrruf", W * 0.5, H * 0.56, H * 0.032, (0.4, 0.88, 1.0, 1))
                menu_btns = [(self.b_play, (0.24, 0.82, 0.43), "ИГРАТЬ" if self.state == "MENU" else "ПРОДОЛЖИТЬ"),
                             (self.b_exit, (0.82, 0.25, 0.25), "ВЫХОД" if self.state == "MENU" else "В МЕНЮ")]
                if self.state == "PAUSE":
                    menu_btns.append((self.b_hud, (0.25, 0.65, 0.95), "КНОПКИ"))
                for br, col, txt in menu_btns:
                    Color(*col)
                    Rectangle(pos=(br[0], br[1]), size=(br[2], br[3]))
                    self.draw_txt(txt, br[0] + br[2] * 0.5, br[1] + br[3] * 0.5, H * 0.044, (0.08, 0.08, 0.08, 1))
            else:
                for c in self.corpses:
                    flist = self.furry_anims.get(c["kind"], self.furry_anims["white"])["idle"]
                    if flist:
                        ftex = flist[0]
                        alpha = min(1.0, c["t"] / 30.0)
                        Color(0.85, 0.65, 0.65, alpha)
                        u0, v0, u1, v1 = ftex.tex_coords[0], ftex.tex_coords[1], ftex.tex_coords[4], ftex.tex_coords[5]
                        tc = (u0, v1, u0, v0, u1, v0, u1, v1) if c["dir"] > 0 else (u1, v0, u1, v1, u0, v1, u0, v0)
                        Rectangle(texture=ftex, pos=(c["x"], c["y"]), size=(c["h"] * 1.25, c["w"] * 0.75), tex_coords=tc)

                for a in self.allies:
                    if not self.heli_fly:
                        acol = (1.0, 0.75, 0.20) if a["role"] == "eng" else (0.95, 0.95, 0.95)
                        Color(*acol)
                        Rectangle(pos=(a["x"], a["y"]), size=(self.p_sz, self.p_sz))
                        Color(0.24, 0.86, 0.35)
                        Rectangle(pos=(a["x"], a["y"] + self.p_sz + 4), size=(self.p_sz * max(0, a["hp"]) / a["max"], 5))
                        self.draw_txt(a["n"], a["x"] + self.p_sz * 0.5, a["y"] + self.p_sz + 20, H * 0.028, (0.6, 1, 0.7, 1))

                if not self.heli_fly:
                    if self.state == "OVER" and self.death_mode in ("TF_DARK", "TF_WHITE"):
                        tf_kind = "dark" if self.death_mode == "TF_DARK" else "white"
                        flist = self.furry_anims[tf_kind]["run"]
                        ftex = flist[int(self.anim_t * 10) % len(flist)]
                        Color(1, 1, 1, 1)
                        u0, v0, u1, v1 = ftex.tex_coords[0], ftex.tex_coords[1], ftex.tex_coords[4], ftex.tex_coords[5]
                        tc = (u0, v0, u1, v0, u1, v1, u0, v1) if self.tf_dir > 0 else (u1, v0, u0, v0, u0, v1, u1, v1)
                        Rectangle(texture=ftex, pos=(self.tf_x, self.tf_y), size=(self.p_sz * 1.35, self.p_sz * 1.35), tex_coords=tc)
                        self.draw_txt("ЗАРАЖЁННЫЙ СОЛДАТ", self.tf_x + self.p_sz * 0.65, self.tf_y + self.p_sz * 1.48, H * 0.030, (1, 0.3, 0.3, 1))
                    elif self.state == "OVER" and self.death_mode == "BLEED":
                        cur_list = self.anims["idle"]
                        if cur_list:
                            cur_tex = cur_list[0]
                            aspect = cur_tex.width / float(cur_tex.height)
                            spr_h = self.p_sz * 1.45
                            spr_w = spr_h * aspect
                            Color(0.85, 0.45, 0.45, 1)
                            u0, v0, u1, v1 = cur_tex.tex_coords[0], cur_tex.tex_coords[1], cur_tex.tex_coords[4], cur_tex.tex_coords[5]
                            tc = (u0, v1, u0, v0, u1, v0, u1, v1) if self.right else (u1, v0, u1, v1, u0, v1, u0, v0)
                            Rectangle(texture=cur_tex, pos=(self.px, self.py), size=(spr_h, spr_w * 0.75), tex_coords=tc)
                    elif self.hp > 0:
                        self.draw_txt("soldier", self.px + self.p_sz * 0.5, self.py + self.p_sz * 1.55, H * 0.032, (0.55, 0.82, 1, 1))
                        for bar in self.bars:
                            Color(0.59, 0.39, 0.20)
                            Rectangle(pos=(bar["x"], bar["y"]), size=(22, 55))
                        if self.muz_t > 0 or self.scd > max(0, self.weapons[self.w_idx]["cd"] - 8):
                            cur_list = self.anims["shot"]
                            fps = 24
                        elif self.is_moving:
                            cur_list = self.anims["run"] if self.spd_l > 0 else self.anims["move"]
                            fps = 12
                        else:
                            cur_list = self.anims["idle"]
                            fps = 8
                        if cur_list:
                            cur_tex = cur_list[int(self.anim_t * fps) % len(cur_list)]
                            aspect = cur_tex.width / float(cur_tex.height)
                            spr_h = self.p_sz * 2.05
                            spr_w = spr_h * aspect
                            spr_x = self.px if self.right else self.px - (spr_w - self.p_sz)
                            y_off = self.p_sz * 0.24

                            Color(1, 1, 1, 1)
                            u0, v0, u1, v1 = cur_tex.tex_coords[0], cur_tex.tex_coords[1], cur_tex.tex_coords[4], cur_tex.tex_coords[5]
                            tc = (u0, v0, u1, v0, u1, v1, u0, v1) if self.right else (u1, v0, u0, v0, u0, v1, u1, v1)
                            Rectangle(texture=cur_tex, pos=(spr_x, self.py - y_off), size=(spr_w, spr_h), tex_coords=tc)

                            if self.muz_t > 0:
                                muz_x = self.px + spr_w - 2 if self.right else spr_x - 22
                                muz_y = self.py + self.p_sz * 0.70
                                Color(1.0, 0.45, 0.0, 0.9)
                                Ellipse(pos=(muz_x, muz_y), size=(26, 15))
                                core_x = muz_x + (2 if self.right else 10)
                                Color(1.0, 0.95, 0.4, 1.0)
                                Ellipse(pos=(core_x, muz_y + 3), size=(14, 9))
                        else:
                            Color(0.27, 0.59, 1.0)
                            Rectangle(pos=(self.px, self.py), size=(self.p_sz, self.p_sz))

                        if self.mel_t > 0:
                            Color(1, 1, 1)
                            Line(circle=(self.px + (self.p_sz if self.right else 0), self.py + self.p_sz * 0.5, 45, -60 if self.right else 120, 60 if self.right else 240), width=4)
                Color(1.0, 0.90, 0.24)
                for b in self.bullets:
                    Rectangle(pos=(b["x"], b["y"]), size=(15, 6))

                for g in self.grenades:
                    Color(0.25, 0.45, 0.25)
                    Ellipse(pos=(g["x"] - 8, g["y"]), size=(16, 16))
                    if (g["t"] // 8) % 2 == 0:
                        Color(1.0, 0.2, 0.2)
                        Ellipse(pos=(g["x"] - 3, g["y"] + 5), size=(6, 6))

                for pt in self.particles:
                    alpha = max(0.0, pt["life"] / float(pt["max"]))
                    Color(pt["c"][0], pt["c"][1], pt["c"][2], alpha)
                    Rectangle(pos=(pt["x"], pt["y"]), size=(pt["sz"], pt["sz"]))

                for e in self.enemies:
                    ek = e.get("kind", "white")
                    k_anims = self.furry_anims.get(ek)
                    if k_anims:
                        if e is self.grabber or e["cd"] > 34:
                            estate, efps = "attack", 14
                        elif e.get("moving", True):
                            estate, efps = "run", 11
                        else:
                            estate, efps = "idle", 6
                        flist = k_anims[estate]
                        ftex = flist[int(self.anim_t * efps) % len(flist)]
                        Color(1, 1, 1, 1)
                        e_right = (self.px + self.p_sz * 0.5) >= (e["x"] + e["w"] * 0.5)
                        u0, v0, u1, v1 = ftex.tex_coords[0], ftex.tex_coords[1], ftex.tex_coords[4], ftex.tex_coords[5]
                        etc = (u0, v0, u1, v0, u1, v1, u0, v1) if e_right else (u1, v0, u0, v0, u0, v1, u1, v1)
                        Rectangle(texture=ftex, pos=(e["x"] - e["w"] * 0.15, e["y"]), size=(e["w"] * 1.35, e["h"] * 1.35), tex_coords=etc)
                    else:
                        Color(0.86, 0.24, 0.24)
                        Rectangle(pos=(e["x"], e["y"]), size=(e["w"], e["h"]))
                    Color(0.24, 0.86, 0.35)
                    Rectangle(pos=(e["x"], e["y"] + e["h"] * 1.38), size=(e["w"] * max(0, e["hp"]) / e["max"], 6))
                    ename = "latex" if ek == "dark" else ("grabber" if ek == "grabber" else "furry")
                    ecol = (0.85, 0.5, 1.0, 1) if ek == "grabber" else (1, 0.63, 0.63, 1)
                    self.draw_txt(ename, e["x"] + e["w"] * 0.5, e["y"] + e["h"] * 1.56, H * 0.030, ecol)

                if self.grabber and self.state == "PLAY":
                    Color(0.15, 0.05, 0.2, 0.78)
                    Rectangle(pos=(W * 0.5 - 240, H * 0.68), size=(480, 74))
                    self.draw_txt("СХВАЧЕН! ЖМИ < И > ЧТОБЫ ВЫРВАТЬСЯ!", W * 0.5, H * 0.68 + 50, H * 0.034, (1, 0.85, 0.2, 1))
                    Color(0.3, 0.3, 0.35)
                    Rectangle(pos=(W * 0.5 - 150, H * 0.68 + 14), size=(300, 16))
                    Color(0.25, 0.9, 0.4)
                    Rectangle(pos=(W * 0.5 - 150, H * 0.68 + 14), size=(300 * (self.grab_prog / 6.0), 16))

                if self.timer <= 0:
                    Color(0.24, 0.43, 0.27)
                    Ellipse(pos=(self.heli_x, self.heli_y), size=(170, 65))
                    rw = 180 if (self.rotor // 2) % 2 == 0 else 40
                    Color(0.86, 0.86, 0.86)
                    Line(points=[self.heli_x + 85 - rw, self.heli_y + 75, self.heli_x + 85 + rw, self.heli_y + 75], width=4)
                    if self.heli_ready and not self.heli_fly:
                        Color(0.9, 0.85, 0.5)
                        Line(points=[self.evac_x, self.heli_y, self.evac_x, self.f2_y], width=3)
                        Color(0.2, 1.0, 0.4, 0.25)
                        Rectangle(pos=(self.evac_x - 45, self.f2_y), size=(90, 90))
                        self.draw_txt("ВСЕ К ТРОСУ!", self.evac_x, self.f2_y + 105, H * 0.036, (0.3, 1, 0.5, 1))
                Color(0.63, 0.16, 0.16)
                Rectangle(pos=(20, H - 40), size=(200, 22))
                Color(0.24, 0.86, 0.35)
                Rectangle(pos=(20, H - 40), size=(200 * max(0, self.hp) / 100.0, 22))
                self.draw_txt(f"HP: {int(self.hp)}", 75, H - 29, H * 0.035)

                cw = self.weapons[self.w_idx]
                wtxt = "ПЕРЕЗАРЯДКА..." if self.rel_t > 0 else f"{cw['n']}: {self.ammo}/{self.reserve} | ГРН: {self.nades}"
                self.draw_txt(wtxt, 20, H - 72, H * 0.033, (1, 0.9, 0.47, 1), center=False)
                sl = self.timer // 60
                ttxt = f"БОМБА: {sl // 60:02d}:{sl % 60:02d}" if self.timer > 0 else "ЭВАКУАЦИЯ НА 2 ЭТАЖЕ!"
                self.draw_txt(ttxt, W * 0.5, H - 30, H * 0.044, (1, 0.35, 0.35, 1) if self.timer > 0 else (0.3, 1, 0.5, 1))
                self.draw_txt(f"Монеты: {self.coins} | Убито: {self.kills}", W - 260, H - 30, H * 0.035, (1, 0.84, 0, 1))

                Color(0.27, 0.29, 0.35)
                Rectangle(pos=(self.b_pause[0], self.b_pause[1]), size=(50, 44))
                self.draw_txt("||", self.b_pause[0] + 25, self.b_pause[1] + 22, H * 0.038)

                ntab = self.box_ov((self.px, self.py, self.p_sz, self.p_sz), self.tab_r, 30)
                nlift = abs((self.px + self.p_sz * 0.5) - (self.lift_x + self.lift_w * 0.5)) < self.lift_w
                act_lbl = "НЕТ ЭНЕРГИИ" if not pwr else (("ЛИФТ ВНИЗ" if self.lift_top else "ЛИФТ ВВЕРХ") if nlift else ("БАФФЫ" if ntab else "МАГАЗИН"))
                act_c = (0.39, 0.71, 1.0) if pwr else (0.35, 0.37, 0.41)
                mel_c = (1.0, 0.55, 0.20) if self.mel_cd == 0 else (0.47, 0.35, 0.24)
                grn_c = (0.35, 0.85, 0.40) if self.nades > 0 else (0.35, 0.37, 0.41)
                rep_c = (0.39, 0.90, 0.51) if (pwr and any(t["hp"] < 100 for t in self.turrets)) else (0.35, 0.37, 0.41)

                btns = [(self.b_l, (0.82, 0.82, 0.82), "<"), (self.b_r, (0.82, 0.82, 0.82), ">"),
                        (self.b_act, act_c, act_lbl), (self.b_rel, (0.71, 0.55, 1.0), "R"),
                        (self.b_grn, grn_c, f"ГРН({self.nades})"),
                        (self.b_f, (1.0, 0.33, 0.33), "FIRE"), (self.b_j, (1.0, 0.75, 0.24), "UP"),
                        (self.b_mel, mel_c, "УДАР"), (self.b_rep, rep_c, "РЕМОНТ (20)" if pwr else "НЕТ ЭНЕРГИИ")]
                if not pwr:
                    btns.append((self.b_bomb, (1.0, 0.45, 0.25) if self.carry_bomb else (0.95, 0.80, 0.20), "ПОСТАВИТЬ" if self.carry_bomb else "ВЗЯТЬ БОМБУ"))

                for br, col, txt in btns:
                    Color(*col)
                    Rectangle(pos=(br[0], br[1]), size=(br[2], br[3]))
                    self.draw_txt(txt, br[0] + br[2] * 0.5, br[1] + br[3] * 0.5, H * 0.030, (0.08, 0.08, 0.08, 1))

                if self.state in ("SHOP", "BUFF"):
                    Color(0.14, 0.15, 0.19)
                    Rectangle(pos=(self.m_r[0], self.m_r[1]), size=(self.m_r[2], self.m_r[3]))
                    Color(0.86, 0.24, 0.24)
                    Rectangle(pos=(self.cl_b[0], self.cl_b[1]), size=(50, 50))
                    self.draw_txt("X", self.cl_b[0] + 25, self.cl_b[1] + 25, H * 0.048)
                    if self.state == "SHOP":
                        has_e = any(a["role"] == "eng" for a in self.allies)
                        has_m = any(a["role"] == "med" for a in self.allies)
                        opts = ("Аптечка +40HP (30)", "Баррикада (40)", f"Оружие ({100 if self.w_idx==0 else 200})" if self.w_idx < 2 else "Макс. оружие", "Турель 1 ур. (80)",
                                "Инженер нанят" if has_e else "Нанять Инженера (90)", "Медик нанят" if has_m else "Нанять Медика (100)")
                        boxes = (self.o1, self.o2, self.o3, self.o4, self.o5, self.o6)
                    else:
                        opts = (f"Скорость {self.spd_l}/4 (50)", f"Вампиризм {self.vamp_l}/4 (70)", f"Патроны {self.ammo_l}/4 (60)", f"Урон {self.dmg_l}/4 (80)")
                        boxes = (self.o1, self.o2, self.o3, self.o4)
                    for br, ot in zip(boxes, opts):
                        Color(0.24, 0.25, 0.31)
                        Rectangle(pos=(br[0], br[1]), size=(br[2], br[3]))
                        self.draw_txt(ot, br[0] + 20, br[1] + br[3] * 0.5, H * 0.032, center=False)
                elif self.state == "WIN":
                    msg = f"ПОБЕДА! СПАСЕНЫ: {', '.join(self.saved_names)}"
                    self.draw_txt(msg, W * 0.5, H * 0.5, H * 0.042, (0.31, 1, 0.47, 1))
                elif self.state == "OVER":
                    if self.death_mode == "TF_DARK":
                        msg = "ВЫ СТАЛИ LATEX! НАЖМИ ДЛЯ РЕСТАРТА"
                        col_m = (0.75, 0.35, 1.0, 1)
                    elif self.death_mode == "TF_WHITE":
                        msg = "ВЫ СТАЛИ FURRY! НАЖМИ ДЛЯ РЕСТАРТА"
                        col_m = (0.95, 0.95, 1.0, 1)
                    elif self.death_mode == "BLEED":
                        msg = "СОЛДАТ ПАЛ В БОЮ, НО НЕ СДАЛСЯ! НАЖМИ ДЛЯ РЕСТАРТА"
                        col_m = (1.0, 0.25, 0.25, 1)
                    else:
                        msg = "БОМБА ВЗОРВАЛАСЬ! НАЖМИ ДЛЯ РЕСТАРТА"
                        col_m = (1.0, 0.55, 0.2, 1)
                    self.draw_txt(msg, W * 0.5, H * 0.52, H * 0.040, col_m)
                elif self.state == "EDIT_HUD":
                    Color(0.04, 0.05, 0.07, 0.65)
                    Rectangle(pos=(0, 0), size=(W, H))
                    self.draw_txt("ПЕРЕТАСКИВАЙ КНОПКИ ПАЛЬЦЕМ", W * 0.5, H - 95, H * 0.036, (0.4, 0.9, 1, 1))
                    edit_btns = [
                        (self.b_l, (0.82, 0.82, 0.82), "<"), (self.b_r, (0.82, 0.82, 0.82), ">"),
                        (self.b_act, (0.39, 0.71, 1.0), "ДЕЙСТВИЕ"), (self.b_rel, (0.71, 0.55, 1.0), "R"),
                        (self.b_grn, (0.35, 0.85, 0.40), "ГРН"),
                        (self.b_f, (1.0, 0.33, 0.33), "FIRE"), (self.b_j, (1.0, 0.75, 0.24), "UP"),
                        (self.b_mel, (1.0, 0.55, 0.20), "УДАР"), (self.b_rep, (0.39, 0.90, 0.51), "РЕМОНТ"),
                        (self.b_bomb, (0.95, 0.80, 0.20), "БОМБА")
                    ]
                    for br, col, txt in edit_btns:
                        Color(*col)
                        Rectangle(pos=(br[0], br[1]), size=(br[2], br[3]))
                        Color(1, 1, 1, 0.9)
                        Line(rectangle=(br[0], br[1], br[2], br[3]), width=1.5)
                        self.draw_txt(txt, br[0] + br[2] * 0.5, br[1] + br[3] * 0.5, H * 0.030, (0.08, 0.08, 0.08, 1))
                    for br, col, txt in ((self.b_hud_reset, (0.85, 0.35, 0.35), "СБРОС"), (self.b_hud_save, (0.24, 0.82, 0.43), "СОХРАНИТЬ")):
                        Color(*col)
                        Rectangle(pos=(br[0], br[1]), size=(br[2], br[3]))
                        self.draw_txt(txt, br[0] + br[2] * 0.5, br[1] + br[3] * 0.5, H * 0.032, (0.08, 0.08, 0.08, 1))

class UnchangedApp(App):
    def build(self):
        return GameWidget()

if __name__ == "__main__":
    UnchangedApp().run()
