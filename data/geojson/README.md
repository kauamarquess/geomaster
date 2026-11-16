# Dados geográficos

## `countries.geojson`
Mapa-múndi com **242 países e territórios**, usado no desafio "clique no país".

- **Fonte:** [Natural Earth](https://www.naturalearthdata.com/), camada *Admin 0 – Countries*, escala 1:50 milhões (domínio público).
- **Tratamento:** simplificado com [mapshaper](https://github.com/mbloch/mapshaper) (`-simplify 30% keep-shapes`, precisão de 0,01°) para o arquivo ficar com cerca de 500 KB. O `keep-shapes` preserva as ilhas pequenas.
- **Propriedades de cada país:**
  - `id`: identificador único usado nas perguntas (`targetId`).
  - `name`: nome em português. `name_en`: nome em inglês. `continent`: continente (em inglês).

## Regra do identificador (`id`)
- Se o país tem código **ISO 3166-1 alfa-3**, usa esse código (exemplos: `BRA`, `FRA`, `SSD`).
- Se não tem, usa o código próprio do Natural Earth: `KOS` (Kosovo), `SOL` (Somalilândia), `CYN` (Chipre do Norte), `KAS` (Glaciar de Siachen), `IOA` (Territórios australianos do Oceano Índico) e `ATC` (Ilhas Ashmore e Cartier).
- Todos os 242 identificadores são únicos (conferido pelos testes automáticos).

A lista completa está em [`COUNTRIES.md`](COUNTRIES.md).

## Observação sobre fronteiras
O mapa segue as fronteiras e as entidades do Natural Earth, que trata Taiwan, Palestina, Kosovo e Saara Ocidental como registros separados. Isso é uma convenção cartográfica do conjunto de dados, não uma posição política do jogo.

## Como regenerar o arquivo (opcional)
1. Baixe `ne_50m_admin_0_countries.geojson` do repositório *natural-earth-vector*.
2. Rode: `npx mapshaper ne_50m_admin_0_countries.geojson -each "id = /^[A-Z]{3}$/.test(ISO_A3) ? ISO_A3 : ADM0_A3, name = NAME_PT, name_en = NAME_EN, continent = CONTINENT" -filter-fields id,name,name_en,continent -simplify 30% keep-shapes -o countries.geojson format=geojson precision=0.01`
3. Rode os testes (`/tests/index.html`): eles conferem identificadores únicos e se o banco de perguntas aponta para países que existem.
