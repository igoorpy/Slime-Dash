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

# PALETA TEMA CAVERNA
COLOR_BG_CAVERNA = (12, 10, 16)
COLOR_BG_CHICLETE = (25, 8, 18)
COLOR_BG_NEVE = (8, 15, 25)

COLOR_FLOOR = (28, 28, 32)
COLOR_MOSS = (65, 135, 55)             # Musgo/Grama verde sobre as pedras e chão
COLOR_SLIME_GOSMA = (120, 220, 90)     
COLOR_SLIME_CHICLETE = (255, 120, 180)
COLOR_SLIME_NEVE = (130, 210, 255)

# ESTALAGMITES, BLOCOS E LAVA
COLOR_SPIKE = (90, 85, 90)
COLOR_BLOCK = (40, 42, 48) 

# BORDAS DINÂMICAS DOS BLOCOS POR MODO
COLOR_BORDER_GOSMA = (85, 160, 85)     
COLOR_BORDER_CHICLETE = (255, 105, 180) 
COLOR_BORDER_NEVE = (135, 206, 250)    

COLOR_LAVA_BASE = (220, 50, 10)  
COLOR_LAVA_DETAIL = (255, 140, 0) 

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

        self.sfx_jump = self._gerar_som_sintetico(520, 60)
        self.sfx_coin = self._gerar_som_sintetico(980, 100)
        self.sfx_death = self._gerar_som_sintetico(130, 180)
        self.sfx_pad = self._gerar_som_sintetico(750, 120)

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
    def __init__(self, x: float, y: float, color: tuple, vel_x: float = None, vel_y: float = None, gravity: float = 0.0, size: int = None, lifespan: int = 255, p_type: str = "generic", target_x: float = 0.0, target_y: float = 0.0):
        self.x = float(x)
        self.y = float(y)
        self.color = color
        self.radius = float(size if size is not None else random.randint(3, 6))
        self.vel_x = vel_x if vel_x is not None else random.uniform(-2.0, 2.0)
        self.vel_y = vel_y if vel_y is not None else random.uniform(-2.0, 2.0)
        self.gravity = gravity
        self.lifespan = lifespan
        self.p_type = p_type
        self.target_x = target_x
        self.target_y = target_y

    def update(self, floor_y: int, new_particles: list):
        if self.p_type == "vortex_pull":
            # Movimento suave de sucção para o centro
            dx = self.target_x - self.x
            dy = self.target_y - self.y
            dist = math.hypot(dx, dy)
            if dist < 10:
                self.lifespan = 0 # Some ao tocar no centro
            else:
                speed = 5.0 # Velocidade da sucção
                self.x += (dx / dist) * speed
                self.y += (dy / dist) * speed
                self.lifespan -= 3
        elif self.p_type == "slime_drip":
            self.vel_y += self.gravity
            self.y += self.vel_y
            self.lifespan -= 4 # Pingo some mais rápido
        elif self.p_type == "pink_bubble":
            self.x += math.sin(self.y * 0.05) * 0.5 # Faz a bolha subir em zigue-zague suave
            self.y += self.vel_y
            self.lifespan -= 2
        else: # Partículas genéricas (poeira, lava)
            self.vel_y += self.gravity
            self.x += self.vel_x
            self.y += self.vel_y
            self.radius = max(0.0, self.radius - 0.1)
            self.lifespan -= 2

    def draw(self, surface: pygame.Surface):
        if self.radius > 0 and self.lifespan > 0:
            alpha = max(0, min(255, self.lifespan))
            if self.p_type in ("pink_bubble", "vortex_pull"):
                # Desenha como bolhas translúcidas vazadas
                p_surf = pygame.Surface((int(self.radius*2+2), int(self.radius*2+2)), pygame.SRCALPHA)
                pygame.draw.circle(p_surf, (*self.color[:3], alpha), (int(self.radius+1), int(self.radius+1)), int(self.radius), 1)
                surface.blit(p_surf, (int(self.x - self.radius), int(self.y - self.radius)))
            else:
                # Partículas sólidas normais
                p_surf = pygame.Surface((int(self.radius*2), int(self.radius*2)), pygame.SRCALPHA)
                pygame.draw.circle(p_surf, (*self.color[:3], alpha), (int(self.radius), int(self.radius)), int(self.radius))
                surface.blit(p_surf, (int(self.x - self.radius), int(self.y - self.radius)))

