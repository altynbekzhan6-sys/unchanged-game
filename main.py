import random, math, struct, wave, os, tempfile
from kivy.app import App
from kivy.uix.widget import Widget
from kivy.clock import Clock
from kivy.graphics import Color, Rectangle, Ellipse, Line
from kivy.core.text import Label as CoreLabel
from kivy.core.audio import SoundLoader

def make_snd(kind):
    try:
        sr = 22050
        dur = 0.08 if kind in ("hit", "buy") else (0.13 if kind in ("shoot", "melee", "rel") else 0.4)
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
        self.snds = {k: make_snd(k) for k in ("shoot", "melee", "hit", "buy", "rel", "alarm")}
        self.tex_cache = {}
        self.fingers = {}
        self.state = "MENU"
        self.weapons = {
            0: {"n": "Пистолет", "d": 20, "cd": 16, "m": 12, "s": 1},
            1: {"n": "Автомат",  "d": 18, "cd": 7,  "m": 30, "s": 1},
            2: {"n": "Дробовик", "d": 16, "cd": 28, "m": 8,  "s": 3},
        }
        self.W, self.H = 0, 0
        self.bind(size=self.on_resize)
        Clock.schedule_interval(self.update, 1.0 / 60.0)

    def play_s(self, k):
        s = self.snds.get(k)
        if s:
            try: s.stop(); s.play()
            except Exception: pass

    def on_resize(self, *args):
        w, h = self.width, self.height
        if w < 10 or h < 10: return
        first = (self.W == 0)
        self.W, self.H = w, h
        self.f1_y, self.f2_y, self.lift_w = h * 0.22, h * 0.58, w * 0.11
        self.lift_x = w - self.lift_w - 10
        self.lad_x = w - self.lift_w - 85
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
        self.b_act = (w * 0.5 - bs * 1.1, by, bs * 2.2, bs)
        self.b_rep = (w * 0.5 - bs * 1.1, by + bs + 6, bs * 2.2, bs * 0.52)
        self.b_bomb = (25, by + bs + 6, bs * 2.1, bs * 0.52)
        self.b_pause = (w - 65, h - 58, 50, 44)
        bw, bh = w * 0.34, h * 0.12
        self.b_play = (w * 0.5 - bw * 0.5, h * 0.40, bw, bh)
        self.b_exit = (w * 0.5 - bw * 0.5, h * 0.24, bw, bh)
        mw, mh = w * 0.65, h * 0.65
        mx, my = (w - mw) * 0.5, (h - mh) * 0.5
        self.m_r = (mx, my, mw, mh)
        oh = mh * 0.16
        self.o1 = (mx + 30, my + mh - 65 - oh, mw - 60, oh)
        self.o2 = (mx + 30, my + mh - 75 - oh * 2, mw - 60, oh)
        self.o3 = (mx + 30, my + mh - 85 - oh * 3, mw - 60, oh)
        self.o4 = (mx + 30, my + mh - 95 - oh * 4, mw - 60, oh)
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
        self.w_idx, self.ammo, self.rel_t, self.scd, self.muz_t, self.mel_t, self.mel_cd = 0, 12, 0, 0, 0, 0, 0
        self.bomb_hp, self.gen_hp, self.timer, self.heli_x, self.rotor = 200, 250, 10 * 3600, -250, 0
        self.lift_y, self.lift_ty, self.lift_top = self.f1_y, self.f1_y, False
        self.vy, self.on_g, self.right = 0, True, True
        self.bullets, self.enemies, self.bars, self.turrets = [], [], [], []
        self.sp_t = 0
        self.state = "PLAY"

    def txt_tex(self, text, size):
        key = (text, int(size))
        if key not in self.tex_cache:
            if len(self.tex_cache) > 150: self.tex_cache.clear()
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
        if self.rel_t == 0 and self.ammo < self.weapons[self.w_idx]["m"] + self.ammo_l * 6:
            self.rel_t = 60; self.play_s("rel")

    def shoot(self):
        if self.rel_t > 0 or self.scd > 0: return
        if self.ammo <= 0: self.start_rel(); return
        w = self.weapons[self.w_idx]
        self.ammo -= 1; self.scd = w["cd"]; self.muz_t = 4; self.play_s("shoot")
        dx = 1 if self.right else -1
        tx = self.px + self.p_sz + 15 if self.right else self.px - 25
        spread = (0,) if w["s"] == 1 else (-3, 0, 3)
        for dy in spread:
            self.bullets.append({"x": tx, "y": self.py + self.p_sz * 0.5, "vx": 22 * dx, "vy": dy, "d": w["d"] + self.dmg_l * 5})
        if self.ammo == 0: self.start_rel()

    def do_melee(self):
        if self.mel_cd > 0: return
        self.mel_t = 10; self.mel_cd = 24; self.play_s("melee")
        dx = 1 if self.right else -1
        hx = self.px + self.p_sz - 10 if self.right else self.px - 75
        hr = (hx, self.py - 10, 85, self.p_sz + 20)
        for e in self.enemies:
            if self.box_ov(hr, (e["x"], e["y"], e["w"], e["h"])):
                e["hp"] -= 30 + self.dmg_l * 5; self.play_s("hit")
                e["x"] = max(0, min(self.W - e["w"], e["x"] + 110 * dx))
                e["vy"] = 7; e["g"] = False
    def on_touch_down(self, touch):
        self.fingers[touch.uid] = (touch.x, touch.y)
        self.handle_tap(touch.x, touch.y)
        return True

    def on_touch_move(self, touch):
        if touch.uid in self.fingers:
            self.fingers[touch.uid] = (touch.x, touch.y)
        return True

    def on_touch_up(self, touch):
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
            elif self.in_r(self.b_exit, x, y): self.state = "MENU"
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
                        self.ammo = self.weapons[self.w_idx]["m"] + self.ammo_l * 6
                        self.rel_t = 0; self.play_s("buy")
                elif self.in_r(self.o4, x, y) and self.coins >= 80:
                    self.coins -= 80; self.play_s("buy")
                    self.turrets.append({"x": self.px + self.p_sz * 0.5 - 15, "y": self.py, "w": 30, "h": 35, "cd": 0, "hp": 100})
            else:
                if self.in_r(self.o1, x, y) and self.coins >= 50 and self.spd_l < 4:
                    self.coins -= 50; self.spd_l += 1; self.play_s("buy")
                elif self.in_r(self.o2, x, y) and self.coins >= 70 and self.vamp_l < 4:
                    self.coins -= 70; self.vamp_l += 1; self.play_s("buy")
                elif self.in_r(self.o3, x, y) and self.coins >= 60 and self.ammo_l < 4:
                    self.coins -= 60; self.ammo_l += 1
                    self.ammo = self.weapons[self.w_idx]["m"] + self.ammo_l * 6; self.play_s("buy")
                elif self.in_r(self.o4, x, y) and self.coins >= 80 and self.dmg_l < 4:
                    self.coins -= 80; self.dmg_l += 1; self.play_s("buy")
            return

        if st == "PLAY":
            if self.in_r(self.b_pause, x, y): self.state = "PAUSE"; return
            if self.in_r(self.b_mel, x, y): self.do_melee()
            if self.in_r(self.b_rel, x, y): self.start_rel()
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

        if self.state == "PLAY":
            ml = mr = up_hold = False
            for fx, fy in self.fingers.values():
                if self.in_r(self.b_l, fx, fy): ml = True
                if self.in_r(self.b_r, fx, fy): mr = True
                if self.in_r(self.b_j, fx, fy): up_hold = True
                if self.in_r(self.b_f, fx, fy): self.shoot()

            on_lad = (not pwr) and abs((self.px + self.p_sz * 0.5) - (self.lad_x + 22)) < 38
            if on_lad and up_hold:
                self.py = min(self.f2_y, self.py + 8)
                self.vy = 0; self.on_g = True
            elif up_hold and self.on_g:
                self.vy = 21; self.on_g = False

            if pwr:
                if self.lift_y < self.lift_ty: self.lift_y = min(self.lift_ty, self.lift_y + 6)
                elif self.lift_y > self.lift_ty: self.lift_y = max(self.lift_ty, self.lift_y - 6)

            spd = 10 + self.spd_l * 2
            if ml: self.px -= spd; self.right = False
            if mr: self.px += spd; self.right = True
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
                if self.rel_t == 0: self.ammo = self.weapons[self.w_idx]["m"] + self.ammo_l * 6

            if self.timer > 0: self.timer -= 1
            else:
                self.rotor += 1
                if self.heli_x < self.px + self.p_sz * 0.5 - 90: self.heli_x += 7
                else: self.state = "WIN"

            self.sp_t += 1
            if self.sp_t >= max(45, 115 - self.kills * 2) and self.timer > 0:
                self.sp_t = 0; es = H * 0.11
                if not pwr and not self.carry_bomb and self.by >= self.f2_y - 10:
                    on_top = True
                else:
                    on_top = random.random() < 0.35
                ex = -es if (on_top or random.random() < 0.5) else W + es
                ey = self.f2_y if on_top else self.f1_y
                mhp = min(140, 40 + (self.kills // 10) * 10)
                self.enemies.append({"x": ex, "y": ey, "w": es, "h": es, "hp": mhp, "max": mhp, "s": random.randint(4, 7), "vy": 0, "g": True, "cd": 0})

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
                        e["hp"] -= b["d"]; self.play_s("hit"); self.bullets.remove(b); break
                if e["hp"] <= 0:
                    self.enemies.remove(e); self.coins += 10; self.kills += 1
                    if self.vamp_l > 0: self.hp = min(100, self.hp + self.vamp_l * 4)
                    continue

                if e["cd"] == 0:
                    if e_2nd == p_2nd and self.box_ov((e["x"], e["y"], e["w"], e["h"]), (self.px, self.py, self.p_sz, self.p_sz), 8):
                        self.hp -= 15; e["cd"] = 51; self.play_s("hit")
                    elif not self.carry_bomb and e_2nd == b_2nd and self.box_ov((e["x"], e["y"], e["w"], e["h"]), (self.bx, self.by, 50, 45)):
                        self.bomb_hp -= 12; e["cd"] = 51
                    elif not e_2nd and pwr and self.box_ov((e["x"], e["y"], e["w"], e["h"]), self.gen_r):
                        self.gen_hp = max(0, self.gen_hp - 15); e["cd"] = 51
                        if self.gen_hp == 0: self.play_s("alarm")

            if self.hp <= 0 or self.bomb_hp <= 0: self.state = "OVER"

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
                sub = "v1.8 | АВАРИЙНАЯ ЛЕСТНИЦА И БОМБА" if self.state == "MENU" else f"УБИТО: {self.kills}  |  МОНЕТЫ: {self.coins}"
                self.draw_txt(sub, W * 0.5, H * 0.62, H * 0.038, (0.7, 0.75, 0.82, 1))
                for br, col, txt in ((self.b_play, (0.24, 0.82, 0.43), "ИГРАТЬ" if self.state == "MENU" else "ПРОДОЛЖИТЬ"),
                                     (self.b_exit, (0.82, 0.25, 0.25), "ВЫХОД" if self.state == "MENU" else "В МЕНЮ")):
                    Color(*col)
                    Rectangle(pos=(br[0], br[1]), size=(br[2], br[3]))
                    self.draw_txt(txt, br[0] + br[2] * 0.5, br[1] + br[3] * 0.5, H * 0.048, (0.08, 0.08, 0.08, 1))
            else:
                self.draw_txt("soldier", self.px + self.p_sz * 0.5, self.py + self.p_sz + 18, H * 0.032, (0.55, 0.82, 1, 1))
                for bar in self.bars:
                    Color(0.59, 0.39, 0.20)
                    Rectangle(pos=(bar["x"], bar["y"]), size=(22, 55))
                Color(0.27, 0.59, 1.0)
                Rectangle(pos=(self.px, self.py), size=(self.p_sz, self.p_sz))
                gx_p = self.px + self.p_sz - 4 if self.right else self.px - 26
                Color(0.08, 0.08, 0.10)
                Rectangle(pos=(gx_p, self.py + self.p_sz * 0.45), size=(30, 10))
                if self.muz_t > 0:
                    Color(1.0, 0.63, 0.0)
                    Ellipse(pos=(gx_p + (30 if self.right else -24), self.py + self.p_sz * 0.42), size=(24, 16))
                if self.mel_t > 0:
                    Color(1, 1, 1)
                    Line(circle=(self.px + (self.p_sz if self.right else 0), self.py + self.p_sz * 0.5, 45, -60 if self.right else 120, 60 if self.right else 240), width=4)

                Color(1.0, 0.90, 0.24)
                for b in self.bullets:
                    Rectangle(pos=(b["x"], b["y"]), size=(15, 6))

                for e in self.enemies:
                    Color(0.86, 0.24, 0.24)
                    Rectangle(pos=(e["x"], e["y"]), size=(e["w"], e["h"]))
                    Color(0.24, 0.86, 0.35)
                    Rectangle(pos=(e["x"], e["y"] + e["h"] + 6), size=(e["w"] * max(0, e["hp"]) / e["max"], 6))
                    self.draw_txt("furry", e["x"] + e["w"] * 0.5, e["y"] + e["h"] + 24, H * 0.032, (1, 0.63, 0.63, 1))

                if self.timer <= 0:
                    Color(0.24, 0.43, 0.27)
                    Ellipse(pos=(self.heli_x, H * 0.78), size=(170, 65))
                    rw = 180 if (self.rotor // 2) % 2 == 0 else 40
                    Color(0.86, 0.86, 0.86)
                    Line(points=[self.heli_x + 85 - rw, H * 0.78 + 75, self.heli_x + 85 + rw, H * 0.78 + 75], width=4)

                Color(0.63, 0.16, 0.16)
                Rectangle(pos=(20, H - 40), size=(200, 22))
                Color(0.24, 0.86, 0.35)
                Rectangle(pos=(20, H - 40), size=(200 * max(0, self.hp) / 100.0, 22))
                self.draw_txt(f"HP: {int(self.hp)}", 75, H - 29, H * 0.035)

                cw = self.weapons[self.w_idx]
                wtxt = "ПЕРЕЗАРЯДКА..." if self.rel_t > 0 else f"{cw['n']}: {self.ammo}/{cw['m'] + self.ammo_l * 6}"
                self.draw_txt(wtxt, 20, H - 62, H * 0.035, (1, 0.9, 0.47, 1), center=False)
                sl = self.timer // 60
                self.draw_txt(f"БОМБА: {sl // 60:02d}:{sl % 60:02d}", W * 0.5, H - 30, H * 0.048, (1, 0.35, 0.35, 1))
                self.draw_txt(f"Монеты: {self.coins} | Убито: {self.kills}", W - 260, H - 30, H * 0.035, (1, 0.84, 0, 1))

                Color(0.27, 0.29, 0.35)
                Rectangle(pos=(self.b_pause[0], self.b_pause[1]), size=(50, 44))
                self.draw_txt("||", self.b_pause[0] + 25, self.b_pause[1] + 22, H * 0.038)

                ntab = self.box_ov((self.px, self.py, self.p_sz, self.p_sz), self.tab_r, 30)
                nlift = abs((self.px + self.p_sz * 0.5) - (self.lift_x + self.lift_w * 0.5)) < self.lift_w
                act_lbl = "НЕТ ЭНЕРГИИ" if not pwr else (("ЛИФТ ВНИЗ" if self.lift_top else "ЛИФТ ВВЕРХ") if nlift else ("БАФФЫ" if ntab else "МАГАЗИН"))
                act_c = (0.39, 0.71, 1.0) if pwr else (0.35, 0.37, 0.41)
                mel_c = (1.0, 0.55, 0.20) if self.mel_cd == 0 else (0.47, 0.35, 0.24)
                rep_c = (0.39, 0.90, 0.51) if (pwr and any(t["hp"] < 100 for t in self.turrets)) else (0.35, 0.37, 0.41)

                btns = [(self.b_l, (0.82, 0.82, 0.82), "<"), (self.b_r, (0.82, 0.82, 0.82), ">"),
                        (self.b_act, act_c, act_lbl), (self.b_rel, (0.71, 0.55, 1.0), "R"),
                        (self.b_f, (1.0, 0.33, 0.33), "FIRE"), (self.b_j, (1.0, 0.75, 0.24), "UP"),
                        (self.b_mel, mel_c, "УДАР"), (self.b_rep, rep_c, "РЕМОНТ (20)" if pwr else "НЕТ ЭНЕРГИИ")]
                if not pwr:
                    btns.append((self.b_bomb, (1.0, 0.45, 0.25) if self.carry_bomb else (0.95, 0.80, 0.20), "ПОСТАВИТЬ" if self.carry_bomb else "ВЗЯТЬ БОМБУ"))

                for br, col, txt in btns:
                    Color(*col)
                    Rectangle(pos=(br[0], br[1]), size=(br[2], br[3]))
                    self.draw_txt(txt, br[0] + br[2] * 0.5, br[1] + br[3] * 0.5, H * 0.032, (0.08, 0.08, 0.08, 1))

                if self.state in ("SHOP", "BUFF"):
                    Color(0.14, 0.15, 0.19)
                    Rectangle(pos=(self.m_r[0], self.m_r[1]), size=(self.m_r[2], self.m_r[3]))
                    Color(0.86, 0.24, 0.24)
                    Rectangle(pos=(self.cl_b[0], self.cl_b[1]), size=(50, 50))
                    self.draw_txt("X", self.cl_b[0] + 25, self.cl_b[1] + 25, H * 0.048)
                    if self.state == "SHOP":
                        opts = ("Аптечка +40HP (30)", "Баррикада (40)", f"Оружие ({100 if self.w_idx==0 else 200})" if self.w_idx < 2 else "Макс. оружие", "Турель 1 ур. (80)")
                    else:
                        opts = (f"Скорость {self.spd_l}/4 (50)", f"Вампиризм {self.vamp_l}/4 (70)", f"Патроны {self.ammo_l}/4 (60)", f"Урон {self.dmg_l}/4 (80)")
                    for br, ot in zip((self.o1, self.o2, self.o3, self.o4), opts):
                        Color(0.24, 0.25, 0.31)
                        Rectangle(pos=(br[0], br[1]), size=(br[2], br[3]))
                        self.draw_txt(ot, br[0] + 20, br[1] + br[3] * 0.5, H * 0.036, center=False)
                elif self.state in ("OVER", "WIN"):
                    msg = "ПОБЕДА! ВЕРТОЛЕТ ПРИЛЕТЕЛ!" if self.state == "WIN" else "ПОРАЖЕНИЕ! НАЖМИ ДЛЯ РЕСТАРТА"
                    col_m = (0.31, 1, 0.47, 1) if self.state == "WIN" else (1, 0.31, 0.31, 1)
                    self.draw_txt(msg, W * 0.5, H * 0.5, H * 0.048, col_m)

class UnchangedApp(App):
    def build(self):
        return GameWidget()

if __name__ == "__main__":
    UnchangedApp().run()
