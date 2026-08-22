# Ante Projeto Elétrico — Araxá/MG — Validação Fotográfica de Postes

Este projeto automatiza (parcialmente) a etapa de evidenciação fotográfica de postes
descrita no **[Guia de Procedimento — Validação e Evidenciação de Postes v2.2](Guia_Validacao_Postes_AnteProjeto_Eletrico_v2.2.pdf)**.
Este README existe pra guardar o contexto e as decisões tomadas — leia antes de mexer em
qualquer coisa aqui.

## Arquivos-fonte do projeto

| Arquivo | O que é |
|---|---|
| `Projeto_Digital_Ante.html` | Relatório HTML com o grafo completo da rede: 9.673 postes na mancha, 3.835 utilizados, trechos de cabo secundário/primário, CTOs, emendas |
| `lista_postes.csv` | Base oficial de postes (mesma fonte que a planilha do Excel/SharePoint citada no guia). **Nunca editar** — é só consulta, regra do guia (§5.6) |
| `Guia_Validacao_Postes_AnteProjeto_Eletrico_v2.2.pdf` | Procedimento oficial: quais postes geram foto, como enquadrar, como nomear, onde arquivar |
| `esquina_index.csv` | Nossa derivação: os 578 postes classificados como "esquina" (ver critério abaixo) |
| `mapa_esquinas.html` | Artifact publicado (mapa interativo) usado para calibrar visualmente o critério de esquina |
| `lote_teste_0X_log.csv` | Logs de cada rodada de teste do pipeline (histórico, ver seção Histórico) |

## Estrutura de pastas em `POSTES UTILIZADOS/`

**Regra de ouro: nada é escrito automaticamente na raiz.** Toda saída do pipeline cai
numa fila de revisão. A raiz só recebe arquivo quando uma pessoa confirma a foto e move
manualmente pra lá — isso é reforçado em código (`pipeline/routing.py`, função
`dest_dir_for`), não é só uma convenção.

| Pasta | Significado | É garantia de qualidade? |
|---|---|---|
| `POSTES UTILIZADOS/` (raiz) | Destino final, curado por humano | ✅ sim — só chega aqui depois de confirmado |
| `ESQUINA/` | Poste está numa esquina (está no `esquina_index.csv`) | ❌ não — fila de revisão, mistura boas e ruins |
| `REVISAO_AUTOMATICA/` | Poste não é esquina, e o algoritmo achou que tinha certeza da forma (par de bordas + ≥2 fios no topo) | ❌ não — testamos e ~40% ainda saem erradas (pilar de muro, tronco de árvore, totem de loja) |
| `POSTE_CASA/` | Forma de poste confirmada, mas poucos fios no topo — indício de ramal residencial único, não rede de distribuição | ❌ não testado a fundo ainda |
| `BAIXA_CONFIANCA/` | Algoritmo não achou nenhum objeto com forma confiável de poste (árvore encobrindo, semáforo, objeto não identificado) | ⚠️ maioria ruim, mas já achamos pelo menos 1 falso negativo (foto boa classificada aqui por engano) |

> Antes de existir `REVISAO_AUTOMATICA`, o pipeline escrevia postes "regulares" (não-esquina)
> direto na raiz sem revisão nenhuma. Verificamos 7 fotos que foram por esse caminho e
> **6 estavam ruins** (semáforo confundido com poste, prédio dominando o quadro, sem poste
> nenhum no enquadramento). Foi aí que fechamos essa rota — ver Histórico, v3→pós-fase-1.

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

## Histórico de decisões (fase 1 de teste)

| Rodada | Mudança | Resultado |
|---|---|---|
| v1 | busca cega 360° | ~30% de acerto |
| v2 | + rumo geométrico (bearing), janela ±55° | ~55–60% de acerto |
| v3 | + forma (bordas+fios) integrada à busca fina; classificação em 3 filas | mesma qualidade, mas agora auto-sinalizada. **Critério travado em produção** |
| v4 | afrouxei o classificador (fios≥3 bastam sozinhos) | reduziu fila de revisão, mas deixou 3 fotos confirmadas ruins passarem como "ok" sem revisão — **revertido** |
| pós-fase-1 | conferência manual de 7 fotos "regulares" que foram direto pra raiz | 6 de 7 ruins → **fechada a rota direta**; criada `REVISAO_AUTOMATICA`; raiz virou destino só-humano |
| +12 regulares (22/ago) | mais dados pra calibrar | 5 boas, 1 razoável, 4 ruins (de 10 "ok") + 1 boa presa em baixa-confiança por engano — confirma o padrão de falsos positivos (pilar, árvore, totem, distância) |

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
- Planilha (`lista_postes.csv`) é só consulta — nunca editar (§5.6)
- Pastas oficiais de entrega são só `POSTES UTILIZADOS` e `POSTES` (cinzas, fora do escopo
  deste pipeline por enquanto). As filas de revisão (`ESQUINA`, `REVISAO_AUTOMATICA`,
  `POSTE_CASA`, `BAIXA_CONFIANCA`) são intermediárias — no fim, tudo que for aprovado
  deve ser movido pra raiz de `POSTES UTILIZADOS`, sem essas subpastas, pra bater com o
  formato de entrega esperado.
