"""
enriquecimento_datajud.py — Cliente da API publica DataJud (CNJ)

Enriquece publicacoes com metadados do processo (classe, assuntos, orgao,
data ajuizamento, movimentos recentes). COMPLEMENTAR ao DataJuri.

Hierarquia de natureza no intimacoes (prioridade descendente):
  1. DataJuri (proprietario, mais rico)   ← PREVALECE
  2. DataJud (publico CNJ)                ← fallback
  3. CNJ parsing (digito J do numero)     ← ultimo fallback

API: https://api-publica.datajud.cnj.jus.br/api_publica_<tribunal>/_search
Docs: https://datajud-wiki.cnj.jus.br/api-publica/

LIMITACOES (vs DataJuri):
  - NAO retorna partes (autor/reu)
  - NAO retorna valor da causa
  - Latencia T+1 a T+7 dias

Uso programatico:
    from enriquecimento_datajud import enriquecer_publicacoes_datajud
    enriquecer_publicacoes_datajud(pubs)  # modifica in-place, retorna stats

Portado de advisian-djen v1 para intimacoes.
"""
from __future__ import annotations

import re
import sys
import json
import time
import threading
from pathlib import Path
from typing import Optional
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

DJ_BASE = "https://api-publica.datajud.cnj.jus.br"
# API key publica rotativel pelo CNJ — conferir periodicamente
DJ_KEY_PUBLICA = "cDZHYzlZa0JadVREZDJCendQbXY6SkJlTzNjLV9TRENyQk1RdnFKZGRQdw=="

CACHE_PATH_DEFAULT = "cache_datajud.json"
CACHE_TTL_DIAS = 7

# Tribunais sem endpoint na DataJud publica
TRIBUNAIS_SEM_DATAJUD = {"STF"}


def _build_session() -> requests.Session:
    s = requests.Session()
    retries = Retry(
        total=3,
        backoff_factor=5,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods={"POST"},
    )
    s.mount("https://", HTTPAdapter(max_retries=retries))
    return s


def normalizar_cnj_20_digitos(numero: str) -> Optional[str]:
    """'0001234-56.2024.8.26.0100' -> '00012345620248260100' (20 digitos)."""
    if not numero:
        return None
    digits = re.sub(r"\D", "", numero)
    return digits if len(digits) == 20 else None


def tribunal_para_alias(sigla: str) -> Optional[str]:
    """Converte sigla DJEN ('TRT2','TJSP','TRF3','STJ','TST') para alias endpoint."""
    if not sigla:
        return None
    up = sigla.upper().strip()
    if up in TRIBUNAIS_SEM_DATAJUD:
        return None
    return up.lower()


def _carregar_cache(cache_path: str) -> dict:
    if not Path(cache_path).exists():
        return {}
    try:
        with open(cache_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _salvar_cache(cache: dict, cache_path: str) -> None:
    try:
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2, default=str)
    except Exception as e:
        print(f"[datajud] aviso: falha salvando cache: {e}", file=sys.stderr)


def _cache_valido(entry: dict) -> bool:
    ts = entry.get("_cached_at")
    if not ts:
        return False
    try:
        cached = datetime.fromisoformat(ts)
        return (datetime.now() - cached) < timedelta(days=CACHE_TTL_DIAS)
    except Exception:
        return False


def _consultar_datajud(
    session: requests.Session,
    alias_tribunal: str,
    numero_20d: str,
) -> Optional[dict]:
    """POST com query match por numeroProcesso. Retorna _source do primeiro hit."""
    url = f"{DJ_BASE}/api_publica_{alias_tribunal}/_search"
    headers = {
        "Authorization": f"APIKey {DJ_KEY_PUBLICA}",
        "Content-Type": "application/json",
    }
    body = {"query": {"match": {"numeroProcesso": numero_20d}}}
    r = session.post(url, headers=headers, json=body, timeout=30)
    if r.status_code == 404:
        return None
    r.raise_for_status()
    data = r.json()
    hits = (data.get("hits") or {}).get("hits") or []
    if not hits:
        return None
    return hits[0].get("_source") or None


