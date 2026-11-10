#!/usr/bin/env bash
set -euo pipefail

iso=${1:?Informe o caminho da ISO}
captura=${2:?Informe o caminho para a captura em caso de falha}
edicao=${3:-debian}
trabalho=$(mktemp -d)
serial="$trabalho/serial.log"
monitor="$trabalho/monitor"
vm=
comando_vm() {
    printf '%s\n' "$1" | socat -T 1 - "UNIX-CONNECT:$monitor" >/dev/null
}
limpar() {
    local resultado=$?
    if [[ -n "$vm" ]]; then
        if [[ "$resultado" -ne 0 && -S "$monitor" ]]; then
            comando_vm "screendump $captura" || true
        fi
        kill "$vm" 2>/dev/null || true
        wait "$vm" || true
    fi
    if [[ -f "$serial" ]]; then cat "$serial"; fi
    rm -rf -- "$trabalho"
}
trap limpar EXIT

# A mesma capacidade de 4 GiB da partição DANASLIVE, em um SSD NVMe virtual.
extraido="$trabalho/iso"
xorriso -osirrox on -indev "$iso" -extract / "$extraido"
chmod -R u+rwX "$extraido"
test -n "$(find "$extraido" -ipath '*/efi/boot/bootx64.efi' -type f -print -quit)"
if [[ "$edicao" == mint ]]; then
    test -f "$extraido/casper/filesystem.squashfs"
    # O Mint inclui atalhos de repositório que só existem em ISO9660.
    find "$extraido/dists" -type l -delete
    kernel='^7\.3\.0-[0-9]+-generic$'
else
    test -f "$extraido/live/filesystem.squashfs"
    kernel='^7\.3\.3\+deb14-amd64$'
fi
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
: > "$serial"
qemu-system-x86_64 -machine q35,smm=on,accel=tcg -smp 4 -m 4096 \
    -global driver=cfi.pflash01,property=secure,value=on \
    -drive if=pflash,format=raw,unit=0,readonly=on,file=/usr/share/OVMF/OVMF_CODE_4M.secboot.fd \
    -drive "if=pflash,format=raw,unit=1,file=$trabalho/vars.fd" \
    -display none -serial "file:$serial" -monitor "unix:$monitor,server=on,wait=off" -nic none -no-reboot \
    -drive "id=danaslive,file=$disco,format=raw,if=none" \
    -device nvme,drive=danaslive,serial=danaslive,bootindex=1 &
vm=$!
for tentativa in $(seq 1 150); do
    if grep -q '^DANASOS_XFCE_PRONTO' "$serial"; then
        grep -E "$kernel" "$serial"
        grep -F 'SecureBoot enabled' "$serial"
        grep -E '^/dev/nvme0n1p1[[:space:]]+vfat' "$serial"
        exit 0
    fi
    kill -0 "$vm"
    # O menu padrão do live-build espera uma escolha. Simula Enter na opção Live.
    if (( tentativa <= 20 && tentativa % 3 == 0 )) && [[ -S "$monitor" ]]; then
        comando_vm "sendkey ret" || true
    fi
    sleep 2
done
echo 'A sessão XFCE não confirmou o boot em NVMe/FAT32 com Secure Boot.' >&2
exit 1
