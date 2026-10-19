import sys
import os
import random
import pygame

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(BASE_DIR)

try:
    from src.levels import NIVEIS, DURACAO_MUSICA_SEGUNDOS, obter_configuracao_nivel
except (ModuleNotFoundError, ImportError):
    from levels import NIVEIS, DURACAO_MUSICA_SEGUNDOS, obter_configuracao_nivel

SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
FPS = 60

TILE_SIZE = 50
NUM_ROWS = 10
FLOOR_Y = 600
CEILING_Y = FLOOR_Y - (NUM_ROWS * TILE_SIZE)  # 100px

TARGET_X = 240.0
VELOCIDADE_JOGO = 6.0
FPS_JOGO = 60

COLUNAS_TOTAL = int((VELOCIDADE_JOGO * FPS_JOGO * DURACAO_MUSICA_SEGUNDOS) / TILE_SIZE)

COLOR_BG = (20, 18, 30)
COLOR_GRID = (45, 40, 65)
COLOR_FLOOR = (40, 30, 60)
COLOR_TEXT = (255, 255, 255)
COLOR_GUIDE = (50, 240, 100)

COLOR_BLOCK = (80, 70, 110)
COLOR_SPIKE = (230, 50, 50)
COLOR_LAVA = (255, 80, 0)
COLOR_PAD = (255, 230, 0)
COLOR_RING = (255, 200, 0)
COLOR_COIN = (255, 215, 0)
COLOR_SLIME_GOSMA = (50, 240, 100)
COLOR_SLIME_CHICLETE = (255, 105, 180)
COLOR_SLIME_NEVE = (135, 206, 250)

PALETES = [
    (" ", "DEL: Apagar", (30, 30, 40)),
    ("1", "1: Bloco", COLOR_BLOCK),
    ("h", "2: Meio Bloco", (120, 110, 150)),
    ("^", "3: Esp. Chão", COLOR_SPIKE),
    ("v", "4: Esp. Teto", (200, 30, 30)),
    ("~", "5: Lava", COLOR_LAVA),
    ("*", "6: Trampolim", COLOR_PAD),
    ("@", "7: Orbe Ar", COLOR_RING),
    ("C", "8: P. Chiclete", COLOR_SLIME_CHICLETE),
    ("N", "9: P. Neve", COLOR_SLIME_NEVE),
    ("G", "0: P. Gosma", COLOR_SLIME_GOSMA),
    ("O", "M: Moeda", COLOR_COIN),
    ("E", "F: Fim", (50, 255, 150)),
]

def salvar_levels_py(fase1_linhas):
    caminho_levels = os.path.join(BASE_DIR, "src", "levels.py")
    if not os.path.exists(os.path.dirname(caminho_levels)):
        caminho_levels = "levels.py"

    conteudo = f'''"""
Módulo de Gerenciamento e Definição das Fases do Slime Dash.
Gerado pelo Editor 2D.
"""
VELOCIDADE_JOGO = 6.0
FPS_JOGO = 60
DURACAO_MUSICA_SEGUNDOS = {DURACAO_MUSICA_SEGUNDOS}
TILE_SIZE = 50
COLUNAS_TOTAL = int((VELOCIDADE_JOGO * FPS_JOGO * DURACAO_MUSICA_SEGUNDOS) / TILE_SIZE)

NIVEIS = {{
    1: {{
        "nome": "1. Origem da Gosma",
        "bpm": 122,
        "cor_tema": (50, 240, 100),
        "fase": {fase1_linhas},
    }},
    2: {{
        "nome": "2. Céu Doce",
        "bpm": 128,
        "cor_tema": (255, 105, 180),
        "fase": [" " * COLUNAS_TOTAL for _ in range(10)],
    }},
    3: {{
        "nome": "3. Pico Congelado",
        "bpm": 130,
        "cor_tema": (135, 206, 250),
        "fase": [" " * COLUNAS_TOTAL for _ in range(10)],
    }},
}}
def obter_configuracao_nivel(id_nivel: int) -> dict:
    return NIVEIS.get(id_nivel, NIVEIS[1])
'''
    with open(caminho_levels, "w", encoding="utf-8") as f:
        f.write(conteudo)

