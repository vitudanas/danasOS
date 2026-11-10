#!/usr/bin/env python3
"""Rebatiza o menu do Mint e recalcula o manifesto dos arquivos modificados."""

import hashlib
from pathlib import Path
import re
import sys


def configurar_boot(midia):
    opcoes = (
        "username=live hostname=danasos locale=pt_BR.UTF-8 "
        "keyboard-configuration/modelcode=abnt2 keyboard-configuration/layoutcode=br"
    )
    grub = midia / "boot/grub/grub.cfg"
    config = grub.read_text(encoding="utf-8")
    if config.count("username=mint hostname=mint") != 3:
        raise ValueError("Menu do Mint diferente da imagem base esperada.")
    config = config.replace("username=mint hostname=mint", opcoes)
    config = config.replace("Start Linux Mint 22.3 Xfce 64-bit", "danasOS 0.3 - Mint Xfce HWE")
    config = config.replace("quiet splash --", "nvidia-drm.modeset=1 quiet splash --", 1)
    config = config.replace("noapic noacpi nosplash irqpoll nomodeset", "nomodeset plymouth.enable=0")
    config = config.replace("\ngrub_platform\n", "\n")
    grub.write_text("set timeout=8\n" + config, encoding="utf-8")

    isolinux = midia / "isolinux/txt.cfg"
    if isolinux.is_file():
        config = isolinux.read_text(encoding="utf-8").replace("username=mint hostname=mint", opcoes)
        config = config.replace("quiet splash --", "nvidia-drm.modeset=1 quiet splash --", 1)
        isolinux.write_text(config, encoding="utf-8")


def atualizar_manifesto(midia):
    manifesto = midia / "md5sum.txt"
    novo = []
    for linha in manifesto.read_text(encoding="utf-8").splitlines():
        campos = re.fullmatch(r"[a-f0-9]{32} ([ *])(.+)", linha)
        if not campos:
            raise ValueError("Linha inesperada no manifesto MD5 da mídia.")
        tipo, nome = campos.groups()
        arquivo = midia / nome
        if not arquivo.resolve().is_relative_to(midia.resolve()):
            raise ValueError(f"Caminho fora da mídia: {nome}")
        with arquivo.open("rb") as conteudo:
            soma = hashlib.file_digest(conteudo, lambda: hashlib.md5(usedforsecurity=False))
        novo.append(f"{soma.hexdigest()} {tipo}{nome}\n")
    manifesto.write_text("".join(novo), encoding="utf-8")


if __name__ == "__main__":
    pasta = Path(sys.argv[1]).resolve(strict=True)
    configurar_boot(pasta)
    atualizar_manifesto(pasta)
