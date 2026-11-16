# Modo História — Etapa 1: design e formato dos dados

## Menu
- **Jogar com amigos**: o GeoMaster atual, sem mudanças.
- **Modo História**: aventura solo em pygame, exportada para a web com pygbag e aberta dentro do site.

## Mundo
Sete regiões, nesta ordem: América do Sul (13 países), América Central e Caribe (32), América do Norte (6), Europa (50), África (56), Ásia (54), Oceania (25). Total: 236 países x 10 fases = 2.360 fases.
- México fica na América do Norte. Seychelles e Maurícia entram na África, Maldivas na Ásia.
- Ficam de fora seis territórios sem população (Antártida, Ilhas Geórgia do Sul, Terras Austrais Francesas, Ilha Heard, Território Britânico do Oceano Índico, Santa Helena). Podem virar fases secretas no futuro.
- A ordem dos países está em `data/world-order.json`. Só a América do Sul já tem ordem pensada (Brasil primeiro); nas demais é alfabética, provisória.

## País = 10 fases
Fases 1 a 9: um monstro da cultura ou lenda do país. Fase 10: o boss, mais forte, com título e um poder como recompensa. Cada país é um arquivo em `data/countries/<ID>.json` (exemplo pronto: `BRA.json`). O arquivo só guarda o que é único do país (monstros, lendas, cenário, poder). Vida, dano e dificuldade vêm de fórmulas.

## Combate por turnos (valores iniciais, serão ajustados nos testes)
- Pergunta com tempo, igual ao jogo atual. Acertou: o monstro perde vida. Errou ou o tempo acabou: o herói perde vida.
- Herói: 100 de vida. Dano causado: 10 x multiplicador da pergunta (fácil 1, média 1,5, difícil 2), mais até 50% por rapidez e 10% por acerto seguido (máx. 50%).
- Monstro: vida = 30 + 6 x (fase - 1); boss x 2,5. Dano ao herói = 8 + fase; boss 15.

## Dificuldade crescente
O progresso `p` vai de 0 (Brasil, fase 1) a 1 (último país, fase 10): `p = (posição do país x 10 + fase - 1) / 2360`. Peso de cada nível: fácil = 1 - p; média = 1 - |2p - 1|; difícil = p. A pergunta sai sorteada por esses pesos.

## De onde vêm as perguntas
Primeiro as ligadas ao país (`data/question-countries.json` do jogo atual), depois da região, depois do mundo, sem repetir no mesmo combate. O banco tem cerca de 6 perguntas por país, então o Modo História pode pedir mais perguntas no futuro.

## Poderes (`data/powers.json`)
Cada boss derrotado dá um poder ligado à sua lenda (Boitatá: Fogo-Fátuo, que elimina duas alternativas). Ativos têm usos por combate; passivos valem sempre. Cinco poderes de exemplo por enquanto.

## Salvamento
Um arquivo de progresso: países vencidos, poderes ganhos e fase atual.

## Arte
Tela interna pequena (320x180) ampliada com pixels nítidos, paleta reduzida e fonte pixelada. Os sprites seguem em aberto.

## Validação
`python story/tools/validate_story_data.py` confere se todos os países estão na ordem, se cada país tem 10 fases, boss só na fase 10 e poder existente.

## Próximas etapas
2 base do pygame (janela pixelada, telas, menu com os dois modos) · 3 combate · 4 mapa-múndi e progresso · 5 América do Sul · 6 poderes · 7 demais regiões · 8 publicação no site.

## Etapa 2 (concluída): base do jogo
- `main.py`: janela de 320x180 ampliada com pixels nítidos, troca de telas (Scene), menu (Nova aventura / Continuar / Sair, com teclado e mouse) e tela provisória das 10 fases do Brasil lida dos dados da Etapa 1.
- Rodar no PC: `pip install pygame` e depois `python story/main.py`.
- No site, o menu inicial agora tem **Jogar com amigos** e **Modo História**. O segundo abre `story/web/index.html`, uma página provisória até a exportação com pygbag (Etapa 8).

