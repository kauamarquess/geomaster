"""Exporta o Modo História para o navegador e instala em story/web/ (a página que o botão do site abre).

Uso (na pasta principal do projeto, com internet):
    pip install pygbag
    python story/tools/build_web.py

O que o script faz:
  1. copia só o necessário do jogo para uma pasta temporária (sem testes, sem cache e sem a pasta web/,
     para o pacote não crescer a cada exportação);
  2. copia o banco de perguntas do site para dentro do pacote;
  3. roda o pygbag, que baixa o modelo da página da internet;
  4. só se tudo deu certo, troca o conteúdo de story/web/ pelo jogo exportado (guarda a página antiga em story/web-backup/).
"""
import shutil
import subprocess
import sys
from pathlib import Path

STORY = Path(__file__).resolve().parent.parent
ROOT = STORY.parent
WORK = ROOT / "_build_story"          # pasta temporária (pode apagar depois)
PACK = WORK / "story"                 # o nome da pasta vira o nome do pacote (story.apk)
WEB = STORY / "web"
BACKUP = STORY / "web-backup"

CODE_FILES = ["main.py", "combat.py", "progress.py", "sprites.py", "mapgeo.py", "mapview.py", "webstore.py", "traveler.py"]
BANK_FILES = ["questions.json", "question-countries.json"]


def fail(message):
    print("\nERRO:", message)
    sys.exit(1)


def main():
    if shutil.which("python") is None and not sys.executable:
        fail("Python não encontrado.")
    try:
        import pygbag  # noqa: F401
    except ImportError:
        fail("pygbag não está instalado. Rode:  pip install pygbag")

    # 1) pacote limpo
    if WORK.exists():
        shutil.rmtree(WORK)
    PACK.mkdir(parents=True)
    for name in CODE_FILES:
        shutil.copy(STORY / name, PACK / name)
    shutil.copytree(STORY / "data", PACK / "data")
    print("pacote montado em", PACK)

    # 2) banco de perguntas do site
    for name in BANK_FILES:
        source = ROOT / "data" / name
        if not source.exists():
            fail(f"não achei {source}. Rode antes: python scripts/merge-question-parts.py")
        shutil.copy(source, PACK / "data" / name)
    print("banco de perguntas copiado")

    # 3) exporta (precisa de internet para baixar o modelo da página)
    print("\nrodando o pygbag (pode demorar alguns minutos)...\n")
    result = subprocess.run([sys.executable, "-m", "pygbag", "--build", str(PACK)])
    built = PACK / "build" / "web"
    if result.returncode != 0 or not (built / "index.html").exists():
        fail("o pygbag não gerou o index.html. Confira se o computador está conectado à internet "
             "(ele baixa o modelo de pygame-web.github.io) e rode de novo. story/web não foi alterada.")

    # 4) instala em story/web/
    if WEB.exists():
        if BACKUP.exists():
            shutil.rmtree(BACKUP)
        shutil.move(str(WEB), str(BACKUP))
    shutil.copytree(built, WEB)
    shutil.rmtree(WORK)
    print("\nPronto! O jogo exportado está em story/web/")
    print("Teste no navegador servindo o site por HTTP (não vale abrir o arquivo com duplo clique):")
    print("    python -m http.server 8000      (na pasta principal)  ->  http://localhost:8000")
    print("    clique em 'Modo História'; na primeira vez o jogo baixa o motor do Python (precisa de internet).")


if __name__ == "__main__":
    main()