class EditorSlime:
    def __init__(self, x: float, y: float):
        self.base_size = 40
        self.x = float(x)
        self.y = float(y)
        self.vel_y = 0.0

        self.gravity = 1.15
        self.jump_strength = -16.5

        self.is_grounded = False
        self.jump_buffer = 0
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
            38
        )

    def solicitar_pulo(self):
        self.jump_buffer = 8

    def tentar_pular(self):
        if self.jump_buffer > 0 and self.is_grounded:
            self.vel_y = self.jump_strength
            self.is_grounded = False
            self.jump_buffer = 0
            self.current_width, self.current_height = 26.0, 54.0

    def update(self, floor_y: int, space_held: bool):
        if self.jump_buffer > 0: self.jump_buffer -= 1
        if space_held: self.jump_buffer = 6

        self.tentar_pular()

        if not self.is_grounded:
            self.vel_y += self.gravity
            self.y += self.vel_y

        if self.y >= floor_y:
            self.y = float(floor_y)
            self.vel_y = 0.0
            self.is_grounded = True
            self.current_width, self.current_height = 54.0, 26.0
            self.tentar_pular()

        self.current_width += (self.base_size - self.current_width) * 0.2
        self.current_height += (self.base_size - self.current_height) * 0.2
        self.update_rect()

    def draw(self, surface: pygame.Surface, alpha: int = 255):
        s = pygame.Surface((int(self.current_width), int(self.current_height)), pygame.SRCALPHA)
        pygame.draw.ellipse(s, (50, 240, 100, alpha), s.get_rect())
        eye_y = (self.current_height / 2.0) - 3
        pygame.draw.circle(s, (255, 255, 255, alpha), (int(self.current_width / 2.0 - 5), int(eye_y)), 4)
        pygame.draw.circle(s, (255, 255, 255, alpha), (int(self.current_width / 2.0 + 5), int(eye_y)), 4)
        pygame.draw.circle(s, (10, 10, 20, alpha), (int(self.current_width / 2.0 - 5), int(eye_y)), 2)
        pygame.draw.circle(s, (10, 10, 20, alpha), (int(self.current_width / 2.0 + 5), int(eye_y)), 2)
        surface.blit(s, (int(self.x - self.current_width / 2.0), int(self.y - self.current_height)))

def carregar_musica_robusta():
    try:
        pygame.mixer.init()
        caminho_abs = os.path.join(BASE_DIR, "assets", "sounds", "fase1.mp3")
        caminho_rel = "assets/sounds/fase1.mp3"

        if os.path.exists(caminho_abs):
            pygame.mixer.music.load(caminho_abs)
        elif os.path.exists(caminho_rel):
            pygame.mixer.music.load(caminho_rel)
        pygame.mixer.music.set_volume(0.5)
    except Exception:
        pass

