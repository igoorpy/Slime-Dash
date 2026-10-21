import math
import random
import sys
import os
import traceback
import pygame

# ==============================================================================
# 1. CONFIGURAÇÕES DE CAMINHO E IMPORTAÇÃO DOS NÍVEIS
# ==============================================================================
# Define a pasta raiz do projeto para permitir importar os módulos da pasta 'src'
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(BASE_DIR)

try:
    from src.levels import NIVEIS, obter_configuracao_nivel, DURACAO_MUSICA_SEGUNDOS
except (ModuleNotFoundError, ImportError):
    from levels import NIVEIS, obter_configuracao_nivel, DURACAO_MUSICA_SEGUNDOS

# ==============================================================================
# 2. CONSTANTES GLOBAIS DE TELA, FÍSICA E CORES
# ==============================================================================
SCREEN_WIDTH = 960   # Largura da janela em pixels
SCREEN_HEIGHT = 720  # Altura da janela em pixels
FPS = 60             # Taxa de quadros por segundo (60 FPS para jogo fluido)

TILE_SIZE = 50       # Tamanho de cada bloco da grade (50x50 pixels)
NUM_ROWS = 10        # Altura do espaço jogável em número de blocos
FLOOR_Y = 600        # Coordenada Y do chão principal
CEILING_Y = FLOOR_Y - (NUM_ROWS * TILE_SIZE) # Coordenada Y do teto principal (100px)

TARGET_X = 240.0     # Posição fixa X na tela onde o Slime corre
SLIME_START_X = -80.0# Posição X inicial fora da tela para animação de entrada

# --- PALETAS DE CORES POR MODO/BIOMA (RGB) ---
COLOR_BG_CAVERNA = (12, 10, 16)   # Fundo escuro do modo Gosma (padrão)
COLOR_BG_CHICLETE = (25, 8, 18)   # Fundo roxo do modo Chiclete
COLOR_BG_NEVE = (8, 15, 25)      # Fundo azul-escuro do modo Neve

COLOR_FLOOR = (28, 28, 32)        # Cor das superfícies do teto e chão
COLOR_MOSS = (65, 135, 55)        # Verde do musgo/grama

# Cores do corpo do Slime dependendo do modo
COLOR_SLIME_GOSMA = (120, 220, 90)     # Verde chamativo
COLOR_SLIME_CHICLETE = (255, 120, 180) # Rosa chiclete
COLOR_SLIME_NEVE = (130, 210, 255)     # Azul gelo

# Obstáculos e Cenário
COLOR_SPIKE = (90, 85, 90)        # Cor base dos espinhos de pedra
COLOR_BLOCK = (40, 42, 48)        # Cor interior dos blocos rochosos

# Borda dos blocos muda dinamicamente conforme o modo do Slime
COLOR_BORDER_GOSMA = (85, 160, 85)     
COLOR_BORDER_CHICLETE = (255, 105, 180) 
COLOR_BORDER_NEVE = (135, 206, 250)    

COLOR_LAVA_BASE = (220, 50, 10)   # Vermelho quente da lava
COLOR_LAVA_DETAIL = (255, 140, 0) # Amarelo/Laranja das ondas de lava

COLOR_PAD = (255, 230, 0)         # Amarelo para os trampolins
COLOR_RING = (255, 200, 0)        # Dourado para os orbes
COLOR_COIN = (255, 215, 0)        # Dourado brilhante para as moedas

# Função utilitária para registrar logs de diagnóstico no terminal
def log_debug(msg: str):
    print(f"[SLIME_DIAGNOSTIC] {msg}")

# ==============================================================================
# 3. GERENCIADOR DE ÁUDIO E EFEITOS SONOROS (SoundManager)
# ==============================================================================
class SoundManager:
    """
    Gerencia a inicialização da placa de som (Pygame Mixer), carregamento da música
    de fundo e síntese digital de som (NumPy) para garantir áudio mesmo sem arquivos.
    """
    def __init__(self):
        self.sounds_enabled = True
        try:
            # Inicializa o mixer de áudio com frequência de 44.1kHz e 2 canais (Estéreo)
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
            log_debug("Mixer de Áudio inicializado com sucesso.")
        except Exception as e:
            log_debug(f"AVISO: Falha ao inicializar áudio: {e}")
            self.sounds_enabled = False

        # Gera efeitos sonoros sintéticos usando ondas senoidais matematicamente
        self.sfx_jump = self._gerar_som_sintetico(520, 60)   # Som do pulo
        self.sfx_coin = self._gerar_som_sintetico(980, 100)  # Som ao pegar moeda
        self.sfx_death = self._gerar_som_sintetico(130, 180) # Som de explosão/morte
        self.sfx_pad = self._gerar_som_sintetico(750, 120)   # Som do trampolim

        # Localiza o arquivo da música principal da fase
        caminho_abs = os.path.join(BASE_DIR, "assets", "sounds", "fase1.mp3")
        caminho_rel = "assets/sounds/fase1.mp3"
        self.musica_fase1 = caminho_abs if os.path.exists(caminho_abs) else caminho_rel

        if self.sounds_enabled and os.path.exists(self.musica_fase1):
            try:
                pygame.mixer.music.load(self.musica_fase1)
                pygame.mixer.music.set_volume(0.5) # Volume em 50%
            except Exception: pass

    def _gerar_som_sintetico(self, frequencia: int, duracao_ms: int):
        """
        Cria um efeito sonoro digital direto na memória usando a biblioteca NumPy.
        Utilizado como fallback caso o arquivo de som físico não esteja disponível.
        """
        if not self.sounds_enabled: return None
        try:
            import numpy as np
            sample_rate = 44100
            n_samples = int(sample_rate * (duracao_ms / 1000.0))
            t = np.linspace(0, duracao_ms / 1000.0, n_samples, False)
            waveform = np.sin(2 * np.pi * frequencia * t) * 0.2
            sound_array = np.int16(waveform * 32767)
            sound_array = np.column_stack((sound_array, sound_array)) # Estéreo
            return pygame.sndarray.make_sound(sound_array)
        except Exception: return None

    # Métodos utilitários de controle da reprodução musical
    def iniciar_musica(self):
        if self.sounds_enabled:
            try: pygame.mixer.music.play(-1) # Loop infinito (-1)
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

