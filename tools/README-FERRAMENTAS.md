# Ferramentas Python do GeoMaster (bastidores)

Estas ferramentas **não fazem parte do jogo** — o GeoMaster continua 100% em HTML, CSS e
JavaScript e nada do site muda. Elas servem para **conferir, medir e montar o banco de
perguntas** antes de publicar. Só precisam do Python 3.10 ou mais novo (nada para instalar).

## Como usar

Abra o terminal na pasta principal do projeto (onde está o `index.html`) e rode:

```bash
python tools/geomaster.py validate   # confere o banco inteiro
python tools/geomaster.py stats      # mostra números e equilíbrio do banco
python tools/geomaster.py merge      # junta as partes questions-part-*.json
python -m unittest discover -s tools/tests -v   # testa as próprias ferramentas
```

No Windows, se `python` não funcionar, tente `py` no lugar.

### `validate`
Roda 7 verificações no `data/questions.json`:

| Verificação | O que confere |
|---|---|
| estrutura | campos obrigatórios e regras de cada tipo (as mesmas do `js/core/questions.js`) |
| ids repetidos | dois itens com o mesmo id |
| enunciados repetidos | mesma pergunta escrita duas vezes (ignora acentos e maiúsculas) |
| alvos do mapa | todo desafio de mapa aponta para um país que existe no GeoJSON |
| bandeiras | a alternativa correta é o país da bandeira; mesma bandeira + mesmas 4 alternativas = repetida |
| explicações | toda pergunta tem explicação para o feedback |
| posição da resposta | a resposta certa não fica sempre na mesma alternativa |

**Erro** = precisa corrigir (o comando termina com código 1). **Aviso** = funciona, mas vale olhar.
Use `--strict` para que avisos também façam o comando falhar, e `--bank arquivo.json` para
conferir outro arquivo (por exemplo `data/questions.dev.json`).

### `stats`
Mostra perguntas por tipo, dificuldade e categoria, a posição da resposta certa e quantas
**partidas dá para jogar sem repetir pergunta** (hoje o limite é o mapa: 242 ÷ 3 = 80 partidas).

### `merge`
Junta todos os `data/questions-part-*.json`, valida, compara com o `questions.json` atual e
salva em `data/questions.merged.json`. **Nunca sobrescreve o banco oficial sozinho**: para
isso é preciso pedir (`--output data/questions.json --overwrite`).

## Atenção: o script antigo está desatualizado

`scripts/merge-question-parts.py` (da Etapa 6) só conhece as cinco primeiras partes e produz
**1.000 perguntas** — ele apagaria as 550 de bandeiras do `questions.json`. Use o comando
`merge` desta pasta no lugar dele.

## Como o código está organizado (programação orientada a objetos)

```
tools/geomaster_tools/
  models.py   Question (classe-mãe) -> OptionsQuestion -> MultipleChoiceQuestion, FlagQuestion
                                    -> MapQuestion
              InvalidQuestion (item quebrado) e QuestionFactory (escolhe a classe pelo "type")
  bank.py     QuestionBank: carrega, junta partes, compara e salva
  geo.py      CountryCatalog: ids e nomes dos países do GeoJSON
  checks.py   Check (classe-mãe) e uma classe por verificação; Validator roda todas
  report.py   ReportBuilder: monta os relatórios em texto
  cli.py      os comandos validate, stats e merge
```

Conceitos em ação:

- **Herança**: `FlagQuestion` e `MultipleChoiceQuestion` herdam de `OptionsQuestion`, que herda de `Question`.
- **Polimorfismo**: todo tipo responde a `question.validate()` do seu jeito, sem `if` por tipo.
- **Encapsulamento**: o banco guarda as perguntas e oferece métodos (`compare`, `save`) em vez de mexer na lista de fora.
- **Classe abstrata**: `Question` e `Check` definem o que as filhas são obrigadas a implementar.

Para criar uma regra nova, escreva uma classe que herda de `Check` em `checks.py`, implemente
`run(bank)` e inclua-a em `default_checks()`.

> As regras daqui espelham `js/core/questions.js` e `js/core/scoring.js`. Se mudar uma regra
> no JavaScript (por exemplo, a composição da partida), atualize também `models.py`.
