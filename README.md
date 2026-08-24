# Ante Projeto Elétrico — Araxá/MG — Validação Fotográfica de Postes

Este projeto automatiza (parcialmente) a etapa de evidenciação fotográfica de postes
descrita no **[Guia de Procedimento — Validação e Evidenciação de Postes v2.2](DOCUMENTACAO/Guia_Validacao_Postes_AnteProjeto_Eletrico_v2.2.pdf)**.
Este README existe pra guardar o contexto e as decisões tomadas — leia antes de mexer em
qualquer coisa aqui.

## Estrutura de pastas do projeto (reorganizado 23/ago)

Reorganizado a pedido do usuário — estava tudo solto na raiz, confuso pra bater o olho e
achar as coisas. Regra geral aplicada em tudo, não só nas fotos de postes: **nome em
português, categoria clara, e revisão sempre separada do aprovado.**

| Pasta | O que tem |
|---|---|
| `BASE DE DADOS/` | Dados-fonte, só consulta, **nunca editar**: `lista_postes.csv` (base oficial, mesma fonte da planilha do guia, regra §5.6), `esquina_index.csv` (nossa derivação, ver critério abaixo), `Projeto_Digital_Ante.html` (grafo completo da rede), `mapa_esquinas.html` (mapa interativo usado pra calibrar o critério de esquina) |
| `DOCUMENTACAO/` | `Guia_Validacao_Postes_AnteProjeto_Eletrico_v2.2.pdf` — o procedimento oficial |
| `FILA DE TRABALHO/` | `links_pendentes.xlsx` — fila de links que o usuário vai preenchendo; ver seção própria abaixo |
| `RELATORIOS/` | Logs e conferências geradas pelo pipeline: `lote_teste_0X_log.csv` (histórico, pipeline CV), `lote_links_01_log.csv` / `conferencia_links_lote01.csv` (histórico, pipeline de link), `colisoes_cod_id.csv` (histórico, formato antigo, não é mais escrito), `confirmar_manual.xlsx` (todo arquivo `!!` não-duplicata, com link+motivo — ver protocolo abaixo), `duplicados_para_validar.xlsx` (todo cod_id duplicado, com os links dos dois lados pra decidir qual é o certo), `links_postes_processados.xlsx` (planilha-mestre: **todo** cod_id já processado, qualquer lote, com `link_usado` + `link_original_base` lado a lado — ver seção própria abaixo) |
| `POSTES UTILIZADOS/` | As fotos em si — ver estrutura detalhada logo abaixo |
| `pipeline/` | Código (inalterado por essa reorganização, só os caminhos internos foram atualizados) |

### Dentro de `POSTES UTILIZADOS/`

**Regra de ouro: nada é escrito automaticamente numa pasta "- OK".** Toda saída do
pipeline cai numa fila "- REVISAO". Uma pasta "- OK" só recebe arquivo quando uma pessoa
confirma a foto e move manualmente pra lá — isso é reforçado em código
(`pipeline/routing.py`, função `dest_dir_for`), não é só uma convenção.

Cada categoria tem duas pastas espelhadas, pra nunca misturar pendente com aprovado:

| Categoria | Fila de revisão | Aprovado |
|---|---|---|
| Esquina (está no `esquina_index.csv`) | `ESQUINA - REVISAO` | `ESQUINA - OK` |
| Regular, forma confiante (par de bordas + ≥2 fios no topo) | `POSTE UTILIZADO - REVISAO` | `POSTE UTILIZADO - OK` |
| Forma confirmada, poucos fios — indício de ramal residencial único, não rede de distribuição | `POSTE CASA - REVISAO` | `POSTE CASA - OK` |
| Nenhuma forma confiável de poste achada (árvore, semáforo, objeto não identificado) | `BAIXA CONFIANCA - REVISAO` | `BAIXA CONFIANCA - OK` |

Além dessas 8, existe `DUPLICADOS/` (sem par REVISAO/OK — todo arquivo aqui está,
por definição, pendente de decisão humana): recebe os dois lados sempre que dois links
diferentes resolvem pro mesmo cod_id. Ver protocolo completo na seção "Identificar o
cod_id certo..." mais abaixo.

**Regra travada 23/ago (pedido do usuário): `ESQUINA - REVISAO` e `POSTE UTILIZADO -
REVISAO` só recebem match confiante — nenhuma dúvida entra ali.** No fluxo de link
(`pipeline/run_from_planilha.py`), qualquer arquivo que `match_cod_id` marcar como
`flagged` (distância/rumo/nome de rua não bateram com confiança) vai direto pra
`BAIXA CONFIANCA - REVISAO`, nunca pra fila normal da categoria com um `!!` no meio —
e toda duplicata continua indo pra `DUPLICADOS`, como já era. Ou seja: as duas filas
"normais" ficam limpas por definição; toda dúvida ou duplicidade concentra só em
`BAIXA CONFIANCA - REVISAO` ou `DUPLICADOS`. Migrados retroativamente 23/ago: 41
arquivos que já estavam flagueados dentro de `ESQUINA - REVISAO`/`POSTE UTILIZADO -
REVISAO` foram movidos pra `BAIXA CONFIANCA - REVISAO` (sem perda — 276 arquivos antes
da limpeza de baixa-confiança sem link, 259 depois, contas batendo).