# ==============================================================================
# 4. SISTEMA DE PARTÍCULAS (Particle)
# ==============================================================================
class Particle:
    """
    Classe para criar e atualizar partículas na tela (poeira, pingos de gosma,
    bolhas de chiclete e partículas de sucção do vórtice final).
    """
    def __init__(self, x: float, y: float, color: tuple, vel_x: float = None, vel_y: float = None, gravity: float = 0.0, size: int = None, lifespan: int = 255, p_type: str = "generic", target_x: float = 0.0, target_y: float = 0.0):
        self.x = float(x)
        self.y = float(y)
        self.color = color
        self.radius = float(size if size is not None else random.randint(3, 6))
        self.vel_x = vel_x if vel_x is not None else random.uniform(-2.0, 2.0)
        self.vel_y = vel_y if vel_y is not None else random.uniform(-2.0, 2.0)
        self.gravity = gravity
        self.lifespan = lifespan # Vida da partícula (255 a 0 - controla o Alpha/Transparência)
        self.p_type = p_type     # Tipo: "vortex_pull", "slime_drip", "pink_bubble", "generic"
        self.target_x = target_x # Ponto de atração (usado na sucção do Vórtice)
        self.target_y = target_y

    def update(self, floor_y: int, new_particles: list):
        """Atualiza a posição física e diminui o tempo de vida da partícula."""
        if self.p_type == "vortex_pull":
            # Movimento de atração em vetor calculado em direção ao centro do Buraco Negro
            dx = self.target_x - self.x
            dy = self.target_y - self.y
            dist = math.hypot(dx, dy)
            if dist < 10:
                self.lifespan = 0 # Some imediatamente ao tocar o núcleo
            else:
                speed = 5.0 # Velocidade do efeito de atração
                self.x += (dx / dist) * speed
                self.y += (dy / dist) * speed
                self.lifespan -= 3
        elif self.p_type == "slime_drip":
            # Pingo caindo do teto do portal de Gosma
            self.vel_y += self.gravity
            self.y += self.vel_y
            self.lifespan -= 4
        elif self.p_type == "pink_bubble":
            # Bolha rosa do portal de Chiclete subindo em senóide (zigue-zague suave)
            self.x += math.sin(self.y * 0.05) * 0.5
            self.y += self.vel_y
            self.lifespan -= 2
        else: # Partículas normais de poeira e colisão
            self.vel_y += self.gravity
            self.x += self.vel_x
            self.y += self.vel_y
            self.radius = max(0.0, self.radius - 0.1)
            self.lifespan -= 2

    def draw(self, surface: pygame.Surface):
        """Desenha a partícula na tela utilizando transparência Alpha."""
        if self.radius > 0 and self.lifespan > 0:
            alpha = max(0, min(255, self.lifespan))
            if self.p_type in ("pink_bubble", "vortex_pull"):
                # Bolhas e anéis translúcidos vazados
                p_surf = pygame.Surface((int(self.radius*2+2), int(self.radius*2+2)), pygame.SRCALPHA)
                pygame.draw.circle(p_surf, (*self.color[:3], alpha), (int(self.radius+1), int(self.radius+1)), int(self.radius), 1)
                surface.blit(p_surf, (int(self.x - self.radius), int(self.y - self.radius)))
            else:
                # Círculos sólidos preenchidos
                p_surf = pygame.Surface((int(self.radius*2), int(self.radius*2)), pygame.SRCALPHA)
                pygame.draw.circle(p_surf, (*self.color[:3], alpha), (int(self.radius), int(self.radius)), int(self.radius))
                surface.blit(p_surf, (int(self.x - self.radius), int(self.y - self.radius)))

# ==============================================================================
# 5. MANCHAS DE POUSO NO CHÃO (Decal)
# ==============================================================================
class Decal:
    """
    Registra e desenha as marcas de gosma deixadas no chão ou no teto
    sempre que o Slime pousa vindo do ar (efeito de impacto visual).
    """
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
        # Converte a coordenada do mundo para a coordenada real da tela do jogador
        tela_x = self.x_mundo + camera_offset_x
        if -50 < tela_x < SCREEN_WIDTH + 50:
            for px, py in self.pontos:
                pygame.draw.circle(surface, self.color, (int(tela_x + px), int(self.y)), abs(py))

