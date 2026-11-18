# Atualização das perguntas e dificuldade — GeoMaster

## O que mudou

- Banco ampliado de 1.550 para 2.132 perguntas.
- Foram acrescentadas 582 perguntas curtas de folclore, cultura e lendas, vinculadas ao país correspondente.
- As novas perguntas usam apenas criaturas/elementos cujos registros não estão marcados como inventados nos dados do jogo.
- As alternativas misturam nomes de outras tradições para evitar respostas óbvias.
- O Modo História passou a priorizar perguntas do país atual (78% de chance quando há perguntas disponíveis), depois da região e, por fim, do banco mundial.
- A dificuldade considera a fase local e o avanço geral: fases iniciais favorecem perguntas fáceis; fases intermediárias, médias; fases finais e chefes, difíceis.
- A seleção continua evitando repetir perguntas dentro do mesmo combate.

## Cobertura cultural

As 582 novas perguntas cobrem 137 países para os quais o projeto já possui registros de folclore não marcados como inventados. Nos demais países, o jogo continua usando as perguntas já existentes (capitais, localização, fronteiras, moedas e geografia). Não foram criadas curiosidades culturais fictícias para preencher lacunas.

## Arquivos alterados

- `data/questions.json`
- `data/question-countries.json`
- `story/combat.py`
- `story/tests/test_combat.py`

## Validação

- JSON das perguntas e do vínculo pergunta-país validado.
- IDs sem duplicação e alternativas corretas verificadas.
- 56 testes de combate, mapa, progresso e salvamento passaram.
- Testes de interface e viajante não foram executados neste ambiente porque dependem de Pygame.