## Etapa 3 (concluída): combate por turnos
- `combat.py`: regras do combate (sem pygame): progresso, pesos de dificuldade, vida e ataque dos monstros, dano, sorteio de perguntas (país → região → mundo, sem repetir) e a classe `Battle`.
- `main.py`: `CombatScene` com barras de vida, tempo de 30 s, perguntas de múltipla escolha (teclas 1 a 4 ou clique), feedback com a resposta certa e a explicação, vitória e derrota. Vencer a fase libera a próxima; vencer o boss dá o poder da lenda (a lista de poderes ganhos fica em memória até o salvamento da Etapa 4).
- Só entram perguntas de múltipla escolha (758). Perguntas de mapa e bandeira dependem do mapa do site e ficam de fora.
- Cada combate começa com 100 de vida. Os valores de dano e vida são provisórios e serão ajustados jogando.
- Testes: `python -m unittest discover story/tests` (regras) e `python story/tests/ui_check.py` (interface sem janela).
- Para a exportação web (Etapa 8), o banco de perguntas precisará ser copiado para `story/data/` (o jogo já procura lá se não achar em `../data`).

## Etapa 4 (concluída): mapa-múndi, progresso e salvamento
- `progress.py`: fases vencidas, poderes ganhos, regra de liberação (um país só abre quando o anterior tem as 10 fases vencidas) e salvamento em `story/save.json` (gravação segura; se o arquivo estiver danificado, o jogo começa do zero; se não der para gravar, o jogo avisa e continua).
- `WorldMapScene` (mapa-múndi): uma região por vez, um quadrado por país na ordem da jornada (verde = concluído, dourado = liberado, cinza = bloqueado, azul = liberado mas ainda sem conteúdo). Setas escolhem, Q/E trocam de região, Enter entra, Esc volta ao menu.
- Menu: Nova aventura (pede confirmação se já existe save), Continuar (só ativo com save) e Sair.
- Vencer a fase 10 de um país volta ao mapa-múndi; o save é gravado a cada vitória.
- Por enquanto só o Brasil tem fases (`data/countries/BRA.json`). Os outros países aparecem como "em breve" e a jornada para ali até a Etapa 5.
- `data/country-names.json` guarda os nomes dos países; o validador confere que estão todos.
- Na versão web (Etapa 8), o salvamento depende do navegador e será testado nessa etapa.

## Etapa 5 (concluída): América do Sul
- Os 13 países da região têm 10 fases cada (9 monstros + boss), com cenário, paleta e poder do boss. Cada boss dá um poder diferente (13 poderes em `data/powers.json`; os efeitos novos são ligados ao combate na Etapa 6).
- Monstros baseados em lendas reais: Brasil, Argentina, Chile, Paraguai, Peru e Colômbia têm as 10 fases com lendas reais. Uruguai, Bolívia, Equador, Venezuela, Guiana e Suriname misturam lendas reais com criaturas **inventadas** (marcadas com `"invented": true` e escritas como "Criatura inventada, inspirada em ..."), porque não tenho material seguro para 10 lendas distintas desses países. Malvinas só tem criaturas inventadas, inspiradas na fauna das ilhas.
- Algumas lendas são compartilhadas entre países vizinhos (Pombero, Luz Mala, Lobizón, La Llorona). Todas as lendas devem ser revisadas por quem conhece cada cultura.
- Para trocar uma criatura inventada por uma lenda real, basta editar o arquivo do país em `data/countries/` e rodar o validador.

## Etapa 6 (concluída): poderes no combate
- **Equipar:** o herói leva até 3 poderes por vez. O primeiro boss já equipa o poder automaticamente enquanto houver vaga. Na tela **Poderes** (tecla P no mapa-múndi ou na tela de fases) Enter equipa ou tira, e a escolha é salva.
- **Poderes passivos (valem o combate inteiro):** Fôlego da Floresta (+5 s por pergunta), Escudo da Lenda (-20% de dano sofrido), Coração Forte (+20 de vida máxima), Ímpeto (começa com 2 acertos seguidos), Picareta do Tío (+15% de dano), Passo Leve (20% de chance de evitar o dano de um erro) e Rajada do Vento Sul (+50% no primeiro acerto).
- **Poderes ativos (teclas A, S e D, ou clique no quadro):** Fogo-Fátuo (elimina 2 alternativas, 1 uso), Luz que Guia (elimina 1, 2 usos), Golpe Duplo (o próximo acerto causa o dobro), Bênção da Cura (+25 de vida), Tempo Congelado (para o relógio por 10 s) e Segunda Chance (desfaz o dano de um erro, mesmo um que derrubaria o herói, e bloqueia a alternativa errada).
- Poderes ativos têm usos por combate; os usos voltam a cada novo combate.
- Saves antigos continuam funcionando (sem a lista de equipados, os primeiros 3 poderes são equipados).
- Testes: `python -m unittest discover story/tests` (21 testes, incluindo cada poder) e `python story/tests/ui_check.py`.

