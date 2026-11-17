# Salvamento do progresso (Modo História)

O progresso é salvo **automaticamente** a cada fase vencida e quando você equipa/desequipa poderes.

## Onde fica
- **No PC:** `story/save.json`, ao lado do jogo.
- **No navegador:** em dois lugares ao mesmo tempo — o arquivo da pasta persistente do pygbag (`/data`) e o
  `localStorage` do navegador. Se só um deles estiver disponível, o jogo continua pelo outro.
- Ao abrir o menu, o jogo lê os dois e usa o **mais recente** (cada save guarda a data em que foi gravado).
  Isso também vale quando você começa uma "Nova aventura": o save novo vence o antigo, mesmo tendo menos fases.

## O que o jogador vê
- O menu mostra `Continuar (20/236)`: quantos países já foram concluídos.
- Se nenhum dos dois lugares funcionar (ex.: navegador bloqueando armazenamento), aparece
  "Não foi possível salvar o progresso!" no rodapé do mapa.

## Apagar o save
- No menu, **Apagar save** pede confirmação ("Enter = sim, Esc = não") e mostra quantos países serão perdidos.
- Apaga o arquivo e, no navegador, grava no localStorage um save **vazio e mais novo**. Assim, se o navegador não
  conseguir remover alguma cópia antiga, ela não "ressuscita" no próximo "Continuar".
- Se mesmo assim sobrar progresso (ex.: arquivo protegido contra escrita no PC), aparece
  "Não foi possível apagar o save." em vermelho.
- Sem save, "Continuar" e "Apagar save" ficam cinzas e não fazem nada.

## Limites (vale saber)
- O save fica no navegador e no aparelho em que se jogou: outro navegador, outro computador ou o modo anônimo
  começam do zero. Limpar os "dados do site" também apaga o save.
- Ainda não há botão de exportar/importar save. Se quiser, esse é um bom próximo passo.

## Arquivos
- `story/webstore.py` — gravação no localStorage (não faz nada no PC).
- `story/progress.py` — save com data, leitura tolerante a arquivo danificado, escolha do save mais recente.
- `story/main.py` — grava nos dois lugares, mostra o contador e tem o menu com Apagar save.
- `story/tests/test_save.py` e `story/tests/ui_check.py` — testes.
- `story/tools/build_web.py` — agora empacota também o `webstore.py`.
