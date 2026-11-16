# Modo História no site (exportação com pygbag)

O botão "Modo História" do site já abre `story/web/index.html`. Falta só colocar o jogo exportado nessa pasta.

## Passo a passo (com internet)
1. Na pasta principal do GeoMaster: `pip install pygbag`
2. `python story/tools/build_web.py`
3. Teste: `python -m http.server 8000` e abra http://localhost:8000 → botão "Modo História".
4. Publique o site inteiro (GitHub Pages ou Netlify). Não commite `story/web-backup/` se não quiser.

## Importante
- O site precisa ser aberto por HTTP (localhost ou publicado). Duplo clique no arquivo não funciona.
- Na primeira vez o navegador baixa o motor do Python (~10 MB) e pede um clique/toque para iniciar.
- O progresso é salvo no navegador (pasta /data do pygbag); limpar dados do site apaga o save.
- Se der erro, abra o jogo e aperte F12 → aba Console, e me mande o texto.
