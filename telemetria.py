"""
telemetria.py — Logger append-only de classificacoes (Controller de Prazos v2.0)

Grava um registro JSONL por publicacao classificada em `telemetria_log.jsonl`.
Formato append-only garante integridade mesmo com multiplas escritas concorrentes.

Uso:
    from telemetria import registrar_classificacao
    registrar_classificacao(pub, resultado)

Utilitarios:
    python telemetria.py --resumo                  # resumo geral do log
    python telemetria.py --custo-mes 2026-04       # custo total do mes
    python telemetria.py --accuracy-vs-gt          # accuracy contra GT V5

Versao: 1.0
Data: 2026-04-15
"""
from __future__ import annotations

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime
from collections import Counter, defaultdict

sys.stdout.reconfigure(encoding="utf-8")

LOG_PATH = "telemetria_log.jsonl"


# ============================================================
# REGISTRO
# ============================================================

# ============================================================
# REGISTRO DE EXECUCAO DO PIPELINE (portado de advisian-djen)
# ============================================================

def registrar_execucao(
    nome_monitorado: str,
    total_capturado: int,
    novas: int,
    repetidas: int,
    duracao_segundos: float,
    janela_dias: int = None,
    enriquecido_datajuri: int = 0,
    enriquecido_datajud: int = 0,
    erros: int = 0,
    log_path: str = "telemetria_execucoes.jsonl",
) -> None:
    """Registra 1 execucao do pipeline_diario em log separado (append-only).

    Complementa registrar_classificacao (que e 1 registro por pub).
    Util pra saude/uptime do pipeline.
    """
    registro = {
        "timestamp": datetime.now().isoformat(),
        "tipo": "execucao_pipeline",
        "nome_monitorado": nome_monitorado,
        "janela_dias": janela_dias,
        "total_capturado": total_capturado,
        "novas": novas,
        "repetidas": repetidas,
        "enriquecido_datajuri": enriquecido_datajuri,
        "enriquecido_datajud": enriquecido_datajud,
        "erros": erros,
        "duracao_segundos": round(duracao_segundos, 2),
    }
    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(registro, ensure_ascii=False, default=str) + "\n")
    except Exception as e:
        print(f"[telemetria] erro ao escrever log execucao: {e}", file=sys.stderr)


def resumo_execucoes(log_path: str = "telemetria_execucoes.jsonl") -> None:
    """Resumo de saude do pipeline (execucoes)."""
    registros = ler_log(log_path)
    if not registros:
        print("Log de execucoes vazio.")
        return

    print(f"=== EXECUCOES PIPELINE — {len(registros)} runs ===\n")
    total_novas = sum(r.get("novas", 0) for r in registros)
    total_capt = sum(r.get("total_capturado", 0) for r in registros)
    total_dj = sum(r.get("enriquecido_datajuri", 0) for r in registros)
    total_djud = sum(r.get("enriquecido_datajud", 0) for r in registros)
    dur_media = sum(r.get("duracao_segundos", 0) for r in registros) / len(registros)
    erros = sum(r.get("erros", 0) for r in registros)

    print(f"Total capturado:      {total_capt}")
    print(f"Total novas:          {total_novas}")
    print(f"Enriquec. DataJuri:   {total_dj}")
    print(f"Enriquec. DataJud:    {total_djud}")
    print(f"Erros acumulados:     {erros}")
    print(f"Duracao media:        {dur_media:.1f}s")

    por_dia = defaultdict(int)
    for r in registros:
        ts = r.get("timestamp", "")
        if len(ts) >= 10:
            por_dia[ts[:10]] += 1
    print(f"\nUltimas 7 execucoes por dia:")
    for dia in sorted(por_dia.keys())[-7:]:
        print(f"  {dia}: {por_dia[dia]} runs")


# ============================================================
# REGISTRO POR PUBLICACAO (existente, nao altera)
# ============================================================

def registrar_classificacao(pub: dict, resultado: dict, log_path: str = LOG_PATH) -> None:
    """
    Registra uma classificacao no log append-only.
    Nao falha se o log nao puder ser escrito (apenas warn).
    """
    tel = resultado.get("_telemetria", {}) or {}

    # Determinar source de confianca
    confidence_source = "ia_only"
    gt_status = resultado.get("_gt_v5_status")
    if gt_status == "CONCORDA":
        confidence_source = "ia+gt_agreement"
    elif gt_status == "CONFLITO":
        confidence_source = "ia+gt_conflict"
    if resultado.get("regra") == "CLASSIFICACAO_MANUAL_OBRIGATORIA":
        confidence_source = "manual"

    registro = {
        "timestamp": datetime.now().isoformat(),
        "pub_id": pub.get("id"),
        "pub_data": pub.get("data"),
        "pub_tribunal": pub.get("tribunal"),
        "pub_tipo_doc": pub.get("tipo_documento"),
        "processo": pub.get("processo"),
        "natureza": (pub.get("contexto", {}) or {}).get("natureza") or pub.get("natureza"),
        "versao_motor": resultado.get("_motor_versao") or tel.get("motor_versao"),
        "regra_final": resultado.get("regra"),
        "confianca_final": resultado.get("confianca"),
        "retry_count": tel.get("retry_count", 0),
        "retry_reasons": tel.get("retry_reasons", []),
        "confidence_source": confidence_source,
        "tokens_input": tel.get("tokens_input_total", 0),
        "tokens_output": tel.get("tokens_output_total", 0),
        "tokens_cache_read": tel.get("tokens_cache_read_total", 0),
        "custo_usd": round(tel.get("custo_usd_total", 0.0), 6),
        "latencia_ms": tel.get("latencia_ms_total", 0),
        "gt_v5_status": resultado.get("_gt_v5_status"),
        "gt_v5_sugerida": resultado.get("_gt_v5_sugerida"),
        "gt_v5_similaridade": resultado.get("_gt_v5_similaridade"),
        "validation_error": resultado.get("_validation_error"),
        "via": resultado.get("_via"),
    }

    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(registro, ensure_ascii=False, default=str) + "\n")
    except Exception as e:
        print(f"[telemetria] erro ao escrever log: {e}", file=sys.stderr)