def main():
    pygame.init()
    carregar_musica_robusta()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Slime Dash - Editor 2D (Porcentagem no Topo)")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("Consolas", 14, bold=True)
    pct_font = pygame.font.SysFont("Consolas", 18, bold=True)

    fase_config = obter_configuracao_nivel(1)
    grid = []

    if isinstance(fase_config["fase"], (list, tuple)):
        for r in range(NUM_ROWS):
            if r < len(fase_config["fase"]):
                linha_list = list(fase_config["fase"][r].ljust(COLUNAS_TOTAL))
                grid.append(linha_list[:COLUNAS_TOTAL])
            else:
                grid.append(list(" " * COLUNAS_TOTAL))
    else:
        l0 = list(str(fase_config["fase"]).ljust(COLUNAS_TOTAL))
        grid.append(l0[:COLUNAS_TOTAL])
        for _ in range(1, NUM_ROWS):
            grid.append(list(" " * COLUNAS_TOTAL))

    camera_x = 0
    item_selecionado = "1"
    mensagem_status = "[S] Salvar no Arquivo | [P/ENTER] Playtest | [A/D / Setas] Rolar Mapa"
    timer_status = 0

    modo_teste = False
    teste_camera_inicial = 0
    teste_distancia = 0.0
    test_slime = EditorSlime(x=TARGET_X, y=FLOOR_Y)

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.MOUSEBUTTONDOWN:
                if not modo_teste:
                    mx, my = event.pos
                    if 10 <= my <= 40:
                        x_ui = 10
                        for char, nome, cor in PALETES:
                            if x_ui <= mx <= x_ui + 85:
                                item_selecionado = char
                                break
                            x_ui += 92

                    if event.button == 4: camera_x = max(0, camera_x - TILE_SIZE * 3)
                    elif event.button == 5: camera_x = min((COLUNAS_TOTAL * TILE_SIZE) - SCREEN_WIDTH, camera_x + TILE_SIZE * 3)

            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_p, pygame.K_RETURN):
                    modo_teste = not modo_teste
                    if modo_teste:
                        teste_camera_inicial = camera_x
                        teste_distancia = 0.0
                        test_slime = EditorSlime(x=TARGET_X, y=FLOOR_Y)
                        test_slime.jump_buffer = 0
                        mensagem_status = "PLAYTEST ATIVO | [ESPAÇO] Pular | [P/ENTER] Sair"
                        try:
                            pygame.mixer.music.rewind()
                            pygame.mixer.music.play(-1)
                        except: pass
                    else:
                        camera_x = teste_camera_inicial
                        mensagem_status = "MODO EDIÇÃO RETORNADO"
                        timer_status = 60
                        try: pygame.mixer.music.stop()
                        except: pass

                if not modo_teste:
                    if event.key == pygame.K_s:
                        fase_formatada = ["".join(linha) for linha in grid]
                        salvar_levels_py(fase_formatada)
                        mensagem_status = "FASE SALVA COM SUCESSO EM SRC/LEVELS.PY!"
                        timer_status = 120
                    elif event.key == pygame.K_1: item_selecionado = "1"
                    elif event.key == pygame.K_2: item_selecionado = "h"
                    elif event.key == pygame.K_3: item_selecionado = "^"
                    elif event.key == pygame.K_4: item_selecionado = "v"
                    elif event.key == pygame.K_5: item_selecionado = "~"
                    elif event.key == pygame.K_6: item_selecionado = "*"
                    elif event.key == pygame.K_7: item_selecionado = "@"
                    elif event.key == pygame.K_8: item_selecionado = "C"
                    elif event.key == pygame.K_9: item_selecionado = "N"
                    elif event.key == pygame.K_0: item_selecionado = "G"
                    elif event.key == pygame.K_m: item_selecionado = "O"
                    elif event.key == pygame.K_f: item_selecionado = "E"
                    elif event.key in (pygame.K_DELETE, pygame.K_BACKSPACE): item_selecionado = " "

                else:
                    if event.key == pygame.K_SPACE:
                        test_slime.solicitar_pulo()

        keys = pygame.key.get_pressed()
        space_held = keys[pygame.K_SPACE] if modo_teste else False

        if modo_teste:
            teste_distancia += VELOCIDADE_JOGO
            curr_camera = teste_camera_inicial + teste_distancia
            test_slime.update(FLOOR_Y, space_held)

            slime_hb = test_slime.get_hitbox()
            start_col = int(curr_camera // TILE_SIZE)
            end_col = int((curr_camera + SCREEN_WIDTH) // TILE_SIZE) + 1

            for c in range(start_col, min(end_col, COLUNAS_TOTAL)):
                for r in range(NUM_ROWS):
                    char = grid[r][c]
                    if char == " ": continue
                    y_pos = FLOOR_Y - ((r + 1) * TILE_SIZE)
                    obj_x = (c * TILE_SIZE) - curr_camera + TARGET_X
                    obj_rect = pygame.Rect(obj_x, y_pos, TILE_SIZE, TILE_SIZE)

                    if char in ("1", "h"):
                        b_rect = obj_rect if char == "1" else pygame.Rect(obj_x, y_pos + TILE_SIZE // 2, TILE_SIZE, TILE_SIZE // 2)
                        if slime_hb.colliderect(b_rect):
                            if test_slime.vel_y >= 0 and (test_slime.y - max(0.0, test_slime.vel_y)) <= b_rect.top + 14:
                                test_slime.y = float(b_rect.top)
                                test_slime.vel_y = 0.0
                                test_slime.is_grounded = True
                                test_slime.tentar_pular()
                            else:
                                teste_distancia = 0.0
                                test_slime = EditorSlime(x=TARGET_X, y=FLOOR_Y)
                                test_slime.jump_buffer = 0

                    elif char in ("^", "v"):
                        spk = pygame.Rect(obj_x + 14, y_pos + 18, TILE_SIZE - 28, TILE_SIZE - 18) if char == "^" else pygame.Rect(obj_x + 14, y_pos, TILE_SIZE - 28, TILE_SIZE - 18)
                        if slime_hb.colliderect(spk):
                            teste_distancia = 0.0
                            test_slime = EditorSlime(x=TARGET_X, y=FLOOR_Y)
                            test_slime.jump_buffer = 0
                    elif char == "~":
                        lva = pygame.Rect(obj_x, y_pos + TILE_SIZE - 14, TILE_SIZE, 14)
                        if slime_hb.colliderect(lva):
                            teste_distancia = 0.0
                            test_slime = EditorSlime(x=TARGET_X, y=FLOOR_Y)
                            test_slime.jump_buffer = 0

        else:
            if keys[pygame.K_RIGHT] or keys[pygame.K_d]: camera_x += 18
            if keys[pygame.K_LEFT] or keys[pygame.K_a]: camera_x -= 18
            
            max_cam = max(0, (COLUNAS_TOTAL * TILE_SIZE) - SCREEN_WIDTH)
            camera_x = max(0, min(camera_x, max_cam))

            mouse_press = pygame.mouse.get_pressed()
            if mouse_press[0] or mouse_press[2]:
                mx, my = pygame.mouse.get_pos()
                if my >= CEILING_Y and my < FLOOR_Y:
                    col_idx = int((mx + camera_x) // TILE_SIZE)
                    row_idx = int((FLOOR_Y - 1 - my) // TILE_SIZE)
                    if 0 <= col_idx < COLUNAS_TOTAL and 0 <= row_idx < NUM_ROWS:
                        caractere = " " if mouse_press[2] else item_selecionado
                        grid[row_idx][col_idx] = caractere

        screen.fill(COLOR_BG)
        pygame.draw.rect(screen, COLOR_FLOOR, (0, FLOOR_Y, SCREEN_WIDTH, SCREEN_HEIGHT - FLOOR_Y))
        pygame.draw.rect(screen, COLOR_FLOOR, (0, 0, SCREEN_WIDTH, CEILING_Y))

        view_cam = teste_camera_inicial + teste_distancia if modo_teste else camera_x
        start_col = int(view_cam // TILE_SIZE)
        end_col = int((view_cam + SCREEN_WIDTH) // TILE_SIZE) + 1

        for c in range(start_col, min(end_col, COLUNAS_TOTAL)):
            x_pos = int((c * TILE_SIZE) - view_cam)
            pygame.draw.line(screen, COLOR_GRID, (x_pos, CEILING_Y), (x_pos, FLOOR_Y), 1)

            for r in range(NUM_ROWS):
                y_pos = FLOOR_Y - ((r + 1) * TILE_SIZE)
                if c == start_col:
                    pygame.draw.line(screen, COLOR_GRID, (0, y_pos), (SCREEN_WIDTH, y_pos), 1)

                char = grid[r][c]
                if char != " ":
                    if char == "1":
                        pygame.draw.rect(screen, COLOR_BLOCK, (x_pos, y_pos, TILE_SIZE, TILE_SIZE))
                        pygame.draw.rect(screen, (150, 140, 180), (x_pos, y_pos, TILE_SIZE, TILE_SIZE), 2)
                    elif char == "h":
                        pygame.draw.rect(screen, COLOR_BLOCK, (x_pos, y_pos + TILE_SIZE // 2, TILE_SIZE, TILE_SIZE // 2))
                        pygame.draw.rect(screen, (150, 140, 180), (x_pos, y_pos + TILE_SIZE // 2, TILE_SIZE, TILE_SIZE // 2), 2)
                    elif char == "^":
                        pygame.draw.polygon(screen, COLOR_SPIKE, [(x_pos, y_pos + TILE_SIZE), (x_pos + TILE_SIZE // 2, y_pos), (x_pos + TILE_SIZE, y_pos + TILE_SIZE)])
                    elif char == "v":
                        pygame.draw.polygon(screen, COLOR_SPIKE, [(x_pos, y_pos), (x_pos + TILE_SIZE // 2, y_pos + TILE_SIZE), (x_pos + TILE_SIZE, y_pos)])
                    elif char == "~":
                        pygame.draw.rect(screen, COLOR_LAVA, (x_pos, y_pos + TILE_SIZE - 14, TILE_SIZE, 14))
                    elif char == "*":
                        pygame.draw.rect(screen, COLOR_PAD, (x_pos + 6, y_pos + TILE_SIZE - 12, TILE_SIZE - 12, 12), border_radius=3)
                    elif char == "@":
                        pygame.draw.circle(screen, COLOR_RING, (x_pos + TILE_SIZE // 2, y_pos + TILE_SIZE // 2), 14, 3)
                    elif char in ("C", "N", "G"):
                        p_c = COLOR_SLIME_CHICLETE if char == "C" else (COLOR_SLIME_NEVE if char == "N" else COLOR_SLIME_GOSMA)
                        pygame.draw.rect(screen, p_c, (x_pos + 8, y_pos, TILE_SIZE - 16, TILE_SIZE), 4)
                    elif char == "O":
                        pygame.draw.circle(screen, COLOR_COIN, (x_pos + TILE_SIZE // 2, y_pos + TILE_SIZE // 2), 14)
                    elif char == "E":
                        pygame.draw.rect(screen, (50, 255, 150), (x_pos + 8, y_pos, 4, TILE_SIZE))

        # LINHAS DE INÍCIO E FIM
        start_x_screen = int(0 - view_cam)
        if -50 <= start_x_screen <= SCREEN_WIDTH + 50:
            pygame.draw.rect(screen, (50, 240, 100), (start_x_screen, CEILING_Y, 6, FLOOR_Y - CEILING_Y))
            txt_start = font.render("INÍCIO (0%)", True, (50, 240, 100))
            screen.blit(txt_start, (start_x_screen + 10, CEILING_Y + 10))

        end_x_screen = int((COLUNAS_TOTAL * TILE_SIZE) - view_cam)
        if -50 <= end_x_screen <= SCREEN_WIDTH + 50:
            pygame.draw.rect(screen, (230, 50, 50), (end_x_screen - 6, CEILING_Y, 6, FLOOR_Y - CEILING_Y))
            txt_end = font.render(f"FIM DA MÚSICA (100% - {COLUNAS_TOTAL} cols)", True, (230, 50, 50))
            screen.blit(txt_end, (end_x_screen - txt_end.get_width() - 10, CEILING_Y + 10))

        if modo_teste:
            test_slime.draw(screen, alpha=255)
        else:
            pygame.draw.line(screen, COLOR_GUIDE, (int(TARGET_X), CEILING_Y), (int(TARGET_X), FLOOR_Y), 2)
            preview_slime = EditorSlime(x=TARGET_X, y=FLOOR_Y)
            preview_slime.draw(screen, alpha=160)

        # TOPO: PALETA DE FERRAMENTAS
        pygame.draw.rect(screen, (10, 8, 20), (0, 0, SCREEN_WIDTH, 50))
        x_ui = 10
        for char, nome, cor in PALETES:
            borda = 3 if item_selecionado == char else 1
            pygame.draw.rect(screen, cor, (x_ui, 10, 85, 30), border_radius=4)
            pygame.draw.rect(screen, (255, 255, 255), (x_ui, 10, 85, 30), borda, border_radius=4)
            txt_p = font.render(nome, True, (0, 0, 0) if sum(cor) > 400 else (255, 255, 255))
            screen.blit(txt_p, (x_ui + 4, 18))
            x_ui += 92

        # ---------------------------------------------------------------------
        # BANNER DE PORCENTAGEM NO TOPO CENTRALIZADO (EM CIMA NO MEIO)
        # ---------------------------------------------------------------------
        col_atual = int((view_cam + TARGET_X) // TILE_SIZE)
        tempo_segundo = int(col_atual / 7.2)
        pct_nivel = min(100, max(0, int((col_atual / COLUNAS_TOTAL) * 100)))

        txt_pct = pct_font.render(f" PROGRESSO: {pct_nivel}% ({tempo_segundo}s / 65s) ", True, (255, 255, 0))
        bg_pct_rect = pygame.Rect(SCREEN_WIDTH // 2 - 160, 55, 320, 28)
        pygame.draw.rect(screen, (10, 8, 25), bg_pct_rect, border_radius=6)
        pygame.draw.rect(screen, (50, 240, 100), bg_pct_rect, 2, border_radius=6)
        screen.blit(txt_pct, (SCREEN_WIDTH // 2 - txt_pct.get_width() // 2, 58))

        if timer_status > 0: timer_status -= 1

        txt_st = font.render(f"Coluna {col_atual}/{COLUNAS_TOTAL} | {mensagem_status}", True, (50, 240, 100) if timer_status > 0 else COLOR_TEXT)
        screen.blit(txt_st, (10, SCREEN_HEIGHT - 25))

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()