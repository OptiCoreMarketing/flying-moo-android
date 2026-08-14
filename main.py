"""
Flying Moo - Android-version bygget med Kivy.
Tap på skærmen for at hoppe, ligesom mellemrum i desktop-versionen.
"""

import json
import os
import random

from kivy.app import App
from kivy.clock import Clock
from kivy.core.image import Image as CoreImage
from kivy.core.window import Window
from kivy.graphics import (
    Color, Rectangle, Ellipse, Line, PushMatrix, PopMatrix,
    Translate, Scale as GraphicsScale, RoundedRectangle
)
from kivy.uix.widget import Widget
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label

# --- Virtuel spil-opløsning (samme koordinatsystem som i desktop-versionen) ---
SPIL_BREDDE = 800
SPIL_HØJDE = 600

# --- Farver (0-1 float, Kivy-stil, ikke 0-255 som pygame) ---
def farve(r, g, b, a=1):
    return (r / 255, g / 255, b / 255, a)

HVID = farve(255, 255, 255)
SORT = farve(0, 0, 0)
RØD = farve(255, 0, 0)
GRØN = farve(0, 200, 0)
BLÅ = farve(0, 0, 255)
GUL = farve(255, 200, 0)
FLY_LYSERØD = farve(255, 133, 173)
FLY_MØRK_LYSERØD = farve(225, 85, 135)
FLY_VINGE = farve(255, 105, 150)
FLY_VINDUE = farve(210, 235, 255)

# --- Spilkonstanter ---
TYNGDEKRAFT = 900.0     # pixels/sek^2 (skaleret op ift. desktop, da vi nu bruger sekunder ikke frames)
HOP_STYRKE = -420.0     # pixels/sek
HINDER_FART = 220.0     # pixels/sek
HINDER_AFSTAND = 300
HINDER_ÅBNING = 220     # lidt større end desktop-versionen, da touch er mindre præcist end tastatur
HINDER_BREDDE = 70


def scoreboard_sti():
    """Finder det rigtige sted at gemme scoreboardet på - virker både på Android og desktop."""
    app = App.get_running_app()
    if app is not None:
        return os.path.join(app.user_data_dir, "scoreboard.json")
    return "scoreboard.json"


