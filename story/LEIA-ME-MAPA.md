# Modo História: mapa-múndi, continentes e fases dentro dos países

## Como o jogador navega
1. **Mapa-múndi** (`GlobeScene`): cada continente da jornada tem uma cor. Setas escolhem, Enter entra, Esc volta ao menu.
2. **Continente** (`WorldMapScene`): o continente aparece em destaque e cada país é uma região do mapa
   (cinza-azulado = bloqueado, dourado = liberado, verde = concluído). Setas andam entre países,
   Tab/Shift+Tab seguem a ordem da jornada, Q/E trocam de continente, Esc volta ao mapa-múndi.
   Países muito pequenos (ilhas) viram "pinos" no mapa.
3. **País** (`WorldScene`): o país ocupa a tela e as 10 fases ficam dentro do desenho dele, ligadas por um caminho.
   A fase 10 (chefão) fica no ponto mais interno do país. Painel à direita com o monstro e a lenda.
   Países que no mapa-múndi são só um pontinho (Vaticano, Mônaco...) aparecem como uma "ilha ampliada".
- O mouse (ou toque) funciona em tudo: 1º clique seleciona, 2º clique entra.
- Um marcador dourado piscando mostra onde a aventura está.

## Arquivos
- `story/data/map.json` — formas dos países e posição das 10 fases (gerado, ~400 KB).
- `story/tools/build_map_data.py` — gera o map.json a partir do GeoJSON do site (`python story/tools/build_map_data.py`).
  Só precisa rodar de novo se mudar o GeoJSON ou as regras de posicionamento das fases.
- `story/mapgeo.py` (geometria, sem pygame) e `story/mapview.py` (desenho).
- `story/tools/build_web.py` — atualizado para empacotar os dois módulos novos.
- `story/tests/test_map.py` e `story/tests/ui_check.py` — testes do mapa e da interface.

## Depois de aplicar
1. `python story/tools/build_web.py`  (gera o jogo para o navegador em story/web)
2. Publicar de novo (git push ou arrastar a pasta no Netlify) e dar Ctrl+F5.
