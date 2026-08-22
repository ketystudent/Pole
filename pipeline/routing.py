"""Decide which folder a poste's photo belongs in, based on esquina_index.csv.

IMPORTANT (as of the fase-1 quality check): the automated pipeline is not
reliable enough yet for anything to land directly in a final delivery folder
(POSTES UTILIZADOS root or ESQUINA) without a human looking at it first. A
spot check of 7 "ok, non-corner" photos that went straight to POSTES
UTILIZADOS found 6 of 7 unusable (traffic signal mistaken for pole, no pole
in frame, real pole dwarfed by a building). So EVERY automated result now
goes to a review queue, never straight to a final folder:

    is_esquina        -> ESQUINA           (review queue -- corner poles)
    otherwise, "ok"    -> REVISAO_AUTOMATICA (review queue -- everything else)
    "poste_casa"       -> POSTE_CASA        (review queue)
    "baixa_confianca"  -> BAIXA_CONFIANCA   (review queue)

POSTES UTILIZADOS (the bare root) is now purely a human-curated destination:
the team moves a file there themselves once they've confirmed it's good.
Nothing is ever written there by dest_dir_for() again.

Usage:
    from routing import dest_dir_for
    dest_dir_for("350236589")  ->  ...\\POSTES UTILIZADOS\\ESQUINA
    dest_dir_for("219298049")  ->  ...\\POSTES UTILIZADOS\\REVISAO_AUTOMATICA
"""
import csv
import glob
import os
import re

BASE_DIR = r"c:\Users\ksenne\OneDrive - azureford\Desktop\Project\Pole\POSTES UTILIZADOS"
ESQUINA_DIR = os.path.join(BASE_DIR, "ESQUINA")
POSTE_CASA_DIR = os.path.join(BASE_DIR, "POSTE_CASA")
BAIXA_CONFIANCA_DIR = os.path.join(BASE_DIR, "BAIXA_CONFIANCA")
REVISAO_AUTOMATICA_DIR = os.path.join(BASE_DIR, "REVISAO_AUTOMATICA")
INDEX_CSV = r"c:\Users\ksenne\OneDrive - azureford\Desktop\Project\Pole\esquina_index.csv"
ALL_QUEUE_DIRS = (BASE_DIR, ESQUINA_DIR, POSTE_CASA_DIR, BAIXA_CONFIANCA_DIR, REVISAO_AUTOMATICA_DIR)

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
    Every path here is a REVIEW QUEUE -- nothing is ever routed straight to
    POSTES UTILIZADOS root. confidence is one of:
      "ok"               -- pole-shape signal confident. Corner poles go to
                            ESQUINA, everything else to REVISAO_AUTOMATICA.
                            Still pending human confirmation either way.
      "poste_casa"       -- shape confirmed but very few wires at the top:
                            looks like a single service drop, not a
                            distribution pole.
      "baixa_confianca"  -- no confident pole shape found at all (tree
                            obstruction, traffic signal mast, unidentified
                            object)."""
    if confidence == "baixa_confianca":
        d = BAIXA_CONFIANCA_DIR
    elif confidence == "poste_casa":
        d = POSTE_CASA_DIR
    elif is_esquina(cod_id):
        d = ESQUINA_DIR
    else:
        d = REVISAO_AUTOMATICA_DIR
    os.makedirs(d, exist_ok=True)
    return d


def already_processed(cod_id):
    """True if a file for this cod_id already exists anywhere under POSTES
    UTILIZADOS (root or any queue) -- checked by scanning the real folder
    tree rather than a hardcoded list, so it stays correct as files get
    generated, reviewed, moved or renamed by hand."""
    for d in ALL_QUEUE_DIRS:
        if glob.glob(os.path.join(d, f"COD ID_{cod_id}*.jpg")):
            return True
    return False


def all_processed_ids():
    """Set of every cod_id that currently has a file anywhere under POSTES
    UTILIZADOS (root or any queue)."""
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