Nenhuma fila é garantia de qualidade — nem "POSTE UTILIZADO - REVISAO" (testamos e ~40%
ainda saem erradas: pilar de muro, tronco de árvore, totem de loja) nem "BAIXA CONFIANCA"
(maioria ruim mesmo, mas já achamos pelo menos 1 falso negativo — foto boa classificada
ali por engano). Isso é histórico de antes da reorganização, quando as pastas eram
`ESQUINA`, `REVISAO_AUTOMATICA`, `POSTE_CASA`, `BAIXA_CONFIANCA`, todas soltas na raiz de
`POSTES UTILIZADOS` e o aprovado ia pra própria raiz sem pasta dedicada — migrado
23/ago, sem perda de arquivo (ver "Incidente" logo abaixo).

> Antes de existir uma fila de revisão pra postes regulares, o pipeline escrevia esses
> postes direto no destino final, sem revisão nenhuma. Verificamos 7 fotos que foram por
> esse caminho e **6 estavam ruins** (semáforo confundido com poste, prédio dominando o
> quadro, sem poste nenhum no enquadramento). Foi aí que fechamos essa rota — ver
> Histórico, v3→pós-fase-1.

### Incidente: quase-perda de dados na reorganização (23/ago, corrigido)

Ao mover os arquivos das pastas antigas pras novas, usei `mv pasta_antiga/*.jpg
pasta_nova/` com `2>/dev/null` (suprimindo erros) pra várias pastas de uma vez. A maioria
das operações **falhou silenciosamente** (provável interferência do OneDrive
sincronizando os arquivos no meio da operação) — só 27 de 84 fotos foram realmente
movidas, e o restante ficou parecendo "sumido" (pastas antigas vazias, sem arquivo nem no
destino novo nem na origem). **Recuperado 100% sem perda** graças a um commit git
automático que capturou o estado momentos antes (`git checkout <commit> --
"POSTES UTILIZADOS"`), seguido de `cp` (não `mv`) com saída visível, comparação de
tamanho de arquivo antigo vs novo, e só então remoção do original.

**Lição travada pra qualquer operação em massa neste projeto daqui pra frente**: nunca
`mv` em lote com erros suprimidos dentro de uma pasta do OneDrive. Sempre `cp` (copia,
não risca o original) + conferir contagem/tamanho batendo + só depois `rm` do original.
Vale para qualquer reorganização futura, não só fotos de poste.

## O critério de "esquina" (`esquina_index.csv`)

O HTML não tem o conceito de esquina — só o grafo da rede e o campo de endereço mais
próximo (`endereco_lote_mais_proximo`), que é aproximado (mediana 7,3 m de distância real).
Testamos vários critérios (ver conversa/decisões) e fechamos em:

- **Cruzamento real de ruas**: duas ruas de nomes distintos (normalizados — "AVENIDA JOÃO
  PAULO II" e "JOÃO PAULO II" são a mesma rua) convergindo a ≤40 m
- **E** o poste tem outro poste real (`poste_numero` preenchido) a ≤12 m — o sinal de
  "2+ postes se encontrando" que gera risco de foto ambígua (qual poste é qual)

Resultado: **578 postes de esquina**, de 3.835 utilizados (15,1%). Validado contra os
4 casos que já estavam manualmente sinalizados como ambíguos ("2 postes próximos") —
os 4 caem dentro do critério.

`esquina_index.csv` tem colunas `cod_id`, `endereco_lote_mais_proximo`, `lat`, `lon`,
`status` (`pendente_geracao` ou `em_ESQUINA_para_revisao`).

## Pipeline automatizado (`pipeline/`)

```
pipeline/
  pano.py          -- núcleo: busca panorama, remove marca d'água, projeta perspectiva,
                       calcula rumo geométrico, avalia forma (bordas+fios), refina centralização
  routing.py        -- decide a pasta de destino (sempre fila de revisão, nunca a raiz)
  run_batch.py       -- script canônico pra rodar lotes: `python run_batch.py --esquina 20 --regular 20`
  export_map.py      -- regenera mapdata.json a partir do HTML + CSV
  build_batch.py     -- (ferramenta original) seleciona candidatos com checagem de cobertura/ambiguidade
  scan_poste.py       -- (ferramenta original) gera contact sheet de 12 ângulos pra escolha manual
  render_final.py    -- recorta e salva um crop final dado um yaw/pitch/fov específico
  mapdata.json        -- cache derivado do HTML: os 3.835 postes utilizados + a rede, em coordenadas
                          já projetadas (metros), pra não reprocessar o HTML de 66 MB toda hora
  experiments/         -- histórico das versões testadas na fase 1 (não usar em produção,
                          só referência de por que as decisões foram tomadas)
```

### Como rodar

```
cd pipeline
python run_batch.py --esquina 20         # 20 postes de esquina novos
python run_batch.py --regular 20         # 20 postes regulares novos
python run_batch.py --esquina 10 --regular 10
```

"Já processado" é checado varrendo a pasta real (`routing.all_processed_ids()`), não uma
lista fixa no código — então rodar de novo sempre pega postes novos automaticamente.

### O que o pipeline faz, por poste

1. Checa cobertura de Street View (`get_pano_meta`)
2. Baixa o panorama equirretangular (zoom 4) e remove a marca d'água do Google (banda
   10–36% da altura, inpaint)