def hent_scoreboard():
    sti = scoreboard_sti()
    if not os.path.exists(sti):
        return []
    try:
        with open(sti, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []


def gem_score(nyt_score):
    import datetime
    scores = hent_scoreboard()
    scores.append({
        "score": nyt_score,
        "dato": datetime.datetime.now().strftime("%d-%m-%Y %H:%M"),
    })
    scores.sort(key=lambda p: p["score"], reverse=True)
    scores = scores[:10]
    try:
        with open(scoreboard_sti(), "w", encoding="utf-8") as f:
            json.dump(scores, f, ensure_ascii=False, indent=2)
    except OSError:
        pass
    return scores


class Hinder:
    def __init__(self, x):
        self.x = x
        self.bredde = HINDER_BREDDE
        self.passeret = False
        self.top_højde = random.randint(50, SPIL_HØJDE - HINDER_ÅBNING - 50)
        self.bund_y = self.top_højde + HINDER_ÅBNING

    def opdater(self, dt):
        self.x -= HINDER_FART * dt

    def er_uden_for_skærm(self):
        return self.x + self.bredde < 0

    def kolliderer_med(self, rect):
        rx, ry, rw, rh = rect
        # Topstykke: fra y=0 til top_højde
        if rx < self.x + self.bredde and rx + rw > self.x and ry < self.top_højde:
            return True
        # Bundstykke: fra bund_y til SPIL_HØJDE
        if rx < self.x + self.bredde and rx + rw > self.x and ry + rh > self.bund_y:
            return True
        return False


class PowerUp:
    def __init__(self):
        self.respawn()
        self.radius = 14

    def respawn(self):
        self.x = random.randint(400, SPIL_BREDDE - 50)
        self.y = random.randint(50, SPIL_HØJDE - 50)

    def opdater(self, dt):
        self.x -= HINDER_FART * dt

    def get_rect(self):
        return (self.x - self.radius, self.y - self.radius, self.radius * 2, self.radius * 2)


class Flodhest:
    def __init__(self, moo_texture):
        self.x = 120
        self.y = SPIL_HØJDE // 2
        self.hastighed_y = 0.0
        self.liv = 3
        self.moo_texture = moo_texture
        self.bredde = 96
        self.højde = 64

    def hop(self):
        self.hastighed_y = HOP_STYRKE

    def opdater(self, dt):
        self.hastighed_y += TYNGDEKRAFT * dt
        self.y += self.hastighed_y * dt

        if self.y - self.højde // 2 < 0:
            self.y = self.højde // 2
            self.hastighed_y = 0
        if self.y + self.højde // 2 > SPIL_HØJDE:
            self.y = SPIL_HØJDE - self.højde // 2
            self.liv = 0

    def get_rect(self):
        indskrump_x = 22
        indskrump_y = 12
        return (
            self.x - self.bredde // 2 + indskrump_x,
            self.y - self.højde // 2 + indskrump_y,
            self.bredde - indskrump_x * 2,
            self.højde - indskrump_y * 2,
        )


class SpilOverflade(Widget):
    """Selve spillets tegne- og logik-overflade. Koordinatsystem: (0,0) er øverst til
    venstre, y vokser NEDAD - ligesom i pygame-versionen - via en flip-transformation."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.moo_texture = CoreImage("moo_sprite.png").texture
        self.ny_spil()
        self._skala = 1.0
        self._offset_x = 0.0
        self._offset_y = 0.0

        Clock.schedule_interval(self.opdater, 1 / 60)
        self.bind(size=self._opdater_transform, pos=self._opdater_transform)
        self._opdater_transform()

        Window.bind(on_key_down=self._on_key_down)

    def ny_spil(self):
        self.flodhest = Flodhest(self.moo_texture)
        self.hindre = [Hinder(SPIL_BREDDE + i * HINDER_AFSTAND) for i in range(3)]
        self.power_up = PowerUp()
        self.score = 0
        self.spillet_er_slut = False
        self.score_er_gemt = False
        self.gemte_scores = []

    def _opdater_transform(self, *args):
        bredde = self.width if self.width > 0 else SPIL_BREDDE
        højde = self.height if self.height > 0 else SPIL_HØJDE
        skala = min(bredde / SPIL_BREDDE, højde / SPIL_HØJDE)
        offset_x = self.x + (bredde - SPIL_BREDDE * skala) / 2
        offset_y = self.y + (højde - SPIL_HØJDE * skala) / 2
        self._skala = skala
        self._offset_x = offset_x
        self._offset_y = offset_y

    def _til_skærm(self, spil_x, spil_y):
        """Konverterer spil-koordinater (0,0 øverst til venstre, y ned) til rigtige skærm-koordinater."""
        sx = self._offset_x + spil_x * self._skala
        sy = self._offset_y + (SPIL_HØJDE - spil_y) * self._skala
        return sx, sy

    def _skaler(self, værdi):
        return værdi * self._skala

    def _on_key_down(self, window, key, *args):
        if key == 32:  # mellemrum (til test på computer)
            self._hop_eller_genstart()

    def on_touch_down(self, touch):
        self._hop_eller_genstart()
        return True

    def _hop_eller_genstart(self):
        if self.spillet_er_slut:
            self.ny_spil()
        else:
            self.flodhest.hop()

    def opdater(self, dt):
        if not self.spillet_er_slut:
            self.flodhest.opdater(dt)

            for hinder in self.hindre:
                hinder.opdater(dt)
            if self.hindre[0].er_uden_for_skærm():
                self.hindre.pop(0)
                ny_x = self.hindre[-1].x + HINDER_AFSTAND
                self.hindre.append(Hinder(ny_x))

            flodhest_rect = self.flodhest.get_rect()
            for hinder in self.hindre:
                if hinder.kolliderer_med(flodhest_rect):
                    self.flodhest.liv -= 1
                    if self.flodhest.liv <= 0:
                        self.spillet_er_slut = True
                if not hinder.passeret and hinder.x + hinder.bredde < self.flodhest.x:
                    hinder.passeret = True
                    self.score += 1

            if self.flodhest.liv <= 0:
                self.spillet_er_slut = True

            self.power_up.opdater(dt)
            if self.power_up.x < -50:
                self.power_up.respawn()
                self.power_up.x = SPIL_BREDDE + 50
            px, py, pw, ph = self.power_up.get_rect()
            fx, fy, fw, fh = flodhest_rect
            if fx < px + pw and fx + fw > px and fy < py + ph and fy + fh > py:
                self.score += 10
                self.power_up.respawn()
                self.power_up.x = SPIL_BREDDE + 50

            if self.spillet_er_slut and not self.score_er_gemt:
                self.gemte_scores = gem_score(self.score)
                self.score_er_gemt = True

        self._tegn()

    def _tegn(self):
        self.canvas.clear()

        def rekt_generel(spil_x, spil_y_top, bredde_v, højde_v):
            sx, sy = self._til_skærm(spil_x, spil_y_top + højde_v)
            return (sx, sy), (self._skaler(bredde_v), self._skaler(højde_v))

        with self.canvas:
            # Baggrund
            Color(*HVID)
            pos, size = rekt_generel(0, 0, SPIL_BREDDE, SPIL_HØJDE)
            Rectangle(pos=pos, size=size)

            # Rør/forhindringer
            for hinder in self.hindre:
                Color(*GRØN)
                pos, size = rekt_generel(hinder.x, 0, hinder.bredde, hinder.top_højde)
                Rectangle(pos=pos, size=size)
                pos, size = rekt_generel(hinder.x, hinder.bund_y, hinder.bredde, SPIL_HØJDE - hinder.bund_y)
                Rectangle(pos=pos, size=size)

            # Power-up
            Color(*BLÅ)
            r = self.power_up.radius
            pos, size = rekt_generel(self.power_up.x - r, self.power_up.y - r, r * 2, r * 2)
            Ellipse(pos=pos, size=size)

            # Fly + Moo
            self._tegn_flodhest()

        self._tegn_tekst_overlay()

    def _tegn_flodhest(self):
        f = self.flodhest
        bw, bh = f.bredde, f.højde
        cx, cy = f.x, f.y

        def rekt(spil_x, spil_y, bredde_v, højde_v):
            sx, sy = self._til_skærm(spil_x, spil_y + højde_v)
            return (sx, sy), (self._skaler(bredde_v), self._skaler(højde_v))

        # Skrog
        Color(*FLY_LYSERØD)
        pos, size = rekt(cx - bw / 2 + 10, cy - 5, bw - 20, bh / 2 + 15)
        RoundedRectangle(pos=pos, size=size, radius=[self._skaler(18)])

        # Vinger
        Color(*FLY_VINGE)
        pos, size = rekt(cx - bw / 2 - 15, cy + bh / 2 - 20, bw + 30, 12)
        Rectangle(pos=pos, size=size)

        # Halefinne
        Color(*FLY_MØRK_LYSERØD)
        p1 = self._til_skærm(cx - bw / 2 + 5, cy + 5)
        p2 = self._til_skærm(cx - bw / 2 + 5, cy - 20)
        p3 = self._til_skærm(cx - bw / 2 - 10, cy - 5)
        Line(points=[p1[0], p1[1], p2[0], p2[1], p3[0], p3[1]], width=1, close=True)

        # Næse/propel
        Color(*FLY_VINDUE)
        næse_x, næse_y = cx + bw / 2 - 8, cy + 8
        pos, size = rekt(næse_x - 10, næse_y - 10, 20, 20)
        Ellipse(pos=pos, size=size)
        Color(*SORT)
        a1 = self._til_skærm(næse_x, næse_y - 13)
        a2 = self._til_skærm(næse_x, næse_y + 13)
        Line(points=[a1[0], a1[1], a2[0], a2[1]], width=1.5)
        b1 = self._til_skærm(næse_x - 13, næse_y)
        b2 = self._til_skærm(næse_x + 13, næse_y)
        Line(points=[b1[0], b1[1], b2[0], b2[1]], width=1.5)

        # Moo selv (billedet)
        Color(1, 1, 1, 1)
        pos, size = rekt(cx - bw / 2 + 8, cy - bh / 2, bw - 20, bh - 10)
        Rectangle(texture=self.moo_texture, pos=pos, size=size)

    def _tegn_tekst_overlay(self):
        # Fjerner gamle labels og tegner nye (simpel løsning, fint til denne mængde tekst)
        if not hasattr(self, "_labels"):
            self._labels = []
        for lbl in self._labels:
            self.remove_widget(lbl)
        self._labels = []

        def tilføj_label(tekst, x, y, størrelse=24, farvekode=(0, 0, 0, 1)):
            lbl = Label(
                text=tekst, font_size=størrelse, color=farvekode,
                pos=(self._offset_x + x * self._skala - 150, self.height - (self._offset_y_top(y))),
                size_hint=(None, None), size=(300, 40), halign="center"
            )
            self.add_widget(lbl)
            self._labels.append(lbl)

        # Da label-positionering med transform er lidt bøvlet, bruger vi skærm-koordinater direkte
        skala = self._skala
        ox, oy = self._offset_x, self._offset_y

        def skærm_pos(spil_x, spil_y):
            return (ox + spil_x * skala, oy + (SPIL_HØJDE - spil_y) * skala)

        def label(tekst, spil_x, spil_y, størrelse=22, farvekode=(0, 0, 0, 1), centreret=False):
            sx, sy = skærm_pos(spil_x, spil_y)
            bredde = 400 if centreret else 300
            lbl = Label(
                text=tekst, font_size=størrelse, color=farvekode, bold=True,
                pos=(sx - bredde / 2 if centreret else sx, sy - 20),
                size_hint=(None, None), size=(bredde, 40),
                halign="center", valign="middle"
            )
            lbl.text_size = lbl.size
            self.add_widget(lbl)
            self._labels.append(lbl)

        label(f"Score: {self.score}", 10, 40)
        label(f"Liv: {self.flodhest.liv}", 10, 80)

        if self.spillet_er_slut:
            label("Game Over!", SPIL_BREDDE / 2, 120, størrelse=40, farvekode=(1, 0, 0, 1), centreret=True)
            label("Tryk på skærmen for at spille igen", SPIL_BREDDE / 2, 170, størrelse=20, centreret=True)
            label("Top scores:", SPIL_BREDDE / 2, 220, størrelse=22, centreret=True)
            for i, post in enumerate(self.gemte_scores[:5]):
                label(f"{i + 1}. {post['score']} point ({post['dato']})", SPIL_BREDDE / 2, 250 + i * 30,
                      størrelse=18, centreret=True)


class FlyingMooApp(App):
    def build(self):
        Window.clearcolor = (1, 1, 1, 1)
        layout = FloatLayout()
        spil = SpilOverflade()
        layout.add_widget(spil)
        return layout


if __name__ == "__main__":
    FlyingMooApp().run()
