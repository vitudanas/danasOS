#!/usr/bin/env bash
set -euo pipefail

iso=${1:?Informe o caminho da ISO}
trabalho=$(mktemp -d)
serial="$trabalho/serial.log"
vm=
limpar() {
    if [[ -n "$vm" ]]; then kill "$vm" 2>/dev/null || true; wait "$vm" || true; fi
    if [[ -f "$serial" ]]; then cat "$serial"; fi
    rm -rf -- "$trabalho"
}
trap limpar EXIT

# A mesma capacidade de 4 GiB da partição DANASLIVE, em um SSD NVMe virtual.
extraido="$trabalho/iso"
xorriso -osirrox on -indev "$iso" -extract / "$extraido"
test -f "$extraido/EFI/boot/bootx64.efi"
test -f "$extraido/live/filesystem.squashfs"
if [[ -n "$(find "$extraido" \( -type l -o -type f -size +4294967295c \) -print -quit)" ]]; then
    echo 'A ISO contém links ou arquivos que não cabem em FAT32.' >&2
    exit 1
fi
disco="$trabalho/danaslive.img"
truncate -s 4098M "$disco"
sgdisk --new=1:2048:+4G --typecode=1:ef00 "$disco"
fat="$disco@@1048576"
mformat -i "$fat" -F -T 8388608 -v DANASLIVE ::
shopt -s dotglob
mcopy -i "$fat" -s "$extraido"/* ::/
shopt -u dotglob

cp /usr/share/OVMF/OVMF_VARS_4M.ms.fd "$trabalho/vars.fd"
qemu-system-x86_64 -machine q35,smm=on,accel=tcg -smp 4 -m 4096 \
    -global driver=cfi.pflash01,property=secure,value=on \
    -drive if=pflash,format=raw,unit=0,readonly=on,file=/usr/share/OVMF/OVMF_CODE_4M.secboot.fd \
    -drive "if=pflash,format=raw,unit=1,file=$trabalho/vars.fd" \
    -display none -serial "file:$serial" -monitor none -nic none -no-reboot \
    -drive "id=danaslive,file=$disco,format=raw,if=none" \
    -device nvme,drive=danaslive,serial=danaslive,bootindex=1 &
vm=$!
for _ in $(seq 1 150); do
    if grep -q '^DANASOS_XFCE_PRONTO' "$serial"; then
        grep -F '7.3.3+deb14-amd64' "$serial"
        grep -F 'SecureBoot enabled' "$serial"
        grep -E '^/dev/nvme0n1p1[[:space:]]+vfat' "$serial"
        exit 0
    fi
    kill -0 "$vm"
    sleep 2
done
echo 'A sessão XFCE não confirmou o boot em NVMe/FAT32 com Secure Boot.' >&2
exit 1
