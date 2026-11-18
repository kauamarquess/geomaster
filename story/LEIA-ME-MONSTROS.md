# Skins e animações dos monstros

O arquivo `sprites.py` agora desenha os monstros em pixel art por famílias de silhueta (serpentes, aves, quadrúpedes, aquáticos, insetos, fantasmas, dragões e criaturas humanoides/gelatinosas). Cada combinação de identificador do monstro, país e paleta gera marcas e variações determinísticas, então o mesmo monstro mantém sua aparência entre partidas e não depende de arquivos de imagem externos.

As poses disponíveis são:
- `idle`: respiração/movimento leve durante a pergunta;
- `attack`: avanço visual quando o jogador erra;
- `hurt`: brilho de impacto quando o jogador acerta;
- `defeat`: queda/rotação quando o monstro é derrotado.

Chefes recebem tamanho maior e detalhes de olhos/ornamentos próprios. A arena de combate foi reorganizada para exibir o viajante e o monstro em escala maior, com barras de vida no cabeçalho, pergunta em área própria e alternativas mais compactas.

Para aplicar a alteração na versão publicada para navegador, gere novamente o pacote do Modo História com `python story/tools/build_web.py` (com `pygbag` instalado e conexão com a internet). Os arquivos já exportados em `story/web/` são artefatos compilados e não são atualizados automaticamente ao editar os fontes.
