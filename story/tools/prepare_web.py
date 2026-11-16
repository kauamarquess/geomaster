"""Prepara a pasta story/ para virar o jogo web com pygbag.
O pygbag só empacota o que está dentro de story/, então o banco de perguntas do site precisa ser copiado para cá.
Uso (na pasta principal do projeto):  python story/tools/prepare_web.py"""
import shutil
from pathlib import Path

STORY = Path(__file__).resolve().parent.parent
DATA = STORY.parent / "data"
(STORY / "data").mkdir(exist_ok=True)
for name in ("questions.json", "question-countries.json"):
    shutil.copy(DATA / name, STORY / "data" / name)
    print("copiado:", name)
print("""
Próximos passos:
  pip install pygbag
  python -m pygbag --build story         (gera story/build/web)
  copie o conteúdo de story/build/web para story/web/ (substitui a página provisória)
  publique o site normalmente (ex.: GitHub Pages) e abra o Modo História pelo botão do menu.""")