# ============================================================
# LEITURA
# ============================================================

def ler_log(log_path: str = LOG_PATH) -> list[dict]:
    """Le todos os registros do log."""
    if not Path(log_path).exists():
        return []
    registros = []
    with open(log_path, "r", encoding="utf-8") as f:
        for linha in f:
            linha = linha.strip()
            if not linha:
                continue
            try:
                registros.append(json.loads(linha))
            except json.JSONDecodeError:
                continue
    return registros


# ============================================================
# ANALISES
# ============================================================

def resumo(log_path: str = LOG_PATH) -> None:
    """Imprime resumo estatistico do log."""
    registros = ler_log(log_path)
    if not registros:
        print("Log vazio ou inexistente.", flush=True)
        return

    print(f"=== TELEMETRIA — {len(registros)} registros ===", flush=True)

    # Distribuicao por confianca
    conf = Counter(r.get("confianca_final", "?") for r in registros)
    print(f"\nConfianca:", flush=True)
    for c, n in conf.most_common():
        pct = n / len(registros) * 100
        print(f"  {c}: {n} ({pct:.1f}%)", flush=True)

    # Distribuicao por motor
    motor = Counter(r.get("versao_motor", "?") for r in registros)
    print(f"\nMotor:", flush=True)
    for m, n in motor.most_common():
        print(f"  {m}: {n}", flush=True)

    # Retry distribution
    retries = Counter(r.get("retry_count", 0) for r in registros)
    print(f"\nRetries:", flush=True)
    for rc in sorted(retries.keys()):
        print(f"  {rc} retries: {retries[rc]}", flush=True)

    # GT V5 status
    gt = Counter(r.get("gt_v5_status", "NO_MATCH") for r in registros)
    print(f"\nGT V5 status:", flush=True)
    for s, n in gt.most_common():
        print(f"  {s}: {n}", flush=True)

    # Custo
    custo_total = sum(r.get("custo_usd", 0) for r in registros)
    lat_media = sum(r.get("latencia_ms", 0) for r in registros) / len(registros)
    print(f"\nCusto total: ${custo_total:.4f}", flush=True)
    print(f"Custo medio/pub: ${custo_total/len(registros):.4f}", flush=True)
    print(f"Latencia media: {lat_media:.0f}ms", flush=True)

    # Top regras
    top_regras = Counter(r.get("regra_final", "?") for r in registros).most_common(15)
    print(f"\nTop 15 regras:", flush=True)
    for regra, n in top_regras:
        print(f"  {n:4} | {regra}", flush=True)


def custo_por_mes(log_path: str = LOG_PATH) -> dict:
    """Agrega custo por mes (YYYY-MM)."""
    registros = ler_log(log_path)
    por_mes: dict[str, float] = defaultdict(float)
    for r in registros:
        ts = r.get("timestamp", "")
        if len(ts) >= 7:
            mes = ts[:7]
            por_mes[mes] += r.get("custo_usd", 0.0)
    return dict(por_mes)


def accuracy_vs_gt(log_path: str = LOG_PATH) -> dict:
    """
    Calcula accuracy contra ground truth:
    - Ignora registros sem gt_v5_status
    - CONCORDA = accerto, CONFLITO = erro
    """
    registros = ler_log(log_path)
    com_gt = [r for r in registros if r.get("gt_v5_status") in ("CONCORDA", "CONFLITO")]
    if not com_gt:
        return {"sem_dados": True}

    acertos = sum(1 for r in com_gt if r["gt_v5_status"] == "CONCORDA")
    total = len(com_gt)
    acc = acertos / total if total else 0

    # Por natureza
    por_natureza = defaultdict(lambda: {"acertos": 0, "total": 0})
    for r in com_gt:
        nat = r.get("natureza", "?")
        por_natureza[nat]["total"] += 1
        if r["gt_v5_status"] == "CONCORDA":
            por_natureza[nat]["acertos"] += 1

    return {
        "total_com_gt": total,
        "acertos": acertos,
        "accuracy": round(acc, 4),
        "por_natureza": {
            nat: {"acertos": d["acertos"], "total": d["total"],
                  "acc": round(d["acertos"] / d["total"], 4) if d["total"] else 0}
            for nat, d in por_natureza.items()
        },
    }


# ============================================================
# CLI
# ============================================================

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--resumo", action="store_true")
    parser.add_argument("--custo-mes", type=str, default=None)
    parser.add_argument("--accuracy-vs-gt", action="store_true")
    parser.add_argument("--execucoes", action="store_true",
                        help="Resumo de execucoes do pipeline (saude/uptime)")
    parser.add_argument("--log", default=LOG_PATH)
    args = parser.parse_args()

    if args.resumo:
        resumo(args.log)
    elif args.custo_mes:
        custos = custo_por_mes(args.log)
        total = custos.get(args.custo_mes, 0.0)
        print(f"Custo {args.custo_mes}: ${total:.4f}", flush=True)
    elif args.accuracy_vs_gt:
        acc = accuracy_vs_gt(args.log)
        print(json.dumps(acc, indent=2, ensure_ascii=False), flush=True)
    elif args.execucoes:
        resumo_execucoes()
    else:
        print("Use --resumo, --custo-mes YYYY-MM, --accuracy-vs-gt ou --execucoes", flush=True)


if __name__ == "__main__":
    main()
