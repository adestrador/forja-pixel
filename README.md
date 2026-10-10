# Forja Pixel

Site de traduções, correções e scripts autorais, preparado para [GitHub Pages](https://docs.github.com/pt/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site). O GitHub gera uma versão estática do site quando você altera o repositório do site ou aciona a publicação manualmente.

## Publicar pela primeira vez

1. Crie um repositório **público** chamado `forja-pixel` na conta `adestrador`, sem gerar README inicial.
2. Envie **o conteúdo desta pasta** à raiz desse repositório. O arquivo `.github/workflows/pages.yml` e os arquivos ocultos devem ser incluídos.
3. Em **Settings → Pages → Build and deployment → Source**, selecione **GitHub Actions**.
4. Aguarde a execução **Publicar Forja Pixel** na aba **Actions**. O endereço esperado é `https://adestrador.github.io/forja-pixel/`.

O repositório do site é separado dos repositórios dos mods. Estes continuam sendo a fonte dos arquivos para download.

## Atualizar após criar um repositório

Depois de criar ou alterar um projeto público, abra [Publicar Forja Pixel](https://github.com/adestrador/forja-pixel/actions/workflows/pages.yml) na sua conta GitHub. Clique em **Run workflow** (ou **Executar fluxo de trabalho**) e confirme em **Run workflow**. Ao terminar a execução, o site estará atualizado. Você não precisa copiar o mod, editar o site nem repetir isso todos os dias.

O fluxo consulta os repositórios públicos de `adestrador`. Repositórios derivados (forks), arquivados e o próprio `forja-pixel` ficam fora. Um projeto novo ganha um card e uma página estática própria, com título, descrição, link ao GitHub, URL própria e entrada no mapa do site. O visitante vê a versão já publicada; a visita não aciona a sincronização.

Uma ficha criada assim é básica: o site não consegue adivinhar compatibilidade e instruções de instalação. Para uma página completa como as quatro iniciais, use o editor abaixo. Se a API do GitHub falhar durante a publicação, o fluxo falha e a versão anterior do site continua disponível. A existência de uma página própria facilita sua descoberta por buscadores, mas a indexação não é garantida.

## Adicionar ou editar pelo painel

Depois da primeira publicação, abra `https://adestrador.github.io/forja-pixel/admin/`. Escolha um projeto existente ou **Novo projeto**, preencha a ficha e clique em **Baixar ficha .json**. O painel inclui as instruções para enviar o arquivo à pasta `projetos` do repositório. O painel não pede senha nem grava direto no GitHub; apenas quem pode confirmar alterações no repositório pode publicar.

## Adicionar um projeto diretamente pelo GitHub

1. No repositório `adestrador/forja-pixel`, abra a pasta `projetos` e escolha **Add file → Create new file**.
2. Dê ao arquivo um nome curto, sem espaços ou acentos, terminado em `.json`, por exemplo `jogo-novo-ptbr.json`.
3. Copie o conteúdo de `projetos/MODELO.json.txt`, ajuste os campos e deixe `slug` igual ao nome do arquivo sem `.json`.
4. Use `category` como `traducoes`, `mods`, `correcoes` ou `scripts`. Coloque a URL do seu repositório em `repo`; em `download`, use a página de lançamento ou o link direto do arquivo.
5. Clique em **Commit changes**. O GitHub recria a capa, a página individual e o mapa do site automaticamente. Veja o resultado na aba **Actions**.

## Editar ou remover

Para editar, abra o arquivo correspondente em `projetos`, clique no lápis, altere e confirme. Para remover, exclua o arquivo e confirme. Cada alteração publicada mantém os links dos demais projetos.

Uma nova descrição de um repositório com ficha básica entra na próxima publicação manual. Para fichas detalhadas criadas no editor, os campos `version`, instruções e descrição são manuais. O link `releases/latest` acompanha a versão mais recente.

Os campos `features` e `steps` são listas de frases. O campo `art` aceita `turing`, `descendant`, `andromeda` ou `script` para o fundo decorativo. Não há prints por padrão. Um JSON inválido faz a publicação falhar e preserva o site anterior; a mensagem de erro aparece em **Actions**.

## Testar no computador

```bash
SITE_ORIGIN=https://adestrador.github.io/forja-pixel python3 build.py
```

O resultado fica em `dist/`. A página inicial é `dist/index.html`.
Para testar a sincronização, acrescente `SYNC_GITHUB_REPOS=1`; no GitHub Actions, o fluxo usa `GITHUB_TOKEN` automaticamente.

## Endereço próprio

O endereço gratuito usa `github.io`. Para usar um domínio como `forjapixel.com.br`, é preciso ter esse domínio e configurá-lo em **Settings → Pages → Custom domain**, além dos registros DNS. Depois, ajuste `SITE_ORIGIN` no fluxo de publicação para o domínio escolhido.

## Créditos

A capa foi criada para Forja Pixel. Marcas e jogos pertencem aos respectivos titulares; as traduções são projetos independentes e não oficiais.
