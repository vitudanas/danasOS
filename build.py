#!/usr/bin/env python3
"""Gera a imagem de instalação do danasOS em um Debian 13 amd64."""

import argparse
import hashlib
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import tempfile

from publicar import VERSAO_INICIAL, criar_pacote

ORIGEM = Path(__file__).resolve().parent
NOME = "danasOS-0.2-amd64"
ABI_TESTE = "7.3.3+deb14-amd64"
OPCOES = (
    "--ignore-system-defaults",
    "--mode", "debian",
    "--distribution", "trixie",
    "--architecture", "amd64",
    "--binary-image", "iso-hybrid",
    "--bootloaders", "grub-efi",
    "--uefi-secure-boot", "enable",
    "--apt-secure", "true",
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
    "boot=live components hostname=danasos username=live locales=pt_BR.UTF-8 "
    "keyboard-model=abnt2 keyboard-layouts=br quiet",
)


def preparar(diretorio):
    config = diretorio / "config"
    shutil.copytree(ORIGEM / "config", config, dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns("__pycache__"))
    for item in config.glob("hooks/live/*.hook.chroot"):
        item.chmod(0o755)
    for item in config.glob("includes.chroot/usr/local/bin/*"):
        item.chmod(0o755)
    (config / "includes.chroot/usr/bin/danasos-auto-update").chmod(0o755)


def preparar_teste_vmd(trabalho):
    config = trabalho / "config"
    hardware = config / "package-lists/hardware.list.chroot"
    hardware.write_text(hardware.read_text().replace("linux-headers-amd64\n", ""))
    boot = config / "package-lists/boot.list.chroot"
    with boot.open("a") as arquivo:
        arquivo.write("initramfs-tools\n")
    marcadores = config / "includes.chroot/etc/danasos"
    marcadores.mkdir(parents=True, exist_ok=True)
    (marcadores / "kernel-teste-vmd").write_text(ABI_TESTE + "\n", encoding="ascii")
    (marcadores / "edicao-publica").touch()
    systemd = config / "includes.chroot/etc/systemd/system"
    habilitados = systemd / "graphical.target.wants"
    habilitados.mkdir(parents=True, exist_ok=True)
    unidade = "danasos-verificar-vm.service"
    shutil.copyfile(ORIGEM / "scripts" / unidade, systemd / unidade)
    (habilitados / unidade).symlink_to(f"../{unidade}")
    subprocess.run(
        ["sh", str(ORIGEM / "scripts/baixar-kernel-vmd.sh"),
         str(config / "packages.chroot"), "--live"], check=True,
    )


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
    ausentes = [p for p in ("lb", "debootstrap", "xorriso", "mksquashfs", "dpkg-deb",
                            "lsinitramfs", "sbverify")
                if not shutil.which(p)]
    if ausentes:
        raise RuntimeError("Ferramentas ausentes: " + ", ".join(ausentes))


def conferir_boot(trabalho, imagem):
    boot = subprocess.check_output(
        ["xorriso", "-indev", str(imagem), "-report_el_torito", "plain"], text=True,
    )
    if "UEFI" not in boot:
        raise RuntimeError("O catálogo de boot da imagem não contém uma entrada UEFI.")

    kernels = list((trabalho / "chroot/boot").glob("vmlinuz-*"))
    if len(kernels) != 1:
        raise RuntimeError("Esperava um único kernel para o boot da ISO.")
    kernel = kernels[0].name
    abi = kernel.removeprefix("vmlinuz-")
    initrd = f"initrd.img-{abi}"
    with tempfile.TemporaryDirectory(prefix="verificar-boot-", dir=trabalho) as pasta:
        subprocess.run(
            ["xorriso", "-osirrox", "on", "-indev", str(imagem),
             "-extract", f"/live/{kernel}", str(Path(pasta) / kernel),
             "-extract", f"/live/{initrd}", str(Path(pasta) / initrd)], check=True,
        )
        subprocess.run(["sbverify", "--list", str(Path(pasta) / kernel)], check=True)
        conteudo = subprocess.check_output(["lsinitramfs", str(Path(pasta) / initrd)], text=True)

    modulos = set()
    for linha in conteudo.splitlines():
        modulo = re.fullmatch(
            rf"(?:usr/)?lib/modules/{re.escape(abi)}/kernel/.*/([^/]+)\.ko(?:\.(?:xz|zst|gz))?",
            linha,
        )
        if modulo:
            modulos.add(modulo[1])
    faltam = {"vmd", "nvme", "nvme-core"} - modulos
    if faltam:
        raise RuntimeError("Módulos ausentes no initramfs da ISO: " + ", ".join(sorted(faltam)))
    print(f"Boot UEFI inspecionado: {abi}, VMD e NVMe presentes no initramfs da ISO.", flush=True)


def compilar(destino, teste_vmd=False):
    verificar_host()
    destino.mkdir(parents=True, exist_ok=True)
    nome = f"{NOME}-teste-vmd" if teste_vmd else NOME
    iso = destino / f"{nome}.iso"
    checksum = destino / f"{nome}.sha256"
    if iso.exists() or checksum.exists():
        raise RuntimeError("Já há uma imagem ou checksum com esse nome. Escolha outra pasta.")
    if shutil.disk_usage(destino).free < 25 * 1024**3:
        raise RuntimeError("Reserve pelo menos 25 GiB livres para a compilação.")

    trabalho = Path(tempfile.mkdtemp(prefix="build-danasos-", dir=destino))
    print(f"Pasta da compilação: {trabalho}", flush=True)
    opcoes = list(OPCOES)
    if teste_vmd:
        opcoes[opcoes.index("--image-name") + 1] = nome
        opcoes.extend(("--linux-flavours", ABI_TESTE))
    subprocess.run(["lb", "config", *opcoes], cwd=trabalho, check=True)
    # O live-build cria os diretórios em branco. Sobrepõe somente a receita.
    preparar(trabalho)
    if teste_vmd:
        preparar_teste_vmd(trabalho)
    criar_pacote(VERSAO_INICIAL, trabalho / "config/packages.chroot")
    subprocess.run(["lb", "build"], cwd=trabalho, check=True)

    imagens = list(trabalho.glob("*.iso"))
    if len(imagens) != 1:
        raise RuntimeError(f"Esperava uma ISO, encontrei {len(imagens)}.")
    imagem = imagens[0]
    conferir_boot(trabalho, imagem)
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
    parser.add_argument("--teste-vmd", action="store_true",
                        help="gera uma ISO de teste com o kernel Debian 7.3.3 assinado")
    args = parser.parse_args()
    try:
        compilar(args.saida.resolve(), teste_vmd=args.teste_vmd)
    except (OSError, RuntimeError, subprocess.CalledProcessError) as erro:
        parser.exit(1, f"Compilação interrompida. {erro}\n")