3. Aponta o ângulo inicial pelo **rumo geométrico** câmera→poste (bearing), restringindo a
   busca a uma janela de **±55°** em vez de varrer os 360° — isso sozinho dobrou a taxa de
   acerto (30%→55-60%, ver Histórico)
4. Refina a centralização em passos de 1°, avaliando em cada candidato:
   - **par de bordas paralelas** (twin edge) — poste é objeto sólido cilíndrico, parede/
     placa/poste de sinalização só tem uma borda
   - **fios convergindo no topo** (wire count) — poste de rede real carrega vários
     condutores; parede/árvore não tem nenhum
5. Classifica confiança (`ok` / `poste_casa` / `baixa_confianca`) e salva na fila certa

### Limitações conhecidas (não resolvidas)

- **Semáforo** pode passar como poste — mastro fino às vezes forma uma borda paralela
  por acaso
- **Antena/parabólica residencial** pode inflar a contagem de fios
- **Pilar de muro/portão** e **totem de loja** têm bordas paralelas reais — confundem o
  teste de "par de bordas" (visto no lote de 12 regulares, 22/ago)
- **Tronco de árvore bifurcado** também engana o par de bordas
- **Distância/enquadramento do panorama**: hoje sempre pega o panorama mais próximo da
  coordenada do poste. Perto de esquina isso pode ser um panorama de rua diferente, longe
  do poste — perto demais corta o topo (pitch fixo de 8° não olha alto o suficiente);
  longe demais deixa o poste pequeno. **Não implementado ainda** — próxima frente sugerida:
  testar pontos de consulta ao redor do poste, não só a coordenada exata, e ajustar
  pitch/FOV dinamicamente pela distância câmera→poste estimada.

## Bug do rumo geométrico (encontrado e corrigido 22/ago)

O `hint_yaw` usado desde a v2 (`bearing_deg`, rumo bússola câmera→poste) estava sendo
aplicado **direto** como `yaw_deg`, assumindo que os tiles equirretangulares crus do
Google são alinhados ao norte verdadeiro. **Isso é falso**: a coluna x=0 do panorama
corresponde ao heading próprio daquele panorama (a direção que o carro de captura estava
olhando), não ao norte. O erro por poste é fixo (o heading daquele panorama específico),
não ruído de GPS — por isso `hint_yaw` acertava a janela de ±55° às vezes e errava por
mais de 100° outras vezes, dependendo só da sorte do heading daquele panorama.

**Como foi confirmado**: usuário mandou 3 links do Google Maps depois de girar manualmente
até o ângulo certo (`...,Nh,Mt/...`). Pra cada um: (1) abri o link de verdade num navegador
e tirei print — prova independente de "como deveria ficar"; (2) gerei o crop com
`yaw_deg = h` (cru) e com `yaw_deg = h - heading_do_panorama` (`meta['heading']` de
`get_pano_meta`). Nos 3 casos, cru caiu numa cena totalmente diferente (~40 a ~215° de
erro, batendo exatamente com o heading daquele panorama) e a versão corrigida bateu
pixel a pixel com o print do navegador.

**Correção**: `pano.yaw_from_bearing(bearing, pano_heading)` faz
`(bearing - pano_heading) % 360`; `run_batch.py` agora usa essa função em vez de passar
`bearing_deg(...)` direto pro `hint_yaw`. `bearing_deg` em si continua correta (é só o
cálculo de rumo bússola) — o bug era só a falta dessa conversão antes de usar como yaw.

**Impacto no que já foi processado**: os postes que já estão na raiz de `POSTES UTILIZADOS`
não precisam de nada — foram conferidos visualmente por humano antes de entrar lá, esse
bug não muda isso. Já os que estão parados nas filas de revisão (`ESQUINA`,
`REVISAO_AUTOMATICA`, `POSTE_CASA`, `BAIXA_CONFIANCA`) foram gerados com o `hint_yaw`
errado — a janela de busca de ±55° podia estar centralizada bem longe do poste real, o
que ajuda a explicar a taxa alta de falso positivo (pilar, árvore, totem) documentada
abaixo. **Recomendação**: reprocessar essas filas do zero com o pipeline corrigido antes
de revisar manualmente, em vez de gastar tempo conferindo fotos que podem ter sido
apontadas na direção errada desde o início. Ainda não reprocessado — decisão pendente do
usuário.

