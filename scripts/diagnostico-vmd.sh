#!/bin/sh
# Ambiente descartável Debian 13. Gera apenas kernel, initramfs e entrada GRUB.
set -eu

test -f /.dockerenv
saida=${1:?Informe a pasta de saída}
abi=7.3.3+deb14-amd64
receita=$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)
trabalho=$(mktemp -d)
trap 'rm -rf -- "$trabalho"' EXIT
test ! -e "/usr/lib/modules/$abi"
mkdir -p "$saida"

sh "$receita/scripts/baixar-kernel-vmd.sh" "$trabalho"
for arquivo in "$trabalho/"*.deb; do
    dpkg-deb -x "$arquivo" /
done

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