def _normalizar_data_datajud(raw) -> Optional[str]:
    if not raw:
        return None
    s = str(raw)
    if len(s) >= 8 and s[:8].isdigit():
        return f"{s[0:4]}-{s[4:6]}-{s[6:8]}"
    if len(s) >= 10 and s[4] == "-" and s[7] == "-":
        return s[:10]
    return s


def _resumir_source(source: dict) -> dict:
    """Extrai apenas campos uteis do _source do DataJud."""
    classe = source.get("classe") or {}
    orgao = source.get("orgaoJulgador") or {}
    assuntos = source.get("assuntos") or []
    movimentos = source.get("movimentos") or []
    try:
        mov_sorted = sorted(movimentos, key=lambda m: m.get("dataHora", ""),
                           reverse=True)[:10]
    except Exception:
        mov_sorted = movimentos[:10]

    return {
        "classe_codigo": classe.get("codigo"),
        "classe_nome": classe.get("nome"),
        "assuntos": [
            {"codigo": a.get("codigo"), "nome": a.get("nome")}
            for a in assuntos if a.get("nome")
        ],
        "orgao_julgador_codigo": orgao.get("codigo"),
        "orgao_julgador_nome": orgao.get("nome"),
        "grau": source.get("grau"),
        "data_ajuizamento": _normalizar_data_datajud(source.get("dataAjuizamento")),
        "nivel_sigilo": source.get("nivelSigilo"),
        "sistema": source.get("sistema"),
        "formato": (source.get("formato") or {}).get("nome"),
        "movimentos_recentes": [
            {
                "codigo": m.get("codigo"),
                "nome": m.get("nome"),
                "dataHora": _normalizar_data_datajud(m.get("dataHora")),
            }
            for m in mov_sorted
        ],
        "total_movimentos": len(movimentos),
        "data_ultima_atualizacao": _normalizar_data_datajud(
            source.get("dataHoraUltimaAtualizacao")
        ),
    }


def _extrair_processo_e_tribunal(pub: dict) -> tuple[Optional[str], Optional[str]]:
    """Aceita varios formatos (state intimacoes, raw DJEN, advisian-djen)."""
    # state intimacoes: "processo" e "tribunal"
    processo = pub.get("processo") or pub.get("numero_processo") or pub.get("numeroprocessocommascara")
    tribunal = pub.get("tribunal") or pub.get("siglaTribunal")
    return processo, tribunal


def _inferir_natureza_de_classe(classe_nome: str) -> Optional[str]:
    """Heuristica: mapeia nome da classe DataJud para natureza do intimacoes."""
    if not classe_nome:
        return None
    nome = classe_nome.upper()
    # Trabalhista
    if any(k in nome for k in [
        "TRABALHISTA", "RECLAMACAO TRABALHISTA", "RECLAMACAO RITO",
        "RECURSO ORDINARIO TRABALHISTA", "RECURSO DE REVISTA",
        "AGRAVO DE PETICAO", "EXECUCAO TRABALHISTA",
    ]):
        return "Trabalhista"
    # Previdenciario
    if any(k in nome for k in [
        "PREVIDENCI", "BENEFICIO", "AUXILIO", "APOSENTADORIA",
        "PENSAO POR MORTE", "LOAS", "BPC",
    ]):
        return "Previdenciário"
    # Cível (inclui Fazenda Pública, Execução Fiscal, etc)
    if any(k in nome for k in [
        "CIVEL", "CíVEL", "FAZENDA PUBLICA", "CUMPRIMENTO DE SENTENCA",
        "EXECUCAO FISCAL", "DESPEJO", "MONITORIA", "PROCEDIMENTO COMUM",
        "JUIZADO ESPECIAL", "PROCEDIMENTO DO JUIZADO",
    ]):
        return "Cível"
    return None


