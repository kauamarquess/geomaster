# Skin do viajante

Um explorador de chapéu de aba larga, cachecol vermelho, túnica azul-esverdeada e cajado, em pixel art 16x20
(`story/viajante-preview.png` mostra todos os quadros; `python story/tools/preview_traveler.py` gera de novo).

## Quadros
parado e respirando (animação), andando 1 e 2, acertou (comemora), errou (leva o golpe), derrotado, e uma
versão minúscula (9x10) para os mapas.

## Onde aparece
- **Menu:** em tamanho grande, ao lado das opções, respirando.
- **Mapa-múndi e continente:** a versão minúscula, em pé no país onde a aventura está (sobe e desce de leve).
- **País:** em pé sobre a próxima fase a vencer.
- **Combate:** retrato ao lado de "Você": respira enquanto você pensa, comemora o acerto, sente o golpe no erro
  ou no tempo esgotado e fica abatido na derrota.

## Como mudar o visual
Tudo está em `story/traveler.py`: as cores em `PALETTE` (por letra) e o desenho em texto (`HAT`, `FACES`, `BODY`,
`LEGS`, `MINI`). Cada letra é uma cor, "." é transparente. `python -m unittest discover -s story/tests` confere
se alguma linha ficou com tamanho errado.
