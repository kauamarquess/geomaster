"""Segundo lugar para guardar o progresso: o localStorage do navegador.

No pygbag o arquivo em /data só vira "permanente" depois que o navegador sincroniza a pasta com o disco, e isso pode não
acontecer se a aba for fechada na hora, ou ainda não ter terminado quando o menu confere se existe save. O localStorage é
síncrono e simples: gravou, ficou. Fora do navegador (no PC) este módulo não faz nada e o jogo usa só o arquivo.
"""
import sys

KEY = "geomaster-story-save"
override = None  # os testes trocam por um objeto com get(chave) e set(chave, valor)


class _LocalStorage:
    def get(self, key):
        import platform  # no pygbag, platform.window é o objeto `window` do JavaScript
        return platform.window.localStorage.getItem(key)

    def set(self, key, value):
        import platform
        platform.window.localStorage.setItem(key, value)


def _backend():
    if override is not None:
        return override
    return _LocalStorage() if sys.platform == "emscripten" else None


def read():
    """Texto do save guardado no navegador, ou None (sem save, fora do navegador ou navegador bloqueou)."""
    backend = _backend()
    if backend is None:
        return None
    try:
        value = backend.get(KEY)
    except Exception:  # erros do JavaScript chegam como tipos variados; o jogo segue só com o arquivo
        return None
    value = None if value is None else str(value)
    return None if value in (None, "", "null", "undefined", "None") else value


def write(text):
    """True se gravou, False se tentou e falhou, None se não há onde gravar (PC)."""
    backend = _backend()
    if backend is None:
        return None
    try:
        backend.set(KEY, text)
        return True
    except Exception:  # cota cheia, navegação privada, permissão negada...
        return False
