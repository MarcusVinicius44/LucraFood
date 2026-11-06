"""Limitador de tokens de SAÍDA por minuto. Sem IA, sem Django.

O Groq limita (na conta gratuita) ~1000 tokens de saída por minuto. Para ler um cardápio em
faixas sem tomar 429, antes de cada chamada esperamos até que:

    tokens gastos na última janela + teto da próxima chamada (max_tokens) <= limite

É conservador de propósito: reserva o teto inteiro, não o que a resposta provavelmente gastará.
"""
import time
from collections import deque


class LimitadorSaida:
    def __init__(self, limite=1000, janela=60.0, relogio=time.monotonic, esperar=time.sleep, ao_esperar=None):
        self.limite = limite
        self.janela = janela
        self._relogio = relogio
        self._esperar = esperar
        self._ao_esperar = ao_esperar  # callback(segundos) só para avisar o usuário
        self._eventos = deque()  # (instante, tokens)

    def _purgar(self, agora):
        while self._eventos and agora - self._eventos[0][0] >= self.janela:
            self._eventos.popleft()

    def aguardar(self, reserva: int) -> float:
        """Bloqueia até caber `reserva` tokens no orçamento. Devolve quantos segundos esperou."""
        if reserva > self.limite:
            raise ValueError(f"max_tokens ({reserva}) maior que o limite por minuto ({self.limite})")
        esperado = 0.0
        while True:
            agora = self._relogio()
            self._purgar(agora)
            if sum(t for _, t in self._eventos) + reserva <= self.limite:
                return esperado
            segundos = self._eventos[0][0] + self.janela - agora + 0.1
            if self._ao_esperar:
                self._ao_esperar(segundos)
            self._esperar(segundos)
            esperado += segundos

    def registrar(self, tokens: int) -> None:
        self._eventos.append((self._relogio(), tokens))