**Próximo passo sugerido (não feito ainda)**: com `hint_yaw` agora confiável, dá pra
testar apertar a janela de busca de ±55° pra algo bem menor (ex. ±20°), o que deve reduzir
ainda mais os falsos positivos listados acima — mas só depois de validar com mais alguns
lotes, pra não trocar um problema por outro.

## Bug do FOV do link do Google (encontrado e corrigido 22/ago, mesmo dia)

Achado ao tentar reproduzir fielmente um link de calibração específico (poste da R.
Tiradentes): a direção (`yaw`) já estava certa depois do bug acima, mas o poste — que
tinha vários fios convergindo no topo — saía cortado no meu recorte, mesmo usando o
mesmo `y` (fov) do link do usuário. **Causa**: o parâmetro `y` da URL do Google Maps
Street View (`...,<y>y,<h>h,<t>t/...`) é o **campo de visão VERTICAL**, não horizontal
— eu vinha passando ele direto como `fov_deg` (horizontal) em `equirect_to_perspective`.
Isso funciona por acaso em enquadramentos quase quadrados, mas quanto mais "retrato" a
imagem final (nosso caso: 1000×1333) e quanto mais alto o poste em relação à distância
da câmera, mais isso corta o topo.

**Como foi confirmado**: mesmo método do bug acima — reproduzi o crop tratando `y` como
horizontal (errado, cortava o poste) e como vertical, convertendo pro horizontal
equivalente dado o aspect ratio de saída (`horizontal_fov_from_google_y`); a segunda
bateu pixel a pixel com o print do navegador (poste inteiro, com todos os fios).

**Correção**: `pano.horizontal_fov_from_google_y(y_deg, out_w, out_h)` faz a conversão;
usar sempre que for reproduzir um link específico do Google Maps (fluxo de calibração
manual). **Não afeta `run_batch.py`** — lá o `FOV=80` é uma constante ajustada visualmente
por conta própria (não vem de nenhuma URL do Google), então seu significado como
horizontal continua correto e nada precisa mudar nesse script.

**Atualização (mesmo dia, poste seguinte): essa correção não é suficiente sozinha.**
Testando outro link da mesma esquina (`y=35.9`, bem mais fechado), o poste saiu cortado
de novo mesmo usando `horizontal_fov_from_google_y`. Causa: o `y` do Google **não é um
valor fixo e portátil** — ele reflete o tamanho da janela do navegador no momento em que
o link foi copiado (janela maior → Google mostra mais campo de visão do que o número `y`
sozinho sugere; confirmado por varredura: o campo de visão vertical real precisado nesse
caso foi ~65°, quase o dobro do `y=35.9` do link). Sem saber o tamanho exato da janela de
quem gerou o link, não dá pra confiar só na fórmula.

## Método definitivo pra reproduzir um link de calibração: screenshot real, não fórmula

Abandonada a tentativa de calcular `yaw`/`pitch`/`fov` a partir da URL para o fluxo de
**reproduzir um link específico que o usuário mandou** (não confundir com `run_batch.py`,
que não tem link nenhum pra reproduzir e continua usando `bearing_deg`/`yaw_from_bearing`
normalmente). Em vez disso: abrir o link de verdade num navegador automatizado
(Playwright/Chromium) numa janela de tamanho fixo e combinado com o usuário, tirar
screenshot, e recortar a interface do Google fora do resultado. Isso usa o renderizador
de verdade do Google — nenhuma matemática de FOV/heading envolvida, então nenhum dos dois
bugs acima pode acontecer nesse fluxo.

**Janela padrão combinada com o usuário**: `2547x1532` pixels físicos (viewport Playwright,
`device_scale_factor=1`) — validado pixel a pixel contra o print real do usuário nessa
mesma janela. Confirmado com as infos de tela do usuário (22/ago): monitor nativo
2560×1600 @60Hz, sem scaling separado reportado no display info do Windows — o navegador
maximizado nessa tela, descontando barra de título/abas do Windows, resulta nesses
2547×1532, batendo com o que já estava calibrado. **Se o usuário trocar de
monitor/resolução ou mudar o scaling do Windows, recalibrar** (só precisa de 1 link + 1
print novo pra confirmar que ainda bate).

**Elementos de UI a recortar fora** (nessa janela): cartão de busca e caixa de pesquisa
(topo, ~0–165px), botões compartilhar/fechar (topo direita), minimapa (~0–190px x,
~1010–1532px y, canto inferior esquerdo), controles de zoom/bússola (canto inferior
direito), texto "Google Maps" + barra de data/copyright (rodapé, últimos ~145px). Uma
margem de `top=175px, bottom=145px` evita todos eles com folga.

