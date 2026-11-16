# Relatório da Etapa 6 — Banco de perguntas (atualizado)

- Total: 1.550
- Múltipla escolha: 758
- Mapa: 242
- Bandeiras: 550
- IDs únicos: 1.550
- Enunciados únicos por tipo: 1.550
- Alvos de mapa presentes no GeoJSON: 242
- Questões de bandeira com código ISO de bandeira: 550

## Dificuldades

- Fácil: 386 (166 antigas + 220 bandeiras)
- Média: 560 (340 antigas + 220 bandeiras)
- Difícil: 604 (494 antigas + 110 bandeiras)

## Categorias

- Cultura: 200
- Fronteiras: 156
- Continentes: 202
- Capitais: 200
- Localização: 242
- Bandeiras: 550

## Mecânica de bandeiras

- Cada desafio exibe a bandeira sem revelar o país.
- O jogador escolhe entre quatro nomes de países.
- A resposta é corrigida pelo motor de pontuação existente.
- A imagem é carregada pelo código ISO de duas letras usando FlagCDN.
- Países sem código de bandeira reconhecido no conjunto de dados (ex.: territórios sem bandeira padronizada) não foram usados como alvos.

## Composição das partidas

- 3 perguntas de múltipla escolha.
- 3 desafios no mapa.
- 4 desafios de bandeiras.
- 10 perguntas por partida; 30 segundos por pergunta.
- Pontuação preservada: fácil 10, média 20, difícil 30.

## Particionamento

- Banco original: questions-part-01.json a questions-part-05.json (200 cada).
- Novos desafios: questions-part-06.json (200), questions-part-07.json (200), questions-part-08.json (150).
- Banco oficial consolidado: data/questions.json.

## Verificações estruturais

- [x] 1.550 perguntas no arquivo consolidado
- [x] IDs únicos
- [x] Enunciados únicos por tipo
- [x] 4 alternativas distintas em cada pergunta de bandeira
- [x] correctIndex válido
- [x] flagCode ISO de duas letras em cada desafio de bandeira
- [x] Tipos de questão integrados ao motor, pontuação e interface
- [ ] Auditoria editorial independente de cada bandeira e alternativa — recomendada antes da publicação