def enriquecer_publicacoes_datajud(
    pubs: list[dict],
    cache_path: str = CACHE_PATH_DEFAULT,
    max_workers: int = 8,
    verbose: bool = True,
    sobrepor_natureza_datajuri: bool = False,
) -> dict:
    """
    Enriquece publicacoes do intimacoes com DataJud (paralelo).

    IMPORTANTE (hierarquia natureza):
      - Por default, NAO sobrescreve natureza vinda do DataJuri (prioritario).
      - DataJud preenche natureza SO em pubs sem natureza_datajuri.
      - sobrepor_natureza_datajuri=True forca sobrescrita (nao recomendado).

    Args:
        pubs: lista de pubs do state.json (modifica in-place)
        cache_path: cache local (default cache_datajud.json)
        max_workers: threads paralelas
        verbose: log progresso
        sobrepor_natureza_datajuri: se True, DataJud sobrescreve natureza DataJuri

    Returns:
        dict com stats: enriquecidos, cache_hits, erros, sem_datajud, nao_encontrados
    """
    cache = _carregar_cache(cache_path)
    session = _build_session()
    cache_lock = threading.Lock()

    queries_unicas: dict[str, list[int]] = {}
    for idx, pub in enumerate(pubs):
        processo, tribunal = _extrair_processo_e_tribunal(pub)
        alias = tribunal_para_alias(tribunal or "")
        num20 = normalizar_cnj_20_digitos(processo or "")
        if not alias or not num20:
            continue
        chave = f"{alias}::{num20}"
        queries_unicas.setdefault(chave, []).append(idx)

    total_queries = len(queries_unicas)
    if verbose:
        print(f"\n[datajud] {len(pubs)} pubs, {total_queries} processos unicos "
              f"({max_workers} workers)", flush=True)

    stats = {
        "total_pubs": len(pubs),
        "processos_unicos": total_queries,
        "enriquecidos": 0,
        "cache_hits": 0,
        "sem_datajud": 0,
        "erros": 0,
        "nao_encontrados": 0,
        "natureza_inferida": 0,
    }

    precisa_query = []
    resumos: dict[str, Optional[dict]] = {}

    for chave in queries_unicas.keys():
        entry = cache.get(chave)
        if entry and _cache_valido(entry) and "datajud" in entry:
            stats["cache_hits"] += 1
            resumos[chave] = entry["datajud"]
        else:
            precisa_query.append(chave)

    if verbose and stats["cache_hits"]:
        print(f"[datajud] cache hits: {stats['cache_hits']}/{total_queries}",
              flush=True)

    def _worker(chave: str) -> tuple[str, Optional[dict], Optional[str]]:
        alias, num20 = chave.split("::", 1)
        try:
            source = _consultar_datajud(session, alias, num20)
            if source is None:
                return (chave, None, "nao_encontrado")
            return (chave, _resumir_source(source), None)
        except Exception as e:
            return (chave, None, str(e))

    contador = {"feitos": 0}
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        future_to_chave = {pool.submit(_worker, c): c for c in precisa_query}
        for future in as_completed(future_to_chave):
            chave, resumo, erro = future.result()
            alias, num20 = chave.split("::", 1)
            contador["feitos"] += 1
            i = contador["feitos"]

            if erro == "nao_encontrado":
                stats["nao_encontrados"] += 1
                resumos[chave] = None
                if verbose and (i % 20 == 0 or i == len(precisa_query)):
                    print(f"  [{i}/{len(precisa_query)}] nao encontrado: {alias} "
                          f"{num20[-6:]}", flush=True)
            elif erro is not None:
                stats["erros"] += 1
                if verbose:
                    print(f"  [{i}/{len(precisa_query)}] ERRO {alias} {num20[-6:]}: "
                          f"{erro[:80]}", flush=True)
                continue
            else:
                stats["enriquecidos"] += 1
                resumos[chave] = resumo
                if verbose and (i % 10 == 0 or i == len(precisa_query)):
                    classe = (resumo.get("classe_nome") or "?")[:35]
                    print(f"  [{i}/{len(precisa_query)}] {alias} {num20[-6:]} "
                          f"-> {classe}", flush=True)

            with cache_lock:
                cache[chave] = {
                    "_cached_at": datetime.now().isoformat(),
                    "datajud": resumos[chave],
                }
                if i % 20 == 0:
                    _salvar_cache(cache, cache_path)

    # Aplica resumos a pubs
    for chave, indices in queries_unicas.items():
        resumo = resumos.get(chave)
        if not resumo:
            continue
        for idx in indices:
            pubs[idx]["datajud"] = resumo

            # === Hierarquia de natureza ===
            # 1) DataJuri (em contexto.natureza) = prioritario
            # 2) DataJud (classe_nome heuristica)
            # 3) CNJ parsing (natureza ja no state)
            ctx = pubs[idx].get("contexto") or {}
            nat_datajuri = ctx.get("natureza") or ""
            nat_atual = pubs[idx].get("natureza") or ""

            # Se natureza ja veio do DataJuri, manter (a nao ser que user force)
            tem_natureza_datajuri = bool(nat_datajuri and nat_datajuri.strip())

            if tem_natureza_datajuri and not sobrepor_natureza_datajuri:
                # Mantem a do DataJuri, so registra a inferida
                nat_datajud = _inferir_natureza_de_classe(resumo.get("classe_nome") or "")
                if nat_datajud:
                    pubs[idx]["natureza_datajud"] = nat_datajud
                    # marca fonte principal como datajuri
                    pubs[idx]["natureza_fonte"] = "datajuri"
            else:
                # Sem DataJuri (ou user quer sobrepor): usa DataJud
                nat_datajud = _inferir_natureza_de_classe(resumo.get("classe_nome") or "")
                if nat_datajud:
                    pubs[idx]["natureza"] = nat_datajud
                    pubs[idx]["natureza_datajud"] = nat_datajud
                    pubs[idx]["natureza_fonte"] = "datajud"
                    stats["natureza_inferida"] += 1

    for pub in pubs:
        if "datajud" not in pub:
            _, tribunal = _extrair_processo_e_tribunal(pub)
            if tribunal_para_alias(tribunal or "") is None:
                stats["sem_datajud"] += 1

    _salvar_cache(cache, cache_path)

    if verbose:
        print(f"\n[datajud] resumo:", flush=True)
        print(f"  enriquecidos:    {stats['enriquecidos']}", flush=True)
        print(f"  cache hits:      {stats['cache_hits']}", flush=True)
        print(f"  natureza novas:  {stats['natureza_inferida']}", flush=True)
        print(f"  nao encontrados: {stats['nao_encontrados']}", flush=True)
        print(f"  sem DataJud:     {stats['sem_datajud']}", flush=True)
        print(f"  erros:           {stats['erros']}", flush=True)

    return stats


# CLI smoke test
if __name__ == "__main__":
    import argparse
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--processo", required=True)
    parser.add_argument("--tribunal", required=True)
    args = parser.parse_args()

    alias = tribunal_para_alias(args.tribunal)
    num20 = normalizar_cnj_20_digitos(args.processo)
    if not alias:
        print(f"[ERRO] {args.tribunal}: sem DataJud publico")
        sys.exit(1)
    if not num20:
        print(f"[ERRO] processo invalido: {args.processo}")
        sys.exit(1)

    session = _build_session()
    source = _consultar_datajud(session, alias, num20)
    if source is None:
        print(f"[NAO ENCONTRADO] {alias} {num20}")
    else:
        print(json.dumps(_resumir_source(source), ensure_ascii=False,
                         indent=2, default=str))