**Posição horizontal do poste**: varia por link (depende de como o usuário enquadrou).
Na prática, como o usuário já centraliza o poste ao escolher o ângulo, cortar a partir do
**centro horizontal da janela inteira** (ignorando a UI, que só ocupa os cantos) costuma
já cair perto do poste — foi o que aconteceu aqui. Se o resultado sair descentralizado,
localizar o poste visualmente (linha vertical escura entre os fios) e recentrar nele antes
de redimensionar pro 1000×1333 final. Em lote, a centralização é feita por detecção de
linha quase-vertical (Hough) restrita à região central da janela, caindo pro centro
geométrico quando não acha nada confiável — ver `pipeline/experiments` ou o histórico
desta sessão pro código de referência (`find_pole_x`).

## Identificar o cod_id certo quando o usuário só manda o link (sem dizer qual poste é)

Sem o cod_id, a única forma de saber qual poste da base (`lista_postes.csv`) um link
mostra é casar pela geometria: (1) pela **distância** entre a posição real da câmera
(`get_pano_meta` — não a coordenada do link, que pode ser só o ponto clicado) e cada
poste `poste_utilizado=True` próximo; (2) pelo **rumo** (`bearing_deg`) até cada
candidato, comparado com o `h` do link (que já é um rumo de bússola verdadeiro, direto
comparável — diferente do `yaw_deg` usado no recorte, que precisa da correção de heading,
ver bug acima).

**Limitação real encontrada (22/ago, lote de 9 links)**: rodei os dois critérios nos 9
links e comparei. Quando o poste está a mais de ~10m da câmera, o rumo é um bom
desempate (ex.: poste a 13,3m, diferença de só 2,1° — confirma o candidato certo com
folga). **Mas quando o poste está bem perto da câmera (menos de uns 5-8m, o caso mais
comum, já que normalmente se fotografa de perto), um erro de GPS/cadastro de poucos
metros vira um erro de rumo enorme** (ex.: um poste a 2,4m com erro de posição de ~2m já
gera 84° de diferença mesmo sendo o poste certo, confirmado visualmente). Ou seja: rumo
**não decide sozinho** pra postes próximos — é só um sinal a mais, não uma prova.

**Achado concreto**: nesse lote de 9, o critério de distância pura errou o cod_id
claramente em pelo menos 1 caso (link do poste na Rua Selda de Castro Alves — o candidato
mais próximo ficava a 155° de diferença do rumo mirado, ou seja quase de costas pra
câmera) e teve 1 caso de confiança moderada (poste a 5m com 34° de diferença — pode ser
ruído de GPS, não dá pra descartar mas também não bate limpo).

**Protocolo adotado pra lote sem revisão individual** (refinado 22/ago depois de um caso
confirmado pelo usuário — link da Av. Getúlio Vargas: candidato mais próximo a 12,6m tinha
155° de diferença de rumo (quase de costas), o candidato certo estava a 15,5m com só 24,3°
de diferença; usuário confirmou visualmente que o de 15,5m era o poste certo):

1. Calcular os dois critérios (distância e rumo) pra cada link, olhando os ~5 candidatos
   `poste_utilizado=True` mais próximos.
2. Se o mais próximo por distância também é o de melhor rumo (ou o de melhor rumo está a
   menos de ~10m, faixa onde ruído de GPS já pode gerar dezenas de graus de erro sozinho),
   usar esse cod_id normalmente, sem marcação.
3. Se o mais próximo por distância tem uma diferença de rumo grande (bem acima de uns
   40-50°, principalmente perto de 180° = câmera de costas) **e** existe outro candidato a
   mais de ~10m (rumo já confiável) com diferença pequena (< uns 30°), usar esse outro
   candidato — é o caso validado acima.
4. Em qualquer caso onde ainda sobra dúvida real (nem a distância nem o rumo dão um
   candidato claramente melhor, ou os dois critérios discordam sem um vencedor óbvio),
   **marcar no nome do arquivo com `!!` logo depois do cod_id** (`COD ID_<cod_id>!!.jpg`,
   sem mais nada no nome — ver correção de convenção abaixo, 23/ago). Convenção do
   marcador definida pelo usuário 22/ago — é pra ficar fácil de bater o olho na pasta e
   saber que precisa confirmar, sem precisar ler o nome inteiro.

   **Correção de caractere (22/ago)**: a convenção original era `**`, mas **`*` não é um
   caractere válido em nome de arquivo no Windows nem no OneDrive** — 7 de 28 arquivos de
   um lote falharam ao salvar (`[Errno 22] Invalid argument`) por causa disso antes de eu
   notar. Trocado pra `!!` (válido em qualquer lugar).

   **Correção de convenção (23/ago, pedido do usuário)**: o nome do arquivo **nunca leva
   comentário/motivo** — só `COD ID_<cod_id>.jpg` ou `COD ID_<cod_id>!!.jpg`. Motivo virou
   demais pra caber legível num nome de arquivo, e cada lote gerava nomes cada vez mais
   longos. Todo comentário agora vai pra um relatório à parte:
   `RELATORIOS/confirmar_manual.xlsx` (colunas: cod_id, linha_planilha, link, endereco,
   motivo, pasta) — uma linha por arquivo marcado `!!` que não é duplicata. Os 42
   flagueados existentes (7 do lote de 9 + 35 do lote de 192) foram migrados pra esse
   formato retroativamente, sem perder o motivo de nenhum.

   **Nunca reusar um cod_id em dois links diferentes** (regra do usuário 22/ago, refinada
   23/ago): se o processo de match (acima) resolver dois links diferentes pro mesmo
   cod_id — seja no mesmo lote ou contra um cod_id já processado antes —, **nenhum dos
   dois fica na fila normal**. Os dois vão pra `POSTES UTILIZADOS/DUPLICADOS/`, nomeados
   por linha da planilha (`COD ID_<cod_id> (linha N).jpg`, sem `!!` — a pasta já é o
   sinal), e `RELATORIOS/duplicados_para_validar.xlsx` lista cod_id + linha + link +
   endereço de cada lado, com uma coluna vazia (`qual_e_o_correto?`) pra o usuário
   preencher depois de abrir os dois links e decidir. Isso substitui o
   `colisoes_cod_id.csv` antigo (mantido só como histórico, não é mais escrito).
   Achado real (lote de 28, 22/ago): dois links diferentes, ~9m de distância um do outro,
   bateram no mesmo cod_id — investigando, eram dois postes de verdade no mesmo endereço
   (`2650511978` e `221891614`), não um erro de duplicata — mesmo assim foram pra
   `DUPLICADOS` pra confirmação, já que o processo automático não tem como saber isso sem
   ajuda. No lote de 192 (23/ago), 11 colisões reais apareceram (22 arquivos movidos).

