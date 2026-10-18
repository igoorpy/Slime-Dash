import math
import random
import sys
import os
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

COLOR_BG = (15, 12, 25)
COLOR_FLOOR = (40, 30, 60)
COLOR_SLIME_GOSMA = (50, 240, 100)
COLOR_SLIME_CHICLETE = (255, 105, 180)
COLOR_SLIME_NEVE = (135, 206, 250)
COLOR_SPIKE = (230, 50, 50)
COLOR_BLOCK = (80, 70, 110)
COLOR_LAVA = (255, 80, 0)
COLOR_PAD = (255, 230, 0)
COLOR_RING = (255, 200, 0)
COLOR_COIN = (255, 215, 0)
COLOR_CHECKPOINT = (50, 255, 150)
COLOR_EYES = (255, 255, 255)
COLOR_PUPIL = (10, 10, 20)

class SoundManager:
    def __init__(self):
        self.sounds_enabled = True
        try:
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
        except Exception:
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
    def __init__(self, x: float, y: float, color: tuple):
        self.x = x
        self.y = y
        self.color = color
        self.radius = random.randint(4, 7)
        self.vel_x = random.uniform(-2, -0.5)
        self.vel_y = random.uniform(-1.5, 1.5)

    def update(self):
        self.x += self.vel_x
        self.y += self.vel_y
        self.radius = max(0, self.radius - 0.15)

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
        self.modo = "GOSMA"
        self.color = COLOR_SLIME_GOSMA

        self.gravity = 1.15
        self.jump_strength = -16.5

        self.is_grounded = False
        self.current_width = float(self.base_size)
        self.current_height = float(self.base_size)
        self.update_rect()

    def update_rect(self):
        self.rect = pygame.Rect(
            int(self.x - self.current_width / 2.0),
            int(self.y - self.current_height),
            int(self.current_width),
            int(self.current_height),
        )

    def get_hitbox(self) -> pygame.Rect:
        return pygame.Rect(
            int(self.x - 13),
            int(self.y - 38),
            26,
            36
        )

    def mudar_modo(self, novo_modo: str):
        self.modo = novo_modo
        if novo_modo == "GOSMA":
            self.color = COLOR_SLIME_GOSMA
            self.gravity = 1.15
            self.jump_strength = -16.5
        elif novo_modo == "CHICLETE":
            self.color = COLOR_SLIME_CHICLETE
            self.gravity = 0.45
            self.jump_strength = -9.0
        elif novo_modo == "NEVE":
            self.color = COLOR_SLIME_NEVE
            self.gravity = -1.15
            self.jump_strength = 16.5

    def solicitar_pulo(self):
        self.jump_buffer = 8

    def tentar_pular(self, sound_mgr: SoundManager = None):
        if self.jump_buffer > 0:
            poulou = False
            if self.modo == "GOSMA" and self.is_grounded:
                self.vel_y = self.jump_strength
                self.is_grounded = False
                self.jump_buffer = 0
                self.current_width, self.current_height = 26.0, 54.0
                poulou = True
            elif self.modo == "CHICLETE":
                self.vel_y = self.jump_strength
                self.jump_buffer = 0
                self.current_width, self.current_height = 32.0, 48.0
                poulou = True
            elif self.modo == "NEVE" and self.is_grounded:
                self.vel_y = self.jump_strength
                self.is_grounded = False
                self.jump_buffer = 0
                self.current_width, self.current_height = 26.0, 54.0
                poulou = True

            if poulou and sound_mgr is not None:
                sound_mgr.tocar(sound_mgr.sfx_jump)

    def update(self, floor_y: int, ceiling_y: int, particles: list, space_held: bool = False, sound_mgr: SoundManager = None):
        if self.jump_buffer > 0: self.jump_buffer -= 1
        if space_held: self.jump_buffer = 6

        self.tentar_pular(sound_mgr)

        if not self.is_grounded or self.modo == "CHICLETE":
            self.vel_y += self.gravity
            self.y += self.vel_y

        if self.gravity > 0 and not self.is_grounded:
            if self.y >= floor_y:
                self.y = float(floor_y)
                self.vel_y = 0.0
                self.is_grounded = True
                self.current_width, self.current_height = 54.0, 26.0
                for _ in range(5): particles.append(Particle(self.x, floor_y - 4, self.color))
                self.tentar_pular(sound_mgr)

        elif self.gravity < 0 and not self.is_grounded:
            if self.y <= ceiling_y:
                self.y = float(ceiling_y)
                self.vel_y = 0.0
                self.is_grounded = True
                self.current_width, self.current_height = 54.0, 26.0
                for _ in range(5): particles.append(Particle(self.x, ceiling_y + 4, self.color))
                self.tentar_pular(sound_mgr)

        self.current_width += (self.base_size - self.current_width) * 0.2
        self.current_height += (self.base_size - self.current_height) * 0.2
        self.update_rect()

    def draw(self, surface: pygame.Surface):
        pygame.draw.ellipse(surface, self.color, self.rect)
        eye_y = self.rect.centery - (3 if self.gravity > 0 else -3)
        pygame.draw.circle(surface, COLOR_EYES, (self.rect.centerx - 4, eye_y), 4)
        pygame.draw.circle(surface, COLOR_EYES, (self.rect.centerx + 4, eye_y), 4)
        pygame.draw.circle(surface, COLOR_PUPIL, (self.rect.centerx - 4, eye_y), 2)
        pygame.draw.circle(surface, COLOR_PUPIL, (self.rect.centerx + 4, eye_y), 2)

