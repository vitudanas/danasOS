#!/usr/bin/env python3
"""Gera a imagem de instalação do danasOS em um Debian 13 amd64."""

import argparse
import hashlib
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile

from publicar import VERSAO_INICIAL, criar_pacote

ORIGEM = Path(__file__).resolve().parent
NOME = "danasOS-0.2-amd64"
OPCOES = (
    "--ignore-system-defaults",
    "--mode", "debian",
    "--distribution", "trixie",
    "--architecture", "amd64",
    "--binary-image", "iso-hybrid",
    "--bootloaders", "grub-efi",
    "--uefi-secure-boot", "enable",
    "--archive-areas", "main contrib non-free non-free-firmware",
    "--apt-recommends", "false",
    "--apt-source-archives", "false",
    "--apt-indices", "true",
    "--backports", "true",
    "--debian-installer", "none",
    "--firmware-binary", "false",
    "--firmware-chroot", "false",
    "--checksums", "sha256",
    "--image-name", NOME,
    "--iso-application", "danasOS",
    "--iso-volume", "DANASOS_02_AMD64",
    "--bootappend-live",
    "boot=live components hostname=danasos username=live locales=pt_BR.UTF-8 keyboard-layouts=br quiet",
)


def preparar(diretorio):
    config = diretorio / "config"
    shutil.copytree(ORIGEM / "config", config, dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns("__pycache__"))
    for item in config.glob("hooks/live/*.hook.chroot"):
        item.chmod(0o755)
    for item in config.glob("includes.chroot/usr/local/bin/*"):
        item.chmod(0o755)


def verificar_host():
    if sys.platform != "linux":
        raise RuntimeError("Compile em uma VM Debian 13 amd64, com acesso à rede.")
    import os

    versao = platform.freedesktop_os_release()
    if versao["ID"] != "debian" or versao.get("VERSION_CODENAME") != "trixie":
        raise RuntimeError("Use Debian 13 como ambiente de compilação.")
    if os.geteuid() != 0:
        raise RuntimeError("Execute o construtor com sudo dentro da VM Debian.")
    if subprocess.check_output(["dpkg", "--print-architecture"], text=True).strip() != "amd64":
        raise RuntimeError("A imagem precisa de um ambiente amd64.")
    ausentes = [p for p in ("lb", "debootstrap", "xorriso", "mksquashfs", "dpkg-deb")
                if not shutil.which(p)]
    if ausentes:
        raise RuntimeError("Ferramentas ausentes: " + ", ".join(ausentes))


def compilar(destino):
    verificar_host()
    destino.mkdir(parents=True, exist_ok=True)
    iso = destino / f"{NOME}.iso"
    checksum = destino / f"{NOME}.sha256"
    if iso.exists() or checksum.exists():
        raise RuntimeError("Já há uma imagem ou checksum com esse nome. Escolha outra pasta.")
    if shutil.disk_usage(destino).free < 25 * 1024**3:
        raise RuntimeError("Reserve pelo menos 25 GiB livres para a compilação.")

    trabalho = Path(tempfile.mkdtemp(prefix="build-danasos-", dir=destino))
    print(f"Pasta da compilação: {trabalho}", flush=True)
    subprocess.run(["lb", "config", *OPCOES], cwd=trabalho, check=True)
    # O live-build cria os diretórios em branco. Sobrepõe somente a receita.
    preparar(trabalho)
    criar_pacote(VERSAO_INICIAL, trabalho / "config/packages.chroot")
    subprocess.run(["lb", "build"], cwd=trabalho, check=True)

    imagens = list(trabalho.glob("*.iso"))
    if len(imagens) != 1:
        raise RuntimeError(f"Esperava uma ISO, encontrei {len(imagens)}.")
    imagem = imagens[0]
    boot = subprocess.check_output(
        ["xorriso", "-indev", str(imagem), "-report_el_torito", "plain"],
        text=True,
    )
    if "UEFI" not in boot:
        raise RuntimeError("O catálogo de boot da imagem não contém uma entrada UEFI.")
    with imagem.open("rb") as arquivo:
        sha = hashlib.file_digest(arquivo, "sha256").hexdigest()
    imagem.chmod(0o644)
    imagem.rename(iso)
    checksum.write_text(f"{sha}  {iso.name}\n", encoding="ascii")
    print(f"Imagem: {iso}\nSHA-256: {sha}")
    print("Teste o boot e a instalação em disco virtual antes de usar num SSD.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--saida", type=Path, default=ORIGEM / "dist")
    args = parser.parse_args()
    try:
        compilar(args.saida.resolve())
    except (OSError, RuntimeError, subprocess.CalledProcessError) as erro:
        parser.exit(1, f"Compilação interrompida. {erro}\n")