## Planilha-mestre: `RELATORIOS/links_postes_processados.xlsx`

Pedido do usuário 23/ago: manter uma lista sempre atualizada de **todo** cod_id já
processado (qualquer lote, qualquer método), com o link usado ao lado do link oficial da
base — pra validar visualmente se bateu no poste certo sem precisar abrir o
`lista_postes.csv` na mão. Colunas: `cod_id`, `endereco`, `pasta_atual`, `link_usado`
(o link que a gente de fato abriu — vazio pros postes gerados pelo pipeline CV antigo,
que não usa um link fixo, só yaw/pitch calculados), `link_original_base` (`street_view_url`
de `lista_postes.csv` pra aquele cod_id — sem heading/pitch escolhido, é só um ponto de
partida pra abrir o Street View naquela coordenada e comparar).

**Hyperlink de verdade, não só texto (achado 23/ago)**: `openpyxl` (biblioteca usada pra
escrever essas planilhas) só grava o texto puro da URL na célula — o Excel só autolinca o
que uma pessoa digita ou cola direto, não o que um script escreve. Resultado: as colunas
de link em `links_postes_processados.xlsx`, `duplicados_para_validar.xlsx`,
`confirmar_manual.xlsx` e até `links_pendentes.xlsx` (as linhas que eu preenchi, não as
que o usuário colou) ficaram sem clicar. Corrigido com `cell.hyperlink = url` +
`cell.style = "Hyperlink"` (função `linkify_row()`), aplicado retroativamente em tudo que
já existia e chamado sempre que o script grava uma URL nova daqui pra frente.

`pipeline/run_from_planilha.py` atualiza essa planilha sozinho no final de cada lote
(`load_processados()` / não duplica linha se o cod_id já está lá). Reconstruída do zero
23/ago pra cobrir os 265 cod_ids já processados até então, cruzando `links_pendentes.xlsx`
+ a base + os links recuperados do histórico da conversa (lote de 9 links, pré-planilha).
Mesma coluna `link_original_base` também foi acrescentada em
`duplicados_para_validar.xlsx`, pelo mesmo motivo.

**Erro achado 23/ago (link errado registrado pro cod_id 219992906)**: ao popular
`link_usado` pro lote de 9 links (pré-planilha, reconstruído de memória da conversa), usei
por engano a URL de um teste de calibração antigo (Mará Müler) em vez do link real que
gerou aquela imagem (Pedro Dias de Carvalho). **O cod_id em si estava certo** — confirmado
rodando a checagem de nome de rua (ver seção abaixo) direto na coordenada real do
processamento original. Foi só erro de transcrição no relatório, não erro do pipeline.
Lição: ao reconstruir link histórico de memória (qualquer lote pré-planilha), sempre
conferir contra o log original, nunca confiar só na lembrança da conversa.