## Etapa 7 (em andamento): demais regiões, em blocos
**Bloco 1 (concluído): América Central e Caribe, primeiros 12 países** — Panamá, Costa Rica, Nicarágua, Honduras, El Salvador, Guatemala, Belize, Cuba, Haiti, República Dominicana, Jamaica e Trinidad e Tobago, nessa ordem (istmo de sul a norte, depois as ilhas maiores). Os outros 20 países da região (territórios e ilhas pequenas) aparecem como "em breve", em ordem alfabética provisória.
- Lendas reais: Popol Vuh maia (Zipacná, Cabracán, Camazotz, Vucub Caquix, Senhores de Xibalbá) na Guatemala; Ciguanaba, Cipitío e Carreta Chillona em El Salvador; Segua e Carreta sin Bueyes na Costa Rica; Güegüense e Cegua na Nicarágua; espíritos taínos (Juracán, Guabancex, Opía, Maboya) em Cuba e na República Dominicana; folclore caribenho (Papa Bois, Mama D'Leau, La Diablesse, Douen, Rolling Calf, Old Hige).
- **63 dos 120 monstros do bloco são criaturas inventadas** (marcadas com `"invented": true`), principalmente em Panamá, Belize e Haiti, onde não tenho material seguro sobre lendas distintas. Elas podem ser trocadas por lendas reais editando o arquivo do país.
- **Níveis de poder:** como 236 países não cabem em 13 poderes, receber um poder que você já tem o faz subir de nível (até 5): +50% de valor por nível e +1 uso por combate a cada 2 níveis (esquiva e redução de dano têm teto de 60%). Só a primeira vitória sobre um boss dá o poder, então repetir a fase não rende nível.
- Regiões restantes: América do Norte (6), Europa (50), África (56), Ásia (54) e Oceania (25), mais os 20 países pendentes da América Central e Caribe.

## Etapa 7 (concluída): os 236 países têm fases
- Todos os países da ordem do mundo têm 10 fases (2.360 fases). A ordem de cada região segue a geografia (oeste→leste, norte→sul): na Europa, de Portugal à Rússia; na África, do Egito às ilhas do Índico; na Ásia, da Turquia a Timor-Leste; na Oceania, da Austrália às ilhas do Pacífico.
- **Do total de 2.360 monstros, 582 são lendas reais e 1.778 são criaturas inventadas** (marcadas com `"invented": true`). Países com folclore que conheço bem (Rússia, Japão, Grécia, México, Reino Unido, Índia, Alemanha, Filipinas, Indonésia, China e outros) têm boa parte de lendas reais. Países pequenos ou sem lenda que eu conheça bem (ilhas, territórios, vários países africanos e asiáticos) usam criaturas genéricas com a frase "Criatura inventada que ...", e o boss é "Guardião de <país>". Para trocar uma criatura inventada por uma lenda real, edite o arquivo do país em `data/countries/` e rode o validador.
- Todas as lendas reais foram escritas de memória e merecem revisão de quem conhece cada cultura. Algumas são compartilhadas entre vizinhos (Nykur, Vodník, Mngwa, Ala, Soucouyant etc.).
- Poderes: cada boss dá um dos 13 poderes, em rodízio; repetir sobe o nível (até 5).

## Arte (pixel art provisória)
- `sprites.py` desenha cada monstro por código, sempre igual para o mesmo monstro, simétrico e com as cores do país (bosses maiores, com olhos vermelhos). São provisórios: arte feita à mão pode substituí-los depois.

## Etapa 8 (preparada, não testada): jogo no site
- `tools/prepare_web.py` copia o banco de perguntas para `story/data/` (o pygbag só empacota a pasta `story/`). Depois: `pip install pygbag`, `python -m pygbag --build story`, copiar `story/build/web` para `story/web/` e publicar o site.
- No navegador o save vai para a pasta persistente `/data/data/geomaster/`. Isso e o restante da exportação **não foram testados** (o ambiente de desenvolvimento não alcança o servidor do pygbag); devem ser testados no seu computador.
