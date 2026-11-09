# danasOS 0.2 • Noite em Neon

Projeto de distribuição Linux para jogos, com identidade, tema, configuração e receita de imagem próprios. A base de pacotes e atualizações é o Debian 13. A área de trabalho é Xfce e o instalador gráfico é Calamares.

Este ZIP contém o **código-fonte e o construtor da ISO**. A imagem ainda precisa ser compilada e testada em uma máquina Linux. Quando compilada, ela sobe direto do pendrive e instala o danasOS no SSD. A instalação copia a imagem do sistema com os aplicativos integrados.

## O que entra na imagem

| Área | Componentes |
| --- | --- |
| Visual | GTK roxo e verde-neon, papel de parede Noite em Neon, tela de login e Central danasOS |
| Uso diário | Firefox, Thunar, editor de texto, leitor PDF, visualizador de imagens, compactador e captura de tela |
| Loja | GNOME Software com pacotes do Debian e Flathub, acessível como Loja danasOS |
| Jogos | Steam com Proton, Heroic, Lutris, Bottles, Prism Launcher e Faugus, pré-instalados pelo construtor |
| Rede e som | NetworkManager, Wi‑Fi, Bluetooth, PipeWire, firmware Intel SOF e firmware para adaptadores comuns |
| Gráficos | Mesa e Vulkan, microcódigo Intel/AMD, utilitário de instalação do driver aberto da NVIDIA |
| Inicialização | Xfce com dependências recomendadas do APT desabilitadas na compilação. Loja e launchers sem entrada ativa de início automático na instalação limpa |
| Instalação | ISO híbrida amd64, sessão live, Calamares e cadeia de boot UEFI assinada do Debian |

O instalador inclui o firmware do Wi‑Fi Intel Killer AX1675i e das GPUs. A RTX 5070 Laptop usa os módulos de kernel abertos da NVIDIA com componentes de usuário do fabricante. O driver NVIDIA é instalado na máquina final para o DKMS gerar uma chave própria, quando for preciso usar MOK. AMD e Intel usam o stack Mesa e o kernel da imagem.

## Gerar a ISO

No GitHub, depois de enviar a pasta do projeto, abra **Actions → Compilar ISO do danasOS → Run workflow** na branch principal. O workflow usa uma máquina Linux do GitHub e precisa de espaço livre suficiente. Se terminar com sucesso, a ISO e o checksum vão para um **rascunho** em **Releases**. O rascunho fica disponível para revisão e teste antes da publicação.

Se o rascunho contiver arquivos `.part-000`, `.part-001` e seguintes, baixe todas as partes, o `.sha256` e o `juntar-iso.ps1` para a mesma pasta. Abra o PowerShell nessa pasta e execute `./juntar-iso.ps1`. O script verifica o SHA-256 antes de disponibilizar a ISO.

### Compilar numa VM local

Use uma VM **Debian 13 amd64**, de preferência instalada sem interface gráfica para compilar. Reserve um disco virtual de 50 GiB ou mais, com pelo menos 25 GiB livres, e conexão à internet. Extraia o ZIP dentro do disco virtual Linux e abra um terminal na pasta extraída.

```sh
sudo apt-get update
sudo apt-get install live-build xorriso squashfs-tools grub-efi-amd64-bin mtools dosfstools
sudo python3 build.py
```

Resultado esperado em `dist/`:

- `danasOS-0.2-amd64.iso`
- `danasOS-0.2-amd64.sha256`

O construtor usa um diretório separado por execução. Se um dos launchers falhar no download, a construção para para evitar publicar uma imagem incompleta. Se faltar espaço ou houver um erro de download, o log do terminal indica a etapa. A ISO é disponibilizada na pasta de saída somente quando a compilação, a inspeção do catálogo UEFI e o cálculo do SHA-256 terminarem.

Para gerar a edição de distribuição pública, use `sudo python3 build.py --publica`. Essa edição inclui os arquivos de fontes Debian e da configuração live e oferece a instalação dos launchers pela Central a partir do Flathub.

## Atualizações pela loja e pelo GitHub

Na **Central danasOS → Atualizações → Abrir loja**, a loja mostra atualizações do Debian e do Flathub. O pacote `danasos-experience`, instalado durante a construção da ISO, permite distribuir novas versões da Central e do tema pelo mesmo fluxo.

A instalação automática vem desligada. Depois de cadastrar o canal assinado, selecione **Central danasOS → Atualizações → Ativar automática** e autorize com a senha do sistema. O agendador verifica o canal diariamente, instala somente versões mais novas de `danasos-experience` e registra o resultado em `journalctl -u danasos-auto-update.service`. A instalação usa índices separados dos repositórios do sistema e exige a assinatura da chave cadastrada. A opção **Desativar automática** cancela as próximas verificações.

### Lançar uma versão