**Incidente: planilha do usuário danificada (23/ago)**. O usuário passou a editar esse
arquivo por conta própria no Excel — acrescentou colunas com `XLOOKUP` (cross-referenciando
`links_pendentes.xlsx` e uma cópia de `lista_postes.csv` em outra pasta,
`Desktop\Project\Street Link\`), checkbox de conferência, e mais duas abas. Ao tentar
corrigir o erro acima com um script que salvava a planilha incondicionalmente (mesmo sem
achar a linha certa — o cod_id 219992906 nem estava mais lá, o usuário já tinha mexido),
o `openpyxl` re-salvou o arquivo inteiro e **quebrou o vínculo externo** pra
`links_pendentes.xlsx` (`xlPathMissing` no XML — o Excel vai pedir pra "recuperar" esse
link ao abrir). O vínculo pra `lista_postes.csv` sobreviveu. Não tinha commit git desse
arquivo pra recuperar (nunca tinha sido versionado). **Correção prática pro usuário**: no
Excel, aba Dados → Editar Links → selecionar o link quebrado → Alterar Origem → apontar de
novo pra `FILA DE TRABALHO\links_pendentes.xlsx`; as fórmulas em si não foram perdidas, só
o caminho.

**Regra travada por causa disso**: depois que o usuário começa a editar um arquivo gerado
por script (fórmulas, abas novas, etc.), **esse arquivo passa a ser dele** — não escrever
nele mais via `openpyxl` sem confirmar antes, mesmo que pareça uma operação inofensiva.
`load_workbook()` + `save()` sem necessidade é uma operação arriscada demais em arquivo
com vínculo externo pra fazer "de passagem".

## Checagem de nome de rua (achado 23/ago)

Terceiro sinal no `match_cod_id`, além de distância e rumo (ver seção acima): o endereço
que o próprio Street View reporta pra uma coordenada (`meta['address']` — vem embutido na
mesma resposta de `get_pano_meta`, sem custo de request nem OCR na imagem;
`pano.normalize_street_name()` faz a mesma normalização do critério de esquina em
`export_map.py`, pra comparar "R. Pedro Dias de Carvalho" com "RUA PEDRO DIAS DE CARVALHO
381, 381, SANTA TEREZINHA" e saber que é a mesma rua).

**Cuidado importante**: a primeira versão comparava nome **exato** (normalizado) e dava
falso positivo toda hora — "Kubitscheck" vs "Kubitschek", "Drumond" vs "Drummond", "Ver.
José Rosinha" vs "Vereador Jose Rosinha", postes de esquina onde a rua mais próxima
varia. Rodando contra 218 casos reais já processados, isso "divergia" em mais de 100 —
inútil. Trocado por `street_word_similarity()` (`pipeline/run_from_planilha.py`):
compara palavra por palavra (fuzzy + abreviação tipo "VER"→"VEREADOR"), não a string
inteira — reduziu pra 48 divergências reais na mesma base de 218. **Mesmo assim, nunca
troca o cod_id sozinho** — só adiciona um aviso `!!` quando a similaridade é muito baixa
(< 0.4). O risco de essa checagem escolher errado (por causa da ambiguidade natural de
esquina) é maior que o benefício de tentar corrigir automaticamente; a decisão final
continua sempre humana.

**Análise pendente (23/ago) — refinamento identificado, NÃO implementado a pedido do
usuário ("vamos manter do jeito que está, por enquanto")**: rodando distância/rumo dos 11
casos de duplicata que o usuário resolveu manualmente contra o cod_id original vs. o
confirmado, achei um padrão claro em 2 casos (linhas 41 e 79 do lote de 192): a regra atual
confia cegamente em qualquer candidato a `<10m`, mesmo com rumo péssimo (166° e 86,7° de
diferença — praticamente de costas). Nos dois casos o candidato certo era mais longe (18,5m
e 23,3m) mas com rumo bem melhor (6,3° e 31°). Como quem mira e centraliza um poste na tela
normalmente erra o rumo por no máximo uns 40-60°, **independente da distância**, um rumo
`>90°` mesmo a `<10m` provavelmente não é ruído de GPS. Correção proposta (não aplicada):
não confiar automaticamente em "perto" quando o rumo do mais próximo passar de ~90°; nesse
caso comparar de verdade com o melhor candidato por rumo antes de decidir. Achei também 2
casos (linhas 30 e 67) com padrão **contrário** (usuário preferiu o mais próximo mesmo com
rumo pior) — poucos demais e contraditórios pra virar regra, não tentar generalizar esses
sem mais exemplos. Retomar essa mudança específica (só a de rumo `>90°`) se o usuário pedir.

## Coluna `Poste` — número de campo como fonte da verdade (24/ago)

Pedido do usuário: pra esquina ou local com postes muito próximos (onde distância/rumo/rua
sozinhos não dão conta), ele preenche a mão a coluna `Poste` em `links_pendentes.xlsx` com
o **número de poste do projeto** (coluna `poste_numero` de `lista_postes.csv` — o número
"de campo", diferente do `cod_id` interno). Conferido 24/ago: é **1:1 único** nos 3.835
postes utilizados (nenhum repetido) — dá pra usar como chave de busca direta.

Quando a coluna `Poste` de uma linha está preenchida, `pipeline/run_from_planilha.py`
**não faz mais o match por distância/rumo/rua nenhum** — só busca o cod_id direto por
`poste_numero` (`load_poste_numero_map()`) e usa sem marcar `!!`, é fonte da verdade. Só
cai de volta no match geométrico (e aí sim marcado `!!`) se o número preenchido não existir
na base — sinal de erro de digitação, não de ambiguidade. Linha sem `Poste` preenchido
segue exatamente como antes (match por distância/rumo/rua).

## Fila de trabalho: `links_pendentes.xlsx`

Pra evitar reabrir um link já processado a cada lote novo, os links do usuário ficam
numa planilha única (`Pole\FILA DE TRABALHO\links_pendentes.xlsx` — antes ficava solta em
Downloads, migrada 23/ago; depois movida de novo pra dentro de `FILA DE TRABALHO/` na
reorganização geral, mesmo dia) com estas colunas:

| Coluna | Preenchida por | O que é |
|---|---|---|
| `link` | usuário | o link do Google Maps já apontado no ângulo certo |
| `cod_id` | pipeline | cod_id resolvido pelo processo de match (distância+rumo) |
| `endereco` | pipeline | endereço do cod_id resolvido, pra conferência rápida |
| `Processado?` | pipeline | `X` quando já gerou o arquivo — linhas sem `X` são as próximas a processar |
| `precisa_confirmar` | pipeline | `SIM` quando o match ficou marcado `!!` |
| `motivo` | pipeline | por que precisa confirmar, ou erro, se houver |

**Fluxo**: usuário só adiciona linhas novas no final (coluna `link`); nunca precisa
apagar nem separar o que já foi feito. `pipeline/run_from_planilha.py` lê a planilha
inteira, pula toda linha com `X` em `Processado?`, processa só as novas, e escreve de
volta `X` + as demais colunas — salva a planilha a cada linha (não só no final), então
uma falha no meio do lote não perde o progresso já feito. Roda com:

```
cd pipeline
python run_from_planilha.py
```

## Histórico de decisões (fase 1 de teste)

| Rodada | Mudança | Resultado |
|---|---|---|
| v1 | busca cega 360° | ~30% de acerto |
| v2 | + rumo geométrico (bearing), janela ±55° | ~55–60% de acerto |
| v3 | + forma (bordas+fios) integrada à busca fina; classificação em 3 filas | mesma qualidade, mas agora auto-sinalizada. **Critério travado em produção** |
| v4 | afrouxei o classificador (fios≥3 bastam sozinhos) | reduziu fila de revisão, mas deixou 3 fotos confirmadas ruins passarem como "ok" sem revisão — **revertido** |
| pós-fase-1 | conferência manual de 7 fotos "regulares" que foram direto pra raiz | 6 de 7 ruins → **fechada a rota direta**; criada `REVISAO_AUTOMATICA`; raiz virou destino só-humano |
| +12 regulares (22/ago) | mais dados pra calibrar | 5 boas, 1 razoável, 4 ruins (de 10 "ok") + 1 boa presa em baixa-confiança por engano — confirma o padrão de falsos positivos (pilar, árvore, totem, distância) |
| bug do rumo (22/ago) | `hint_yaw` usava bearing cru sem corrigir pelo heading do panorama — corrigido (ver seção acima) | provável causa raiz de boa parte dos falsos positivos acima; filas de revisão pendentes de reprocessamento |

**Decisão vigente:** critério do v3 (mais conservador) é o padrão. Prioriza nunca entregar
foto errada sem revisão, mesmo custando mais volume de trabalho manual — porque a raiz de
`POSTES UTILIZADOS` não tem mais rede de segurança nenhuma depois dela.

## Regras do guia que este pipeline precisa respeitar

- Uma imagem só, sem marca d'água, sem interface do navegador/Google (§2.1–2.3)
- Nome do arquivo: `COD ID_<cod_id>` + sufixo `TRANSFORMADOR`/`CHAVE`/`TRANSFORMADOR E
  CHAVE` **só quando visível na foto** — nunca a partir do cadastro, que pode divergir
  (guia §6, exemplo do Poste 692) — por isso o pipeline não aplica sufixo automaticamente
- Duas imagens (lado a lado) só quando localização ou qualidade forem ruins (§2.2) — não
  implementado; hoje é sempre 1 imagem
- Planilha (`lista_postes.csv`, dentro de `BASE DE DADOS/`) é só consulta — nunca editar (§5.6)
- Pastas oficiais de entrega são só `POSTES UTILIZADOS` e `POSTES` (cinzas, fora do escopo
  deste pipeline por enquanto). As 4 filas de revisão (`ESQUINA - REVISAO`,
  `POSTE UTILIZADO - REVISAO`, `POSTE CASA - REVISAO`, `BAIXA CONFIANCA - REVISAO`) e as
  4 pastas de aprovado (`... - OK`) são todas intermediárias/internas nossas — **o guia
  espera os arquivos direto na raiz de `POSTES UTILIZADOS`, sem subpastas nenhuma**.
  Isso significa que, antes da entrega de verdade pra fora do projeto, falta um passo de
  "achatar" as pastas `... - OK` (copiar tudo que já foi aprovado pra raiz de
  `POSTES UTILIZADOS`, sem as subpastas) — **não implementado ainda**, ninguém pediu essa
  entrega final até agora. Não esquecer disso quando chegar a hora.