# ==============================================================================
# 6. CLASSE PRINCIPAL DO PERSONAGEM (Slime)
# ==============================================================================
class Slime(pygame.sprite.Sprite):
    """
    Contém a física, animação de deformação (Squash & Stretch), caixas de colisão
    e gerenciamento dos 3 modos de jogo (GOSMA, CHICLETE e NEVE).
    """
    def __init__(self, x: float, y: float):
        super().__init__()
        self.base_size = 40          # Tamanho base do Slime (40x40 pixels)
        self.x = float(x)
        self.y = float(y)
        self.vel_y = 0.0             # Velocidade vertical
        self.jump_buffer = 0         # Buffer de entrada para pulos precisos
        self.imunidade_portal = 0    # Quadros de imunidade ao atravessar portais
        self.modo = "GOSMA"          # Modo inicial
        self.color = COLOR_SLIME_GOSMA

        self.gravity = 1.15          # Gravidade normal
        self.jump_strength = -16.5   # Força de pulo para cima
        self.is_grounded = False     # Indica se está pisando em superfície sólida
        self.current_width = float(self.base_size)
        self.current_height = float(self.base_size)
        self.update_rect()

    def update_rect(self):
        """Atualiza a caixa retangular visual do Sprite baseada nas deformações."""
        w = max(4, int(round(self.current_width)))
        h = max(4, int(round(self.current_height)))
        self.rect = pygame.Rect(int(round(self.x - w / 2.0)), int(round(self.y)) - h, w, h)

    def get_hitbox(self) -> pygame.Rect:
        """Retorna a caixa de colisão de DANO (ligeiramente menor para ser justo com o jogador)."""
        return pygame.Rect(int(self.x - 13), int(self.y - 38), 26, 38)

    def get_ground_check_hitbox(self) -> pygame.Rect:
        """
        Hitbox estendida em 1px para baixo para manter contato contínuo ao deslizar sobre blocos,
        evitando falsas quedas durante o movimento contínuo.
        """
        return pygame.Rect(int(self.x - 13), int(self.y - 38), 26, 39)

    def mudar_modo(self, novo_modo: str):
        """Altera dinamicamente as leis da física dependendo do portal atravessado."""
        log_debug(f"🔄 MUDANÇA DE MODO: {self.modo} -> {novo_modo} | PosY: {self.y:.1f}")
        self.modo = novo_modo
        self.imunidade_portal = 15 # 15 quadros protegidos
        if novo_modo == "GOSMA":
            self.color = COLOR_SLIME_GOSMA
            self.gravity = 1.15
            self.jump_strength = -16.5
        elif novo_modo == "CHICLETE": # Voo livre sustentado
            self.color = COLOR_SLIME_CHICLETE
            self.gravity = 0.0
            self.jump_strength = 0.0
            self.vel_y = -1.8
        elif novo_modo == "NEVE":     # Gravidade invertida (anda no teto)
            self.color = COLOR_SLIME_NEVE
            self.gravity = -1.15
            self.jump_strength = 16.5

    def solicitar_pulo(self):
        """Registra a intenção de pulo no Jump Buffer (guarda o comando por 8 frames)."""
        self.jump_buffer = 8

    def tentar_pular(self, sound_mgr: SoundManager = None, trigger_flash_func=None):
        """Tenta executar o pulo se houver comando no buffer e o Slime estiver no chão."""
        if self.jump_buffer > 0:
            poulou = False
            if self.modo in ("GOSMA", "NEVE") and self.is_grounded:
                self.vel_y = self.jump_strength
                self.is_grounded = False
                self.jump_buffer = 0
                # Deforma o Slime verticalmente ao pular (Estica: 20px largura x 65px altura)
                self.current_width, self.current_height = 20.0, 65.0
                poulou = True

            if poulou:
                log_debug(f"🦘 PULO EXECUTADO | Modo: {self.modo} | VelY: {self.vel_y:.2f} | PosY: {self.y:.1f}")
                if trigger_flash_func is not None: trigger_flash_func(0.08)
                if sound_mgr is not None: sound_mgr.tocar(sound_mgr.sfx_jump)

    def aplicar_impacto_chao(self, origem_nome="Chão/Bloco", dist_total: float = 0, decals_list: list = None):
        """Aplica o efeito de esmagamento (Squash: 68px x 20px) no instante do impacto com o chão."""
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
        """Atualiza a posição, velocidade, física e animação de recuperação de forma do Slime."""
        if self.jump_buffer > 0: self.jump_buffer -= 1
        if self.imunidade_portal > 0: self.imunidade_portal -= 1

        # Estica o personagem quando está voando/caindo rápido
        if not self.is_grounded and abs(self.vel_y) > 8.0 and self.modo != "CHICLETE":
            self.current_width += (26.0 - self.current_width) * 0.2
            self.current_height += (55.0 - self.current_height) * 0.2

        # Lógica especial de controle do MODO CHICLETE (Voo livre)
        if self.modo == "CHICLETE":
            if space_held: self.vel_y = max(-3.2, self.vel_y - 0.25) # Sobe ao segurar Espaço
            else: self.vel_y = min(3.2, self.vel_y + 0.22)            # Desce ao soltar Espaço
            self.vel_y *= 0.94 # Desaceleração por atrito com o ar
            self.y += self.vel_y
            if random.random() < 0.3:
                particles.append(Particle(self.x - 10, self.y - 20, self.color, vel_x=-3.0, vel_y=random.uniform(-0.5, 0.5), size=4))
        else:
            # Modos GOSMA e NEVE (Plataforma tradicional / Invertida)
            if space_held: self.jump_buffer = 6
            self.tentar_pular(sound_mgr, trigger_flash_func)

            if not self.is_grounded:
                self.vel_y += self.gravity
                self.y += self.vel_y

            # Checagem de limite com o chão principal
            if self.gravity > 0 and not self.is_grounded:
                if self.y >= floor_y:
                    self.y = float(floor_y)
                    self.aplicar_impacto_chao("Chão Principal", dist_total, decals_list)
                    for _ in range(5): particles.append(Particle(self.x, floor_y - 4, self.color))
                    self.tentar_pular(sound_mgr, trigger_flash_func)
            # Checagem de limite com o teto principal (Modo Neve Invertido)
            elif self.gravity < 0 and not self.is_grounded:
                if self.y <= ceiling_y:
                    self.y = float(ceiling_y)
                    self.aplicar_impacto_chao("Teto Principal", dist_total, decals_list)
                    for _ in range(5): particles.append(Particle(self.x, ceiling_y + 4, self.color))
                    self.tentar_pular(sound_mgr, trigger_flash_func)

            if self.is_grounded and random.random() < 0.3:
                py_pos = self.y if self.gravity > 0 else self.y - 38
                particles.append(Particle(self.x - 12, py_pos, (140, 140, 160), vel_x=-2.5, vel_y=random.uniform(-0.8, 0.2), size=3))

        # INTERPOLAÇÃO LINEAR: Fazer o Slime recuperar suavemente sua forma redonda original (40x40px)
        self.current_width += (self.base_size - self.current_width) * 0.15
        self.current_height += (self.base_size - self.current_height) * 0.15
        self.update_rect()

    def draw(self, surface: pygame.Surface, scale: float = 1.0, angle: float = 0.0):
        """Desenha o Slime em estilo Pixel Art com brilho, olhos e expressões dinâmicas."""
        try:
            w = max(6, int(round(self.rect.width * scale)))
            h = max(6, int(round(self.rect.height * scale)))
            slime_surf = pygame.Surface((w, h), pygame.SRCALPHA)

            dark_outline = (30, 80, 20)
            highlight_color = (200, 255, 170)

            # Desenha o corpo esférico e brilho especular
            pygame.draw.ellipse(slime_surf, dark_outline, (0, 0, w, h))
            pygame.draw.ellipse(slime_surf, self.color, (2, 2, w - 4, h - 4))
            pygame.draw.ellipse(slime_surf, highlight_color, (w // 4, 3, w // 2, h // 3))

            eye_y = (h // 2) - int(2 * scale)
            jumping = (self.vel_y < -2.0 if self.gravity > 0 else self.vel_y > 2.0) and not self.is_grounded

            # Expressão facial: Olhos abertos no ar/voando e olhos normais no chão
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

# ==============================================================================
# 7. FUNÇÕES VISUAIS DE CENÁRIO E PARALLAX
# ==============================================================================
def desenhar_parallax_caverna(surface: pygame.Surface, camera_x: float):
    """
    Desenha 2 camadas de silhuetas rochosas ao fundo deslizando em velocidades reduzidas
    (0.15x e 0.35x), criando uma ilusão ótica de profundidade 3D (Efeito Parallax).
    """
    # Camada 1: Estalactites e formações de pedra distantes (Velocidade 0.15x)
    offset_1 = (camera_x * 0.15) % 200
    for i in range(-1, int(SCREEN_WIDTH / 200) + 2):
        bx = i * 200 - offset_1
        pygame.draw.polygon(surface, (18, 16, 24), [(bx, FLOOR_Y), (bx + 30, FLOOR_Y - 340), (bx + 60, FLOOR_Y)])
        pygame.draw.polygon(surface, (15, 14, 20), [(bx + 80, FLOOR_Y), (bx + 115, FLOOR_Y - 260), (bx + 150, FLOOR_Y)])
        pygame.draw.polygon(surface, (18, 16, 24), [(bx + 15, 0), (bx + 50, 300), (bx + 85, 0)])
        pygame.draw.polygon(surface, (15, 14, 20), [(bx + 105, 0), (bx + 135, 220), (bx + 165, 0)])

    # Camada 2: Pilares rochosos intermediários (Velocidade 0.35x)
    offset_2 = (camera_x * 0.35) % 260
    for i in range(-1, int(SCREEN_WIDTH / 260) + 2):
        bx = i * 260 - offset_2
        pygame.draw.polygon(surface, (26, 24, 32), [(bx + 20, 0), (bx + 45, 240), (bx + 35, FLOOR_Y - 220), (bx + 65, FLOOR_Y), (bx + 5, FLOOR_Y), (bx + 10, 0)])
        pygame.draw.polygon(surface, (22, 20, 28), [(bx + 140, FLOOR_Y), (bx + 175, FLOOR_Y - 180), (bx + 210, FLOOR_Y)])
        pygame.draw.polygon(surface, (22, 20, 28), [(bx + 180, 0), (bx + 205, 160), (bx + 230, 0)])

def desenhar_estalactite_obstaculo(surface, rect: pygame.Rect, facing_down: bool):
    """Desenha os espinhos/estalactites que causam dano com sombreamento 3D facetado."""
    COLOR_ROCK_LIGHT = (90, 85, 90) # Lado esquerdo iluminado
    COLOR_ROCK_DARK = (40, 42, 48)  # Lado direito sombreado
    
    if facing_down: # Espinho do teto aponta para baixo
        left_poly = [(rect.x, rect.top), (rect.centerx, rect.bottom), (rect.centerx, rect.top)]
        right_poly = [(rect.centerx, rect.top), (rect.centerx, rect.bottom), (rect.right, rect.top)]
    else:           # Espinho do chão aponta para cima
        left_poly = [(rect.x, rect.bottom), (rect.centerx, rect.top), (rect.centerx, rect.bottom)]
        right_poly = [(rect.centerx, rect.bottom), (rect.centerx, rect.top), (rect.right, rect.bottom)]
    
    pygame.draw.polygon(surface, COLOR_ROCK_LIGHT, left_poly)
    pygame.draw.polygon(surface, COLOR_ROCK_DARK, right_poly)

def draw_pixel_grass(surface, block_rect, world_x_offset):
    """
    Desenha tufos de grama detalhados no topo dos blocos. Utiliza uma função HASH
    para fixar a variação de altura sem fazer os fios piscarem durante o scroll.
    """
    COLOR_MOSS_LIGHT = (95, 185, 75)
    COLOR_MOSS_DARK = (45, 115, 45)
    
    for i in range(int(block_rect.width)):
        world_px = int(world_x_offset + i)
        h = 2 + (hash(str(world_px)) % 4) # Fios entre 2px e 5px
        pygame.draw.line(surface, COLOR_MOSS_LIGHT, (block_rect.x + i, block_rect.top), (block_rect.x + i, block_rect.top + 1))
        pygame.draw.line(surface, COLOR_MOSS_DARK, (block_rect.x + i, block_rect.top + 2), (block_rect.x + i, block_rect.top + h))

def desenhar_portal(surface, portal_rect: pygame.Rect, tipo: str, frame_count: int, beat_pulse: float, particles: list):
    """Desenha os portais de mudança de modo com estilos e partículas exclusivos."""
    x, y, w, h = portal_rect.x, portal_rect.y, portal_rect.width, portal_rect.height
    
    if tipo == "G": # PORTAL DA GOSMA: Pilares laterais com véu translúcido oscilante
        pygame.draw.rect(surface, (40, 42, 48), (x, y, 8, h))
        pygame.draw.rect(surface, (40, 42, 48), (x + w - 8, y, 8, h))
        
        alpha = int(100 + 40 * math.sin(frame_count * 0.08))
        curtain = pygame.Surface((w - 16, h), pygame.SRCALPHA)
        curtain.fill((120, 220, 90, alpha))
        surface.blit(curtain, (x + 8, y))
        
        if random.random() < 0.15:
            particles.append(Particle(x + random.uniform(10, w - 10), y + 5, COLOR_SLIME_GOSMA, vel_x=0, vel_y=random.uniform(0.5, 1.5), gravity=0.15, size=random.randint(2, 3), lifespan=200, p_type="slime_drip"))

    elif tipo == "C": # PORTAL DO CHICLETE: Anel rosa flutuante que pulsa no BPM da música
        scale = 1.0 + (beat_pulse * 0.15)
        ring_w, ring_h = int(w * scale), int(h * scale)
        rx, ry = portal_rect.centerx - ring_w // 2, portal_rect.centery - ring_h // 2
        
        pygame.draw.ellipse(surface, (255, 120, 180), (rx, ry, ring_w, ring_h), 4)
        
        if random.random() < 0.2:
            particles.append(Particle(portal_rect.centerx + random.uniform(-15, 15), ry + ring_h, COLOR_SLIME_CHICLETE, vel_x=0, vel_y=random.uniform(-1.5, -0.5), gravity=0, size=random.randint(3, 6), lifespan=150, p_type="pink_bubble"))

    elif tipo == "N": # PORTAL DA NEVE: Obeliscos azuis congelados
        pygame.draw.rect(surface, (100, 180, 240), (x, y, 4, h))
        pygame.draw.rect(surface, (100, 180, 240), (x + w - 4, y, 4, h))
        ice = pygame.Surface((w - 8, h), pygame.SRCALPHA)
        ice.fill((130, 210, 255, 90))
        surface.blit(ice, (x + 4, y))

def desenhar_vortice_final(surface, cx: int, cy: int, frame_count: int, beat_pulse: float):
    """Desenha o Buraco Negro de saída da fase com anéis externos giratórios e pulsantes."""
    pygame.draw.circle(surface, (0, 0, 0), (cx, cy), 35) # Núcleo preto absoluto
    
    pulse_mod = int(beat_pulse * 8)
    pygame.draw.circle(surface, (255, 0, 255), (cx, cy), 35 + pulse_mod, 3)
    pygame.draw.circle(surface, (0, 255, 255), (cx, cy), 42 + pulse_mod, 2)
    
    ang = frame_count * 0.05
    for r, speed_mod, color in [(25, 1, (200, 100, 255)), (15, -1.5, (100, 230, 255))]:
        for i in range(4):
            a = ang * speed_mod + (i * math.pi / 2)
            px = cx + r * math.cos(a)
            py = cy + r * math.sin(a)
            pygame.draw.circle(surface, color, (int(px), int(py)), 3)

# ==============================================================================
# 8. LAÇO PRINCIPAL DO JOGO (main)
# ==============================================================================
def main():
    """
    Função principal que inicializa a janela, carrega as matrizes da fase
    e roda o Game Loop (Entrada de usuário -> Física -> Colisão -> Renderização).
    """
    log_debug("=== INICIANDO SLIME DASH - CORREÇÃO DE SQUASH E PARALLAX CAVERNA SEM TOCHAS ===")
    pygame.init()
    sound_mgr = SoundManager()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Slime Dash")
    clock = pygame.time.Clock()

    # Fontes do sistema para a Interface (HUD, Debug e Banners)
    font = pygame.font.SysFont("Consolas", 15, bold=True)
    attempt_font = pygame.font.SysFont("Consolas", 58, bold=True)
    title_font = pygame.font.SysFont("Consolas", 42, bold=True)
    debug_font = pygame.font.SysFont("Consolas", 15, bold=True)

    scroll_speed = 6.0 # Velocidade horizontal de rolagem da fase
    distancia_total_musica = scroll_speed * FPS * DURACAO_MUSICA_SEGUNDOS

    # Configuração e leitura do arquivo de nível
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

    # Ferramentas de Teste/Administrador
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
        """Gera 35 partículas caindo com gravidade ao morrer."""
        for _ in range(35):
            vx = random.uniform(-6.0, 6.0)
            vy = random.uniform(-10.0, -2.0)
            particles.append(Particle(x, y, color, vel_x=vx, vel_y=vy, gravity=0.45, size=random.randint(5, 10)))

    estado_jogo = "MENU" # Estados: "MENU", "INTRO_WAIT", "INTRO_RUN", "JOGANDO", "PAUSADO"
    timer_intro_wait = 0
    frames_por_batida = int((60 * FPS) / bpm_atual) # Duração de 1 batida musical em frames

    slime = Slime(x=SLIME_START_X, y=FLOOR_Y)
    particles = []
    decals = []

    show_debug = True
    causa_morte = ""
    morto_parado = False
    global_frame_count = 0

    def pre_carregar_mapa():
        """Converte os caracteres da matriz do nível em coordenadas de pixels na tela."""
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
        """Reseta as variáveis do jogo para começar a tentativa do início."""
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
        """Registra a morte do jogador e abre o painel de reset."""
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
        """Reinicia a partida ou volta para o Checkpoint Admin caso esteja ativo."""
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
        # --- GAME LOOP PRINCIPAL ---
        while running:
            dt_fps = clock.get_fps()
            global_frame_count += 1

            # ------------------------------------------------------------------
            # A. PROCESSAMENTO DE EVENTOS DO TECLADO
            # ------------------------------------------------------------------
            for event in pygame.event.get():
                if event.type == pygame.QUIT: running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_g: show_debug = not show_debug
                    # Atalhos de testes para a apresentação (Ativa Imunidade, Checkpoints e Câmera)
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

            # Cálculo de Sincronização BPM com a Música
            frames_contador += 1
            if frames_contador % frames_por_batida == 0: beat_pulse = 1.0
            else: beat_pulse = max(0.0, beat_pulse - 0.05)

            # Partículas de Esporos no ar da caverna
            if estado_jogo == "JOGANDO" and random.random() < 0.15:
                particles.append(Particle(random.uniform(0, SCREEN_WIDTH), random.uniform(0, CEILING_Y+150), (100, 255, 100), vel_x=-1.5, vel_y=random.uniform(0.5, 1.2), gravity=0, size=2, lifespan=255))

            bg_flash_alpha = max(0.0, bg_flash_alpha - 0.015)

            # Transição suave de cores do Fundo dependendo do modo atual
            target_bg = COLOR_BG_CAVERNA
            if slime.modo == "CHICLETE": target_bg = COLOR_BG_CHICLETE
            elif slime.modo == "NEVE": target_bg = COLOR_BG_NEVE

            for i in range(3):
                current_bg_color[i] += (target_bg[i] - current_bg_color[i]) * 0.05

            attempt_text_x = float(SCREEN_WIDTH // 2)

            # ------------------------------------------------------------------
            # B. ATUALIZAÇÃO DA MÁQUINA DE ESTADOS E FÍSICA
            # ------------------------------------------------------------------
            if not morto_parado:
                if estado_jogo == "INTRO_WAIT":
                    distancia_percorrida = 0.0
                    slime.x = SLIME_START_X
                    slime.jump_buffer = 0
                    slime.update_rect()
                    attempt_text_x = float(SCREEN_WIDTH // 2)
                    timer_intro_wait += 1
                    if timer_intro_wait >= 30: estado_jogo = "INTRO_RUN"
                elif estado_jogo == "INTRO_RUN": # Animação do Slime entrando pela esquerda
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
                        distancia_percorrida += scroll_speed # Avanço do mapa
                        slime.update(FLOOR_Y, CEILING_Y, particles, space_held, sound_mgr, trigger_flash, distancia_percorrida, decals)
                        attempt_text_x = (SCREEN_WIDTH // 2) - distancia_percorrida

                        # Condição de Morte no modo Chiclete ao tocar nas paredes do mapa
                        if slime.modo == "CHICLETE" and slime.imunidade_portal == 0 and not modo_imunidade_admin:
                            if slime.y <= CEILING_Y + 15: reset_game("Chiclete bateu no TETO do Mapa!")
                            elif slime.y >= FLOOR_Y - 5: reset_game("Chiclete bateu no CHÃO do Mapa!")
                    else: # Animação de Sucção no Vórtice de Vitória
                        timer_anim_vitoria += 1
                        fim_x_tela = fim_fase_x_relativo + TARGET_X - distancia_percorrida
                        vortex_center_y = FLOOR_Y - 100
                        slime.x += (fim_x_tela - slime.x) * 0.15
                        slime.y += (vortex_center_y - slime.y) * 0.15
                        slime.update_rect()
                        if timer_anim_vitoria >= 60:
                            animando_vitoria = False
                            vitoria = True

            # Atualização e limpeza de partículas destruídas
            new_particles = []
            for p in particles[:]:
                p.update(FLOOR_Y, new_particles)
                if p.radius <= 0 or p.lifespan <= 0: particles.remove(p)
            particles.extend(new_particles)

            # Separa os elementos visíveis na tela para checar colisão
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

            # ------------------------------------------------------------------
            # C. DETECÇÃO DE COLISÕES (AABB)
            # ------------------------------------------------------------------
            if estado_jogo == "JOGANDO" and not vitoria and not morto_parado and not animando_vitoria:
                # 1. Portais de Mudança de Modo
                for portal_rect, tipo in portais:
                    if slime_hb.colliderect(portal_rect):
                        if tipo == "C" and slime.modo != "CHICLETE": slime.mudar_modo("CHICLETE")
                        elif tipo == "N" and slime.modo != "NEVE": slime.mudar_modo("NEVE")
                        elif tipo == "G" and slime.modo != "GOSMA": slime.mudar_modo("GOSMA")

                # 2. Trampolins (Super Pulo)
                for pad in trampolins_rects:
                    if slime_hb.colliderect(pad):
                        slime.vel_y = -22.5
                        slime.is_grounded = False
                        slime.current_width, slime.current_height = 18.0, 75.0
                        sound_mgr.tocar(sound_mgr.sfx_pad)

                # 3. Orbes Douradas
                for orb in orbes_rects:
                    if slime_hb.colliderect(orb) and space_held and slime.jump_buffer > 0:
                        slime.vel_y = -18.5
                        slime.jump_buffer = 0
                        slime.current_width, slime.current_height = 20.0, 65.0
                        sound_mgr.tocar(sound_mgr.sfx_jump)

                # 4. Coleta de Moedas
                for coin_rect, coin_id in moedas:
                    if slime_hb.colliderect(coin_rect):
                        moedas_pegas_ids.add(coin_id)
                        moedas_coletadas += 1
                        sound_mgr.tocar(sound_mgr.sfx_coin)

                # 5. Colisão com Obstáculos Mortais
                if not modo_imunidade_admin:
                    for spike, c_idx in espinhos_chao_rects:
                        if slime_hb.colliderect(spike): reset_game(f"Espinho do Chão (Coluna {c_idx})")
                    for spike_top, c_idx in espinhos_teto_rects:
                        if slime_hb.colliderect(spike_top): reset_game(f"Espinho do Teto (Coluna {c_idx})")
                    for lva, c_idx in lavas_rects:
                        if slime_hb.colliderect(lva): reset_game(f"Lava Quente (Coluna {c_idx})")

                # 6. Colisão Físicas de Pouso/Grave/Frontal com Blocos
                em_cima_de_bloco = False
                for block, c_idx, orig_y in blocos_rects:
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
                            elif slime.gravity < 0: # Gravidade Invertida
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

                # Checa a chegada no final da fase
                if slime.x >= fim_fase_x:
                    animando_vitoria = True
                    timer_anim_vitoria = 0

            # ------------------------------------------------------------------
            # D. PIPELINE DE RENDERIZAÇÃO GRÁFICA (Desenho das Camadas)
            # ------------------------------------------------------------------
            final_bg = (int(current_bg_color[0]), int(current_bg_color[1]), int(current_bg_color[2]))
            screen.fill(final_bg)

            # 1. Desenha o Fundo em Parallax
            desenhar_parallax_caverna(screen, distancia_percorrida)

            # Flash branco de impacto
            if bg_flash_alpha > 0:
                flash_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
                flash_surf.fill((255, 255, 255, int(bg_flash_alpha * 255)))
                screen.blit(flash_surf, (0, 0))

            # 2. Desenha o Chão e o Teto
            pygame.draw.rect(screen, COLOR_FLOOR, (0, FLOOR_Y, SCREEN_WIDTH, SCREEN_HEIGHT - FLOOR_Y))
            pygame.draw.rect(screen, COLOR_FLOOR, (0, 0, SCREEN_WIDTH, CEILING_Y))

            # 3. Desenha as Manchas de Gosma
            offset_camera = TARGET_X - distancia_percorrida
            for dec in decals: dec.draw(screen, offset_camera)

            # 4. Desenha a Lava com Ondas Animadas
            for lva, _ in lavas_rects:
                pygame.draw.rect(screen, COLOR_LAVA_BASE, lva)
                onda_offset = (global_frame_count * 2) % 20
                for lx in range(lva.x, lva.right, 20):
                    pygame.draw.line(screen, COLOR_LAVA_DETAIL, (lx - onda_offset, lva.y + 4), (lx + 10 - onda_offset, lva.y + 4), 2)
                if estado_jogo == "JOGANDO" and random.random() < 0.08:
                    particles.append(Particle(random.uniform(lva.x, lva.right), lva.y+5, (255, 120, 0), vel_x=-scroll_speed, vel_y=random.uniform(-3, -1), gravity=0.1, size=random.randint(2,4)))

            # 5. Desenha os Espinhos 3D
            for spike_rect, _ in espinhos_chao_rects: 
                desenhar_estalactite_obstaculo(screen, spike_rect, facing_down=False)
            for spike_top_rect, _ in espinhos_teto_rects: 
                desenhar_estalactite_obstaculo(screen, spike_top_rect, facing_down=True)

            # 6. Desenha os Blocos, Grama e Flores
            current_block_border = COLOR_BORDER_GOSMA
            if slime.modo == "CHICLETE": current_block_border = COLOR_BORDER_CHICLETE
            elif slime.modo == "NEVE": current_block_border = COLOR_BORDER_NEVE

            for block, col_idx, orig_y in blocos_rects:
                pygame.draw.rect(screen, COLOR_BLOCK, block)
                pygame.draw.rect(screen, current_block_border, block, 2) 
                pygame.draw.rect(screen, (30, 30, 35), (block.x + 10, block.y + 10, TILE_SIZE - 20, TILE_SIZE - 20))
                
                draw_pixel_grass(screen, block, block.x + distancia_percorrida)
                
                # 35% de chance de florzinhas decorativas fixas
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

            # 7. Desenha Trampolins com Brilho Pulsante no Ritmo da Música
            for pad in trampolins_rects: 
                pad_color = COLOR_PAD
                if beat_pulse > 0:
                    glow_pad = pygame.Surface((pad.width + 10, pad.height + 10), pygame.SRCALPHA)
                    glow_pad.fill((255, 255, 100, int(beat_pulse * 150)))
                    screen.blit(glow_pad, (pad.x - 5, pad.y - 5))
                    pad_color = (255, 255, 150)
                pygame.draw.rect(screen, pad_color, pad, border_radius=3)

            # 8. Desenha Orbes, Portais e Moedas
            for orb in orbes_rects:
                pygame.draw.circle(screen, COLOR_RING, orb.center, 14, 3)
                pygame.draw.circle(screen, (255, 255, 255), orb.center, 6)

            for portal_rect, tipo in portais:
                desenhar_portal(screen, portal_rect, tipo, global_frame_count, beat_pulse, particles)

            for coin_rect, _ in moedas:
                pygame.draw.circle(screen, COLOR_COIN, coin_rect.center, 14)
                pygame.draw.circle(screen, (255, 255, 200), coin_rect.center, 6)

            # 9. Desenha o Vórtice de Saída
            fim_x_tela = fim_fase_x_relativo + TARGET_X - distancia_percorrida
            if -150 < fim_x_tela < SCREEN_WIDTH + 150:
                vortex_center_x = fim_x_tela
                vortex_center_y = FLOOR_Y - 100
                
                if estado_jogo == "JOGANDO" and random.random() < 0.4:
                    ang = random.uniform(0, 2 * math.pi)
                    dist_spawn = random.uniform(70, 110)
                    sp_x = vortex_center_x + dist_spawn * math.cos(ang)
                    sp_y = vortex_center_y + dist_spawn * math.sin(ang)
                    particles.append(Particle(sp_x, sp_y, (240, 240, 255), target_x=vortex_center_x, target_y=vortex_center_y, size=random.randint(2, 4), lifespan=120, p_type="vortex_pull"))
                    
                desenhar_vortice_final(screen, vortex_center_x, vortex_center_y, global_frame_count, beat_pulse)

            # 10. Desenha as Partículas
            for p in particles: p.draw(screen)

            # 11. Desenha o Slime
            if estado_jogo in ("INTRO_RUN", "JOGANDO", "PAUSADO") and not morto_parado:
                if animando_vitoria:
                    s_factor = max(0.05, 1.0 - (timer_anim_vitoria / 60.0))
                    rot_angle = timer_anim_vitoria * 18.0
                    slime.draw(screen, scale=s_factor, angle=rot_angle)
                else:
                    slime.draw(screen)

            # 12. Caixas de Debug e Hitbox Verde (Ativada por Tecla G)
            if show_debug and estado_jogo != "MENU":
                pygame.draw.rect(screen, (0, 255, 0), slime_hb, 2)
                info_text = f"FPS: {dt_fps:.1f} | X: {slime.x:.1f} Y: {slime.y:.1f} | Modo: {slime.modo} | Imunidade [I]: {'ON' if modo_imunidade_admin else 'OFF'}"
                lbl_info = debug_font.render(info_text, True, (255, 255, 0) if modo_imunidade_admin else (255, 255, 255))
                pygame.draw.rect(screen, (0, 0, 0), (10, SCREEN_HEIGHT - 30, lbl_info.get_width() + 10, 22))
                screen.blit(lbl_info, (15, SCREEN_HEIGHT - 28))

            # 13. Exibe o Texto de "TENTATIVA X" na entrada
            if estado_jogo in ("INTRO_WAIT", "INTRO_RUN", "JOGANDO", "PAUSADO") and attempt_text_x > -300:
                txt_attempt = attempt_font.render(f"TENTATIVA {tentativas}", True, (255, 255, 255))
                screen.blit(txt_attempt, (int(attempt_text_x - txt_attempt.get_width() // 2), 260))

            # 14. Interface de Usuário (Barra de Progresso Porcentagem %)
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

            # 15. Painel de Morte e Atalhos de Testes Administrador
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

            # 16. Overlay do Menu Inicial
            if estado_jogo == "MENU":
                overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
                overlay.fill((10, 8, 20, 230))
                screen.blit(overlay, (0, 0))
                t1 = title_font.render("SLIME DASH", True, (50, 240, 100))
                t2 = font.render("Pressione ESPAÇO para Iniciar", True, (255, 255, 255))
                screen.blit(t1, (SCREEN_WIDTH // 2 - t1.get_width() // 2, 220))
                screen.blit(t2, (SCREEN_WIDTH // 2 - t2.get_width() // 2, 310))

            # 17. Overlay de Pausa
            elif estado_jogo == "PAUSADO":
                overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
                overlay.fill((0, 0, 0, 180))
                screen.blit(overlay, (0, 0))
                p1 = title_font.render("JOGO PAUSADO", True, (255, 215, 0))
                p2 = font.render("[ESPAÇO / P] Continuar  |  [R] Reiniciar  |  [M] Menu", True, (255, 255, 255))
                screen.blit(p1, (SCREEN_WIDTH // 2 - p1.get_width() // 2, 260))
                screen.blit(p2, (SCREEN_WIDTH // 2 - p2.get_width() // 2, 330))

            # 18. Overlay de Vitória (Fase Concluída)
            if vitoria:
                s = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
                s.fill((0, 0, 0, 180))
                screen.blit(s, (0, 0))
                txt_vic = title_font.render("LEVEL COMPLETE!", True, (50, 240, 100))
                txt_sub = font.render(f"Moedas: {moedas_coletadas}/3  |  Pressione ESPAÇO para Recomeçar", True, (255, 255, 255))
                screen.blit(txt_vic, (SCREEN_WIDTH // 2 - txt_vic.get_width() // 2, 280))
                screen.blit(txt_sub, (SCREEN_WIDTH // 2 - txt_sub.get_width() // 2, 350))

            # Atualiza o buffer da tela e segura o laço em 60 FPS
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