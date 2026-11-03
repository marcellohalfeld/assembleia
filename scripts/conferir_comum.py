"""Confere se o `blatt.comum` de um módulo é igual à fonte canônica do assembleia.

Uso:
    python scripts/conferir_comum.py <raiz do repositório do módulo>
    python scripts/conferir_comum.py --atualizar   (só no assembleia, depois de mudar o comum)

Sai com código 1 se faltar arquivo, sobrar arquivo ou algum hash divergir.
Só biblioteca padrão, para rodar em qualquer repositório sem instalar nada.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
FONTE = RAIZ / "comum" / "src" / "blatt" / "comum"
MANIFESTO = RAIZ / "comum" / "MANIFESTO.json"


def hashes(pasta: Path) -> dict[str, str]:
    return {
        arquivo.name: hashlib.sha256(arquivo.read_bytes()).hexdigest()
        for arquivo in sorted(pasta.glob("*.py"))
    }


def atualizar() -> int:
    manifesto = json.loads(MANIFESTO.read_text(encoding="utf-8"))
    manifesto["arquivos"] = hashes(FONTE)
    MANIFESTO.write_text(json.dumps(manifesto, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Manifesto atualizado: {len(manifesto['arquivos'])} arquivos.")
    return 0


def conferir(raiz_modulo: Path) -> int:
    esperado: dict[str, str] = json.loads(MANIFESTO.read_text(encoding="utf-8"))["arquivos"]
    if hashes(FONTE) != esperado:
        print("ERRO: a fonte do assembleia diverge do próprio manifesto; rode --atualizar.")
        return 1
    pasta = raiz_modulo / "src" / "blatt" / "comum"
    if not pasta.is_dir():
        print(f"ERRO: {pasta} não existe.")
        return 1
    obtido = hashes(pasta)
    problemas = [f"falta {nome}" for nome in esperado if nome not in obtido]
    problemas += [f"sobra {nome}" for nome in obtido if nome not in esperado]
    problemas += [
        f"diverge {nome}"
        for nome, valor in esperado.items()
        if nome in obtido and obtido[nome] != valor
    ]
    if problemas:
        print(f"blatt.comum em {raiz_modulo} difere do assembleia:")
        for problema in problemas:
            print(f"  - {problema}")
        return 1
    print(f"blatt.comum em {raiz_modulo} igual ao assembleia ({len(esperado)} arquivos).")
    return 0


def main(argumentos: list[str]) -> int:
    if argumentos == ["--atualizar"]:
        return atualizar()
    if len(argumentos) != 1:
        print(__doc__)
        return 2
    return conferir(Path(argumentos[0]).resolve())


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
