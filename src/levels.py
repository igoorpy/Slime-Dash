"""
Módulo de Gerenciamento e Definição das Fases do Slime Dash.
Gerado pelo Editor 2D.
"""
VELOCIDADE_JOGO = 6.0
FPS_JOGO = 60
DURACAO_MUSICA_SEGUNDOS = 65.0
TILE_SIZE = 50
COLUNAS_TOTAL = int((VELOCIDADE_JOGO * FPS_JOGO * DURACAO_MUSICA_SEGUNDOS) / TILE_SIZE)

NIVEIS = {
    1: {
        "nome": "1. Origem da Gosma",
        "bpm": 122,
        "cor_tema": (50, 240, 100),
        "fase": ['        ^      ^        ^^1~~1~~1          ^     1111111~~~11111111~~111111111~~~~~~~~~~~~~~~1111111111111111111111111111~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~11111111      1             1^^^^^^^^1         1 1 1 1  1  1  1  1   11111111111111~~1~~1~~1~~1~~11111~~1~~1~~1~~1~~1~~1~~~~~~~~~~~~~~~~~~~~~1     ^^11~~~~~111~~~~~~~111^^      ^^    * ^^      ^     ^     ^1~~1~~1~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~1111111111~~~~~~~~~~~~~~~~~111111111111111                  ', '                             1  1                              ^     111111111               1111111111111111111111111111                                          11111111      1                                1 1 1       1  1  1    1111111111111  1  1  1     11111  1  1  1  1  1  1                  hhh^           hh     hh                                               1  1     h  hhh^                    1111111111                 1111111111111                    ', '                                1                                         ^     h            1111111111111111111111111111                                          11111111      1                                1 1            1  1     111111           1  1               1  1  1  1  1             hhh^                          hh                                               1   h         hhh^              111     111              ^11111111111111                     ', '                                                                                   h         11111111111111111111111111111111                                  111111111111                                       1                 1                         1  1    O          1  1  1  1       hhhh^                                                                                  h                 h                1       h        hh                                     ', '                                                                                      h      1111111111111111111111^           hh                                          C                                                                   G                 1                  1  1  1     h                                                   vv              v     v                                   h     hh      ^          h                                            ', '                                                                                         h  11111111111       11111                h                 hhh^                  C                                               1                   G                    1                  1  1   h                                                     hh              h     h                                      h                        h                                         ', '                                                                                                 ^^      111      ^                   h        hhh^       h         1111111                                 1              1                                                              1 h                                                               vv                                                          1111111                    11111111111                      ', '                                                                                                 hh      ^^^                             h                   h      1111111              1                  1 1         1  1              111111                                                                                                            hh                                                          1111111                    1111111111111                    ', '                                                                                                                                            h                   1   1111111              1                  1 1 1    1  1  1             1111111                    vvv                                                                                                                                                 1111111                   111111111111111                   ', '                                                                                                                                                                ^   1111111              1     1vvvvvvvv1   1 1 1 1  1  1  1            11111111                    111                                                                                                                                                 111111111111111111111111111111111111111111                  '],
    },
    2: {
        "nome": "2. Céu Doce",
        "bpm": 128,
        "cor_tema": (255, 105, 180),
        "fase": [" " * COLUNAS_TOTAL for _ in range(10)],
    },
    3: {
        "nome": "3. Pico Congelado",
        "bpm": 130,
        "cor_tema": (135, 206, 250),
        "fase": [" " * COLUNAS_TOTAL for _ in range(10)],
    },
}
def obter_configuracao_nivel(id_nivel: int) -> dict:
    return NIVEIS.get(id_nivel, NIVEIS[1])