def main():
    pygame.init()
    sound_mgr = SoundManager()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Slime Dash - Tolerância de Pulo Aplicada")
    clock = pygame.time.Clock()

    font = pygame.font.SysFont("Consolas", 15, bold=True)
    attempt_font = pygame.font.SysFont("Consolas", 58, bold=True)
    title_font = pygame.font.SysFont("Consolas", 42, bold=True)
    debug_font = pygame.font.SysFont("Consolas", 18, bold=True)

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
    estado_jogo = "MENU"
    timer_intro_wait = 0
    checkpoint = None
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

        for row_idx, line in enumerate(fase_matriz):
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
        estado_jogo = "INTRO_WAIT"
        timer_intro_wait = 0
        distancia_percorrida = 0.0
        causa_morte = ""
        morto_parado = False
        slime.mudar_modo("GOSMA")
        slime.x = SLIME_START_X
        slime.y = FLOOR_Y
        slime.vel_y = 0
        slime.jump_buffer = 0
        slime.update_rect()
        sound_mgr.iniciar_musica()

    def carregar_nivel(id_nivel: int):
        nonlocal config_nivel, fase_matriz, bpm_atual, moedas_coletadas, moedas_pegas_ids
        nonlocal vitoria, checkpoint, frames_por_batida, id_nivel_atual
        id_nivel_atual = id_nivel
        config_nivel = obter_configuracao_nivel(id_nivel)
        fase_matriz = config_nivel["fase"]
        bpm_atual = config_nivel["bpm"]
        frames_por_batida = int((60 * FPS) / bpm_atual)
        pre_carregar_mapa()
        moedas_coletadas = 0
        moedas_pegas_ids.clear()
        checkpoint = None
        vitoria = False
        iniciar_fase()

    def reset_game(motivo="", dados_extras=""):
        nonlocal tentativas, vitoria, causa_morte, morto_parado
        causa_morte = motivo
        morto_parado = True
        tentativas += 1
        vitoria = False
        sound_mgr.tocar(sound_mgr.sfx_death)
        sound_mgr.parar_musica()

        print("\n" + "="*60)
        print(f"[DEBUG_LOG] Tentativa {tentativas - 1} FALHOU!")
        print(f"  Motivo: {motivo}")
        print(f"  Slime -> X: {slime.x:.1f} | Y: {slime.y:.1f} | Vel_Y: {slime.vel_y:.2f} | Modo: {slime.modo} | Grounded: {slime.is_grounded}")
        print(f"  Distancia Percorrida: {distancia_percorrida:.1f}px")
        if dados_extras:
            print(f"  Detalhes do Objeto: {dados_extras}")
        print("="*60 + "\n")

    def concluir_reset():
        nonlocal estado_jogo, distancia_percorrida, checkpoint, morto_parado
        morto_parado = False
        sound_mgr.reiniciar_musica()
        if checkpoint is not None:
            distancia_percorrida = checkpoint["distancia"]
            slime.mudar_modo(checkpoint["modo"])
            slime.x = TARGET_X
            slime.y = checkpoint["y"]
            slime.vel_y = 0
            slime.jump_buffer = 0
            slime.update_rect()
            estado_jogo = "JOGANDO"
        else:
            iniciar_fase()

    frames_contador = 0
    beat_pulse = 0.0
    running = True

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_g:
                    show_debug = not show_debug

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
                            if id_nivel_atual < len(NIVEIS): carregar_nivel(id_nivel_atual + 1)
                            else: carregar_nivel(1)
                        elif estado_jogo == "JOGANDO":
                            slime.solicitar_pulo()

        keys = pygame.key.get_pressed()
        space_held = keys[pygame.K_SPACE] if (estado_jogo == "JOGANDO" and not morto_parado) else False

        frames_contador += 1
        if frames_contador % frames_por_batida == 0: beat_pulse = 1.0
        else: beat_pulse = max(0.0, beat_pulse - 0.1)

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
                distancia_percorrida += scroll_speed
                slime.update(FLOOR_Y, CEILING_Y, particles, space_held, sound_mgr)
                attempt_text_x = (SCREEN_WIDTH // 2) - distancia_percorrida

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

        if estado_jogo == "JOGANDO" and not vitoria and not morto_parado:
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
                    for _ in range(8): particles.append(Particle(pad.centerx, pad.top, COLOR_PAD))

            for orb in orbes_rects:
                if slime_hb.colliderect(orb) and space_held and slime.jump_buffer > 0:
                    slime.vel_y = -18.5
                    slime.jump_buffer = 0
                    sound_mgr.tocar(sound_mgr.sfx_jump)
                    for _ in range(10): particles.append(Particle(orb.centerx, orb.centery, COLOR_RING))

            for coin_rect, coin_id in moedas:
                if slime_hb.colliderect(coin_rect):
                    moedas_pegas_ids.add(coin_id)
                    moedas_coletadas += 1
                    sound_mgr.tocar(sound_mgr.sfx_coin)
                    for _ in range(8): particles.append(Particle(coin_rect.centerx, coin_rect.centery, COLOR_COIN))

            for spike, c_idx in espinhos_chao_rects:
                if slime_hb.colliderect(spike):
                    reset_game(f"Espinho do Chão (Coluna {c_idx})", f"Spike Rect: {spike}")

            for spike_top, c_idx in espinhos_teto_rects:
                if slime_hb.colliderect(spike_top):
                    reset_game(f"Espinho do Teto (Coluna {c_idx})", f"SpikeTop Rect: {spike_top}")

            for lva, c_idx in lavas_rects:
                if slime_hb.colliderect(lva):
                    reset_game(f"Lava (Coluna {c_idx})", f"Lava Rect: {lva}")

            em_cima_de_bloco = False
            for block, c_idx, orig_y in blocos_rects:
                if slime_hb.colliderect(block):
                    # 1. Pouso normal caindo/parado no topo
                    if slime.gravity > 0 and slime.vel_y >= 0 and (slime.y - max(0.0, slime.vel_y)) <= block.top + 14:
                        slime.y = float(block.top)
                        slime.vel_y = 0.0
                        slime.is_grounded = True
                        em_cima_de_bloco = True
                        slime.tentar_pular(sound_mgr)
                    # 2. Pouso no teto (Modo Neve)
                    elif slime.gravity < 0 and slime.vel_y <= 0 and (slime.y - min(0.0, slime.vel_y)) >= block.bottom - 14:
                        slime.y = float(block.bottom)
                        slime.vel_y = 0.0
                        slime.is_grounded = True
                        em_cima_de_bloco = True
                        slime.tentar_pular(sound_mgr)
                    else:
                        # 3. CORREÇÃO CRÍTICA: Se o Slime estiver SUBINDO (vel_y < 0) e no TOPO do bloco, É UM PULO LEGÍTIMO!
                        if slime.gravity > 0 and slime.vel_y < 0 and slime_hb.bottom <= block.top + 18:
                            continue  # Ignora colisão falsa durante a subida do pulo!
                        elif slime.gravity < 0 and slime.vel_y > 0 and slime_hb.top >= block.bottom - 18:
                            continue

                        # Se for colisão lateral de fato (parede) -> Morte
                        reset_game(f"Colisão Frontal com Bloco (Coluna {c_idx})", f"Block Rect: {block}")
                        break

            if not em_cima_de_bloco and slime.y < FLOOR_Y:
                if slime.modo != "CHICLETE": slime.is_grounded = False

            if slime.x >= fim_fase_x or distancia_percorrida >= distancia_total_musica:
                vitoria = True

        screen.fill(COLOR_BG)
        pygame.draw.rect(screen, COLOR_FLOOR, (0, FLOOR_Y, SCREEN_WIDTH, SCREEN_HEIGHT - FLOOR_Y))
        pygame.draw.rect(screen, COLOR_FLOOR, (0, 0, SCREEN_WIDTH, CEILING_Y))

        line_bright = int(120 + beat_pulse * 100)
        pygame.draw.line(screen, (0, line_bright, int(line_bright * 0.8)), (0, FLOOR_Y), (SCREEN_WIDTH, FLOOR_Y), 3)

        for spike, _ in espinhos_chao_rects: pygame.draw.polygon(screen, COLOR_SPIKE, [(spike.x - 4, spike.bottom), (spike.centerx, spike.top), (spike.right + 4, spike.bottom)])
        for spike_top, _ in espinhos_teto_rects: pygame.draw.polygon(screen, COLOR_SPIKE, [(spike_top.x - 4, spike_top.top), (spike_top.centerx, spike_top.bottom), (spike_top.right + 4, spike_top.top)])
        for lva, _ in lavas_rects: pygame.draw.rect(screen, COLOR_LAVA, lva)
        for block, _, _ in blocos_rects:
            pygame.draw.rect(screen, COLOR_BLOCK, block)
            pygame.draw.rect(screen, (150, 140, 180), block, 2)
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

        for p in particles: p.draw(screen)

        if estado_jogo in ("INTRO_RUN", "JOGANDO", "PAUSADO"): slime.draw(screen)

        if show_debug and estado_jogo != "MENU":
            pygame.draw.rect(screen, (0, 255, 0), slime_hb, 2)
            lbl_slime = debug_font.render(f"Slime (Y: {int(slime.y)})", True, (0, 255, 0))
            screen.blit(lbl_slime, (slime_hb.x - 10, slime_hb.y - 20))

            for spike, _ in espinhos_chao_rects: pygame.draw.rect(screen, (255, 0, 0), spike, 2)
            for block, _, _ in blocos_rects: pygame.draw.rect(screen, (0, 120, 255), block, 2)
            pygame.draw.line(screen, (255, 255, 0), (int(TARGET_X), 0), (int(TARGET_X), SCREEN_HEIGHT), 1)

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
            banner_x = (SCREEN_WIDTH - 720) // 2
            banner_y = 10
            banner_w = 720
            banner_h = 85

            pygame.draw.rect(screen, (180, 25, 25), (banner_x, banner_y, banner_w, banner_h), border_radius=8)
            pygame.draw.rect(screen, (255, 255, 255), (banner_x, banner_y, banner_w, banner_h), 2, border_radius=8)

            txt_m1 = debug_font.render("--- DIAGNÓSTICO DE COLISÃO ---", True, (255, 255, 255))
            txt_m2 = debug_font.render(f"MORTE: {causa_morte}", True, (255, 255, 0))
            txt_m3 = font.render("Pressione [ESPAÇO] para tentar novamente", True, (230, 230, 230))

            screen.blit(txt_m1, (SCREEN_WIDTH // 2 - txt_m1.get_width() // 2, banner_y + 10))
            screen.blit(txt_m2, (SCREEN_WIDTH // 2 - txt_m2.get_width() // 2, banner_y + 34))
            screen.blit(txt_m3, (SCREEN_WIDTH // 2 - txt_m3.get_width() // 2, banner_y + 58))

        if estado_jogo == "MENU":
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((10, 8, 20, 230))
            screen.blit(overlay, (0, 0))
            t1 = title_font.render("SLIME DASH", True, (50, 240, 100))
            t2 = font.render("Pressione ESPAÇO para Iniciar", True, (255, 255, 255))
            t3 = font.render("Controles: [ESPAÇO] Pular | [R] Reiniciar | [P / ESC] Pausar", True, (180, 180, 200))
            t4 = font.render("Aperte [G] para ativar/desativar o Modo Diagnóstico", True, (255, 255, 0))
            screen.blit(t1, (SCREEN_WIDTH // 2 - t1.get_width() // 2, 220))
            screen.blit(t2, (SCREEN_WIDTH // 2 - t2.get_width() // 2, 310))
            screen.blit(t3, (SCREEN_WIDTH // 2 - t3.get_width() // 2, 370))
            screen.blit(t4, (SCREEN_WIDTH // 2 - t4.get_width() // 2, 430))

        elif estado_jogo == "PAUSADO":
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 180))
            screen.blit(overlay, (0, 0))
            p1 = title_font.render("JOGO PAUSADO", True, (255, 215, 0))
            p2 = font.render("[ESPAÇO / P] Continuar  |  [R] Reiniciar  |  [M] Menu", True, (255, 255, 255))
            screen.blit(p1, (SCREEN_WIDTH // 2 - p1.get_width() // 2, 280))
            screen.blit(p2, (SCREEN_WIDTH // 2 - p2.get_width() // 2, 360))

        if vitoria:
            s = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            s.fill((0, 0, 0, 180))
            screen.blit(s, (0, 0))
            txt_vic = title_font.render("FASE CONCLUÍDA!", True, config_nivel["cor_tema"])
            txt_sub = font.render(f"Moedas: {moedas_coletadas}/3  |  Pressione ESPAÇO para Avançar", True, (255, 255, 255))
            screen.blit(txt_vic, (SCREEN_WIDTH // 2 - txt_vic.get_width() // 2, 280))
            screen.blit(txt_sub, (SCREEN_WIDTH // 2 - txt_sub.get_width() // 2, 350))

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()