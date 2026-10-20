import math
import random
import sys
import os
import traceback
import pygame

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(BASE_DIR)

try:
    from src.levels import NIVEIS, obter_configuracao_nivel, DURACAO_MUSICA_SEGUNDOS
except (ModuleNotFoundError, ImportError):
    from levels import NIVEIS, obter_configuracao_nivel, DURACAO_MUSICA_SEGUNDOS

SCREEN_WIDTH = 960
SCREEN_HEIGHT = 720
FPS = 60

TILE_SIZE = 50
NUM_ROWS = 10
FLOOR_Y = 600
CEILING_Y = FLOOR_Y - (NUM_ROWS * TILE_SIZE)

TARGET_X = 240.0
SLIME_START_X = -80.0

# PALETA TEMA CAVERNA BIOLUMINESCENTE
COLOR_BG_CAVERNA = (14, 12, 22)
COLOR_BG_CHICLETE = (28, 10, 22)
COLOR_BG_NEVE = (10, 18, 30)

COLOR_FLOOR = (28, 22, 40)
COLOR_SLIME_GOSMA = (120, 220, 90)     # Tom de verde fiel ao "Green Slime"
COLOR_SLIME_CHICLETE = (255, 120, 180)
COLOR_SLIME_NEVE = (130, 210, 255)

# ESTALAGMITES E RIACHO DE GOSMA
COLOR_SPIKE = (170, 55, 75)
COLOR_BLOCK = (48, 52, 72)
COLOR_LAVA = (0, 210, 180)  # Riacho Bioluminescente (Ciano)
COLOR_PAD = (255, 230, 0)
COLOR_RING = (255, 200, 0)
COLOR_COIN = (255, 215, 0)

def log_debug(msg: str):
    print(f"[SLIME_DIAGNOSTIC] {msg}")

class SoundManager:
    def __init__(self):
        self.sounds_enabled = True
        try:
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
            log_debug("Mixer de Áudio inicializado com sucesso.")
        except Exception as e:
            log_debug(f"AVISO: Falha ao inicializar áudio: {e}")
            self.sounds_enabled = False

        self.sfx_jump = self._gerar_som_sintetico(frequencia=520, duracao_ms=60)
        self.sfx_coin = self._gerar_som_sintetico(frequencia=980, duracao_ms=100)
        self.sfx_death = self._gerar_som_sintetico(frequencia=130, duracao_ms=180)
        self.sfx_pad = self._gerar_som_sintetico(frequencia=750, duracao_ms=120)

        caminho_abs = os.path.join(BASE_DIR, "assets", "sounds", "fase1.mp3")
        caminho_rel = "assets/sounds/fase1.mp3"
        self.musica_fase1 = caminho_abs if os.path.exists(caminho_abs) else caminho_rel

        if self.sounds_enabled and os.path.exists(self.musica_fase1):
            try:
                pygame.mixer.music.load(self.musica_fase1)
                pygame.mixer.music.set_volume(0.5)
            except Exception: pass

    def _gerar_som_sintetico(self, frequencia: int, duracao_ms: int):
        if not self.sounds_enabled: return None
        try:
            import numpy as np
            sample_rate = 44100
            n_samples = int(sample_rate * (duracao_ms / 1000.0))
            t = np.linspace(0, duracao_ms / 1000.0, n_samples, False)
            waveform = np.sin(2 * np.pi * frequencia * t) * 0.2
            sound_array = np.int16(waveform * 32767)
            sound_array = np.column_stack((sound_array, sound_array))
            return pygame.sndarray.make_sound(sound_array)
        except Exception: return None

    def iniciar_musica(self):
        if self.sounds_enabled:
            try: pygame.mixer.music.play(-1)
            except Exception: pass

    def parar_musica(self):
        if self.sounds_enabled:
            try: pygame.mixer.music.stop()
            except Exception: pass

    def reiniciar_musica(self):
        if self.sounds_enabled:
            try:
                pygame.mixer.music.rewind()
                pygame.mixer.music.play(-1)
            except Exception: pass

    def tocar(self, som):
        if self.sounds_enabled and som is not None:
            try: som.play()
            except Exception: pass

class Particle:
    def __init__(self, x: float, y: float, color: tuple, vel_x: float = None, vel_y: float = None, gravity: float = 0.0, size: int = None):
        self.x = float(x)
        self.y = float(y)
        self.color = color
        self.radius = float(size if size is not None else random.randint(4, 7))
        self.vel_x = vel_x if vel_x is not None else random.uniform(-2.0, -0.5)
        self.vel_y = vel_y if vel_y is not None else random.uniform(-1.5, 1.5)
        self.gravity = gravity

    def update(self):
        self.vel_y += self.gravity
        self.x += self.vel_x
        self.y += self.vel_y
        self.radius = max(0.0, self.radius - 0.12)

    def draw(self, surface: pygame.Surface):
        if self.radius > 0:
            pygame.draw.circle(surface, self.color, (int(self.x), int(self.y)), int(self.radius))

