# Atualizar o danasOS já instalado

O primeiro pacote instala a configuração do canal oficial e a chave pública do projeto. Depois da primeira atualização, use **Central danasOS → Atualizações → Verificar** ou **Ativar automática**. Não é necessário iniciar pelo pendrive.

No terminal do **danasOS instalado**, copie o bloco abaixo uma vez. Ele baixa arquivos para uma pasta temporária, verifica o fingerprint e a assinatura do pacote, e só então pede autorização para instalar. Se qualquer verificação falhar, ele encerra sem instalar.

```sh
(
  set -eu
  pasta=$(mktemp -d)
  trap 'rm -rf -- "$pasta"' EXIT
  cd "$pasta"
  canal=https://vitudanas.github.io/danasOS
  pacote=danasos-experience_0.4-1_all.deb
  chave=03F1100B22C6C9760977042E0FCEC1F004C97E6B
  atual=$(dpkg-query -W -f='${Version}' danasos-experience)
  if dpkg --compare-versions "$atual" ge 0.4-1; then
    printf '%s\n' 'Já está nesta versão ou em uma versão mais recente. Use a Central.'
    exit 0
  fi
  mkdir -m 700 gnupg
  baixar() { curl --fail --silent --show-error --location --proto '=https' --proto-redir '=https' --output "$2" "$canal/$1"; }
  baixar danasos-release.asc publica.asc
  baixar "apt/$pacote" "$pacote"
  baixar "$pacote.sig" "$pacote.sig"
  gpg --homedir "$pasta/gnupg" --batch --with-colons --show-keys publica.asc > chave.txt
  test "$(awk -F: '$1=="pub" {n++} END {print n+0}' chave.txt)" = 1
  test "$(awk -F: '$1=="fpr" {print $10; exit}' chave.txt)" = "$chave"
  gpg --homedir "$pasta/gnupg" --batch --dearmor --output publica.gpg publica.asc
  gpgv --homedir "$pasta/gnupg" --keyring "$pasta/publica.gpg" "$pacote.sig" "$pacote"
  sudo apt install "./$pacote"
)
```

Feche a Central anterior, abra-a novamente e selecione **Atualizações → Ativar automática**. A verificação diária se aplica ao pacote danasOS. O Gerenciador de Atualizações do Mint continua gerenciando os pacotes do sistema, e a loja gerencia os Flatpaks.

O botão de recuperação aparece quando a Central tem uma versão anterior verificada no cache. A primeira migração da 0.2-2 ainda não tem essa cópia. A recuperação desativa a atualização automática para não reinstalar imediatamente a versão que você acabou de reverter.

Para aumentar fontes sem trocar os Hz, abra **Configurações danasOS → Tamanho do texto**. Para trocar frequência ou resolução, use **Monitores, resolução, escala e Hz** e confirme apenas quando todos os monitores exibirem imagem. Se algum apagar, aguarde a reversão do módulo de vídeo do Xfce.
