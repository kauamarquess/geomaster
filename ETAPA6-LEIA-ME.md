# GeoMaster — Etapa 6: banco em partes

## Conteúdo

O banco foi dividido em cinco arquivos de 200 perguntas cada:

- `data/questions-part-01.json`
- `data/questions-part-02.json`
- `data/questions-part-03.json`
- `data/questions-part-04.json`
- `data/questions-part-05.json`

O arquivo `data/questions.json` também já contém o banco consolidado, no formato que o carregador atual espera.

## Distribuição

- 1.550 perguntas no total
- 758 de múltipla escolha
- 242 desafios no mapa (um para cada recurso do GeoJSON)
- Categorias: capitais, cultura/moedas, sub-regiões geográficas, fronteiras e localização no mapa
- Três níveis: `easy`, `medium`, `hard`

## Mesclar novamente as partes

Na pasta principal `GeoMaster/GeoMaster`, execute:

```bash
python scripts/merge-question-parts.py
```

O script confere se existem cinco partes, se cada uma tem 200 perguntas, se o total é 1.550 e se os IDs são únicos. Em seguida recria `data/questions.json`.

## Compatibilidade

O formato usa os campos aceitos por `js/core/questions.js`: `id`, `type`, `difficulty`, `category`, `text`, `options`, `correctIndex`, `explanation`, `targetId` e `targetName`. Não foi necessário alterar o motor. Os desafios de mapa usam os códigos `properties.id` de `data/geojson/countries.geojson`.

## Fontes e cautelas

- ONU — classificação M49 de regiões e sub-regiões: https://unstats.un.org/unsd/methodology/M49
- GeoJSON do próprio projeto — nomes e códigos dos alvos de mapa (base cartográfica Natural Earth, conforme documentação já presente no projeto).
- CountryInfo — referência auxiliar para capitais, moedas e fronteiras: https://pypi.org/project/countryinfo/
- Babel — nomes localizados das moedas: https://babel.pocoo.org/

**Importante:** esta entrega valida estrutura, unicidade, compatibilidade e correspondência dos alvos de mapa com o GeoJSON. Capitais, moedas e fronteiras vêm de uma fotografia de dados auxiliar; isso não equivale a uma auditoria editorial independente de cada facto. A revisão factual final deve ser concluída na Etapa 8, com atenção a países com capitais múltiplas, moedas partilhadas e fronteiras disputadas.
