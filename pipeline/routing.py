"""Decide which folder a poste's photo belongs in, based on esquina_index.csv.

IMPORTANT (as of the fase-1 quality check): the automated pipeline is not
reliable enough yet for anything to land directly in a final delivery folder
without a human looking at it first. A spot check of 7 "ok, non-corner"
photos that went straight to a final folder found 6 of 7 unusable (traffic
signal mistaken for pole, no pole in frame, real pole dwarfed by a
building). So EVERY automated result now goes to a review queue, never
straight to a final folder:

    is_esquina        -> "ESQUINA - REVISAO"           (review queue -- corner poles)
    otherwise, "ok"    -> "POSTE UTILIZADO - REVISAO"   (review queue -- everything else)
    "poste_casa"       -> "POSTE CASA - REVISAO"        (review queue)
    "baixa_confianca"  -> "BAIXA CONFIANCA - REVISAO"   (review queue)

Reorganizado 23/ago (pedido do usuario -- pastas soltas demais, nomes
confusos): cada categoria agora tem duas pastas espelhadas dentro de
POSTES UTILIZADOS, pra nunca misturar o que ja foi aprovado com o que
ainda esta pendente:

    "<categoria> - REVISAO"   -- destino automatico do pipeline, pendente
    "<categoria> - OK"        -- destino humano-curado; o time move um
                                 arquivo pra ca a mao depois de conferir.
                                 Nada e escrito aqui por dest_dir_for().

Antes da reorganizacao essas pastas eram ESQUINA, REVISAO_AUTOMATICA,
POSTE_CASA e BAIXA_CONFIANCA, todas soltas direto na raiz de POSTES
UTILIZADOS, com os arquivos aprovados indo pra propria raiz (sem pasta
"OK" dedicada). Migrado com `git mv`/verificacao de tamanho, historico
completo ainda no commit anterior a essa mudanca se precisar conferir.

Usage:
    from routing import dest_dir_for
    dest_dir_for("350236589")  ->  ...\\POSTES UTILIZADOS\\ESQUINA - REVISAO
    dest_dir_for("219298049")  ->  ...\\POSTES UTILIZADOS\\POSTE UTILIZADO - REVISAO
"""
import csv
import glob
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE_DIR = os.path.join(ROOT, "POSTES UTILIZADOS")

ESQUINA_REVISAO_DIR = os.path.join(BASE_DIR, "ESQUINA - REVISAO")
ESQUINA_OK_DIR = os.path.join(BASE_DIR, "ESQUINA - OK")
POSTE_CASA_REVISAO_DIR = os.path.join(BASE_DIR, "POSTE CASA - REVISAO")
POSTE_CASA_OK_DIR = os.path.join(BASE_DIR, "POSTE CASA - OK")
BAIXA_CONFIANCA_REVISAO_DIR = os.path.join(BASE_DIR, "BAIXA CONFIANCA - REVISAO")
BAIXA_CONFIANCA_OK_DIR = os.path.join(BASE_DIR, "BAIXA CONFIANCA - OK")
POSTE_UTILIZADO_REVISAO_DIR = os.path.join(BASE_DIR, "POSTE UTILIZADO - REVISAO")
POSTE_UTILIZADO_OK_DIR = os.path.join(BASE_DIR, "POSTE UTILIZADO - OK")

# aliases (nomes antigos) -- mantidos pra nao quebrar quem importar por esse nome
ESQUINA_DIR = ESQUINA_REVISAO_DIR
POSTE_CASA_DIR = POSTE_CASA_REVISAO_DIR
BAIXA_CONFIANCA_DIR = BAIXA_CONFIANCA_REVISAO_DIR
REVISAO_AUTOMATICA_DIR = POSTE_UTILIZADO_REVISAO_DIR

INDEX_CSV = os.path.join(ROOT, "BASE DE DADOS", "esquina_index.csv")

ALL_QUEUE_DIRS = (
    ESQUINA_REVISAO_DIR, ESQUINA_OK_DIR,
    POSTE_CASA_REVISAO_DIR, POSTE_CASA_OK_DIR,
    BAIXA_CONFIANCA_REVISAO_DIR, BAIXA_CONFIANCA_OK_DIR,
    POSTE_UTILIZADO_REVISAO_DIR, POSTE_UTILIZADO_OK_DIR,
)

_esquina_ids = None


def _load_esquina_ids():
    global _esquina_ids
    if _esquina_ids is None:
        ids = set()
        try:
            with open(INDEX_CSV, encoding="utf-8-sig") as f:
                for row in csv.DictReader(f, delimiter=";"):
                    ids.add(row["cod_id"])
        except FileNotFoundError:
            pass
        _esquina_ids = ids
    return _esquina_ids


def is_esquina(cod_id):
    return str(cod_id) in _load_esquina_ids()


def dest_dir_for(cod_id, confidence="ok"):
    """Return the folder a rendered image for this cod_id should be saved to.
    Every path here is a REVIEW QUEUE ("... - REVISAO") -- nothing is ever
    routed straight into a "... - OK" folder by this function; those are
    human-curated only. confidence is one of:
      "ok"               -- pole-shape signal confident. Corner poles go to
                            "ESQUINA - REVISAO", everything else to
                            "POSTE UTILIZADO - REVISAO". Still pending
                            human confirmation either way.
      "poste_casa"       -- shape confirmed but very few wires at the top:
                            looks like a single service drop, not a
                            distribution pole.
      "baixa_confianca"  -- no confident pole shape found at all (tree
                            obstruction, traffic signal mast, unidentified
                            object)."""
    if confidence == "baixa_confianca":
        d = BAIXA_CONFIANCA_REVISAO_DIR
    elif confidence == "poste_casa":
        d = POSTE_CASA_REVISAO_DIR
    elif is_esquina(cod_id):
        d = ESQUINA_REVISAO_DIR
    else:
        d = POSTE_UTILIZADO_REVISAO_DIR
    os.makedirs(d, exist_ok=True)
    return d


def already_processed(cod_id):
    """True if a file for this cod_id already exists anywhere under POSTES
    UTILIZADOS (qualquer fila de revisao OU ja aprovado em alguma "... - OK")
    -- checked by scanning the real folder tree rather than a hardcoded
    list, so it stays correct as files get generated, reviewed, moved or
    renamed by hand."""
    for d in ALL_QUEUE_DIRS:
        if glob.glob(os.path.join(d, f"COD ID_{cod_id}*.jpg")):
            return True
    return False


def all_processed_ids():
    """Set of every cod_id that currently has a file anywhere under POSTES
    UTILIZADOS (qualquer fila de revisao ou ja aprovado)."""
    ids = set()
    pat = re.compile(r"COD ID_(\d+)")
    for d in ALL_QUEUE_DIRS:
        if not os.path.isdir(d):
            continue
        for f in os.listdir(d):
            m = pat.match(f)
            if m:
                ids.add(m.group(1))
    return ids
