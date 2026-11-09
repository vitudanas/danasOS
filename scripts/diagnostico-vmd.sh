#!/bin/sh
# Ambiente descartável Debian 13. Gera apenas kernel, initramfs e entrada GRUB.
set -eu

test -f /.dockerenv
saida=${1:?Informe a pasta de saída}
abi=7.3.3+deb14-amd64
versao=7.3.3-1
repo=https://deb.debian.org/debian/pool/main/l
receita=$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)
trabalho=$(mktemp -d)
trap 'rm -rf -- "$trabalho"' EXIT
test ! -e "/usr/lib/modules/$abi"
mkdir -p "$saida"

# SHA-256 do índice amd64 do Debian, autenticado pelo InRelease de sid.
extrair() {
    arquivo="$2-${abi}_${versao}_amd64.deb"
    curl -fLsS --retry 3 "$repo/$1/$arquivo" -o "$trabalho/$arquivo"
    printf '%s  %s\n' "$3" "$trabalho/$arquivo" | sha256sum -c -
    dpkg-deb -x "$trabalho/$arquivo" /
}
extrair linux linux-base 8ea48e0c7aeb709c895c13699f09676de9a236183a17124572bc695d70b23cb1
extrair linux linux-modules 40073c12c078013c2127fe43e8510c1fa6c73b15fe2411fa18dff72dd84fead3
extrair linux-signed-amd64 linux-binary bf17f1f217b3af4195128febf01ca2fc0cdb0163bf4a7c64f6bf5d2d5362bb43

kernel="/usr/lib/modules/$abi/vmlinuz"
sbverify --list "$kernel"
depmod "$abi"
cp "/usr/lib/modules/$abi/config" "/boot/config-$abi"

config="$trabalho/initramfs-tools"
cp -a /etc/initramfs-tools "$config"
cp "$receita/config/includes.chroot/etc/initramfs-tools/modules" "$config/modules"
mkdir -p "$config/scripts/init-premount"
cat > "$config/scripts/init-premount/danasos-vmd" <<'SCRIPT'
#!/bin/sh
case "${1:-}" in prereqs) exit 0 ;; esac
udevadm settle --timeout=15 || true
echo '=== danasOS: teste de armazenamento antes de montar o sistema ==='
uname -r
cat /proc/partitions
if [ -d /sys/class/nvme ]; then
    ls /sys/class/nvme
fi
echo 'DANASOS_VMD_DIAGNOSTICO_PRONTO'
SCRIPT
chmod 755 "$config/scripts/init-premount/danasos-vmd"
mkinitramfs -d "$config" -o "$saida/initrd.img" "$abi"
lsinitramfs "$saida/initrd.img" > "$trabalho/conteudo"
for modulo in vmd nvme nvme-core; do
    grep -E "/$modulo\.ko(\.[[:alnum:]]+)?$" "$trabalho/conteudo"
done
cp "$kernel" "$saida/vmlinuz"
cat > "$saida/grub.cfg" <<'GRUB'
set timeout=5
set default=0
menuentry "danasOS: testar NVMe e Intel VMD (Debian 7.3.3)" {
    search --no-floppy --file --set=root /danas-vmd/vmlinuz
    linux /danas-vmd/vmlinuz break=mount ro
    initrd /danas-vmd/initrd.img
}
GRUB
(cd "$saida" && sha256sum vmlinuz initrd.img grub.cfg > SHA256SUMS)
