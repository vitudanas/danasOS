# Publicar o canal de experiência

O cliente consulta `https://vitudanas.github.io/danasOS/apt/`. Mantenha o índice e o pacote no mesmo commit da branch de publicação, com `.nojekyll` e GitHub Pages servindo a raiz. Use somente arquivos de uma execução bem-sucedida de **Validar e empacotar atualização danasOS**. O workflow antigo de Pages na branch padrão era uma alternativa e dependia de outra configuração de publicação.

1. Aumente `VERSAO_INICIAL` e atualize os changelogs. Valide o pacote em Linux antes da assinatura.
2. No ambiente do mantenedor, confira o SHA-256 do artefato da CI, o pacote em `Packages` e a entrada de `Packages` na seção SHA256 de `Release`.
3. Assine `Release` com o fingerprint oficial `03F1100B22C6C9760977042E0FCEC1F004C97E6B`, gerando `InRelease` com `gpg --local-user FINGERPRINT --output InRelease --clearsign Release`. A assinatura destacada do primeiro pacote acompanha o bootstrap documentado em [ATUALIZAR.md](ATUALIZAR.md).
4. Em Linux, rode `python3 verificar-canal.py publicacao DESTINO FINGERPRINT`, com `publicacao/danasos-publica.asc` e `publicacao/apt/`. Confira o material preparado antes de enviar a publicação.
5. Leia novamente `InRelease`, `Packages` e o pacote pela URL pública após o deploy. Verifique a assinatura e os hashes recebidos. Publique versões crescentes e renove o índice antes da data `Valid-Until` de 90 dias, inclusive quando a versão permanecer igual.

A chave de release foi criada no perfil local do mantenedor com frase protegida pelo Windows. Faça um backup privado recuperável da chave e da revogação antes de depender dela em outra máquina. Use a CI com chave efêmera para testes. A chave pública está no pacote, mas uma rotação futura deve chegar em versão assinada pela chave que os clientes já confiam.
