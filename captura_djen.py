"""
captura_djen.py — Modulo de captura DJEN (Comunica API PJE/CNJ).

Extraido de pipeline_diario.py + melhorias do advisian-djen.

Suporta:
- Filtros multiplos (OAB, nome de advogado, nome de escritorio, termo)
- Janela de N dias (default: hoje + ontem)
- Retry automatico 3x com backoff exponencial
- Timeout 90s (CNJ pode estar lento de manha)
- Dedup por id DJEN dentro da execucao

Uso programatico:
    from captura_djen import capturar_publicacoes

    # Modo "advisian-djen" (1 nome):
    items = capturar_publicacoes(filtros=[{"nomeAdvogado": "JOAO"}], janela_dias=3)

    # Modo "intimacoes" (multiplos filtros):
    filtros = [
        {"numeroOab": "30079", "ufOab": "ES"},
        {"nomeAdvogado": "JOAO FURTADO GUERINI"},
        {"nomeAdvogado": "FURTADO GUERINI SOCIEDADE INDIVIDUAL DE ADVOCACIA"},
    ]
    items = capturar_publicacoes(filtros, janela_dias=2)

Versao: 1.0 (port advisian-djen para intimacoes)
"""
from __future__ import annotations

import sys
import time
from datetime import datetime, timedelta
from typing import Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

DJEN_URL = "https://comunicaapi.pje.jus.br/api/v1/comunicacao"
PAGE_SIZE = 100
TIMEOUT_SEGUNDOS = 90
SLEEP_ENTRE_PAGINAS = 0.3
RETRY_TOTAL = 3


def _build_session() -> requests.Session:
    """HTTP session com retry automatico e backoff."""
    session = requests.Session()
    retries = Retry(
        total=RETRY_TOTAL,
        backoff_factor=10,
        status_forcelist=[429, 500, 502, 503, 504],
    )
    session.mount("https://", HTTPAdapter(max_retries=retries))
    return session


def _buscar_pagina(
    session: requests.Session,
    params: dict,
    verbose: bool = True,
) -> dict:
    """Busca 1 pagina com retry manual para ReadTimeout."""
    for tentativa in range(RETRY_TOTAL):
        try:
            r = session.get(DJEN_URL, params=params, timeout=TIMEOUT_SEGUNDOS)
            r.raise_for_status()
            return r.json()
        except (requests.exceptions.ReadTimeout,
                requests.exceptions.ConnectionError) as e:
            if tentativa < RETRY_TOTAL - 1:
                wait = 30 * (tentativa + 1)
                if verbose:
                    print(f"  [DJEN timeout tentativa {tentativa+1}/{RETRY_TOTAL}, "
                          f"aguardando {wait}s...]", flush=True)
                time.sleep(wait)
            else:
                raise


def _buscar_filtro_data(
    session: requests.Session,
    filtro: dict,
    data_alvo: str,
    verbose: bool = True,
) -> list[dict]:
    """Busca todas paginas de 1 filtro em 1 data."""
    items_total: list[dict] = []
    pagina = 1
    while True:
        params = {
            **filtro,
            "meio": "D",
            "dataDisponibilizacaoInicio": data_alvo,
            "dataDisponibilizacaoFim": data_alvo,
            "pagina": pagina,
        }
        data = _buscar_pagina(session, params, verbose)
        items = data.get("items", [])
        items_total.extend(items)
        if len(items) < PAGE_SIZE:
            break
        pagina += 1
        time.sleep(SLEEP_ENTRE_PAGINAS)
    return items_total


