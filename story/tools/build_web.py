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


def patch_browser_page(index):
    """Aplica tela cheia e controles de navegador à página gerada pelo pygbag."""
    page = index.read_text(encoding="utf-8")
    if 'id="geomaster-fullscreen"' in page:
        return
    styles = r'''
html, body { width:100%; height:100%; min-height:100%; margin:0; overflow:hidden; background:#071426; }
body { position:fixed; inset:0; padding:0; }
canvas.emscripten { position:fixed; inset:0; display:block; width:100vw !important; height:100vh !important; max-width:100vw; max-height:100vh; object-fit:fill; }
#transfer { position:fixed; z-index:10001; top:12px; left:12px; color:#eaf2ff; }
#geomaster-fullscreen { position:fixed; z-index:10002; top:12px; right:12px; padding:10px 14px; border:1px solid #6c91c9; border-radius:10px; background:rgba(10,29,54,.92); color:#fff; font:600 14px Arial,sans-serif; cursor:pointer; box-shadow:0 4px 18px #0005; }
#geomaster-fullscreen:hover { background:#1d4f91; }
:fullscreen { background:#071426; }
:fullscreen #geomaster-fullscreen { top:10px; right:10px; opacity:.72; }
@media (max-width:600px) { #geomaster-fullscreen { top:auto; bottom:10px; right:10px; padding:9px 11px; font-size:12px; } }
'''
    control = r'''
<button id="geomaster-fullscreen" type="button" aria-label="Ativar tela cheia">⛶ Tela cheia</button>
<script>
(function () {
  const button = document.getElementById("geomaster-fullscreen");
  if (!button) return;
  button.addEventListener("click", async function () {
    try {
      if (!document.fullscreenElement && document.documentElement.requestFullscreen) await document.documentElement.requestFullscreen();
      else if (document.fullscreenElement && document.exitFullscreen) await document.exitFullscreen();
    } catch (error) { console.warn("Tela cheia não disponível:", error); }
  });
  document.addEventListener("fullscreenchange", function () {
    const active = !!document.fullscreenElement;
    button.textContent = active ? "⤢ Sair da tela cheia" : "⛶ Tela cheia";
  });
})();
</script>
'''
    page = page.replace("</head>", "<style>" + styles + "</style>\n</head>", 1)
    page = page.replace("</body>", control + "\n</body>", 1)
    index.write_text(page, encoding="utf-8")


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
    patch_browser_page(WEB / "index.html")
    shutil.rmtree(WORK)
    print("\nPronto! O jogo exportado está em story/web/")
    print("Teste no navegador servindo o site por HTTP (não vale abrir o arquivo com duplo clique):")
    print("    python -m http.server 8000      (na pasta principal)  ->  http://localhost:8000")
    print("    clique em 'Modo História'; na primeira vez o jogo baixa o motor do Python (precisa de internet).")


if __name__ == "__main__":
    main()
