# Prompt reutilizável — adaptar um mapa HTML para uso em campo

Use este texto (copie e cole, ajustando o caminho do arquivo) sempre que tiver um
novo HTML de mapa autocontido para transformar da mesma forma que fizemos com o
`Projeto_Digital_Ante_Campo.html`. Não é específico de nenhum projeto — serve para
qualquer mapa (postes, caixas, CTOs, obras, vistorias etc.), mesmo que a estrutura
interna do HTML seja diferente.

---

## Prompt

> Tenho um arquivo HTML autocontido com um mapa (provavelmente Leaflet, mas pode
> ser outra biblioteca) que mostra elementos de campo a partir de dados já
> embutidos no próprio arquivo. Ele está em: **`<caminho/do/arquivo.html>`**.
>
> Quero uma **cópia** desse arquivo (não altere o original) com estas adaptações:
>
> **1. Identificação da pessoa + cor própria**
> - Ao abrir o site, pedir o nome da pessoa num campo obrigatório (aparece toda vez
>   que o site é aberto).
> - Depois de digitar, atribuir automaticamente uma cor a essa pessoa, garantida
>   diferente: (a) das cores já usadas no mapa/tema do site (linhas de rede, ícones,
>   paleta visual); (b) das cores já atribuídas a outras pessoas.
> - Guardar a relação nome → cor de forma persistente: a mesma pessoa, digitando o
>   mesmo nome de novo, deve sempre receber a mesma cor.
>
> **2. Seleção em massa no mapa**
> - Adicionar uma ferramenta de desenho (retângulo, ou polígono se fizer mais
>   sentido para o caso) que, ao terminar o desenho, seleciona todos os elementos
>   do mapa que caem dentro da área desenhada.
> - Depois de selecionar, mostrar uma barra de confirmação com a quantidade
>   selecionada e os botões **"Marcar como feito"** e **"Cancelar"**.
> - Ao confirmar, os elementos selecionados mudam para a cor da pessoa logada, e
>   deve ficar registrado quem marcou e quando.
> - Também permitir marcar/desmarcar um elemento individualmente (por exemplo, a
>   partir do popup dele no mapa).
>
> **3. Botão "Salvar" com sincronização entre pessoas**
> - Adicionar um botão "Salvar" visível e persistente na tela.
> - Este arquivo será publicado como link estático (GitHub Pages ou similar) e
>   acessado por várias pessoas ao mesmo tempo — uma marcação feita por alguém
>   precisa aparecer para as outras.
> - Como página estática não tem banco de dados próprio, use uma Planilha Google
>   como backend, via Google Apps Script publicado como Web App público. Gere:
>   (a) o código `.gs` pronto para colar (leitura via `doGet`, gravação via
>   `doPost`, com upsert por ID do elemento e `LockService` para evitar condição
>   de corrida entre gravações simultâneas);
>   (b) um guia passo a passo em português, sem jargão técnico, explicando como
>   criar a planilha, publicar o Web App, copiar a URL gerada e colá-la numa
>   constante no topo do HTML (algo como `SHEET_API_URL`).
> - Sem essa URL configurada, o site deve continuar funcionando sozinho (salvando
>   no navegador local), avisando que está em "modo local" até a planilha ser
>   configurada.
>
> **4. Filtro / localizador**
> - Campo de busca que aceite os identificadores relevantes do projeto (nome de
>   rua/endereço, código/ID do elemento, número), com sugestões automáticas
>   enquanto digita e um botão "Localizar" que dá zoom e destaque no mapa.
> - Se vários elementos baterem com o termo buscado, enquadrar todos no mapa.
>
> **Antes de programar**, investigue o arquivo para descobrir: a biblioteca de
> mapa usada, os nomes reais dos campos de dados (ID do elemento, coordenadas,
> endereço/rua, se já existe algum campo de "status/concluído"), se já existe
> alguma ferramenta de desenho/seleção no arquivo (reaproveite em vez de duplicar),
> e o padrão visual/de código já usado (classes CSS, modais, botões) para o
> resultado parecer parte do mesmo site.
>
> Esses HTMLs costumam ser enormes (dezenas de MB de dados e imagens em base64
> embutidos) — não tente ler o arquivo inteiro de uma vez. Trabalhe em cópias
> menores sem essas linhas grandes, usando marcadores para recolocá-las depois via
> shell, sem nunca carregar o conteúdo delas no contexto. Ao final, valide a
> sintaxe do JavaScript resultante antes de entregar, e sempre gere uma cópia nova
> (nunca sobrescreva o arquivo original).
>
> Pergunte apenas o que for realmente uma decisão minha (ex.: se prefiro
> sincronizar via planilha, outro backend, ou só localStorage) — não pergunte
> detalhes que dá para decidir olhando o próprio arquivo.

---

## Dicas ao reutilizar

- Troque `<caminho/do/arquivo.html>` pelo caminho real do novo mapa.
- Se o novo mapa já tiver conceito de "status" diferente de "feito/não feito"
  (ex.: várias etapas), descreva isso no prompt para adaptar a barra de confirmação.
- Se quiser reaproveitar a **mesma planilha/backend** entre vários mapas (em vez de
  criar uma planilha nova por projeto), diga isso explicitamente — dá pra usar o
  mesmo Apps Script, filtrando por um campo de projeto/cidade, como já foi feito
  aqui (`cidade` + `run_id`).
- O arquivo `Codigo_Planilha_AppsScript.gs` gerado para este projeto é um bom ponto
  de partida: em muitos casos só precisa trocar o nome do campo `cod_id` pelo
  identificador do novo projeto.
