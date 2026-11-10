#!/usr/bin/env python3
"""Converte o plano autenticado do APT em downloads paralelos com SHA-2."""

import re
import shlex
import sys
from urllib.parse import urlsplit


entradas = set()
verificados = set()
for linha in sys.stdin:
    if not linha.startswith("'"):
        continue
    campos = shlex.split(linha)
    if len(campos) not in {3, 4}:
        sys.exit(f"Linha inesperada no plano do APT: {linha.strip()}")
    uri, nome, tamanho = campos[:3]
    endereco = urlsplit(uri)
    if (endereco.scheme not in {"http", "https"} or not endereco.hostname
            or not re.fullmatch(r"[a-zA-Z0-9_.+%~-]+\.deb", nome)
            or not tamanho.isdecimal() or int(tamanho) <= 0):
        sys.exit(f"Pacote sem URL, nome ou tamanho válido no plano APT: {nome}")
    entradas.add(nome)
    if len(campos) == 3 or nome in verificados:
        continue
    tipo, _, soma = campos[3].partition(":")
    if tipo not in {"SHA256", "SHA512"} or not re.fullmatch(
        r"[a-f0-9]{%d}" % (int(tipo[3:]) // 4), soma
    ):
        sys.exit(f"Hash inesperado no plano do APT: {nome}")
    verificados.add(nome)

    fontes = [uri]
    if endereco.hostname in {"archive.ubuntu.com", "security.ubuntu.com"}:
        if endereco.path.startswith("/ubuntu/pool/"):
            fontes.insert(0, "https://mirrors.edge.kernel.org" + endereco.path)
    print("\t".join(fontes))
    print(f"  out={nome}")
    print(f"  checksum=sha-{tipo[3:]}={soma}")

for nome in sorted(entradas - verificados):
    print(f"Download reservado ao APT: {nome}", file=sys.stderr)
