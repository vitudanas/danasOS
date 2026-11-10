#!/usr/bin/env python3
"""Converte o plano autenticado do APT em downloads paralelos com SHA-256."""

import re
import shlex
import sys
from urllib.parse import urlsplit


for linha in sys.stdin:
    if not linha.startswith("'"):
        continue
    uri, nome, tamanho, hash_apt = shlex.split(linha)
    endereco = urlsplit(uri)
    if (endereco.scheme not in {"http", "https"} or not endereco.hostname
            or not re.fullmatch(r"[a-zA-Z0-9_.+%~-]+\.deb", nome)
            or not tamanho.isdecimal() or int(tamanho) <= 0
            or not re.fullmatch(r"SHA256:[a-f0-9]{64}", hash_apt)):
        sys.exit(f"Pacote sem URL, nome ou SHA-256 válido no plano APT: {nome}")

    fontes = [uri]
    if endereco.hostname in {"archive.ubuntu.com", "security.ubuntu.com"}:
        if endereco.path.startswith("/ubuntu/pool/"):
            fontes.insert(0, "https://mirrors.edge.kernel.org" + endereco.path)
    print("\t".join(fontes))
    print(f"  out={nome}")
    print(f"  checksum=sha-256={hash_apt.removeprefix('SHA256:')}")
