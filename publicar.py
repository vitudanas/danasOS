#!/usr/bin/env python3
"""Empacota a Central e o tema ou gera um canal APT assinado."""

import argparse
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

PACOTE = "danasos-experience"
VERSAO_INICIAL = "0.2-1"
OVERLAY = Path(__file__).resolve().parent / "config/includes.chroot"
CAMINHOS = (
    "usr/share/danasos/catalogo.py",
    "usr/share/danasos/central.py",
    "usr/share/danasos/danasos.svg",
    "usr/share/danasos/noite-em-neon.png",
    "usr/share/danasos/noite-em-neon.svg",
    "usr/share/themes/danasOS/index.theme",
    "usr/share/themes/danasOS/gtk-3.0/gtk.css",
    "usr/share/applications/danasos-central.desktop",
    "usr/share/applications/danasos-loja.desktop",
)


def criar_pacote(versao, saida):
    if not re.fullmatch(r"\d+(?:\.\d+)+-\d+", versao):
        raise ValueError("Use uma versão Debian como 0.2-2 ou 0.3-1.")
    saida.mkdir(parents=True, exist_ok=True)
    alvo = saida / f"{PACOTE}_{versao}_all.deb"
    if alvo.exists():
        raise FileExistsError(alvo)
    with tempfile.TemporaryDirectory(prefix="danasos-pacote-") as temp:
        raiz = Path(temp)
        raiz.chmod(0o755)
        for caminho in CAMINHOS:
            origem, destino = OVERLAY / caminho, raiz / caminho
            destino.parent.mkdir(parents=True, exist_ok=True)
            if origem.is_symlink():
                raise ValueError(f"Arquivo simbólico fora do pacote: {caminho}")
            shutil.copyfile(origem, destino)
        metadados = raiz / "DEBIAN"
        metadados.mkdir()
        (metadados / "control").write_text(
            f"Package: {PACOTE}\nVersion: {versao}\nArchitecture: all\n"
            "Section: x11\nPriority: optional\nMaintainer: danasOS Project <maintainers@danasos.invalid>\n"
            "Depends: python3-gi, gir1.2-gtk-3.0, gnome-software, flatpak, xfce4-terminal\n"
            "Description: danasOS desktop identity and gaming hub\n",
            encoding="utf-8",
        )
        subprocess.run(["dpkg-deb", "--root-owner-group", "--build", str(raiz), str(alvo)], check=True)
    return alvo


def criar_canal(versao, saida, chave):
    if not re.fullmatch(r"(?:[A-Fa-f0-9]{40}|[A-Fa-f0-9]{64})", chave):
        raise ValueError("Informe o fingerprint completo da chave OpenPGP de assinatura.")
    if saida.exists():
        raise FileExistsError(saida)
    saida.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="danasos-canal-", dir=saida.parent) as temp:
        repositorio = Path(temp) / "apt"
        criar_pacote(versao, repositorio)
        with (repositorio / "Packages").open("wb") as indices:
            subprocess.run(["apt-ftparchive", "packages", "."], cwd=repositorio,
                           stdout=indices, check=True)
        # Gere Release fora do repositório para o índice não incluir o próprio arquivo.
        release = Path(temp) / "Release"
        with release.open("wb") as conteudo:
            subprocess.run(
                ["apt-ftparchive", "-o", "APT::FTPArchive::Release::Origin=danasOS",
                 "-o", "APT::FTPArchive::Release::Label=danasOS", "release", "."],
                cwd=repositorio, stdout=conteudo, check=True,
            )
        shutil.move(release, repositorio / "Release")
        subprocess.run(
            ["gpg", "--batch", "--local-user", chave, "--output", "InRelease",
             "--clearsign", "Release"],
            cwd=repositorio, check=True,
        )
        repositorio.rename(saida)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--versao", required=True)
    parser.add_argument("--saida", type=Path, required=True)
    parser.add_argument("--fingerprint", default=os.environ.get("DANASOS_APT_FINGERPRINT"))
    args = parser.parse_args()
    try:
        if args.fingerprint:
            criar_canal(args.versao, args.saida.resolve(), args.fingerprint)
        else:
            print(criar_pacote(args.versao, args.saida.resolve()))
    except (ValueError, OSError, subprocess.CalledProcessError) as erro:
        parser.exit(1, f"Publicação interrompida. {erro}\n")