class Decal:
    def __init__(self, x_mundo: float, y: float, width: float, color: tuple, invertido: bool = False):
        self.x_mundo = x_mundo
        self.y = y
        self.width = width
        self.color = color
        self.invertido = invertido
        
        self.pontos = []
        num_pontos = max(3, int(width // 10))
        for i in range(num_pontos):
            offset_x = (i * 10) - (width / 2) + random.uniform(-2, 2)
            gota_h = random.randint(3, 7)
            if invertido:
                self.pontos.append((offset_x, gota_h))
            else:
                self.pontos.append((offset_x, -gota_h))

    def draw(self, surface: pygame.Surface, camera_offset_x: float):
        tela_x = self.x_mundo + camera_offset_x
        if -50 < tela_x < SCREEN_WIDTH + 50:
            for px, py in self.pontos:
                pygame.draw.circle(surface, self.color, (int(tela_x + px), int(self.y)), abs(py))

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
        self.rect = pygame.Rect(int(round(self.x - w / 2.0)), int(round(self.y)) - h, w, h)

    def get_hitbox(self) -> pygame.Rect:
        return pygame.Rect(int(self.x - 13), int(self.y - 38), 26, 38)

    def get_ground_check_hitbox(self) -> pygame.Rect:
        # Hitbox estendida em 1px para baixo para manter contato contínuo ao deslizar nos blocos
        return pygame.Rect(int(self.x - 13), int(self.y - 38), 26, 39)

    def mudar_modo(self, novo_modo: str):
        log_debug(f"🔄 MUDANÇA DE MODO: {self.modo} -> {novo_modo} | PosY: {self.y:.1f}")
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
                self.current_width, self.current_height = 20.0, 65.0
                poulou = True

            if poulou:
                log_debug(f"🦘 PULO EXECUTADO | Modo: {self.modo} | VelY: {self.vel_y:.2f} | PosY: {self.y:.1f}")
                if trigger_flash_func is not None: trigger_flash_func(0.08)
                if sound_mgr is not None: sound_mgr.tocar(sound_mgr.sfx_jump)

    def aplicar_impacto_chao(self, origem_nome="Chão/Bloco", dist_total: float = 0, decals_list: list = None):
        # SÓ APLICA O SQUASH E O RASTRO SE ESTAVA NO AR (MOMENTO EXATO DO POUSO)
        if not self.is_grounded:
            self.current_width, self.current_height = 68.0, 20.0
            log_debug(f"💥 POUSO E ESMAGAMENTO (SQUASH) em [{origem_nome}] | Slime Y: {self.y:.1f} | Dimensões: 68x20px")
            
            if decals_list is not None:
                mundo_x = self.x - (TARGET_X - dist_total)
                invertido = self.gravity < 0
                decals_list.append(Decal(mundo_x, self.y, self.current_width, self.color, invertido))

        self.is_grounded = True
        self.vel_y = 0.0

    def update(self, floor_y: int, ceiling_y: int, particles: list, space_held: bool, sound_mgr: SoundManager, trigger_flash_func, dist_total: float, decals_list: list):
        if self.jump_buffer > 0: self.jump_buffer -= 1
        if self.imunidade_portal > 0: self.imunidade_portal -= 1

        if not self.is_grounded and abs(self.vel_y) > 8.0 and self.modo != "CHICLETE":
            self.current_width += (26.0 - self.current_width) * 0.2
            self.current_height += (55.0 - self.current_height) * 0.2

        if self.modo == "CHICLETE":
            if space_held: self.vel_y = max(-3.2, self.vel_y - 0.25)
            else: self.vel_y = min(3.2, self.vel_y + 0.22)
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
                    self.aplicar_impacto_chao("Chão Principal", dist_total, decals_list)
                    for _ in range(5): particles.append(Particle(self.x, floor_y - 4, self.color))
                    self.tentar_pular(sound_mgr, trigger_flash_func)
            elif self.gravity < 0 and not self.is_grounded:
                if self.y <= ceiling_y:
                    self.y = float(ceiling_y)
                    self.aplicar_impacto_chao("Teto Principal", dist_total, decals_list)
                    for _ in range(5): particles.append(Particle(self.x, ceiling_y + 4, self.color))
                    self.tentar_pular(sound_mgr, trigger_flash_func)

            if self.is_grounded and random.random() < 0.3:
                py_pos = self.y if self.gravity > 0 else self.y - 38
                particles.append(Particle(self.x - 12, py_pos, (140, 140, 160), vel_x=-2.5, vel_y=random.uniform(-0.8, 0.2), size=3))

        # RECUPERAR A FORMA REDONDA NATURAL (40x40px)
        self.current_width += (self.base_size - self.current_width) * 0.15
        self.current_height += (self.base_size - self.current_height) * 0.15
        self.update_rect()

    def draw(self, surface: pygame.Surface, scale: float = 1.0, angle: float = 0.0):
        try:
            w = max(6, int(round(self.rect.width * scale)))
            h = max(6, int(round(self.rect.height * scale)))
            slime_surf = pygame.Surface((w, h), pygame.SRCALPHA)

            dark_outline = (30, 80, 20)
            highlight_color = (200, 255, 170)

            pygame.draw.ellipse(slime_surf, dark_outline, (0, 0, w, h))
            pygame.draw.ellipse(slime_surf, self.color, (2, 2, w - 4, h - 4))
            pygame.draw.ellipse(slime_surf, highlight_color, (w // 4, 3, w // 2, h // 3))

            eye_y = (h // 2) - int(2 * scale)
            jumping = (self.vel_y < -2.0 if self.gravity > 0 else self.vel_y > 2.0) and not self.is_grounded

            if jumping or self.modo == "CHICLETE":
                eye_r = int(4 * scale)
                pygame.draw.circle(slime_surf, (255, 255, 255), (w // 2 - int(8 * scale), eye_y + 2), eye_r)
                pygame.draw.circle(slime_surf, (255, 255, 255), (w // 2 + int(6 * scale), eye_y + 2), eye_r)
                pygame.draw.circle(slime_surf, (20, 30, 20), (w // 2 - int(8 * scale), eye_y + 2), eye_r - 1)
                pygame.draw.circle(slime_surf, (20, 30, 20), (w // 2 + int(6 * scale), eye_y + 2), eye_r - 1)
                
                mouth_rect = pygame.Rect(w // 2 - int(4 * scale), eye_y + int(4 * scale), int(8 * scale), int(6 * scale))
                pygame.draw.ellipse(slime_surf, (20, 30, 20), mouth_rect)
                pygame.draw.ellipse(slime_surf, (200, 50, 50), (mouth_rect.x + 1, mouth_rect.y + 2, mouth_rect.width - 2, mouth_rect.height - 2))
            else:
                eye_w = max(2, int(2 * scale))
                eye_h = max(4, int(6 * scale))
                pygame.draw.rect(slime_surf, (20, 30, 20), (w // 2 - int(8 * scale), eye_y, eye_w, eye_h))
                pygame.draw.rect(slime_surf, (20, 30, 20), (w // 2 + int(6 * scale), eye_y, eye_w, eye_h))

                mouth_y = eye_y + eye_h + int(1 * scale)
                mw = int(2 * scale)
                pygame.draw.rect(slime_surf, (20, 30, 20), (w // 2 - int(6 * scale), mouth_y, mw, mw))
                pygame.draw.rect(slime_surf, (20, 30, 20), (w // 2 - int(3 * scale), mouth_y + mw, mw, mw))
                pygame.draw.rect(slime_surf, (20, 30, 20), (w // 2, mouth_y, mw, mw))
                pygame.draw.rect(slime_surf, (20, 30, 20), (w // 2 + int(3 * scale), mouth_y + mw, mw, mw))
                pygame.draw.rect(slime_surf, (20, 30, 20), (w // 2 + int(5 * scale), mouth_y, mw, mw))

            if angle != 0: slime_surf = pygame.transform.rotate(slime_surf, angle)
            surface.blit(slime_surf, slime_surf.get_rect(center=self.rect.center))
        except Exception: pass

# --- FUNDO CAVERNA: ESTALACTITES, ESTALAGMITES E PEDRAS AFIADAS (SEM TOCHAS) ---
def desenhar_parallax_caverna(surface: pygame.Surface, camera_x: float):
    # Camada 1: Estalactites e Estalagmites Afiadas de Fundo Distante (0.15x)
    offset_1 = (camera_x * 0.15) % 200
    for i in range(-1, int(SCREEN_WIDTH / 200) + 2):
        bx = i * 200 - offset_1
        # Estalagmites e pedras afiadas no chão
        pygame.draw.polygon(surface, (18, 16, 24), [(bx, FLOOR_Y), (bx + 30, FLOOR_Y - 340), (bx + 60, FLOOR_Y)])
        pygame.draw.polygon(surface, (15, 14, 20), [(bx + 80, FLOOR_Y), (bx + 115, FLOOR_Y - 260), (bx + 150, FLOOR_Y)])
        
        # Estalactites penduradas do teto
        pygame.draw.polygon(surface, (18, 16, 24), [(bx + 15, 0), (bx + 50, 300), (bx + 85, 0)])
        pygame.draw.polygon(surface, (15, 14, 20), [(bx + 105, 0), (bx + 135, 220), (bx + 165, 0)])

    # Camada 2: Pilares rochosos e Formações de Pedras Afiadas Intermediárias (0.35x)
    offset_2 = (camera_x * 0.35) % 260
    for i in range(-1, int(SCREEN_WIDTH / 260) + 2):
        bx = i * 260 - offset_2
        # Colunas rochosas e rochas serrilhadas
        pygame.draw.polygon(surface, (26, 24, 32), [(bx + 20, 0), (bx + 45, 240), (bx + 35, FLOOR_Y - 220), (bx + 65, FLOOR_Y), (bx + 5, FLOOR_Y), (bx + 10, 0)])
        pygame.draw.polygon(surface, (22, 20, 28), [(bx + 140, FLOOR_Y), (bx + 175, FLOOR_Y - 180), (bx + 210, FLOOR_Y)]) # Pedra afiada no chão
        pygame.draw.polygon(surface, (22, 20, 28), [(bx + 180, 0), (bx + 205, 160), (bx + 230, 0)])                   # Estalactite média no teto

# --- FUNÇÕES DE DESENHO VISUAL (PIXEL ART) ---
def desenhar_estalactite_obstaculo(surface, rect: pygame.Rect, facing_down: bool):
    """Desenha os espinhos obstáculos com efeito 3D facetado"""
    # Cores do espinho 3D
    COLOR_ROCK_LIGHT = (90, 85, 90) # Lado iluminado (Esquerda)
    COLOR_ROCK_DARK = (40, 42, 48)  # Lado com sombra (Direita)
    
    if facing_down: # Espinho do teto (aponta pra baixo)
        left_poly = [(rect.x, rect.top), (rect.centerx, rect.bottom), (rect.centerx, rect.top)]
        right_poly = [(rect.centerx, rect.top), (rect.centerx, rect.bottom), (rect.right, rect.top)]
    else:           # Espinho do chão (aponta pra cima)
        left_poly = [(rect.x, rect.bottom), (rect.centerx, rect.top), (rect.centerx, rect.bottom)]
        right_poly = [(rect.centerx, rect.bottom), (rect.centerx, rect.top), (rect.right, rect.bottom)]
    
    pygame.draw.polygon(surface, COLOR_ROCK_LIGHT, left_poly)
    pygame.draw.polygon(surface, COLOR_ROCK_DARK, right_poly)

def draw_pixel_grass(surface, block_rect, world_x_offset):
    """Desenha grama orgânica e florzinhas fixas no topo do bloco"""
    COLOR_MOSS_LIGHT = (95, 185, 75)
    COLOR_MOSS_DARK = (45, 115, 45)
    
    # Desenha os fios de grama orgânicos (tamanhos gerados por hash para não piscar na tela)
    for i in range(int(block_rect.width)):
        world_px = int(world_x_offset + i)
        h = 2 + (hash(str(world_px)) % 4) # Fios de grama variando entre 2 e 5 pixels
        
        pygame.draw.line(surface, COLOR_MOSS_LIGHT, (block_rect.x + i, block_rect.top), (block_rect.x + i, block_rect.top + 1))
        pygame.draw.line(surface, COLOR_MOSS_DARK, (block_rect.x + i, block_rect.top + 2), (block_rect.x + i, block_rect.top + h))

def desenhar_portal(surface, portal_rect: pygame.Rect, tipo: str, frame_count: int, beat_pulse: float, particles: list):
    x, y, w, h = portal_rect.x, portal_rect.y, portal_rect.width, portal_rect.height
    
    if tipo == "G": # GOSMA: Pilares escuros com véu verde
        # Pilares de pedra (Esquerda e Direita)
        pygame.draw.rect(surface, (40, 42, 48), (x, y, 8, h))
        pygame.draw.rect(surface, (40, 42, 48), (x + w - 8, y, 8, h))
        
        # Véu Verde oscilando no centro
        alpha = int(100 + 40 * math.sin(frame_count * 0.08))
        curtain = pygame.Surface((w - 16, h), pygame.SRCALPHA)
        curtain.fill((120, 220, 90, alpha))
        surface.blit(curtain, (x + 8, y))
        
        # Pingos de Gosma caindo
        if random.random() < 0.15:
            particles.append(Particle(x + random.uniform(10, w - 10), y + 5, COLOR_SLIME_GOSMA, vel_x=0, vel_y=random.uniform(0.5, 1.5), gravity=0.15, size=random.randint(2, 3), lifespan=200, p_type="slime_drip"))

    elif tipo == "C": # CHICLETE: Anel flutuante rosa pulsante
        # Calcula o pulso do anel
        scale = 1.0 + (beat_pulse * 0.15)
        ring_w, ring_h = int(w * scale), int(h * scale)
        rx, ry = portal_rect.centerx - ring_w // 2, portal_rect.centery - ring_h // 2
        
        # Desenha o anel
        pygame.draw.ellipse(surface, (255, 120, 180), (rx, ry, ring_w, ring_h), 4)
        
        # Bolhas subindo
        if random.random() < 0.2:
            particles.append(Particle(portal_rect.centerx + random.uniform(-15, 15), ry + ring_h, COLOR_SLIME_CHICLETE, vel_x=0, vel_y=random.uniform(-1.5, -0.5), gravity=0, size=random.randint(3, 6), lifespan=150, p_type="pink_bubble"))

    elif tipo == "N": # NEVE: Simples obeliscos cianos
        pygame.draw.rect(surface, (100, 180, 240), (x, y, 4, h))
        pygame.draw.rect(surface, (100, 180, 240), (x + w - 4, y, 4, h))
        ice = pygame.Surface((w - 8, h), pygame.SRCALPHA)
        ice.fill((130, 210, 255, 90))
        surface.blit(ice, (x + 4, y))

def desenhar_vortice_final(surface, cx: int, cy: int, frame_count: int, beat_pulse: float):
    # Fundo do Vórtice (Preto Absoluto)
    pygame.draw.circle(surface, (0, 0, 0), (cx, cy), 35)
    
    # Bordas Pulsantes Ciano e Magenta
    pulse_mod = int(beat_pulse * 8)
    pygame.draw.circle(surface, (255, 0, 255), (cx, cy), 35 + pulse_mod, 3)
    pygame.draw.circle(surface, (0, 255, 255), (cx, cy), 42 + pulse_mod, 2)
    
    # Anéis tracejados rodando suavemente
    ang = frame_count * 0.05
    for r, speed_mod, color in [(25, 1, (200, 100, 255)), (15, -1.5, (100, 230, 255))]:
        for i in range(4): # 4 traços por anel
            a = ang * speed_mod + (i * math.pi / 2)
            px = cx + r * math.cos(a)
            py = cy + r * math.sin(a)
            pygame.draw.circle(surface, color, (int(px), int(py)), 3)
            
def main():
    log_debug("=== INICIANDO SLIME DASH - CORREÇÃO DE SQUASH E PARALLAX CAVERNA SEM TOCHAS ===")
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
    decals = []

    show_debug = True
    causa_morte = ""
    morto_parado = False
    global_frame_count = 0

    def pre_carregar_mapa():
        nonlocal fim_fase_x_relativo, mapa_objetos
        mapa_objetos.clear()
        fim_fase_x_relativo = distancia_total_musica
        for row_idx in range(len(fase_matriz)):
            line = fase_matriz[row_idx]
            y_pos = FLOOR_Y - ((row_idx + 1) * TILE_SIZE)
            for col_idx, char in enumerate(line):
                rel_x = col_idx * TILE_SIZE
                if char == "E": fim_fase_x_relativo = rel_x
                elif char in ("^", "v", "1", "h", "~", "*", "@", "O", "C", "N", "G"):
                    mapa_objetos.append((rel_x, y_pos, char, col_idx))
    pre_carregar_mapa()

    def iniciar_fase():
        nonlocal estado_jogo, timer_intro_wait, distancia_percorrida, causa_morte, morto_parado, animando_vitoria, timer_anim_vitoria, vitoria, current_bg_color
        log_debug(f"--- REINICIANDO DO INÍCIO (Tentativa {tentativas}) ---")
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
        decals.clear()
        sound_mgr.iniciar_musica()

    def reset_game(motivo=""):
        nonlocal tentativas, vitoria, causa_morte, morto_parado, animando_vitoria
        if modo_imunidade_admin: return
        causa_morte = motivo
        morto_parado = True
        tentativas += 1
        vitoria = False
        animando_vitoria = False

        log_debug(f"💀 MORTE CONFIRMADA: {motivo}")
        log_debug(f"   TELEMETRIA: Slime X={slime.x:.1f}, Y={slime.y:.1f} | Distância={distancia_percorrida:.1f}px")

        gerar_explosao_slime(slime.x, slime.y - 20, slime.color)
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
        else: iniciar_fase()

    frames_contador = 0
    beat_pulse = 0.0
    running = True

    try:
        while running:
            dt_fps = clock.get_fps()
            global_frame_count += 1

            for event in pygame.event.get():
                if event.type == pygame.QUIT: running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_g: show_debug = not show_debug
                    elif event.key == pygame.K_i:
                        modo_imunidade_admin = not modo_imunidade_admin
                        log_debug(f"Modo Imunidade Admin [I]: {'ATIVADO' if modo_imunidade_admin else 'DESATIVADO'}")
                        if morto_parado:
                            morto_parado = False
                            estado_jogo = "JOGANDO"
                            sound_mgr.reiniciar_musica()
                    elif event.key == pygame.K_c:
                        checkpoint_manual_admin = {"distancia": distancia_percorrida, "y": slime.y, "modo": slime.modo}
                        log_debug(f"📌 CHECKPOINT SALVO | Dist: {distancia_percorrida:.1f}px | Y: {slime.y:.1f} | Modo: {slime.modo}")
                    elif event.key == pygame.K_v and checkpoint_manual_admin:
                        distancia_percorrida = checkpoint_manual_admin["distancia"]
                        slime.mudar_modo(checkpoint_manual_admin["modo"])
                        slime.y = checkpoint_manual_admin["y"]
                        slime.vel_y = 0.0
                        morto_parado = False
                        estado_jogo = "JOGANDO"
                        log_debug("🚀 TELEPORTE PARA CHECKPOINT EXECUTADO!")
                    elif event.key == pygame.K_LEFT:
                        distancia_percorrida = max(0.0, distancia_percorrida - 250.0)
                        log_debug(f"⏪ Câmera Recuada: {distancia_percorrida:.1f}px")
                        if morto_parado:
                            morto_parado = False
                            estado_jogo = "JOGANDO"
                            sound_mgr.reiniciar_musica()
                    elif event.key == pygame.K_RIGHT:
                        distancia_percorrida = min(distancia_total_musica, distancia_percorrida + 250.0)
                        log_debug(f"⏩ Câmera Avançada: {distancia_percorrida:.1f}px")
                        if morto_parado:
                            morto_parado = False
                            estado_jogo = "JOGANDO"
                            sound_mgr.reiniciar_musica()

                    if morto_parado:
                        if event.key == pygame.K_SPACE: concluir_reset()
                    else:
                        if event.key in (pygame.K_ESCAPE, pygame.K_p):
                            if estado_jogo in ("JOGANDO", "INTRO_WAIT", "INTRO_RUN"):
                                estado_jogo = "PAUSADO"
                                sound_mgr.parar_musica()
                            elif estado_jogo == "PAUSADO":
                                estado_jogo = "JOGANDO"
                                sound_mgr.reiniciar_musica()
                        elif event.key == pygame.K_r and estado_jogo != "MENU": reset_game("RECOMEÇO VOLUNTÁRIO (TECLA R)")
                        elif event.key == pygame.K_m:
                            estado_jogo = "MENU"
                            sound_mgr.parar_musica()
                        elif event.key == pygame.K_SPACE:
                            if estado_jogo == "MENU": iniciar_fase()
                            elif estado_jogo == "PAUSADO":
                                estado_jogo = "JOGANDO"
                                sound_mgr.reiniciar_musica()
                            elif vitoria: iniciar_fase()
                            elif estado_jogo == "JOGANDO" and slime.modo != "CHICLETE" and not animando_vitoria:
                                slime.solicitar_pulo()

            keys = pygame.key.get_pressed()
            space_held = keys[pygame.K_SPACE] if (estado_jogo == "JOGANDO" and not morto_parado and not animando_vitoria) else False

            frames_contador += 1
            if frames_contador % frames_por_batida == 0: beat_pulse = 1.0
            else: beat_pulse = max(0.0, beat_pulse - 0.05)

            # Partículas Esporos Caverna
            if estado_jogo == "JOGANDO" and random.random() < 0.15:
                particles.append(Particle(random.uniform(0, SCREEN_WIDTH), random.uniform(0, CEILING_Y+150), (100, 255, 100), vel_x=-1.5, vel_y=random.uniform(0.5, 1.2), gravity=0, size=2, lifespan=255))

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
                    slime.update_rect()
                    attempt_text_x = float(SCREEN_WIDTH // 2)
                    if slime.x >= TARGET_X:
                        slime.x = TARGET_X
                        estado_jogo = "JOGANDO"
                elif estado_jogo == "JOGANDO" and not vitoria:
                    if not animando_vitoria:
                        slime_prev_y = slime.y
                        distancia_percorrida += scroll_speed
                        slime.update(FLOOR_Y, CEILING_Y, particles, space_held, sound_mgr, trigger_flash, distancia_percorrida, decals)
                        attempt_text_x = (SCREEN_WIDTH // 2) - distancia_percorrida

                        if slime.modo == "CHICLETE" and slime.imunidade_portal == 0 and not modo_imunidade_admin:
                            if slime.y <= CEILING_Y + 15: reset_game("Chiclete bateu no TETO do Mapa!")
                            elif slime.y >= FLOOR_Y - 5: reset_game("Chiclete bateu no CHÃO do Mapa!")
                    else:
                        timer_anim_vitoria += 1
                        fim_x_tela = fim_fase_x_relativo + TARGET_X - distancia_percorrida
                        vortex_center_y = FLOOR_Y - 100
                        slime.x += (fim_x_tela - slime.x) * 0.15
                        slime.y += (vortex_center_y - slime.y) * 0.15
                        slime.update_rect()
                        if timer_anim_vitoria >= 60:
                            animando_vitoria = False
                            vitoria = True

            new_particles = []
            for p in particles[:]:
                p.update(FLOOR_Y, new_particles)
                if p.radius <= 0 or p.lifespan <= 0: particles.remove(p)
            particles.extend(new_particles)

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
            slime_ground_hb = slime.get_ground_check_hitbox()

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
                        slime.current_width, slime.current_height = 18.0, 75.0
                        log_debug(f"⚡ TRAMPOLIM ACIONADO! PosY={slime.y:.1f}")
                        sound_mgr.tocar(sound_mgr.sfx_pad)

                for orb in orbes_rects:
                    if slime_hb.colliderect(orb) and space_held and slime.jump_buffer > 0:
                        slime.vel_y = -18.5
                        slime.jump_buffer = 0
                        slime.current_width, slime.current_height = 20.0, 65.0
                        log_debug(f"✨ ORBE ACIONADO! PosY={slime.y:.1f}")
                        sound_mgr.tocar(sound_mgr.sfx_jump)

                for coin_rect, coin_id in moedas:
                    if slime_hb.colliderect(coin_rect):
                        moedas_pegas_ids.add(coin_id)
                        moedas_coletadas += 1
                        log_debug(f"🪙 MOEDA COLETADA! Total={moedas_coletadas}/3")
                        sound_mgr.tocar(sound_mgr.sfx_coin)

                if not modo_imunidade_admin:
                    for spike, c_idx in espinhos_chao_rects:
                        if slime_hb.colliderect(spike): reset_game(f"Espinho do Chão (Coluna {c_idx})")
                    for spike_top, c_idx in espinhos_teto_rects:
                        if slime_hb.colliderect(spike_top): reset_game(f"Espinho do Teto (Coluna {c_idx})")
                    for lva, c_idx in lavas_rects:
                        if slime_hb.colliderect(lva): reset_game(f"Lava Quente (Coluna {c_idx})")

                em_cima_de_bloco = False
                for block, c_idx, orig_y in blocos_rects:
                    # USAMOS slime_ground_hb (COM 1PX EXTRA PARA BAIXO) PARA CHECAGEM CONTÍNUA DO CHÃO
                    if slime_ground_hb.colliderect(block):
                        if slime.modo == "CHICLETE":
                            if slime.imunidade_portal == 0 and not modo_imunidade_admin:
                                reset_game(f"Colisão de Voo com Bloco (Coluna {c_idx})")
                                break
                        else:
                            pes_acima_do_topo = (slime.y <= block.top + 12) or (slime_prev_y <= block.top + 12)
                            if slime.gravity > 0:
                                if pes_acima_do_topo and slime.vel_y >= 0:
                                    slime.y = float(block.top)
                                    slime.aplicar_impacto_chao(f"Bloco Coluna {c_idx}", distancia_percorrida, decals)
                                    em_cima_de_bloco = True
                                    slime.update_rect()
                                    slime.tentar_pular(sound_mgr, trigger_flash)
                                elif pes_acima_do_topo and slime.vel_y < 0: em_cima_de_bloco = True
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
                                    slime.aplicar_impacto_chao(f"Bloco Invertido Coluna {c_idx}", distancia_percorrida, decals)
                                    em_cima_de_bloco = True
                                    slime.update_rect()
                                    slime.tentar_pular(sound_mgr, trigger_flash)
                                elif pes_no_fundo and slime.vel_y > 0: em_cima_de_bloco = True
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

            # Parallax da Caverna (Fundo limpo original)
            desenhar_parallax_caverna(screen, distancia_percorrida)

            if bg_flash_alpha > 0:
                flash_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
                flash_surf.fill((255, 255, 255, int(bg_flash_alpha * 255)))
                screen.blit(flash_surf, (0, 0))

            # Chão e Teto limpos (sem a borda/serra verde do mapa)
            pygame.draw.rect(screen, COLOR_FLOOR, (0, FLOOR_Y, SCREEN_WIDTH, SCREEN_HEIGHT - FLOOR_Y))
            pygame.draw.rect(screen, COLOR_FLOOR, (0, 0, SCREEN_WIDTH, CEILING_Y))

            # Desenha as Manchas de Gosma dos Pousos
            offset_camera = TARGET_X - distancia_percorrida
            for dec in decals: dec.draw(screen, offset_camera)

            # Lava
            for lva, _ in lavas_rects:
                pygame.draw.rect(screen, COLOR_LAVA_BASE, lva)
                onda_offset = (global_frame_count * 2) % 20
                for lx in range(lva.x, lva.right, 20):
                    pygame.draw.line(screen, COLOR_LAVA_DETAIL, (lx - onda_offset, lva.y + 4), (lx + 10 - onda_offset, lva.y + 4), 2)
                if estado_jogo == "JOGANDO" and random.random() < 0.08:
                    particles.append(Particle(random.uniform(lva.x, lva.right), lva.y+5, (255, 120, 0), vel_x=-scroll_speed, vel_y=random.uniform(-3, -1), gravity=0.1, size=random.randint(2,4)))

            # ESPINHOS DOS OBSTÁCULOS (3D Facetado com Luz e Sombra)
            for spike_rect, _ in espinhos_chao_rects: 
                desenhar_estalactite_obstaculo(screen, spike_rect, facing_down=False)
            for spike_top_rect, _ in espinhos_teto_rects: 
                desenhar_estalactite_obstaculo(screen, spike_top_rect, facing_down=True)

            # BLOCOS DE PEDRA COM GRAMA ORGÂNICA E FLORES NO TOPO
            current_block_border = COLOR_BORDER_GOSMA
            if slime.modo == "CHICLETE": current_block_border = COLOR_BORDER_CHICLETE
            elif slime.modo == "NEVE": current_block_border = COLOR_BORDER_NEVE

            for block, col_idx, orig_y in blocos_rects:
                pygame.draw.rect(screen, COLOR_BLOCK, block)
                pygame.draw.rect(screen, current_block_border, block, 2) 
                pygame.draw.rect(screen, (30, 30, 35), (block.x + 10, block.y + 10, TILE_SIZE - 20, TILE_SIZE - 20))
                
                # Grama Pixel Art Orgânica no topo do bloco
                draw_pixel_grass(screen, block, block.x + distancia_percorrida)
                
                # Florzinhas fixas no topo dos blocos (35% de chance)
                random.seed(orig_y + col_idx)
                if random.random() < 0.35:
                    cor_flor = random.choice([(255, 200, 0), (200, 50, 255), (255, 100, 100)])
                    fx = block.x + random.randint(5, 35)
                    fy = block.y - 2
                    pygame.draw.rect(screen, cor_flor, (fx, fy, 2, 2))
                    pygame.draw.rect(screen, cor_flor, (fx-2, fy+2, 2, 2))
                    pygame.draw.rect(screen, cor_flor, (fx+2, fy+2, 2, 2))
                    pygame.draw.rect(screen, (255, 255, 255), (fx, fy+2, 2, 2)) # Miolo
                random.seed()

            # Trampolins com Glow
            for pad in trampolins_rects: 
                pad_color = COLOR_PAD
                if beat_pulse > 0:
                    glow_pad = pygame.Surface((pad.width + 10, pad.height + 10), pygame.SRCALPHA)
                    glow_pad.fill((255, 255, 100, int(beat_pulse * 150)))
                    screen.blit(glow_pad, (pad.x - 5, pad.y - 5))
                    pad_color = (255, 255, 150)
                pygame.draw.rect(screen, pad_color, pad, border_radius=3)

            for orb in orbes_rects:
                pygame.draw.circle(screen, COLOR_RING, orb.center, 14, 3)
                pygame.draw.circle(screen, (255, 255, 255), orb.center, 6)

            # --- RENDERIZAÇÃO DOS PORTAIS DE MUDANÇA DE MODO ---
            for portal_rect, tipo in portais:
                desenhar_portal(screen, portal_rect, tipo, global_frame_count, beat_pulse, particles)

            for coin_rect, _ in moedas:
                pygame.draw.circle(screen, COLOR_COIN, coin_rect.center, 14)
                pygame.draw.circle(screen, (255, 255, 200), coin_rect.center, 6)

            # --- RENDERIZAÇÃO DO VÓRTICE FINAL ---
            fim_x_tela = fim_fase_x_relativo + TARGET_X - distancia_percorrida
            if -150 < fim_x_tela < SCREEN_WIDTH + 150:
                vortex_center_x = fim_x_tela
                vortex_center_y = FLOOR_Y - 100
                
                # Partículas de Sucção (Pull Effect)
                if estado_jogo == "JOGANDO" and random.random() < 0.4:
                    ang = random.uniform(0, 2 * math.pi)
                    dist_spawn = random.uniform(70, 110)
                    sp_x = vortex_center_x + dist_spawn * math.cos(ang)
                    sp_y = vortex_center_y + dist_spawn * math.sin(ang)
                    particles.append(Particle(sp_x, sp_y, (240, 240, 255), target_x=vortex_center_x, target_y=vortex_center_y, size=random.randint(2, 4), lifespan=120, p_type="vortex_pull"))
                    
                desenhar_vortice_final(screen, vortex_center_x, vortex_center_y, global_frame_count, beat_pulse)

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
                txt_m3 = font.render("[ESPAÇO] Reiniciar do Início (0%)  |  [I] Ativar Imunidade", True, (230, 230, 230))
                txt_m4 = font.render("[← / →] Mover  |  [C] Salvar Ponto  |  [V] Ir ao Ponto", True, (200, 240, 255))
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
                screen.blit(t1, (SCREEN_WIDTH // 2 - t1.get_width() // 2, 220))
                screen.blit(t2, (SCREEN_WIDTH // 2 - t2.get_width() // 2, 310))

            elif estado_jogo == "PAUSADO":
                overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
                overlay.fill((0, 0, 0, 180))
                screen.blit(overlay, (0, 0))
                p1 = title_font.render("JOGO PAUSADO", True, (255, 215, 0))
                p2 = font.render("[ESPAÇO / P] Continuar  |  [R] Reiniciar  |  [M] Menu", True, (255, 255, 255))
                screen.blit(p1, (SCREEN_WIDTH // 2 - p1.get_width() // 2, 260))
                screen.blit(p2, (SCREEN_WIDTH // 2 - p2.get_width() // 2, 330))

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