def capturar_publicacoes(
    filtros: list[dict],
    janela_dias: int = 2,
    hoje: Optional[datetime] = None,
    verbose: bool = True,
) -> list[dict]:
    """
    Busca DJEN para N filtros em janela de datas.

    Args:
        filtros: lista de dicts, cada um com UMA de:
                 - {"numeroOab": "30079", "ufOab": "ES"}
                 - {"nomeAdvogado": "NOME"}
                 - {"termo": "texto livre"}
        janela_dias: quantos dias pra tras (default 2 = hoje + ontem)
        hoje: data de referencia (default: datetime.now(); util para testes)
        verbose: log de progresso

    Returns:
        Lista de items unicos da API DJEN (dedup por id).
        Cada item tem: id, texto, numeroprocessocommascara, data_disponibilizacao,
        siglaTribunal, tipoDocumento, link, destinatarios, etc.
    """
    if not filtros:
        raise ValueError("filtros nao pode ser vazio")

    hoje = hoje or datetime.now()
    datas_alvo = [
        (hoje - timedelta(days=i)).strftime("%Y-%m-%d")
        for i in range(janela_dias)
    ]

    if verbose:
        print(f"[captura_djen] {len(filtros)} filtro(s) x {len(datas_alvo)} data(s):",
              flush=True)
        for f in filtros:
            print(f"  filtro: {f}", flush=True)
        print(f"  datas: {datas_alvo[0]} a {datas_alvo[-1]}", flush=True)

    session = _build_session()
    seen_ids: set = set()
    todos: list[dict] = []

    for data_alvo in datas_alvo:
        for filtro in filtros:
            try:
                items = _buscar_filtro_data(session, filtro, data_alvo, verbose)
            except Exception as e:
                if verbose:
                    print(f"  [ERRO] filtro {filtro} data {data_alvo}: {e}",
                          flush=True)
                continue
            novos = 0
            for it in items:
                id_ = it.get("id")
                if id_ is not None and id_ not in seen_ids:
                    seen_ids.add(id_)
                    todos.append(it)
                    novos += 1
            if verbose:
                filtro_key = next(iter(filtro.keys()))
                filtro_val = str(filtro.get(filtro_key))[:25]
                print(f"  {data_alvo} [{filtro_key}={filtro_val}]: "
                      f"{len(items)} itens ({novos} novos)", flush=True)

    if verbose:
        print(f"[captura_djen] Total unicos: {len(todos)} publicacoes", flush=True)
    return todos


# Alias compat: chamada antiga advisian-djen (1 nome)
def capturar_por_nome(
    nome: str,
    janela_dias: int = 3,
    hoje: Optional[datetime] = None,
    verbose: bool = True,
) -> list[dict]:
    """Wrapper de compatibilidade para advisian-djen: captura por 1 nome."""
    if not nome or not nome.strip():
        raise ValueError("nome nao pode ser vazio")
    return capturar_publicacoes(
        filtros=[{"nomeAdvogado": nome}],
        janela_dias=janela_dias,
        hoje=hoje,
        verbose=verbose,
    )


# ============================================================
# SELF-TEST / CLI
# ============================================================

if __name__ == "__main__":
    import argparse
    import json as _json

    sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="Captura publicacoes DJEN.")
    parser.add_argument("--nome", help="Nome de advogado")
    parser.add_argument("--oab", help="Numero OAB (use junto com --uf)")
    parser.add_argument("--uf", help="UF da OAB")
    parser.add_argument("--termo", help="Termo livre de busca")
    parser.add_argument("--janela", type=int, default=2, help="Dias (default: 2)")
    parser.add_argument("--output", help="Arquivo JSON de saida")
    args = parser.parse_args()

    filtros = []
    if args.nome:
        filtros.append({"nomeAdvogado": args.nome})
    if args.oab and args.uf:
        filtros.append({"numeroOab": args.oab, "ufOab": args.uf})
    if args.termo:
        filtros.append({"termo": args.termo})
    if not filtros:
        parser.error("Informe pelo menos --nome, --oab+--uf ou --termo")

    items = capturar_publicacoes(filtros, janela_dias=args.janela)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            _json.dump(items, f, ensure_ascii=False, indent=2, default=str)
        print(f"[OK] {len(items)} pubs salvas em {args.output}")
    else:
        print(f"\n[RESUMO] {len(items)} pubs")
        for i, it in enumerate(items[:3], 1):
            print(f"\n--- Pub {i} ---")
            print(f"  id: {it.get('id')}")
            print(f"  processo: {it.get('numeroprocessocommascara')}")
            print(f"  data: {it.get('data_disponibilizacao')}")
            print(f"  tribunal: {it.get('siglaTribunal')}")
            print(f"  tipo: {it.get('tipoDocumento')}")
        if len(items) > 3:
            print(f"\n  ... +{len(items)-3} pubs")
