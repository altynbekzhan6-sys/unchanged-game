import pygame, random

pygame.init()
screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
W, H = screen.get_size()
clock = pygame.time.Clock()
def init_layout():
    global f_sm, f_md, f1_y, f2_y, lift_w, f1_r, f2_r, lift_x, lift_r, bomb_r, gen_r, p_sz
    global b_s, b_l, b_r, b_j, b_f, b_rel, b_act, m_r, o1, o2, o3, cl_b, o4, b_rep, tab_r, b_mel
    f_sm = pygame.font.SysFont(None, max(20, int(H * 0.04)))
    f_md = pygame.font.SysFont(None, max(28, int(H * 0.055)))
    f1_y, f2_y, lift_w = int(H * 0.78), int(H * 0.42), int(W * 0.11)
    f1_r = pygame.Rect(-500, f1_y, W * 3, H - f1_y)
    f2_r = pygame.Rect(0, f2_y, W - lift_w - 20, int(H * 0.035))
    lift_x = W - lift_w - 10
    lift_r = pygame.Rect(lift_x, f1_y - 16, lift_w, 16)
    bomb_r = pygame.Rect(W // 2 - 25, f2_y - 45, 50, 45)
    gen_r = pygame.Rect(W // 2 - 35, f1_y - 65, 70, 65)
    tab_r = pygame.Rect(int(W * 0.22), f2_y - 68, 44, 52)
    p_sz = int(H * 0.11)
    b_s = int(H * 0.15)
    by = H - b_s - int(H * 0.025)
    b_l, b_r = pygame.Rect(25, by, b_s, b_s), pygame.Rect(35 + b_s, by, b_s, b_s)
    b_j = pygame.Rect(W - b_s - 25, by, b_s, b_s)
    b_f = pygame.Rect(W - b_s * 2 - 40, by, b_s, b_s)
    b_mel = pygame.Rect(W - b_s * 2 - 40, by - int(b_s * 0.56) - 4, b_s, int(b_s * 0.52))
    b_rel = pygame.Rect(W - b_s * 3 - 55, by, b_s, b_s)
    b_act = pygame.Rect(W // 2 - int(b_s * 1.1), by, int(b_s * 2.2), b_s)
    b_rep = pygame.Rect(W // 2 - int(b_s * 1.1), by - int(b_s * 0.56) - 4, int(b_s * 2.2), int(b_s * 0.52))
    mw, mh = int(W * 0.65), int(H * 0.65)
    m_r = pygame.Rect((W - mw) // 2, (H - mh) // 2, mw, mh)
    o1 = pygame.Rect(m_r.x + 30, m_r.y + 65, mw - 60, int(mh * 0.16))
    o2 = pygame.Rect(m_r.x + 30, m_r.y + 75 + int(mh * 0.16), mw - 60, int(mh * 0.16))
    o3 = pygame.Rect(m_r.x + 30, m_r.y + 85 + int(mh * 0.32), mw - 60, int(mh * 0.16))
    o4 = pygame.Rect(m_r.x + 30, m_r.y + 95 + int(mh * 0.48), mw - 60, int(mh * 0.16))
    cl_b = pygame.Rect(m_r.right - 65, m_r.y + 15, 50, 50)

init_layout()
lift_ty, lift_top = f1_y - 16, False
bomb_hp, gen_hp, timer, heli_x, rotor = 200, 250, 10 * 60 * 60, -250, 0
player = pygame.Rect(W // 2 - 80, f1_y - p_sz, p_sz, p_sz)
hp, coins, kills, spd_l, vamp_l, ammo_l, dmg_l = 100, 0, 0, 0, 0, 0, 0
vy, on_g, right = 0, True, True

weapons = {
    0: {"n": "Пистолет", "d": 20, "cd": 16, "m": 12, "s": 1},
    1: {"n": "Автомат",  "d": 18, "cd": 7,  "m": 30, "s": 1},
    2: {"n": "Дробовик", "d": 16, "cd": 28, "m": 8,  "s": 3},
}
w_idx, ammo, rel_t, scd, muz_t, mel_t, mel_cd = 0, 12, 0, 0, 0, 0, 0
bullets, enemies, bars, sp_t, fingers, state = [], [], [], 0, {}, "PLAY"
turrets = []

def reset():
    global hp, coins, kills, spd_l, vamp_l, ammo_l, dmg_l, w_idx, ammo, rel_t, bomb_hp, gen_hp, timer, lift_top, lift_ty, heli_x, state, mel_t, mel_cd
    player.midbottom = (W // 2 - 80, f1_y)
    hp, coins, kills, spd_l, vamp_l, ammo_l, dmg_l, w_idx, ammo, rel_t = 100, 0, 0, 0, 0, 0, 0, 0, 12, 0
    bomb_hp, gen_hp, timer, lift_top, lift_ty, heli_x, state, mel_t, mel_cd = 200, 250, 10 * 60 * 60, False, f1_y - 16, -250, "PLAY", 0, 0
    lift_r.y = lift_ty
    bullets.clear(); enemies.clear(); bars.clear(); turrets.clear()

def start_rel():
    global rel_t
    if rel_t == 0 and ammo < weapons[w_idx]["m"] + ammo_l * 6: rel_t = 60

def shoot():
    global ammo, scd, muz_t
    if rel_t > 0 or scd > 0: return
    if ammo <= 0: start_rel(); return
    w = weapons[w_idx]
    ammo -= 1; scd = w["cd"]; muz_t = 4
    dx = 1 if right else -1
    tx = player.right + 20 if right else player.left - 30
    spread = (0,) if w["s"] == 1 else (-3, 0, 3)
    for dy in spread:
        bullets.append({"r": pygame.Rect(tx, player.centery - 4, 15, 6), "vx": 22 * dx, "vy": dy, "d": w["d"] + dmg_l * 5})
    if ammo == 0: start_rel()

def melee():
    global mel_t, mel_cd
    if mel_cd > 0: return
    mel_t = 10; mel_cd = 24
    dx = 1 if right else -1
    hit_r = pygame.Rect(player.right - 10 if right else player.left - 75, player.top - 10, 85, player.height + 20)
    for e in enemies:
        if hit_r.colliderect(e["r"]):
            e["hp"] -= 30 + dmg_l * 5
            e["r"].x = max(0, min(W - e["r"].width, e["r"].x + 110 * dx))
            e["vy"] = -7; e["g"] = False

run = True
while run:
    cw, ch = screen.get_size()
    if cw != W or ch != H:
        W, H = cw, ch; init_layout()
        lift_ty = f2_y if lift_top else f1_y - 16; lift_r.y = lift_ty
        player.size = (p_sz, p_sz); player.midbottom = (W // 2 - 80, f1_y)
    tap = None
    for ev in pygame.event.get():
        if ev.type == pygame.QUIT: run = False
        elif ev.type == pygame.FINGERDOWN:
            fingers[ev.finger_id] = tap = (ev.x * W, ev.y * H)
        elif ev.type == pygame.FINGERMOTION:
            fingers[ev.finger_id] = (ev.x * W, ev.y * H)
        elif ev.type == pygame.FINGERUP:
            fingers.pop(ev.finger_id, None)

    if gen_hp <= 0 and state in ("SHOP", "BUFF"): state = "PLAY"

    if state in ("SHOP", "BUFF") and tap:
        if cl_b.collidepoint(tap): state = "PLAY"
        elif state == "SHOP":
            if o1.collidepoint(tap) and coins >= 30 and hp < 100: coins -= 30; hp = min(100, hp + 40)
            elif o2.collidepoint(tap) and coins >= 40:
                coins -= 40
                bars.append({"r": pygame.Rect(player.right + 15 if right else player.left - 35, player.bottom - 55, 22, 55), "hp": 120})
            elif o3.collidepoint(tap) and w_idx < 2:
                c = 100 if w_idx == 0 else 200
                if coins >= c: coins -= c; w_idx += 1; ammo = weapons[w_idx]["m"] + ammo_l * 6; rel_t = 0
            elif o4.collidepoint(tap) and coins >= 80:
                coins -= 80
                turrets.append({"r": pygame.Rect(player.centerx - 15, player.bottom - 35, 30, 35), "cd": 0, "hp": 100})
        else:
            if o1.collidepoint(tap) and coins >= 50 and spd_l < 4: coins -= 50; spd_l += 1
            elif o2.collidepoint(tap) and coins >= 70 and vamp_l < 4: coins -= 70; vamp_l += 1
            elif o3.collidepoint(tap) and coins >= 60 and ammo_l < 4: coins -= 60; ammo_l += 1; ammo = weapons[w_idx]["m"] + ammo_l * 6
            elif o4.collidepoint(tap) and coins >= 80 and dmg_l < 4: coins -= 80; dmg_l += 1
    elif state in ("OVER", "WIN") and tap: reset()

    if state == "PLAY":
        ml = mr = False
        for p in fingers.values():
            if b_l.collidepoint(p): ml = True
            if b_r.collidepoint(p): mr = True
            if b_j.collidepoint(p) and on_g: vy = -21; on_g = False
            if b_f.collidepoint(p): shoot()

        ntab = player.colliderect(tab_r.inflate(40, 20))
        nlift = abs(player.centerx - lift_r.centerx) < lift_w
        if nlift: act_lbl = "ЛИФТ ВНИЗ" if lift_top else "ЛИФТ ВВЕРХ"
        elif gen_hp <= 0: act_lbl = "НЕТ ЭНЕРГИИ"
        else: act_lbl = "БАФФЫ" if ntab else "МАГАЗИН"

        if tap and b_mel.collidepoint(tap): melee()
        if gen_hp > 0 and tap and tab_r.inflate(25, 25).collidepoint(tap): state = "BUFF"
        if tap and b_rel.collidepoint(tap): start_rel()
        if tap and b_act.collidepoint(tap):
            if nlift: lift_top = not lift_top; lift_ty = f2_y if lift_top else f1_y - 16
            elif gen_hp > 0: state = "BUFF" if ntab else "SHOP"
        if gen_hp > 0 and tap and b_rep.collidepoint(tap) and coins >= 20:
            dmg_t = [t for t in turrets if t["hp"] < 100]
            if dmg_t:
                near_t = min(dmg_t, key=lambda t: abs(t["r"].centerx - player.centerx))
                coins -= 20; near_t["hp"] = min(100, near_t["hp"] + 60)
        lift_r.y += 6 if lift_r.y < lift_ty else (-6 if lift_r.y > lift_ty else 0)
        if abs(lift_r.y - lift_ty) < 6: lift_r.y = lift_ty

        spd = 10 + spd_l * 2
        if ml: player.x -= spd; right = False
        if mr: player.x += spd; right = True
        player.x = max(0, min(W - p_sz, player.x))

        pb = player.bottom; vy += 1.1; player.y += vy; on_g = False
        for plat in (f1_r, f2_r, lift_r):
            if vy >= 0 and pb <= plat.top + 14 and player.colliderect(plat):
                player.bottom = plat.top; vy = 0; on_g = True

        if scd > 0: scd -= 1
        if muz_t > 0: muz_t -= 1
        if mel_t > 0: mel_t -= 1
        if mel_cd > 0: mel_cd -= 1
        if rel_t > 0:
            rel_t -= 1
            if rel_t == 0: ammo = weapons[w_idx]["m"] + ammo_l * 6

        if timer > 0: timer -= 1
        else:
            rotor += 1
            if heli_x < player.centerx - 90: heli_x += 7
            else: state = "WIN"

        sp_t += 1
        if sp_t >= max(45, 115 - kills * 2) and timer > 0:
            sp_t = 0; es = int(H * 0.11)
            on_top = random.random() < 0.35
            ex = -es if (on_top or random.random() < 0.5) else W + es
            ey = (f2_y if on_top else f1_y) - es
            mhp = min(140, 40 + (kills // 10) * 10)
            enemies.append({"r": pygame.Rect(ex, ey, es, es),
                            "hp": mhp, "max_hp": mhp, "s": random.randint(4, 7), "vy": 0, "g": True, "atk_cd": 0})
        for t in turrets:
            if t["cd"] > 0: t["cd"] -= 1
            else:
                same_fl = [e["r"] for e in enemies if abs(e["r"].centery - t["r"].centery) < 120]
                if same_fl:
                    trg = min(same_fl, key=lambda r: abs(r.centerx - t["r"].centerx))
                    dx = 1 if trg.centerx > t["r"].centerx else -1
                    bullets.append({"r": pygame.Rect(t["r"].centerx, t["r"].centery - 6, 14, 5), "vx": 20 * dx, "vy": 0, "d": 15})
                    t["cd"] = 35
        for b in bullets[:]:
            b["r"].x += b["vx"]; b["r"].y += b["vy"]
            if b["r"].right < 0 or b["r"].left > W: bullets.remove(b)
        for e in enemies[:]:
            er = e["r"]
            if e["atk_cd"] > 0: e["atk_cd"] -= 1
            e_on_2nd = er.bottom <= f2_r.bottom + 10
            p_on_2nd = player.bottom <= f2_r.bottom + 10
            chase_p = False
            if e_on_2nd:
                if p_on_2nd and on_g: tx = player.centerx; chase_p = True
                else: tx = bomb_r.centerx
            else:
                if not p_on_2nd and on_g: tx = player.centerx; chase_p = True
                elif gen_hp > 0: tx = gen_r.centerx
                else: tx = player.centerx; chase_p = True
            if e["g"] and e_on_2nd and random.random() < 0.018:
                e["vy"] = -20; e["g"] = False
            blk = False
            for bar in bars[:]:
                if er.colliderect(bar["r"]):
                    blk = True
                    if e["atk_cd"] == 0:
                        bar["hp"] -= 25; e["atk_cd"] = 51
                        if bar["hp"] <= 0: bars.remove(bar)
                    break
            for t in turrets[:]:
                if er.colliderect(t["r"]):
                    blk = True
                    if e["atk_cd"] == 0:
                        t["hp"] -= 25; e["atk_cd"] = 51
                        if t["hp"] <= 0: turrets.remove(t)
                    break
            if chase_p and abs(player.centerx - er.centerx) < p_sz * 0.85:
                blk = True
            if not blk: er.x += e["s"] * (1 if tx > er.centerx else -1)
            eb = er.bottom; et = er.top; e["vy"] += 1.1; er.y += e["vy"]; e["g"] = False
            if e["vy"] < 0 and et >= f2_r.bottom - 12 and er.colliderect(f2_r):
                er.top = f2_r.bottom; e["vy"] = 0
            for plat in (f1_r, f2_r):
                if e["vy"] >= 0 and eb <= plat.top + 14 and er.colliderect(plat):
                    er.bottom = plat.top; e["vy"] = 0; e["g"] = True
            for b in bullets[:]:
                if er.colliderect(b["r"]): e["hp"] -= b["d"]; bullets.remove(b); break
            if e["hp"] <= 0:
                enemies.remove(e); coins += 10; kills += 1
                if vamp_l > 0: hp = min(100, hp + vamp_l * 4)
                continue
            if e["atk_cd"] == 0:
                if e_on_2nd == p_on_2nd and er.colliderect(player.inflate(16, 0)):
                    hp -= 15; e["atk_cd"] = 51
                elif e_on_2nd and er.colliderect(bomb_r):
                    bomb_hp -= 12; e["atk_cd"] = 51
                elif not e_on_2nd and gen_hp > 0 and er.colliderect(gen_r):
                    gen_hp = max(0, gen_hp - 15); e["atk_cd"] = 51
        if hp <= 0 or bomb_hp <= 0: state = "OVER"

    pwr = gen_hp > 0
    screen.fill((28, 30, 38) if pwr else (14, 15, 20))
    pygame.draw.rect(screen, (42, 44, 52) if pwr else (22, 23, 28), (40, 30, W - 80, f1_y - 30))
    pygame.draw.line(screen, (55, 60, 70), (40, int(H * 0.28)), (W - lift_w - 25, int(H * 0.28)), 4)
    for i, wx in enumerate(range(120, W - 220, 260)):
        for j, wy in enumerate((int(H * 0.14), int(H * 0.52))):
            pygame.draw.rect(screen, (18, 22, 32) if pwr else (10, 12, 18), (wx, wy, 110, 90))
            if (i + j) % 2 == 0:
                pygame.draw.line(screen, (70, 80, 95), (wx + 15, wy + 12), (wx + 48, wy + 45), 2)
                pygame.draw.line(screen, (70, 80, 95), (wx + 48, wy + 45), (wx + 35, wy + 78), 2)
                pygame.draw.line(screen, (70, 80, 95), (wx + 48, wy + 45), (wx + 85, wy + 60), 2)

    for bx, by_c, bw, bh in ((90, f1_y - 42, 46, 42), (140, f1_y - 34, 38, 34), (112, f1_y - 74, 34, 32), (W - lift_w - 130, f2_y - 36, 40, 36)):
        pygame.draw.rect(screen, (95, 70, 45) if pwr else (55, 40, 28), (bx, by_c, bw, bh))
        pygame.draw.rect(screen, (65, 48, 30), (bx, by_c, bw, bh), 2)
        pygame.draw.line(screen, (65, 48, 30), (bx, by_c), (bx + bw, by_c + bh), 2)

    pygame.draw.rect(screen, (20, 20, 25), (lift_x - 5, 30, lift_w + 10, f1_y - 30))
    pygame.draw.rect(screen, (180, 150, 50), lift_r)
    pygame.draw.rect(screen, (75, 80, 85), f1_r); pygame.draw.rect(screen, (85, 90, 95), f2_r)
    for t in turrets:
        pygame.draw.rect(screen, (110, 120, 130), t["r"], border_radius=5)
        pygame.draw.rect(screen, (30, 30, 35), (t["r"].x - 6, t["r"].y + 6, 42, 8))
        pygame.draw.rect(screen, (60, 220, 90), (t["r"].x, t["r"].y - 8, int(30 * max(0, t["hp"]) / 100), 5))

    pygame.draw.rect(screen, (55, 65, 75) if pwr else (35, 35, 40), gen_r, border_radius=6)
    pygame.draw.rect(screen, (40, 200, 255) if pwr else (90, 30, 30), gen_r.inflate(-24, -24), border_radius=4)
    pygame.draw.rect(screen, (60, 220, 90), (gen_r.x - 5, gen_r.y - 14, int(80 * max(0, gen_hp) / 250), 7))
    g_lbl = f_sm.render("ГЕНЕРАТОР" if pwr else "СЛОМАН", True, (100, 220, 255) if pwr else (255, 80, 80))
    screen.blit(g_lbl, (gen_r.centerx - g_lbl.get_width() // 2, gen_r.top - 36))

    pygame.draw.rect(screen, (30, 35, 45), tab_r, border_radius=6)
    pygame.draw.rect(screen, (0, 210, 255) if pwr else (45, 50, 55), tab_r.inflate(-8, -14))
    if pwr:
        pygame.draw.line(screen, (255, 255, 255), (tab_r.x + 8, tab_r.y + 14), (tab_r.right - 8, tab_r.y + 14), 2)
        pygame.draw.line(screen, (100, 255, 160), (tab_r.x + 8, tab_r.y + 22), (tab_r.right - 12, tab_r.y + 22), 2)
    t_lbl = f_sm.render("БАФФЫ" if pwr else "OFFLINE", True, (0, 220, 255) if pwr else (130, 130, 130))
    screen.blit(t_lbl, (tab_r.centerx - t_lbl.get_width() // 2, tab_r.top - 24))

    pygame.draw.rect(screen, (50, 55, 60), bomb_r, border_radius=6)
    pygame.draw.circle(screen, (255, 50, 50) if (pygame.time.get_ticks() // 300) % 2 == 0 else (150, 30, 30), bomb_r.center, 10)
    pygame.draw.rect(screen, (60, 220, 90), (bomb_r.x - 15, bomb_r.y - 16, int(80 * max(0, bomb_hp) / 200), 8))
    s_lbl = f_sm.render("soldier", True, (140, 210, 255))
    screen.blit(s_lbl, (player.centerx - s_lbl.get_width() // 2, player.top - 28))
    for bar in bars: pygame.draw.rect(screen, (150, 100, 50), bar["r"])
    pygame.draw.rect(screen, (70, 150, 255), player)
    gun = pygame.Rect(player.right - 4 if right else player.left - 26, player.centery - 6, 30, 10)
    pygame.draw.rect(screen, (20, 20, 25), gun)
    if muz_t > 0:
        mx, my, ds = (gun.right if right else gun.left), gun.centery, (1 if right else -1)
        pygame.draw.polygon(screen, (255, 160, 0), [(mx, my), (mx + 26 * ds, my - 11), (mx + 38 * ds, my), (mx + 26 * ds, my + 11)])
    if mel_t > 0:
        ds = 1 if right else -1
        sx = player.right + 15 if right else player.left - 15
        pygame.draw.arc(screen, (255, 255, 255), (sx - 35, player.top - 10, 70, player.height + 20), -1.2 if right else 1.9, 1.2 if right else 4.3, 6)
    for b in bullets: pygame.draw.rect(screen, (255, 230, 60), b["r"])
    for e in enemies:
         er = e["r"]
         pygame.draw.rect(screen, (220, 60, 60), er)
         pygame.draw.rect(screen, (60, 220, 90), (er.x, er.y - 10, int(er.width * max(0, e["hp"]) / e["max_hp"]), 6))
         f_lbl = f_sm.render("furry", True, (255, 160, 160))
         screen.blit(f_lbl, (er.centerx - f_lbl.get_width() // 2, er.y - 36))
    if timer <= 0:
        pygame.draw.ellipse(screen, (60, 110, 70), (heli_x, int(H * 0.16), 170, 65))
        pygame.draw.rect(screen, (50, 95, 60), (heli_x - 80, int(H * 0.16) + 22, 90, 16))
        rw = 180 if (rotor // 2) % 2 == 0 else 40
        pygame.draw.line(screen, (220, 220, 220), (heli_x + 85 - rw, int(H * 0.16) - 10), (heli_x + 85 + rw, int(H * 0.16) - 10), 5)

    pygame.draw.rect(screen, (160, 40, 40), (20, 18, 200, 22))
    pygame.draw.rect(screen, (60, 220, 90), (20, 18, int(200 * max(0, hp) / 100), 22))
    screen.blit(f_sm.render(f"HP: {int(hp)}", True, (255, 255, 255)), (25, 20))
    rep_col = (100, 230, 130) if (pwr and any(t["hp"] < 100 for t in turrets)) else (90, 95, 105)
    pygame.draw.rect(screen, rep_col, b_rep, border_radius=12)
    rt = f_sm.render("РЕМОНТ (20)" if pwr else "НЕТ ЭНЕРГИИ", True, (20, 20, 20))
    screen.blit(rt, (b_rep.centerx - rt.get_width() // 2, b_rep.centery - rt.get_height() // 2))

    cw_d = weapons[w_idx]
    screen.blit(f_sm.render("ПЕРЕЗАРЯДКА..." if rel_t > 0 else f"{cw_d['n']}: {ammo}/{cw_d['m'] + ammo_l * 6}", True, (255, 230, 120)), (20, 48))
    sl = timer // 60
    screen.blit(f_md.render(f"БОМБА: {sl // 60:02d}:{sl % 60:02d}", True, (255, 90, 90)), (W // 2 - 90, 18))
    screen.blit(f_sm.render(f"Монеты: {coins} | Убито: {kills}", True, (255, 215, 0)), (W - 360, 20))

    act_c = (100, 180, 255) if (pwr or nlift) else (90, 95, 105)
    mel_c = (255, 140, 50) if mel_cd == 0 else (120, 90, 60)
    for r, col, txt in ((b_l, (210,210,210), "<"), (b_r, (210,210,210), ">"), (b_act, act_c, act_lbl),
                        (b_rel, (180,140,255), "R"), (b_f, (255,85,85), "FIRE"), (b_j, (255,190,60), "UP"), (b_mel, mel_c, "УДАР")):
        pygame.draw.rect(screen, col, r, border_radius=16)
        ts = f_sm.render(txt, True, (20, 20, 20))
        screen.blit(ts, (r.centerx - ts.get_width() // 2, r.centery - ts.get_height() // 2))

    if state in ("SHOP", "BUFF"):
        pygame.draw.rect(screen, (35, 38, 48), m_r, border_radius=20)
        pygame.draw.rect(screen, (220, 60, 60), cl_b, border_radius=12)
        screen.blit(f_md.render("X", True, (255, 255, 255)), (cl_b.centerx - 12, cl_b.centery - 15))
        opts = ["Аптечка +40HP (30)", "Баррикада (40)", f"Оружие ({100 if w_idx==0 else 200})" if w_idx < 2 else "Макс. оружие", "Турель 1 ур. (80)"] if state == "SHOP" else [
               f"Скорость {spd_l}/4 (50)", f"Вампиризм {vamp_l}/4 (70)", f"Патроны {ammo_l}/4 (60)", f"Урон {dmg_l}/4 (80)"]
        for br, ot in zip((o1, o2, o3, o4), opts):
            pygame.draw.rect(screen, (60, 65, 80), br, border_radius=12)
            screen.blit(f_sm.render(ot, True, (255, 255, 255)), (br.x + 20, br.centery - 12))
    elif state in ("OVER", "WIN"):
        screen.blit(f_md.render("ПОБЕДА! ВЕРТОЛЕТ ПРИЛЕТЕЛ!" if state == "WIN" else "ПОРАЖЕНИЕ! НАЖМИ ДЛЯ РЕСТАРТА", True, (80, 255, 120) if state == "WIN" else (255, 80, 80)), (W // 2 - 220, H // 2))

    pygame.display.flip()
    clock.tick(60)
pygame.quit()
