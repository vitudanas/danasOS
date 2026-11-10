#!/usr/bin/env bash
set -euo pipefail

tmp=$(mktemp -d)
relogio_original=$(date -u +%s)
inicio=$SECONDS
relogio_ajustado=0
limpar() {
    if [ "$relogio_ajustado" -eq 1 ]; then
        sudo date -u --set "@$((relogio_original + SECONDS - inicio))" >/dev/null
    fi
    rm -rf -- "$tmp"
}
trap limpar EXIT
mkdir "$tmp/bin" "$tmp/usuario" "$tmp/chave-alternativa"
chmod 700 "$tmp/chave-alternativa"
fpr=03F1100B22C6C9760977042E0FCEC1F004C97E6B
pacote=danasos-experience_0.4-1_all.deb

extrair_bloco() {
    awk '/^```sh$/ {bloco=1; next} /^```$/ && bloco {exit} bloco {print}'
}

extrair_bloco < ATUALIZAR.md > "$tmp/bootstrap.sh"
git show 3a73eb7:ATUALIZAR.md | extrair_bloco > "$tmp/anterior.sh"
test -s "$tmp/bootstrap.sh"
test -s "$tmp/anterior.sh"
sh -n "$tmp/bootstrap.sh"

gpg --no-options --homedir "$tmp/chave-alternativa" --batch --passphrase '' \
    --quick-generate-key 'Chave alternativa de teste' ed25519 sign 1d
gpg --no-options --homedir "$tmp/chave-alternativa" --batch --armor --export > "$tmp/alternativa.asc"

cat > "$tmp/bin/curl" <<'SH'
#!/bin/sh
set -eu
/usr/bin/curl "$@"
saida=
for argumento do
    if [ "$saida" = procurar ]; then saida=$argumento; break; fi
    if [ "$argumento" = --output ]; then saida=procurar; fi
done
case "$CASO:$saida" in
    chave:publica.asc) cp "$CHAVE_ALTERNATIVA" "$saida" ;;
    pacote:*.deb) printf 'arquivo alterado\n' >> "$saida" ;;
    assinatura:*.sig)
        python3 -c 'from pathlib import Path; import sys; p=Path(sys.argv[1]); b=bytearray(p.read_bytes()); b[-1]^=1; p.write_bytes(b)' "$saida"
        ;;
esac
SH
cat > "$tmp/bin/sudo" <<'SH'
#!/bin/sh
printf '%s\n' 'O bloco chegou ao sudo.' >> "$MARCADOR_SUDO"
exit 42
SH
chmod +x "$tmp/bin/"*

versao() { dpkg-query -W -f='${Version}' danasos-experience; }
execucao_isolada() {
    env -u GNUPGHOME HOME="$tmp/usuario" LC_ALL=C "$@"
}

export CHAVE_ALTERNATIVA="$tmp/alternativa.asc" MARCADOR_SUDO="$tmp/chamou-sudo"
test "$(versao)" = 0.2-2
test ! -e "$tmp/usuario/.gnupg"

status_anterior=0
execucao_isolada env PATH="$tmp/bin:$PATH" CASO=anterior sh -x "$tmp/anterior.sh" \
    > "$tmp/anterior.log" 2>&1 || status_anterior=$?
cat "$tmp/anterior.log"
if [ "$status_anterior" -eq 42 ] && [ -f "$MARCADOR_SUDO" ]; then
    echo 'O bloco anterior verificou os arquivos públicos neste ambiente limpo.'
else
    printf 'O bloco anterior falhou antes de instalar, código %s.\n' "$status_anterior"
fi
rm -f -- "$MARCADOR_SUDO"

# A VM descartável pode estar atrás da data de publicação. Primeiro teste
# a recusa nessa condição, depois execute com um horário válido de teste.
if [ "$relogio_original" -lt 1794346264 ]; then
    if execucao_isolada env PATH="$tmp/bin:$PATH" CASO=relogio sh -x "$tmp/bootstrap.sh" \
        > "$tmp/relogio.log" 2>&1; then
        echo 'O bloco aceitou o relógio atrasado.' >&2
        exit 1
    fi
    cat "$tmp/relogio.log"
    grep -Fq 'Relógio atrasado' "$tmp/relogio.log"
    test ! -e "$MARCADOR_SUDO"
    relogio_ajustado=1
    sudo date -u --set '@1794346564'
fi

for caso in chave pacote assinatura; do
    if execucao_isolada env PATH="$tmp/bin:$PATH" CASO="$caso" sh -x "$tmp/bootstrap.sh" \
        > "$tmp/$caso.log" 2>&1; then
        cat "$tmp/$caso.log"
        echo "O bloco aceitou a entrada alterada: $caso" >&2
        exit 1
    fi
    cat "$tmp/$caso.log"
    test ! -e "$MARCADOR_SUDO"
    test "$(versao)" = 0.2-2
    if [ "$caso" = chave ]; then
        grep -Fq 'Chave recusada:' "$tmp/$caso.log"
        if grep -q '^+ gpgv ' "$tmp/$caso.log"; then exit 1; fi
    else
        grep -Fxq "Fingerprint confirmado: $fpr" "$tmp/$caso.log"
        grep -q '^+ gpgv ' "$tmp/$caso.log"
        if grep -Fxq 'Assinatura oficial do pacote confirmada.' "$tmp/$caso.log"; then exit 1; fi
    fi
    printf 'Rejeitado antes de sudo: %s\n' "$caso"
done

test ! -e "$tmp/usuario/.gnupg"
execucao_isolada sh -x "$tmp/bootstrap.sh" < <(printf 'y\n') > "$tmp/positivo.log" 2>&1 || {
    cat "$tmp/positivo.log"
    exit 1
}
cat "$tmp/positivo.log"
awk -v fpr="$fpr" -v pacote="$pacote" '
    $0 == "Fingerprint confirmado: " fpr { chave=NR }
    $0 == "Assinatura oficial do pacote confirmada." { assinatura=NR }
    $0 == "+ sudo apt install ./" pacote { instalacao=NR }
    END { exit !(chave && assinatura > chave && instalacao > assinatura) }
' "$tmp/positivo.log"
test "$(versao)" = 0.4-1
test ! -e "$tmp/usuario/.gnupg"
echo 'Bootstrap literal aprovado: fingerprint, assinatura, três recusas e instalação 0.4-1.'
