# Como fazer todo mundo ver o mesmo progresso (planilha compartilhada)

O arquivo `Projeto_Digital_Ante_Campo.html` já funciona sozinho: cada
pessoa que abrir o link se identifica, ganha uma cor e pode marcar
postes como feitos. Mas para que **todo mundo veja a mesma coisa**
(o poste que a Maria marcou aparecer colorido também na tela do João),
o site precisa de uma planilha por trás — é exatamente essa peça que
este guia monta. Leva uns 10 minutos e não precisa saber programar,
é só copiar e colar.

## Passo 1 — Criar a planilha

1. Acesse [sheets.google.com](https://sheets.google.com) e crie uma
   planilha em branco.
2. Dê um nome a ela, por exemplo **"Progresso Postes — Araxá"**.
3. Não precisa criar nenhuma aba/coluna manualmente — o código do
   Passo 2 cria tudo sozinho na primeira vez que for usado.

## Passo 2 — Colar o código que liga a planilha à internet

1. Na planilha, vá em **Extensões → Apps Script**.
2. Apague qualquer código que já esteja lá (geralmente um
   `function myFunction() {}` vazio).
3. Abra o arquivo **`Codigo_Planilha_AppsScript.gs`** (está nesta
   mesma pasta), copie tudo e cole no editor do Apps Script.
4. Clique no ícone de disquete (Salvar projeto). Pode dar o nome que
   quiser, por exemplo "Backend Postes".

## Passo 3 — Publicar como "Aplicativo da Web"

1. No editor do Apps Script, clique em **Implantar → Nova implantação**.
2. Em "Selecionar tipo", clique na engrenagem e escolha
   **Aplicativo da Web**.
3. Configure:
   - **Executar como:** Eu (seu e-mail)
   - **Quem pode acessar:** Qualquer pessoa
4. Clique em **Implantar**. O Google vai pedir para autorizar o
   script — autorize com sua conta Google (é normal aparecer um aviso
   de "app não verificado"; clique em "Acessar (não seguro)" e depois
   em "Permitir", pois o app é seu e feito por você).
5. Copie a **URL do aplicativo da Web** que aparece (termina em
   `/exec`). Guarde essa URL, ela é a "chave" que liga o site à
   planilha.

> Dica: se você editar o código depois, precisa criar uma **nova
> versão** da mesma implantação (Implantar → Gerenciar implantações →
> ✏️ Editar → Nova versão) para as mudanças valerem — a URL continua
> a mesma.

## Passo 4 — Colar a URL no site

1. Abra `Projeto_Digital_Ante_Campo.html` num editor de texto (Bloco
   de Notas, VS Code, etc.).
2. Procure por esta linha, perto do começo do `<script>`:

   ```js
   const SHEET_API_URL='';
   ```

3. Cole a URL do Passo 3 entre as aspas, assim:

   ```js
   const SHEET_API_URL='https://script.google.com/macros/s/SEU_ID_AQUI/exec';
   ```

4. Salve o arquivo.

Pronto — a partir de agora, quando alguém marcar postes e clicar em
**"Salvar progresso"**, os códigos (`cod_id`) desses postes entram na
aba **Postes** da planilha, junto com o nome e a cor da pessoa. Toda
vez que o site é aberto (ou a cada ~25 segundos com a página aberta),
ele consulta a planilha de novo e atualiza as cores no mapa — assim
todo mundo que acessar o link vê o mesmo progresso.

## Passo 5 — Publicar no GitHub Pages

1. Suba `Projeto_Digital_Ante_Campo.html` (já com a `SHEET_API_URL`
   preenchida) para o seu repositório no GitHub.
2. Em **Settings → Pages**, ative o GitHub Pages apontando para a
   branch onde está o arquivo.
3. Compartilhe o link gerado. Qualquer pessoa que abrir esse link:
   - se identifica com o nome dela;
   - ganha (ou recupera) a cor dela;
   - pode marcar postes e ver o progresso de todo mundo.

## Perguntas comuns

**A planilha vira um Excel de verdade?**
Sim — é uma Planilha Google, mas você pode baixá-la como `.xlsx` a
qualquer momento em **Arquivo → Fazer download → Microsoft Excel**.
Ela é a fonte da verdade: cada linha da aba "Postes" é um poste
marcado como feito (`cod_id`, cidade, quem marcou, a cor e quando).

**Não quero configurar planilha agora, dá pra usar assim mesmo?**
Dá. Sem a `SHEET_API_URL` preenchida, o site funciona 100% localmente
no navegador de cada pessoa (as marcações ficam salvas ali, mesmo
fechando e abrindo de novo) — só não aparecem para as outras pessoas
até você configurar a planilha depois. O indicador ao lado do botão
"Salvar progresso" mostra "Modo local" nesse caso.

**Como sei se está funcionando?**
Abra o site, identifique-se, marque um poste como feito e veja o
indicador mudar para "Tudo sincronizado ✓". Depois abra a URL do
Passo 3 direto no navegador (ela deve mostrar um JSON com o poste que
você marcou) — se aparecer, a planilha está recebendo os dados
corretamente.

**Erro "Não sincronizou" aparecendo sempre?**
- Confira se copiou a URL completa (termina em `/exec`, não `/dev`).
- Confira se em "Quem pode acessar" está "Qualquer pessoa".
- Abra o Console do navegador (F12) na aba "Console" para ver a
  mensagem de erro exata.
