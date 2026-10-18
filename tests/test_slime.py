import unittest
import os
import sys

# Configura drivers dummy para execução headless no terminal
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import pygame
from src.main import Slime, SoundManager, Particle
from src.levels import obter_configuracao_nivel, NIVEIS


class TestSlimeDashEngine(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        pygame.init()

    def setUp(self):
        self.slime = Slime(x=240.0, y=600.0)
        self.sound_mgr = SoundManager()

    # --- TESTES ATUAIS ---
    def test_carregamento_modulo_niveis(self):
        """[CTFL: Teste Funcional] Garante que o gerenciador de níveis retorna a estrutura correta"""
        config = obter_configuracao_nivel(1)
        self.assertIn("nome", config)
        self.assertIn("bpm", config)
        self.assertIn("fase", config)
        self.assertGreater(len(config["fase"]), 0, "A string da fase não pode estar vazia")

    def test_transicao_estado_portal_chiclete(self):
        """[CTFL: Transição de Estado] Garante que o Portal Chiclete altera a gravidade"""
        self.slime.mudar_modo("CHICLETE")
        self.assertEqual(self.slime.modo, "CHICLETE")
        self.assertEqual(self.slime.gravity, 0.45)

    def test_transicao_estado_portal_neve(self):
        """[CTFL: Transição de Estado] Garante que o Portal Neve inverte a gravidade"""
        self.slime.mudar_modo("NEVE")
        self.assertEqual(self.slime.modo, "NEVE")
        self.assertLess(self.slime.gravity, 0)

    def test_jump_buffering(self):
        """[CTFL: Teste de Usabilidade] Garante que solicitar pulo ativa o buffer de entrada"""
        self.slime.solicitar_pulo()
        self.assertEqual(
            self.slime.jump_buffer,
            8,
            "O buffer de pulo deve ser preenchido com 8 frames",
        )

    def test_robustez_sound_manager(self):
        """[CTFL: Teste de Robustez] Garante que o SoundManager responde sem lançar exceções"""
        self.assertIsNotNone(self.sound_mgr)
        self.sound_mgr.tocar(self.sound_mgr.sfx_jump)

    # --- NOVOS TESTES PARA COBERTURA COMPLETA (QA / CTFL) ---

    def test_hitbox_perdoavel(self):
        """[CTFL: Limite de Fronteira] Garante que a Hitbox e menor que o retangulo grafico"""
        hitbox = self.slime.get_hitbox()
        self.assertLess(hitbox.width, self.slime.rect.width)
        self.assertLess(hitbox.height, self.slime.rect.height)

    def test_pouso_no_solo(self):
        """[CTFL: Teste de Física] Garante que ao tocar o chão a velocidade e zerada e o chão e detectado"""
        self.slime.vel_y = 10.0
        self.slime.is_grounded = False
        
        # Simula atualização tocando o chão (FLOOR_Y = 600.0)
        self.slime.update(floor_y=600, ceiling_y=100, particles=[])
        
        self.assertEqual(self.slime.y, 600.0)
        self.assertEqual(self.slime.vel_y, 0.0)
        self.assertTrue(self.slime.is_grounded)

    def test_decaimento_de_particulas(self):
        """[CTFL: Teste de Ciclo de Vida] Garante que as partículas diminuem de tamanho até sumir"""
        p = Particle(x=240, y=600, color=(50, 240, 100))
        raio_inicial = p.radius
        p.update()
        self.assertLess(p.radius, raio_inicial)

    def test_colisao_com_espinho(self):
        """[CTFL: Regra de Negocio] Testa sobreposicao do Slime com o retangulo de espinho"""
        espinho_rect = pygame.Rect(230, 560, 30, 40)
        slime_hb = self.slime.get_hitbox()
        self.assertTrue(slime_hb.colliderect(espinho_rect))


if __name__ == "__main__":
    unittest.main()