class Slime(pygame.sprite.Sprite):
    def __init__(self, x: float, y: float):
        super().__init__()
        self.base_size = 40
        self.x = float(x)
        self.y = float(y)
        self.vel_y = 0.0
        self.jump_buffer = 0
        self.imunidade_portal = 0
        self.modo = "GOSMA"
        self.color = COLOR_SLIME_GOSMA

        self.gravity = 1.15
        self.jump_strength = -16.5

        self.is_grounded = False
        self.current_width = float(self.base_size)
        self.current_height = float(self.base_size)
        self.update_rect()

    def update_rect(self):
        w = max(4, int(round(self.current_width)))
        h = max(4, int(round(self.current_height)))
        self.rect = pygame.Rect(
            int(round(self.x - w / 2.0)),
            int(round(self.y)) - h,
            w,
            h,
        )

    def get_hitbox(self) -> pygame.Rect:
        return pygame.Rect(
            int(self.x - 13),
            int(self.y - 38),
            26,
            38
        )

    def mudar_modo(self, novo_modo: str):
        log_debug(f"🔄 MUDANÇA DE MODO: {self.modo} -> {novo_modo}")
        self.modo = novo_modo
        self.imunidade_portal = 15
        if novo_modo == "GOSMA":
            self.color = COLOR_SLIME_GOSMA
            self.gravity = 1.15
            self.jump_strength = -16.5
        elif novo_modo == "CHICLETE":
            self.color = COLOR_SLIME_CHICLETE
            self.gravity = 0.0
            self.jump_strength = 0.0
            self.vel_y = -1.8
        elif novo_modo == "NEVE":
            self.color = COLOR_SLIME_NEVE
            self.gravity = -1.15
            self.jump_strength = 16.5

    def solicitar_pulo(self):
        self.jump_buffer = 8

    def tentar_pular(self, sound_mgr: SoundManager = None, trigger_flash_func=None):
        if self.jump_buffer > 0:
            poulou = False
            if self.modo in ("GOSMA", "NEVE") and self.is_grounded:
                self.vel_y = self.jump_strength
                self.is_grounded = False
                self.jump_buffer = 0
                self.current_width, self.current_height = 28.0, 50.0
                poulou = True

            if poulou:
                if trigger_flash_func is not None:
                    trigger_flash_func(0.08)  # Brilho super suave exclusivo do pulo
                if sound_mgr is not None:
                    sound_mgr.tocar(sound_mgr.sfx_jump)

    def update(self, floor_y: int, ceiling_y: int, particles: list, space_held: bool = False, sound_mgr: SoundManager = None, trigger_flash_func=None):
        if self.jump_buffer > 0: self.jump_buffer -= 1
        if self.imunidade_portal > 0: self.imunidade_portal -= 1

        if self.modo == "CHICLETE":
            if space_held:
                self.vel_y = max(-3.2, self.vel_y - 0.25)
            else:
                self.vel_y = min(3.2, self.vel_y + 0.22)

            self.vel_y *= 0.94
            self.y += self.vel_y

            if random.random() < 0.3:
                particles.append(Particle(self.x - 10, self.y - 20, self.color, vel_x=-3.0, vel_y=random.uniform(-0.5, 0.5), size=4))

        else:
            if space_held: self.jump_buffer = 6
            self.tentar_pular(sound_mgr, trigger_flash_func)

            if not self.is_grounded:
                self.vel_y += self.gravity
                self.y += self.vel_y

            if self.gravity > 0 and not self.is_grounded:
                if self.y >= floor_y:
                    self.y = float(floor_y)
                    self.vel_y = 0.0
                    self.is_grounded = True
                    self.current_width, self.current_height = 50.0, 28.0
                    for _ in range(5): particles.append(Particle(self.x, floor_y - 4, self.color))
                    self.tentar_pular(sound_mgr, trigger_flash_func)

            elif self.gravity < 0 and not self.is_grounded:
                if self.y <= ceiling_y:
                    self.y = float(ceiling_y)
                    self.vel_y = 0.0
                    self.is_grounded = True
                    self.current_width, self.current_height = 50.0, 28.0
                    for _ in range(5): particles.append(Particle(self.x, ceiling_y + 4, self.color))
                    self.tentar_pular(sound_mgr, trigger_flash_func)

            if self.is_grounded and random.random() < 0.3:
                py_pos = self.y if self.gravity > 0 else self.y - 38
                particles.append(Particle(self.x - 12, py_pos, (140, 140, 160), vel_x=-2.5, vel_y=random.uniform(-0.8, 0.2), size=3))

        self.current_width += (self.base_size - self.current_width) * 0.2
        self.current_height += (self.base_size - self.current_height) * 0.2
        self.update_rect()

    def draw(self, surface: pygame.Surface, scale: float = 1.0, angle: float = 0.0):
        try:
            w = max(6, int(round(self.rect.width * scale)))
            h = max(6, int(round(self.rect.height * scale)))

            slime_surf = pygame.Surface((w, h), pygame.SRCALPHA)

            # CORPO PIXEL ART DO GREEN SLIME (DOME/CÚPULA)
            dark_outline = (30, 80, 20)
            highlight_color = (200, 255, 170)

            # Desenha a silhueta da cúpula com borda escura
            rect_body = pygame.Rect(0, 0, w, h)
            pygame.draw.ellipse(slime_surf, dark_outline, rect_body)
            pygame.draw.ellipse(slime_surf, self.color, (2, 2, w - 4, h - 4))
            
            # Brilho no topo do slime (Estilo a imagem 'Green Slime')
            pygame.draw.ellipse(slime_surf, highlight_color, (w // 4, 3, w // 2, h // 3))

            # ROSTO PIXEL ART FIEL À SUA GIF (Olhos estilo Tracinhos + Boca 'w')
            eye_w = max(2, int(2 * scale))
            eye_h = max(4, int(6 * scale))
            eye_y = (h // 2) - int(2 * scale)

            # Olho Esquerdo e Direito (Linhas verticais escuras)
            pygame.draw.rect(slime_surf, (20, 30, 20), (w // 2 - int(8 * scale), eye_y, eye_w, eye_h))
            pygame.draw.rect(slime_surf, (20, 30, 20), (w // 2 + int(6 * scale), eye_y, eye_w, eye_h))

            # Boquinha em estilo 'w' (Pixel Art)
            mouth_y = eye_y + eye_h + int(1 * scale)
            mw = int(2 * scale)
            pygame.draw.rect(slime_surf, (20, 30, 20), (w // 2 - int(6 * scale), mouth_y, mw, mw))
            pygame.draw.rect(slime_surf, (20, 30, 20), (w // 2 - int(3 * scale), mouth_y + mw, mw, mw))
            pygame.draw.rect(slime_surf, (20, 30, 20), (w // 2, mouth_y, mw, mw))
            pygame.draw.rect(slime_surf, (20, 30, 20), (w // 2 + int(3 * scale), mouth_y + mw, mw, mw))
            pygame.draw.rect(slime_surf, (20, 30, 20), (w // 2 + int(5 * scale), mouth_y, mw, mw))

            if angle != 0:
                slime_surf = pygame.transform.rotate(slime_surf, angle)

            dest_rect = slime_surf.get_rect(center=self.rect.center)
            surface.blit(slime_surf, dest_rect)
        except Exception: pass

def main():
    log_debug("=== INICIANDO SLIME DASH - PIXEL ART GREEN SLIME APLICADO ===")
    pygame.init()
    sound_mgr = SoundManager()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Slime Dash")
    clock = pygame.time.Clock()

    font = pygame.font.SysFont("Consolas", 15, bold=True)
    attempt_font = pygame.font.SysFont("Consolas", 58, bold=True)
    title_font = pygame.font.SysFont("Consolas", 42, bold=True)
    debug_font = pygame.font.SysFont("Consolas", 15, bold=True)

    scroll_speed = 6.0
    distancia_total_musica = scroll_speed * FPS * DURACAO_MUSICA_SEGUNDOS

    id_nivel_atual = 1
    config_nivel = obter_configuracao_nivel(id_nivel_atual)
    fase_matriz = config_nivel["fase"]
    bpm_atual = config_nivel["bpm"]
    mapa_objetos = []
    fim_fase_x_relativo = distancia_total_musica
    distancia_percorrida = 0.0
    tentativas = 1
    moedas_coletadas = 0
    moedas_pegas_ids = set()
    vitoria = False

    modo_imunidade_admin = False
    checkpoint_manual_admin = None

    animando_vitoria = False
    timer_anim_vitoria = 0

    bg_flash_alpha = 0.0
    current_bg_color = list(COLOR_BG_CAVERNA)

    def trigger_flash(intensity: float = 0.08):
        nonlocal bg_flash_alpha
        bg_flash_alpha = max(bg_flash_alpha, intensity)

    def gerar_explosao_slime(x, y, color):
        for _ in range(35):
            vx = random.uniform(-6.0, 6.0)
            vy = random.uniform(-10.0, -2.0)
            particles.append(Particle(x, y, color, vel_x=vx, vel_y=vy, gravity=0.45, size=random.randint(5, 10)))

    estado_jogo = "MENU"
    timer_intro_wait = 0
    frames_por_batida = int((60 * FPS) / bpm_atual)

    slime = Slime(x=SLIME_START_X, y=FLOOR_Y)
    particles = []

    show_debug = True
    causa_morte = ""
    morto_parado = False

    def pre_carregar_mapa():
        nonlocal fim_fase_x_relativo, mapa_objetos
        mapa_objetos.clear()
        fim_fase_x_relativo = distancia_total_musica

        for row_idx in range(len(fase_matriz)):
            line = fase_matriz[row_idx]
            y_pos = FLOOR_Y - ((row_idx + 1) * TILE_SIZE)
            for col_idx, char in enumerate(line):
                rel_x = col_idx * TILE_SIZE
                if char == "E":
                    fim_fase_x_relativo = rel_x
                elif char in ("^", "v", "1", "h", "~", "*", "@", "O", "C", "N", "G"):
                    mapa_objetos.append((rel_x, y_pos, char, col_idx))

    pre_carregar_mapa()

    def iniciar_fase():
        nonlocal estado_jogo, timer_intro_wait, distancia_percorrida, causa_morte, morto_parado
        nonlocal animando_vitoria, timer_anim_vitoria, vitoria, current_bg_color
        estado_jogo = "INTRO_WAIT"
        timer_intro_wait = 0
        distancia_percorrida = 0.0
        causa_morte = ""
        morto_parado = False
        animando_vitoria = False
        timer_anim_vitoria = 0
        vitoria = False
        current_bg_color = list(COLOR_BG_CAVERNA)
        slime.mudar_modo("GOSMA")
        slime.x = SLIME_START_X
        slime.y = FLOOR_Y
        slime.vel_y = 0
        slime.jump_buffer = 0
        slime.update_rect()
        sound_mgr.iniciar_musica()

    def reset_game(motivo="", dados_extras=""):
        nonlocal tentativas, vitoria, causa_morte, morto_parado, animando_vitoria
        if modo_imunidade_admin:
            return

        causa_morte = motivo
        morto_parado = True
        tentativas += 1
        vitoria = False
        animando_vitoria = False

        gerar_explosao_slime(slime.x, slime.y - 20, slime.color)

        log_debug(f"💀 MORTE CONFIRMADA: {motivo}")
        sound_mgr.tocar(sound_mgr.sfx_death)
        sound_mgr.parar_musica()

    def concluir_reset():
        nonlocal estado_jogo, distancia_percorrida, morto_parado, vitoria, animando_vitoria
        morto_parado = False
        animando_vitoria = False
        vitoria = False
        sound_mgr.reiniciar_musica()

        if checkpoint_manual_admin is not None:
            distancia_percorrida = checkpoint_manual_admin["distancia"]
            slime.mudar_modo(checkpoint_manual_admin["modo"])
            slime.x = TARGET_X
            slime.y = checkpoint_manual_admin["y"]
            slime.vel_y = 0.0
            slime.jump_buffer = 0
            slime.update_rect()
            estado_jogo = "JOGANDO"
        else:
            iniciar_fase()

    frames_contador = 0
    beat_pulse = 0.0
    running = True

    try:
        while running:
            dt_fps = clock.get_fps()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_g:
                        show_debug = not show_debug

                    elif event.key == pygame.K_i:
                        modo_imunidade_admin = not modo_imunidade_admin
                        if morto_parado:
                            morto_parado = False
                            estado_jogo = "JOGANDO"
                            sound_mgr.reiniciar_musica()

                    elif event.key == pygame.K_c:
                        checkpoint_manual_admin = {
                            "distancia": distancia_percorrida,
                            "y": slime.y,
                            "modo": slime.modo
                        }

                    elif event.key == pygame.K_v:
                        if checkpoint_manual_admin is not None:
                            distancia_percorrida = checkpoint_manual_admin["distancia"]
                            slime.mudar_modo(checkpoint_manual_admin["modo"])
                            slime.y = checkpoint_manual_admin["y"]
                            slime.vel_y = 0.0
                            morto_parado = False
                            estado_jogo = "JOGANDO"

                    elif event.key == pygame.K_LEFT:
                        distancia_percorrida = max(0.0, distancia_percorrida - 250.0)
                        if morto_parado:
                            morto_parado = False
                            estado_jogo = "JOGANDO"
                            sound_mgr.reiniciar_musica()

                    elif event.key == pygame.K_RIGHT:
                        distancia_percorrida = min(distancia_total_musica, distancia_percorrida + 250.0)
                        if morto_parado:
                            morto_parado = False
                            estado_jogo = "JOGANDO"
                            sound_mgr.reiniciar_musica()

                    if morto_parado:
                        if event.key == pygame.K_SPACE:
                            concluir_reset()
                    else:
                        if event.key in (pygame.K_ESCAPE, pygame.K_p):
                            if estado_jogo in ("JOGANDO", "INTRO_WAIT", "INTRO_RUN"):
                                estado_jogo = "PAUSADO"
                                sound_mgr.parar_musica()
                            elif estado_jogo == "PAUSADO":
                                estado_jogo = "JOGANDO"
                                sound_mgr.reiniciar_musica()

                        elif event.key == pygame.K_r:
                            if estado_jogo != "MENU":
                                reset_game("RECOMEÇO VOLUNTÁRIO")

                        elif event.key == pygame.K_m:
                            estado_jogo = "MENU"
                            sound_mgr.parar_musica()

                        elif event.key == pygame.K_SPACE:
                            if estado_jogo == "MENU":
                                iniciar_fase()
                            elif estado_jogo == "PAUSADO":
                                estado_jogo = "JOGANDO"
                                sound_mgr.reiniciar_musica()
                            elif vitoria:
                                iniciar_fase()
                            elif estado_jogo == "JOGANDO" and slime.modo != "CHICLETE" and not animando_vitoria:
                                slime.solicitar_pulo()

            keys = pygame.key.get_pressed()
            space_held = keys[pygame.K_SPACE] if (estado_jogo == "JOGANDO" and not morto_parado and not animando_vitoria) else False

            frames_contador += 1
            if frames_contador % frames_por_batida == 0:
                beat_pulse = 1.0
            else:
                beat_pulse = max(0.0, beat_pulse - 0.1)

            bg_flash_alpha = max(0.0, bg_flash_alpha - 0.015)

            target_bg = COLOR_BG_CAVERNA
            if slime.modo == "CHICLETE": target_bg = COLOR_BG_CHICLETE
            elif slime.modo == "NEVE": target_bg = COLOR_BG_NEVE

            for i in range(3):
                current_bg_color[i] += (target_bg[i] - current_bg_color[i]) * 0.05

            attempt_text_x = float(SCREEN_WIDTH // 2)

            if not morto_parado:
                if estado_jogo == "INTRO_WAIT":
                    distancia_percorrida = 0.0
                    slime.x = SLIME_START_X
                    slime.jump_buffer = 0
                    slime.update_rect()
                    attempt_text_x = float(SCREEN_WIDTH // 2)
                    timer_intro_wait += 1
                    if timer_intro_wait >= 30: estado_jogo = "INTRO_RUN"

                elif estado_jogo == "INTRO_RUN":
                    distancia_percorrida = 0.0
                    slime.x += 4.5
                    slime.y = FLOOR_Y
                    slime.is_grounded = True
                    slime.jump_buffer = 0
                    slime.update_rect()
                    attempt_text_x = float(SCREEN_WIDTH // 2)
                    if slime.x >= TARGET_X:
                        slime.x = TARGET_X
                        slime.jump_buffer = 0
                        slime.update_rect()
                        estado_jogo = "JOGANDO"

                elif estado_jogo == "JOGANDO" and not vitoria:
                    if not animando_vitoria:
                        slime_prev_y = slime.y
                        distancia_percorrida += scroll_speed
                        slime.update(FLOOR_Y, CEILING_Y, particles, space_held, sound_mgr, trigger_flash)
                        attempt_text_x = (SCREEN_WIDTH // 2) - distancia_percorrida

                        if slime.modo == "CHICLETE" and slime.imunidade_portal == 0 and not modo_imunidade_admin:
                            if slime.y <= CEILING_Y + 15: reset_game("Chiclete bateu no TETO!")
                            elif slime.y >= FLOOR_Y - 5: reset_game("Chiclete bateu no CHÃO!")

                    else:
                        timer_anim_vitoria += 1
                        fim_x_tela = fim_fase_x_relativo + TARGET_X - distancia_percorrida
                        vortex_center_y = FLOOR_Y - 100

                        slime.x += (fim_x_tela - slime.x) * 0.15
                        slime.y += (vortex_center_y - slime.y) * 0.15
                        slime.update_rect()

                        for _ in range(2):
                            ang = random.uniform(0, math.pi * 2)
                            rad = random.uniform(20, 60)
                            px = fim_x_tela + math.cos(ang) * rad
                            py = vortex_center_y + math.sin(ang) * rad
                            vx = (fim_x_tela - px) * 0.1
                            vy = (vortex_center_y - py) * 0.1
                            particles.append(Particle(px, py, (180, 50, 255), vel_x=vx, vel_y=vy))

                        if timer_anim_vitoria >= 60:
                            animando_vitoria = False
                            vitoria = True

            for p in particles[:]:
                p.update()
                if p.radius <= 0: particles.remove(p)

            espinhos_chao_rects, espinhos_teto_rects, lavas_rects = [], [], []
            blocos_rects, trampolins_rects, orbes_rects = [], [], []
            portais, moedas = [], []

            fim_fase_x = fim_fase_x_relativo + TARGET_X - distancia_percorrida

            for rel_x, y_pos, char, col_idx in mapa_objetos:
                obj_x = rel_x + TARGET_X - distancia_percorrida
                if -100 < obj_x < SCREEN_WIDTH + 100:
                    if char == "^": espinhos_chao_rects.append((pygame.Rect(obj_x + 14, y_pos + 18, TILE_SIZE - 28, TILE_SIZE - 18), col_idx))
                    elif char == "v": espinhos_teto_rects.append((pygame.Rect(obj_x + 14, y_pos, TILE_SIZE - 28, TILE_SIZE - 18), col_idx))
                    elif char == "1": blocos_rects.append((pygame.Rect(obj_x, y_pos, TILE_SIZE, TILE_SIZE), col_idx, y_pos))
                    elif char == "h": blocos_rects.append((pygame.Rect(obj_x, y_pos + TILE_SIZE // 2, TILE_SIZE, TILE_SIZE // 2), col_idx, y_pos))
                    elif char == "~": lavas_rects.append((pygame.Rect(obj_x, y_pos + TILE_SIZE - 14, TILE_SIZE, 14), col_idx))
                    elif char == "*": trampolins_rects.append(pygame.Rect(obj_x + 6, y_pos + TILE_SIZE - 12, TILE_SIZE - 12, 12))
                    elif char == "@": orbes_rects.append(pygame.Rect(obj_x + 8, y_pos + 8, TILE_SIZE - 16, TILE_SIZE - 16))
                    elif char in ("C", "N", "G"): portais.append((pygame.Rect(obj_x + 8, y_pos, TILE_SIZE - 16, TILE_SIZE), char))
                    elif char == "O" and col_idx not in moedas_pegas_ids: moedas.append((pygame.Rect(obj_x + 12, y_pos + 12, 36, 36), col_idx))

            slime_hb = slime.get_hitbox()

            if estado_jogo == "JOGANDO" and not vitoria and not morto_parado and not animando_vitoria:
                for portal_rect, tipo in portais:
                    if slime_hb.colliderect(portal_rect):
                        if tipo == "C" and slime.modo != "CHICLETE": slime.mudar_modo("CHICLETE")
                        elif tipo == "N" and slime.modo != "NEVE": slime.mudar_modo("NEVE")
                        elif tipo == "G" and slime.modo != "GOSMA": slime.mudar_modo("GOSMA")

                for pad in trampolins_rects:
                    if slime_hb.colliderect(pad):
                        slime.vel_y = -22.5
                        slime.is_grounded = False
                        sound_mgr.tocar(sound_mgr.sfx_pad)

                for orb in orbes_rects:
                    if slime_hb.colliderect(orb) and space_held and slime.jump_buffer > 0:
                        slime.vel_y = -18.5
                        slime.jump_buffer = 0
                        sound_mgr.tocar(sound_mgr.sfx_jump)

                for coin_rect, coin_id in moedas:
                    if slime_hb.colliderect(coin_rect):
                        moedas_pegas_ids.add(coin_id)
                        moedas_coletadas += 1
                        sound_mgr.tocar(sound_mgr.sfx_coin)

                if not modo_imunidade_admin:
                    for spike, c_idx in espinhos_chao_rects:
                        if slime_hb.colliderect(spike): reset_game(f"Espinho do Chão (Coluna {c_idx})")

                    for spike_top, c_idx in espinhos_teto_rects:
                        if slime_hb.colliderect(spike_top): reset_game(f"Espinho do Teto (Coluna {c_idx})")

                    for lva, c_idx in lavas_rects:
                        if slime_hb.colliderect(lva): reset_game(f"Riacho Bioluminescente (Coluna {c_idx})")

                em_cima_de_bloco = False

                for block, c_idx, orig_y in blocos_rects:
                    if slime_hb.colliderect(block):
                        if slime.modo == "CHICLETE":
                            if slime.imunidade_portal == 0 and not modo_imunidade_admin:
                                reset_game(f"Colisão de Voo com Bloco (Coluna {c_idx})")
                                break
                        else:
                            pes_acima_do_topo = (slime.y <= block.top + 12) or (slime_prev_y <= block.top + 12)

                            if slime.gravity > 0:
                                if pes_acima_do_topo and slime.vel_y >= 0:
                                    slime.y = float(block.top)
                                    slime.vel_y = 0.0
                                    slime.is_grounded = True
                                    em_cima_de_bloco = True
                                    slime.update_rect()
                                    slime.tentar_pular(sound_mgr, trigger_flash)

                                elif pes_acima_do_topo and slime.vel_y < 0:
                                    em_cima_de_bloco = True

                                elif slime.vel_y < 0 and (slime_prev_y - 38) >= block.bottom - 12:
                                    if not modo_imunidade_admin:
                                        reset_game(f"Colisão de Cabeça com Bloco (Coluna {c_idx})")
                                        break

                                else:
                                    if not modo_imunidade_admin:
                                        reset_game(f"Colisão Frontal com Bloco (Coluna {c_idx})")
                                        break

                            elif slime.gravity < 0:
                                pes_no_fundo = (slime.y - 38 >= block.bottom - 12) or (slime_prev_y - 38 >= block.bottom - 12)
                                if pes_no_fundo and slime.vel_y <= 0:
                                    slime.y = float(block.bottom + 38)
                                    slime.vel_y = 0.0
                                    slime.is_grounded = True
                                    em_cima_de_bloco = True
                                    slime.update_rect()
                                    slime.tentar_pular(sound_mgr, trigger_flash)
                                elif pes_no_fundo and slime.vel_y > 0:
                                    em_cima_de_bloco = True
                                else:
                                    if not modo_imunidade_admin:
                                        reset_game(f"Colisão Frontal com Bloco (Coluna {c_idx})")
                                        break

                if not em_cima_de_bloco and slime.y < FLOOR_Y:
                    if slime.modo != "CHICLETE": slime.is_grounded = False

                if slime.x >= fim_fase_x:
                    animando_vitoria = True
                    timer_anim_vitoria = 0

            # --- RENDERIZAÇÃO ---
            final_bg = (int(current_bg_color[0]), int(current_bg_color[1]), int(current_bg_color[2]))
            screen.fill(final_bg)

            if bg_flash_alpha > 0:
                flash_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
                flash_surf.fill((255, 255, 255, int(bg_flash_alpha * 255)))
                screen.blit(flash_surf, (0, 0))

            pygame.draw.rect(screen, COLOR_FLOOR, (0, FLOOR_Y, SCREEN_WIDTH, SCREEN_HEIGHT - FLOOR_Y))
            pygame.draw.rect(screen, COLOR_FLOOR, (0, 0, SCREEN_WIDTH, CEILING_Y))

            line_bright = int(100 + beat_pulse * 40)
            pygame.draw.line(screen, (0, line_bright, int(line_bright * 0.8)), (0, FLOOR_Y), (SCREEN_WIDTH, FLOOR_Y), 3)

            for spike, _ in espinhos_chao_rects: pygame.draw.polygon(screen, COLOR_SPIKE, [(spike.x - 4, spike.bottom), (spike.centerx, spike.top), (spike.right + 4, spike.bottom)])
            for spike_top, _ in espinhos_teto_rects: pygame.draw.polygon(screen, COLOR_SPIKE, [(spike_top.x - 4, spike_top.top), (spike_top.centerx, spike_top.bottom), (spike_top.right + 4, spike_top.top)])
            for lva, _ in lavas_rects: pygame.draw.rect(screen, COLOR_LAVA, lva)
            for block, _, _ in blocos_rects:
                pygame.draw.rect(screen, COLOR_BLOCK, block)
                pygame.draw.rect(screen, (80, 90, 120), block, 2)
            for pad in trampolins_rects: pygame.draw.rect(screen, COLOR_PAD, pad, border_radius=3)
            for orb in orbes_rects:
                pygame.draw.circle(screen, COLOR_RING, orb.center, 14, 3)
                pygame.draw.circle(screen, (255, 255, 255), orb.center, 6)
            for portal_rect, tipo in portais:
                p_color = COLOR_SLIME_CHICLETE if tipo == "C" else (COLOR_SLIME_NEVE if tipo == "N" else COLOR_SLIME_GOSMA)
                pygame.draw.rect(screen, p_color, portal_rect, 4)
            for coin_rect, _ in moedas:
                pygame.draw.circle(screen, COLOR_COIN, coin_rect.center, 14)
                pygame.draw.circle(screen, (255, 255, 200), coin_rect.center, 6)

            fim_x_tela = fim_fase_x_relativo + TARGET_X - distancia_percorrida
            if -100 < fim_x_tela < SCREEN_WIDTH + 100:
                center_vortex = (int(fim_x_tela), FLOOR_Y - 100)
                pygame.draw.circle(screen, (180, 50, 255), center_vortex, 45, 4)
                pygame.draw.circle(screen, (50, 240, 255), center_vortex, 30, 3)
                pygame.draw.circle(screen, (10, 5, 20), center_vortex, 20)

            for p in particles: p.draw(screen)

            if estado_jogo in ("INTRO_RUN", "JOGANDO", "PAUSADO") and not morto_parado:
                if animando_vitoria:
                    s_factor = max(0.05, 1.0 - (timer_anim_vitoria / 60.0))
                    rot_angle = timer_anim_vitoria * 18.0
                    slime.draw(screen, scale=s_factor, angle=rot_angle)
                else:
                    slime.draw(screen)

            if show_debug and estado_jogo != "MENU":
                pygame.draw.rect(screen, (0, 255, 0), slime_hb, 2)
                for spike, _ in espinhos_chao_rects: pygame.draw.rect(screen, (255, 0, 0), spike, 1)
                for block, _, _ in blocos_rects: pygame.draw.rect(screen, (0, 150, 255), block, 1)

                info_text = f"FPS: {dt_fps:.1f} | X: {slime.x:.1f} Y: {slime.y:.1f} | Modo: {slime.modo} | Imunidade [I]: {'ON' if modo_imunidade_admin else 'OFF'}"
                lbl_info = debug_font.render(info_text, True, (255, 255, 0) if modo_imunidade_admin else (255, 255, 255))
                pygame.draw.rect(screen, (0, 0, 0), (10, SCREEN_HEIGHT - 30, lbl_info.get_width() + 10, 22))
                screen.blit(lbl_info, (15, SCREEN_HEIGHT - 28))

            if estado_jogo in ("INTRO_WAIT", "INTRO_RUN", "JOGANDO", "PAUSADO") and attempt_text_x > -300:
                txt_attempt = attempt_font.render(f"TENTATIVA {tentativas}", True, (255, 255, 255))
                screen.blit(txt_attempt, (int(attempt_text_x - txt_attempt.get_width() // 2), 260))

            if estado_jogo != "MENU" and not morto_parado:
                porcentagem = min(100, int((distancia_percorrida / distancia_total_musica) * 100))
                if vitoria: porcentagem = 100
                bar_width = 320
                bar_height = 14
                bar_x = (SCREEN_WIDTH - bar_width) // 2
                bar_y = 18

                pygame.draw.rect(screen, (50, 40, 70), (bar_x, bar_y, bar_width, bar_height), border_radius=6)
                pygame.draw.rect(screen, config_nivel["cor_tema"], (bar_x, bar_y, int(bar_width * (porcentagem / 100)), bar_height), border_radius=6)
                txt_pct = font.render(f"{porcentagem}%", True, (255, 255, 255))
                screen.blit(txt_pct, (bar_x + bar_width + 12, bar_y - 2))
                txt_nome = font.render(config_nivel["nome"], True, config_nivel["cor_tema"])
                txt_tentativas = font.render(f"Tentativa: {tentativas}", True, (255, 255, 255))
                txt_moedas = font.render(f"Moedas: {moedas_coletadas}/3", True, COLOR_COIN)
                screen.blit(txt_nome, (18, 18))
                screen.blit(txt_tentativas, (18, 38))
                screen.blit(txt_moedas, (18, 58))

            if morto_parado:
                banner_x = (SCREEN_WIDTH - 840) // 2
                banner_y = 10
                banner_w = 840
                banner_h = 105

                pygame.draw.rect(screen, (180, 25, 25), (banner_x, banner_y, banner_w, banner_h), border_radius=8)
                pygame.draw.rect(screen, (255, 255, 255), (banner_x, banner_y, banner_w, banner_h), 2, border_radius=8)

                txt_m1 = debug_font.render("--- PAINEL DE MORTE E TESTES ADMIN ---", True, (255, 255, 255))
                txt_m2 = debug_font.render(f"MORTE: {causa_morte}", True, (255, 255, 0))
                txt_m3 = font.render("[ESPAÇO] Reiniciar do Início (0%)  |  [I] Ativar Imunidade e Continuar", True, (230, 230, 230))
                txt_m4 = font.render("[← / →] Mover Posição no Mapa  |  [C] Salvar Ponto  |  [V] Ir ao Ponto Manual", True, (200, 240, 255))

                screen.blit(txt_m1, (SCREEN_WIDTH // 2 - txt_m1.get_width() // 2, banner_y + 8))
                screen.blit(txt_m2, (SCREEN_WIDTH // 2 - txt_m2.get_width() // 2, banner_y + 30))
                screen.blit(txt_m3, (SCREEN_WIDTH // 2 - txt_m3.get_width() // 2, banner_y + 54))
                screen.blit(txt_m4, (SCREEN_WIDTH // 2 - txt_m4.get_width() // 2, banner_y + 76))

            if estado_jogo == "MENU":
                overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
                overlay.fill((10, 8, 20, 230))
                screen.blit(overlay, (0, 0))
                t1 = title_font.render("SLIME DASH", True, (50, 240, 100))
                t2 = font.render("Pressione ESPAÇO para Iniciar", True, (255, 255, 255))
                t3 = font.render("Controles Admin: [I] Imunidade | [C] Salvar Ponto | [V] Ir ao Ponto | [← / →] Mover", True, (255, 255, 0))
                screen.blit(t1, (SCREEN_WIDTH // 2 - t1.get_width() // 2, 220))
                screen.blit(t2, (SCREEN_WIDTH // 2 - t2.get_width() // 2, 310))
                screen.blit(t3, (SCREEN_WIDTH // 2 - t3.get_width() // 2, 380))

            elif estado_jogo == "PAUSADO":
                overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
                overlay.fill((0, 0, 0, 180))
                screen.blit(overlay, (0, 0))
                p1 = title_font.render("JOGO PAUSADO", True, (255, 215, 0))
                p2 = font.render("[ESPAÇO / P] Continuar  |  [R] Reiniciar  |  [M] Menu", True, (255, 255, 255))
                p3 = font.render("Use [← / →] para ir para qualquer porcentagem da fase", True, (50, 240, 100))
                screen.blit(p1, (SCREEN_WIDTH // 2 - p1.get_width() // 2, 260))
                screen.blit(p2, (SCREEN_WIDTH // 2 - p2.get_width() // 2, 330))
                screen.blit(p3, (SCREEN_WIDTH // 2 - p3.get_width() // 2, 380))

            if vitoria:
                s = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
                s.fill((0, 0, 0, 180))
                screen.blit(s, (0, 0))
                txt_vic = title_font.render("LEVEL COMPLETE!", True, (50, 240, 100))
                txt_sub = font.render(f"Moedas: {moedas_coletadas}/3  |  Pressione ESPAÇO para Recomeçar", True, (255, 255, 255))
                screen.blit(txt_vic, (SCREEN_WIDTH // 2 - txt_vic.get_width() // 2, 280))
                screen.blit(txt_sub, (SCREEN_WIDTH // 2 - txt_sub.get_width() // 2, 350))

            pygame.display.flip()
            clock.tick(FPS)

    except Exception as fatal_error:
        print("\n" + "="*70)
        print("🚨 ERRO DETECTADO 🚨")
        traceback.print_exc()
        print("="*70 + "\n")

    finally:
        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    main()