1. Coloque o projeto num repositório GitHub e em **Settings → Pages → Source** escolha **GitHub Actions**. Use um repositório que permita publicar no Pages.
2. Use uma chave OpenPGP exclusiva para o projeto. Guarde a chave privada e sua cópia de segurança protegida fora da pasta do repositório. A variável de Actions **DANASOS_APT_FINGERPRINT** recebe somente o fingerprint público. Restrinja o ambiente `github-pages` à branch principal e mantenha o Push Protection ligado.
3. Em um Linux com `apt-utils`, `dpkg` e `gnupg`, assine a versão com `python3 publicar.py --versao 0.2-3 --saida pasta-temporaria/apt --fingerprint FINGERPRINT_COMPLETO`. Use uma versão maior que a instalada. A assinatura acontece no Linux onde está sua chave.
4. Copie somente os arquivos gerados para `publicacao/apt/` e exporte a **chave pública** com `gpg --armor --export FINGERPRINT_COMPLETO > publicacao/danasos-publica.asc`. Depois de enviar esses arquivos, abra **Actions → Publicar atualização do danasOS → Run workflow**. O workflow verifica a assinatura, o conteúdo do pacote e os hashes antes de publicar. A URL do Pages aparece no resultado.

### Conectar uma instalação ao canal

Salve a chave pública que recebeu do mantenedor e confira o fingerprint por um canal confiável. Use a URL real do seu Pages e o fingerprint completo:

```sh
sudo danasos-canal-github https://USUARIO.github.io/REPOSITORIO/apt/ ./danasos-publica.asc FINGERPRINT_COMPLETO
```

Abra **Central danasOS → Atualizações** e atualize a lista. O canal APT aceita somente o pacote `danasos-experience` do host configurado, com a assinatura da chave cadastrada. Os outros pacotes continuam nas fontes do Debian e do Flathub. Use uma nova compilação da ISO para mudanças nos pacotes de base ou no instalador. A publicação e a conexão dependem de um repositório GitHub Pages e de uma chave ainda não configurados.

## Validar antes de usar no Acer

1. Confira o hash com `sha256sum -c danasOS-0.2-amd64.sha256`. Crie outra VM com disco virtual em branco, firmware UEFI e Secure Boot com as chaves padrão do firmware.
2. Dê boot pela ISO. Abra a Central, a loja e os launchers. Confira `flatpak list --app` e o menu do Xfce. Teste o instalador no **disco virtual**, retire a ISO e reinicie.
3. No sistema instalado, confira a identidade com `cat /etc/os-release`, a GPU com `vulkaninfo --summary` e o Secure Boot com `mokutil --sb-state`. Saia da conta e faça login de novo para verificar que os launchers ficaram fechados.
4. No Acer, primeiro teste a sessão live pelo pendrive. Confira tela e taxa de atualização, touchpad, Wi‑Fi, Bluetooth, áudio e se o SSD aparece. O teste do driver NVIDIA e a comparação de RAM e FPS com o Mint devem ser feitos depois do boot pelo SSD.

## Dual boot com o Windows

Faça backup. Confira se o Windows usa BitLocker ou Criptografia do Dispositivo e deixe a [chave de recuperação](https://support.microsoft.com/pt-br/windows/security/encryption/find-your-bitlocker-recovery-key) acessível fora do notebook. Mantenha Secure Boot ativo e reserve o espaço do Linux no Gerenciamento de Disco do Windows.

Grave a ISO verificada num pendrive que possa ser apagado. Confira o disco de destino no gravador e inicialize pelo pendrive em modo UEFI. No Calamares, revise a prévia das mudanças antes de confirmar. Use exclusivamente a área destinada ao Linux e preserve as partições do Windows, EFI e recuperação. Em particionamento manual, a partição Linux pode ser ext4 montada em `/`. Use a partição EFI existente em `/boot/efi` **sem formatá-la**. Se o SSD sumir, a opção lado a lado pedir para encolher uma partição criptografada ou houver dúvida sobre o mapa de partições, saia do instalador antes da confirmação.

Após a instalação, confirme que o Windows Boot Manager continua disponível no menu UEFI e que ambos iniciam. O GRUB é configurado para procurar outros sistemas.

## RTX 5070 Laptop e jogos

No danasOS instalado, abra a **Central → Driver NVIDIA** ou rode:

```sh
sudo danasos-driver-nvidia
```

O utilitário adiciona o repositório APT oficial da NVIDIA para Debian 13 e instala `nvidia-open`. Se solicitar o cadastro da chave MOK, escolha **Enroll MOK** na próxima inicialização e informe a senha temporária. Depois confira `nvidia-smi -L` e atualize os Flatpaks pela loja para baixar a extensão gráfica correspondente ao driver.

Na Steam, use Proton quando o jogo precisar da camada de compatibilidade. No primeiro uso, os launchers ainda podem pedir login e baixar atualizações e runtimes. Mantenha desligada a opção de iniciar com o sistema dentro dos próprios clientes. Para Fortnite, Warzone e jogos instalados pelo aplicativo Xbox do PC Game Pass, use o Windows.

## Estado da entrega

A receita, os scripts e os arquivos de tema foram validados localmente no Windows. O ambiente disponível não tem um Linux funcional para executar o live-build. A ISO, a instalação real, o boot com Secure Boot, o carregamento do driver e os números de RAM/FPS ainda aguardam teste.

## Referências

- [Debian Live e Calamares](https://www.debian.org/CD/live/)
- [Manual do Debian Live](https://live-team.pages.debian.net/live-manual/html/live-manual/index.en.html)
- [Secure Boot no Debian](https://wiki.debian.org/SecureBoot)
- [NVIDIA para Debian](https://docs.nvidia.com/datacenter/tesla/driver-installation-guide/debian.html)
- [Steamworks sobre Proton](https://partner.steamgames.com/doc/steamdeck/proton)
