"""Dashboard ADVISIAN - identidade visual ADVISIAN (azul marinho + vermelho IA)"""
import json, sys, base64
from datetime import datetime
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")

# Carregar logo em base64
LOGO_PATH = Path("advisian-logo.png")
if LOGO_PATH.exists():
    with open(LOGO_PATH, "rb") as f:
        LOGO_B64 = base64.b64encode(f.read()).decode()
    LOGO_SRC = f"data:image/png;base64,{LOGO_B64}"
else:
    LOGO_SRC = ""

with open("intimacoes_state.json", "r", encoding="utf-8") as f:
    state = json.load(f)

pubs = state["publicacoes"]
data_geracao = datetime.now().strftime("%d/%m/%Y %H:%M")

DATAJURI_URL = "https://dj33.datajuri.com.br/app/#/lista/Processo/"
DATAJURI_TAB = "?relDir=asc&relSize=20&relPagina=1&tab=HistoricoAtividades"

rows = []
for pub in pubs:
    cls = pub.get("classificacao", {})
    ctx = pub.get("contexto", {})
    sinal = pub.get("sinal", {})
    processo = pub.get("processo", "")
    dj_id = pub.get("datajuri_id", ctx.get("id", ""))
    dj_url = ""
    if dj_id:
        try:
            dj_url = DATAJURI_URL + str(int(float(dj_id))) + DATAJURI_TAB
        except:
            pass

    def esc(s):
        if not s or not isinstance(s, str):
            return str(s) if s else ""
        return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\r", "").replace("\t", " ").replace("`", "'").replace("${", "$ {")

    gt_v3 = cls.get("gt_v3", {})
    gt_status = gt_v3.get("status", "")
    gt_regra = gt_v3.get("regra_gt_sugerida", "") or ""
    gt_sim = gt_v3.get("similaridade_max", 0)

    rows.append({
        "processo": esc(processo),
        "dj_url": esc(dj_url),
        "djen_link": esc(pub.get("link", "")),
        "data": esc(pub.get("data_disponibilizacao", "")),
        "tribunal": esc(pub.get("tribunal", "")),
        "tipo_doc": esc(pub.get("tipo_documento", "")),
        "natureza": esc(ctx.get("natureza", "") or pub.get("natureza", "")),
        "cliente": esc(ctx.get("cliente", "")),
        "adverso": esc(ctx.get("adverso", "")),
        "assunto_dj": esc(ctx.get("assunto", "")),
        "tipo_acao": esc(ctx.get("tipo_acao", "")),
        "fase_atual": esc(ctx.get("fase_atual", "")),
        "valor_causa": esc(ctx.get("valor_causa", "")),
        "tipo_processo": esc(ctx.get("tipo_processo", "")),
        "regra": esc(cls.get("regra", "")),
        "confianca": esc(cls.get("confianca", "")),
        "prazo": esc(str(cls.get("prazo_dias", "") or "")),
        "justificativa": esc(cls.get("justificativa", "")),
        "observacoes": esc(cls.get("observacoes", "")),
        "raciocinio": esc(cls.get("raciocinio", "")),
        "flags": esc(", ".join(cls.get("flags", []) if isinstance(cls.get("flags"), list) else [])),
        "texto": esc(pub.get("texto_completo", pub.get("texto_resumo", ""))),
        "gt_status": esc(gt_status),
        "gt_regra": esc(gt_regra),
        "gt_sim": esc(str(round(gt_sim, 2))) if gt_sim else "",
    })

rows_json = json.dumps(rows, ensure_ascii=False)
pend = ["PENDENTE","PENDENTE_CLASSIFICACAO","","ERRO_CLASSIFICACAO"]
total = len(rows)
alta = sum(1 for r in rows if r["confianca"] == "ALTA")
media = sum(1 for r in rows if r["confianca"] == "MEDIA")
baixa = sum(1 for r in rows if r["confianca"] == "BAIXA" and r["regra"] not in pend)
manual = sum(1 for r in rows if "MANUAL" in r["regra"] or "NENHUMA" in r["regra"])
pendentes = sum(1 for r in rows if r["regra"] in pend)
info = sum(1 for r in rows if r["regra"] == "INFORMATIVO_SEM_PRAZO")
excl = set(pend) | {"INFORMATIVO_SEM_PRAZO"}
workflows = sum(1 for r in rows if r["regra"] and r["regra"] not in excl and "MANUAL" not in r["regra"] and "NENHUMA" not in r["regra"])
gt_concorda = sum(1 for r in rows if r.get("gt_status") == "CONCORDA")
gt_conflito = sum(1 for r in rows if r.get("gt_status") == "CONFLITO")

html = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<title>ADVISIAN — Controller de Prazos</title>
<link rel="icon" type="image/png" href=\"""" + LOGO_SRC + """\">
<style>
/* ============ ADVISIAN DESIGN SYSTEM ============ */
:root{
--advisian-navy:#0A1E3D;
--advisian-navy-light:#1E3A5F;
--advisian-red:#D4303C;
--advisian-red-light:#E84855;
--bg-dark:#0A0E1A;
--bg-card:#121826;
--bg-elevated:#1A2236;
--border:#1E293B;
--border-light:rgba(30,41,59,0.6);
--border-accent:rgba(10,30,61,0.4);
--txt:#E2E8F0;
--txt-muted:#94A3B8;
--txt-dim:#64748B;
--success:#10B981;
--warning:#F59E0B;
--danger:#EF4444;
}
body.light{
--bg-dark:#F8FAFC;
--bg-card:#FFFFFF;
--bg-elevated:#F1F5F9;
--border:#E2E8F0;
--border-light:#E2E8F0;
--border-accent:rgba(10,30,61,0.15);
--txt:#0F172A;
--txt-muted:#475569;
--txt-dim:#94A3B8;
}

*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,"Inter","SF Pro Display","Segoe UI",sans-serif;background:var(--bg-dark);color:var(--txt);-webkit-font-smoothing:antialiased;transition:background .2s,color .2s}

/* ============ HEADER ADVISIAN ============ */
.header{background:#FFFFFF;padding:24px 40px;border-bottom:3px solid var(--advisian-red);display:flex;justify-content:space-between;align-items:center;box-shadow:0 4px 24px rgba(10,30,61,0.08);gap:32px;flex-wrap:wrap}
body.light .header{background:#FFFFFF}
.header-brand{display:flex;align-items:center;gap:24px;flex:1;min-width:0}
.header-brand img{height:56px;width:auto;display:block}
.header-divider{width:1px;height:48px;background:rgba(10,30,61,0.15);flex-shrink:0}
.header-title h1{font-size:18px;font-weight:800;color:var(--advisian-navy);letter-spacing:-0.4px;text-transform:uppercase}
.header-title .sub{color:#64748B;font-size:12px;margin-top:4px;font-weight:500;letter-spacing:0.3px}

/* ============ TECH CREDENTIALS ============ */
.credentials{display:flex;gap:8px;align-items:center;flex-wrap:wrap}
.cred-pill{display:flex;align-items:center;gap:8px;padding:8px 14px;background:linear-gradient(135deg,rgba(10,30,61,0.04),rgba(10,30,61,0.02));border:1px solid rgba(10,30,61,0.12);border-radius:999px;font-size:10.5px;font-weight:700;color:var(--advisian-navy);letter-spacing:0.3px;white-space:nowrap;transition:all .15s}
.cred-pill:hover{border-color:var(--advisian-red);color:var(--advisian-red);transform:translateY(-1px)}
.cred-pill .cred-icon{width:14px;height:14px;flex-shrink:0}
.cred-pill .cred-label{font-weight:500;color:#64748B;text-transform:uppercase;letter-spacing:0.5px;font-size:9px;margin-right:2px}
.cred-pill strong{font-weight:800;color:var(--advisian-navy)}
.cred-pill:hover strong{color:var(--advisian-red)}
.cred-separator{width:1px;height:20px;background:rgba(10,30,61,0.15);margin:0 4px}
.theme-toggle{background:var(--advisian-navy);border:1px solid var(--advisian-navy);color:#FFFFFF;padding:10px 18px;border-radius:999px;cursor:pointer;font-size:12px;font-weight:700;display:flex;align-items:center;gap:6px;transition:all .15s;font-family:inherit;letter-spacing:0.3px}
.theme-toggle:hover{background:var(--advisian-red);border-color:var(--advisian-red)}

/* ============ STATS CARDS ============ */
.stats{display:flex;gap:12px;padding:20px 40px;background:var(--bg-card);border-bottom:1px solid var(--border);flex-wrap:wrap}
.sc{background:var(--bg-elevated);border:1px solid var(--border-light);border-radius:10px;padding:16px 20px;min-width:120px;cursor:pointer;transition:all .2s;user-select:none;position:relative;overflow:hidden}
.sc::before{content:'';position:absolute;top:0;left:0;width:3px;height:100%;background:transparent;transition:background .2s}
.sc:hover{border-color:var(--advisian-red);transform:translateY(-2px);box-shadow:0 8px 16px rgba(0,0,0,0.15)}
.sc:hover::before{background:var(--advisian-red)}
.sc.active{border-color:var(--advisian-red);background:var(--bg-card);box-shadow:0 0 0 2px rgba(212,48,60,0.15)}
.sc.active::before{background:var(--advisian-red)}
.sc .n{font-size:28px;font-weight:800;letter-spacing:-0.8px;line-height:1}
.sc .l{font-size:10px;color:var(--txt-dim);text-transform:uppercase;letter-spacing:1.2px;margin-top:6px;font-weight:700}

/* ============ FILTROS ============ */
.filters{display:flex;gap:12px;padding:16px 40px;background:var(--bg-card);flex-wrap:wrap;align-items:end;border-bottom:1px solid var(--border)}
.fg{display:flex;flex-direction:column;gap:5px;position:relative}
.fg label{font-size:10px;color:var(--txt-dim);text-transform:uppercase;letter-spacing:1.2px;font-weight:700}
.multi-btn{background:var(--bg-elevated);border:1px solid var(--border-light);color:var(--txt);padding:8px 14px;border-radius:8px;font-size:12px;font-family:inherit;cursor:pointer;min-width:150px;text-align:left;display:flex;justify-content:space-between;align-items:center;gap:8px;transition:all .15s;font-weight:500}
.multi-btn:hover{border-color:var(--advisian-red)}
.multi-btn.has-val{border-color:var(--advisian-red);color:var(--advisian-red);background:rgba(212,48,60,0.05)}
.multi-btn::after{content:"▾";font-size:9px;color:var(--txt-dim)}
.multi-dropdown{display:none;position:absolute;top:100%;left:0;background:var(--bg-card);border:1px solid var(--border-light);border-radius:10px;margin-top:6px;min-width:220px;max-height:340px;overflow-y:auto;z-index:1000;box-shadow:0 12px 32px rgba(0,0,0,0.25)}
.multi-dropdown.open{display:block}
.multi-actions{display:flex;gap:6px;padding:10px;border-bottom:1px solid var(--border-light);background:var(--bg-elevated)}
.multi-actions button{flex:1;background:var(--bg-card);border:1px solid var(--border-light);color:var(--txt-muted);padding:6px 10px;border-radius:6px;font-size:10px;cursor:pointer;font-family:inherit;font-weight:700;text-transform:uppercase;letter-spacing:0.5px;transition:all .1s}
.multi-actions button:hover{color:var(--advisian-red);border-color:var(--advisian-red)}
.multi-opt{padding:8px 14px;font-size:12px;cursor:pointer;display:flex;align-items:center;gap:10px;transition:background .1s}
.multi-opt:hover{background:var(--bg-elevated)}
.multi-opt input{cursor:pointer;accent-color:var(--advisian-red);width:14px;height:14px}
.multi-opt .lb-opt{color:var(--txt);flex:1;font-weight:500}
.multi-opt.selected .lb-opt{color:var(--advisian-red);font-weight:700}
.fg input[type=text]{background:var(--bg-elevated);border:1px solid var(--border-light);color:var(--txt);padding:8px 14px;border-radius:8px;font-size:12px;font-family:inherit;font-weight:500}
.fg input:focus{outline:none;border-color:var(--advisian-red)}

/* ============ TABELA ============ */
.tc{padding:0 40px 40px;overflow-x:auto;margin-top:16px}
table{width:100%;border-collapse:separate;border-spacing:0;font-size:12px}
th{background:var(--bg-card);color:var(--txt-dim);padding:12px 16px;text-align:left;font-size:10px;text-transform:uppercase;letter-spacing:1.2px;font-weight:800;position:sticky;top:0;cursor:pointer;border-bottom:2px solid var(--advisian-navy);white-space:nowrap;z-index:10}
th:hover{color:var(--advisian-red)}
tr{border-bottom:1px solid var(--border-light);transition:background .15s;cursor:pointer}
tr:hover{background:var(--bg-elevated)}
td{padding:12px 16px;vertical-align:top;color:var(--txt)}

/* ============ BADGES ============ */
.b{display:inline-block;padding:3px 10px;border-radius:6px;font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:0.5px}
.b-a{background:rgba(16,185,129,0.12);color:var(--success);border:1px solid rgba(16,185,129,0.25)}
.b-m{background:rgba(245,158,11,0.12);color:var(--warning);border:1px solid rgba(245,158,11,0.25)}
.b-b{background:rgba(239,68,68,0.12);color:var(--danger);border:1px solid rgba(239,68,68,0.25)}
.b-man{background:rgba(249,115,22,0.12);color:#FB923C;border:1px solid rgba(249,115,22,0.25)}
.b-info{background:rgba(30,58,95,0.2);color:#93C5FD;border:1px solid rgba(30,58,95,0.4)}
.b-p{background:rgba(100,116,139,0.12);color:#94A3B8;border:1px solid rgba(100,116,139,0.25)}

/* ============ LINKS E TEXTO ============ */
a{color:var(--advisian-navy-light);text-decoration:none;font-weight:600}
a:hover{color:var(--advisian-red);text-decoration:underline}
body.light a{color:var(--advisian-navy)}
.dj{color:var(--advisian-red);font-weight:700}
.dj:hover{color:var(--advisian-red-light)}
.obs{color:var(--txt-muted);font-size:11px;max-width:420px;line-height:1.6;padding:10px 16px !important}
.flag{color:#FB923C;font-size:10px;font-weight:700}
.rm{border-left:3px solid #FB923C}
.rb{border-left:3px solid var(--danger)}
.empty{text-align:center;padding:60px;color:var(--txt-dim);font-size:14px}

/* ============ BRAND ACCENT ============ */
.badge-ia{background:linear-gradient(135deg,var(--advisian-navy),var(--advisian-navy-light));color:#FFFFFF;padding:2px 6px;border-radius:3px;font-weight:800;font-size:9px;letter-spacing:1px}
.badge-ia span{color:var(--advisian-red)}
</style>
</head>
<body>
<div class="header">
<div class="header-brand">
""" + (f'<img src="{LOGO_SRC}" alt="ADVISIAN">' if LOGO_SRC else '<div style="color:#fff;font-size:28px;font-weight:900">ADVIS<span style="color:var(--advisian-red)">IA</span>N</div>') + """
<div class="header-divider"></div>
<div class="header-title">
<h1>Controller de Prazos</h1>
<div class="sub">Furtado Guerini · """ + data_geracao + """ · Classificação I<span style="color:var(--advisian-red);font-weight:800">A</span></div>
</div>
</div>

<div class="credentials">
<div class="cred-pill" title="Dados obtidos diretamente da API pública do Conselho Nacional de Justiça"><svg class="cred-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M12 2L3 7l9 5 9-5-9-5z"/><path d="M3 12l9 5 9-5"/><path d="M3 17l9 5 9-5"/></svg><span><span class="cred-label">Fonte</span><strong>API DJEN/CNJ</strong></span></div>

<div class="cred-pill" title="Motor de classificação IA de última geração"><svg class="cred-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M9 3H5a2 2 0 00-2 2v4m6-6h10a2 2 0 012 2v4M9 3v18m0 0H5a2 2 0 01-2-2v-4m6 6h10a2 2 0 002-2v-4M3 9h18M3 15h18"/></svg><span><span class="cred-label">Motor</span><strong>GPT-4.1</strong></span></div>

<div class="cred-pill" title="Base de ground truth extraída do cruzamento DJEN × DataJuri"><svg class="cred-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M3 3v18h18"/><path d="M7 14l4-4 4 4 5-5"/></svg><span><span class="cred-label">Precedentes</span><strong>22.625</strong></span></div>

<div class="cred-pill" title="170 regras de workflow do DataJuri mapeadas"><svg class="cred-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M9 11l3 3L22 4"/><path d="M21 12v7a2 2 0 01-2 2H5a2 2 0 01-2-2V5a2 2 0 012-2h11"/></svg><span><span class="cred-label">Workflows</span><strong>170 regras</strong></span></div>

<button class="theme-toggle" onclick="toggleTheme()" id="themeBtn">🌙 Escuro</button>
</div>
</div>

<div class="stats" id="statsContainer">
<div class="sc" data-filter="all"><div class="n" style="color:var(--advisian-navy-light)" id="st">""" + str(total) + """</div><div class="l">Total</div></div>
<div class="sc" data-filter="workflow"><div class="n" style="color:var(--success)" id="sw">""" + str(workflows) + """</div><div class="l">Workflows</div></div>
<div class="sc" data-filter="regra:MANUAL"><div class="n" style="color:#FB923C" id="sr">""" + str(manual) + """</div><div class="l">Manual</div></div>
<div class="sc" data-filter="regra:INFORMATIVO_SEM_PRAZO"><div class="n" style="color:var(--advisian-navy-light)" id="si">""" + str(info) + """</div><div class="l">Informativo</div></div>
<div class="sc" data-filter="regra:PENDENTE"><div class="n" style="color:var(--txt-dim)" id="sp">""" + str(pendentes) + """</div><div class="l">Pendentes</div></div>
</div>

<div class="filters">
<div class="fg"><label>Natureza</label><button class="multi-btn" data-filter="fn">Todas</button><div class="multi-dropdown"><div class="multi-actions"><button onclick="selectAll('fn')">Todos</button><button onclick="clearAll('fn')">Limpar</button></div><div class="multi-opts" id="opts-fn"></div></div></div>
<div class="fg"><label>Confiança</label><button class="multi-btn" data-filter="fc">Todas</button><div class="multi-dropdown"><div class="multi-actions"><button onclick="selectAll('fc')">Todos</button><button onclick="clearAll('fc')">Limpar</button></div><div class="multi-opts" id="opts-fc"></div></div></div>
<div class="fg"><label>Tribunal</label><button class="multi-btn" data-filter="ft">Todos</button><div class="multi-dropdown"><div class="multi-actions"><button onclick="selectAll('ft')">Todos</button><button onclick="clearAll('ft')">Limpar</button></div><div class="multi-opts" id="opts-ft"></div></div></div>
<div class="fg"><label>Tipo Doc</label><button class="multi-btn" data-filter="ftd">Todos</button><div class="multi-dropdown"><div class="multi-actions"><button onclick="selectAll('ftd')">Todos</button><button onclick="clearAll('ftd')">Limpar</button></div><div class="multi-opts" id="opts-ftd"></div></div></div>
<div class="fg"><label>Data</label><button class="multi-btn" data-filter="fd">Todas</button><div class="multi-dropdown"><div class="multi-actions"><button onclick="selectAll('fd')">Todos</button><button onclick="clearAll('fd')">Limpar</button></div><div class="multi-opts" id="opts-fd"></div></div></div>
<div class="fg"><label>Regra</label><button class="multi-btn" data-filter="fr">Todas</button><div class="multi-dropdown"><div class="multi-actions"><button onclick="selectAll('fr')">Todos</button><button onclick="clearAll('fr')">Limpar</button></div><div class="multi-opts" id="opts-fr"></div></div></div>
<div class="fg"><label>Buscar</label><input type="text" id="fb" oninput="f()" placeholder="processo..." style="width:200px"></div>
<div class="fg"><label style="opacity:0">Clear</label><button class="multi-btn" onclick="clearAllFilters()" style="background:rgba(212,48,60,0.08);color:var(--advisian-red);border-color:rgba(212,48,60,0.3);min-width:100px;text-align:center;font-weight:700">Limpar tudo</button></div>
</div>

<div class="tc">
<table><thead><tr>
<th onclick="s(0)">Processo</th><th onclick="s(1)">Data</th><th onclick="s(2)">Natureza</th>
<th onclick="s(3)">Tribunal</th><th onclick="s(4)">Tipo Doc</th><th onclick="s(5)">Regra</th>
<th onclick="s(6)">Confiança</th><th onclick="s(7)">Prazo</th><th>GT V4</th><th>Teor da Intimação</th><th>Flags</th>
</tr></thead><tbody id="tb"></tbody></table>
</div>

<script>
const LOGO_SRC = \"""" + LOGO_SRC + """\";
var D=""" + rows_json + """;
var sc=-1,sa=true;
var filters={fn:[],fc:[],ft:[],ftd:[],fd:[],fr:[]};
var cardFilter=null;

function toggleTheme(){
  document.body.classList.toggle('light');
  var btn=document.getElementById('themeBtn');
  btn.innerHTML=document.body.classList.contains('light')?'☀️ Claro':'🌙 Escuro';
  localStorage.setItem('advisianTheme',document.body.classList.contains('light')?'light':'dark');
}
if(localStorage.getItem('advisianTheme')==='light'){document.body.classList.add('light');document.getElementById('themeBtn').innerHTML='☀️ Claro';}

function bg(c){if(!c)return'';var m={'ALTA':'b-a','MEDIA':'b-m','BAIXA':'b-b'};return'<span class="b '+(m[c]||'b-p')+'">'+c+'</span>';}
function rg(r){if(!r)return'';if(r.indexOf('MANUAL')>=0||r.indexOf('NENHUMA')>=0)return'<span class="b b-man">'+r+'</span>';if(r=='INFORMATIVO_SEM_PRAZO')return'<span class="b b-info">INFORMATIVO</span>';if(r=='PENDENTE'||r=='PENDENTE_CLASSIFICACAO'||r=='ERRO_CLASSIFICACAO')return'<span class="b b-p">'+r+'</span>';return r;}

function openVL(idx){
  var r=D[idx];
  var txt=(r.texto||'').replace(/\\\\n/g,'\\n').replace(/\\n/g,' ');
  var clean=txt;
  clean=clean.replace(/[#.]?[a-zA-Z][\\w-]*\\s*\\{[^}]*\\}/g,' ');
  clean=clean.replace(/[a-z-]+\\s*:\\s*[^;\\n]+;?/gi,function(m){if(/font-family|padding|margin|color|background|border|display|width|height|line-height|text-align|font-size|font-weight|font-style/i.test(m))return ' ';return m;});
  clean=clean.replace(/<[^>]+>/g,' ').replace(/&[a-z]+;/gi,' ').replace(/&#\\d+;/g,' ');
  clean=clean.replace(/\\s+/g,' ').trim();

  var upper=clean.replace(/[^A-Z]/g,'').length;
  var alpha=clean.replace(/[^a-zA-Z]/g,'').length;
  if(alpha>0&&upper/alpha>0.6){
    clean=clean.toLowerCase().replace(/(^|[.!?;:]\\s+)([a-z])/g,function(m,p,c){return p+c.toUpperCase()});
    ['INSS','RPV','CLT','CPC','CPF','CNPJ','OAB','TRT','TRF','TST','STJ','STF','DJEN','FGTS'].forEach(function(s){var re=new RegExp('\\\\b'+s.toLowerCase()+'\\\\b','gi');clean=clean.replace(re,s)});
  }

  clean=clean.replace(/(\\d+)\\s*\\(?([^)]*?)\\)?\\s*(dias?|horas?)/gi,'<strong style="color:#D4303C">$1 $2 $3</strong>');
  clean=clean.replace(/R\\$\\s*[\\d.,]+/gi,function(m){return'<strong style="color:#10B981">'+m+'</strong>'});
  clean=clean.replace(/(\\d{2}\\/\\d{2}\\/\\d{4})/g,'<strong style="color:#1E3A5F">$1</strong>');
  ['JULGO PROCEDENTE','JULGO IMPROCEDENTE','ACORDAM','NEGO PROVIMENTO','DOU PROVIMENTO'].forEach(function(t){var re=new RegExp('('+t+')','gi');clean=clean.replace(re,'<strong style="color:#F59E0B">$1</strong>')});
  ['SOB PENA DE','REVELIA','PRECLUSAO'].forEach(function(t){var re=new RegExp('('+t+')','gi');clean=clean.replace(re,'<strong style="color:#FB923C">$1</strong>')});
  ['INTIME-SE','CITE-SE','DEFIRO','INDEFIRO'].forEach(function(t){var re=new RegExp('('+t+')','gi');clean=clean.replace(re,'<strong style="color:#1E3A5F">$1</strong>')});
  clean=clean.replace(/(https?:\\/\\/[^\\s]+)/g,'<a href="$1" target="_blank" class="url">$1</a>');

  var frases=[];
  clean.split(/(?<=[.;!?])\\s+/).forEach(function(f){if(f.trim().length>3)frases.push(f.trim())});
  if(frases.length<2&&clean.length>150){
    frases=[];var words=clean.split(/\\s+/),line='';
    words.forEach(function(w){if((line+' '+w).length>180){if(line.trim())frases.push(line.trim());line=w}else{line+=(line?' ':'')+w}});
    if(line.trim())frases.push(line.trim());
  }
  var confColor=r.confianca=='ALTA'?'#10B981':r.confianca=='MEDIA'?'#F59E0B':'#EF4444';

  var w=window.open('','_blank');
  var h='<!DOCTYPE html><html><head><meta charset="UTF-8"><title>'+r.processo+' · ADVISIAN</title>';
  h+='<link rel="icon" type="image/png" href="'+LOGO_SRC+'">';
  h+='<style>';
  h+='*{margin:0;padding:0;box-sizing:border-box}';
  h+='html,body{background:#0A0E1A;color:#E2E8F0;font-family:-apple-system,BlinkMacSystemFont,"Inter",sans-serif;-webkit-font-smoothing:antialiased}';
  h+='.layout{display:grid;grid-template-columns:1fr 400px;min-height:100vh}';
  h+='.topbar{background:#FFFFFF;padding:20px 40px;border-bottom:3px solid #D4303C;display:flex;align-items:center;gap:24px;box-shadow:0 4px 24px rgba(10,30,61,0.08)}';
  h+='.topbar img{height:48px;width:auto;display:block}';
  h+='.topbar .titlebar{color:#64748B;font-size:11px;text-transform:uppercase;letter-spacing:1.5px;font-weight:700;padding-left:24px;border-left:1px solid rgba(10,30,61,0.15)}';
  h+='.main{padding:0;overflow-y:auto}';
  h+='.hero{padding:40px 48px 32px;border-bottom:1px solid rgba(255,255,255,0.06)}';
  h+='.crumb{font-size:11px;color:#64748B;margin-bottom:16px;font-weight:600;letter-spacing:0.5px;text-transform:uppercase}';
  h+='.crumb span{color:#475569;margin:0 8px}';
  h+='.titulo{font-size:36px;font-weight:800;color:#F1F5F9;letter-spacing:-1.2px;line-height:1.1}';
  h+='.subt{font-size:13px;color:#94A3B8;margin-top:10px;font-weight:500}';
  h+='.subt strong{color:#D4303C;font-weight:700}';
  h+='.meta-grid{display:grid;grid-template-columns:repeat(3,1fr);margin-top:36px;border-top:1px solid rgba(10,30,61,0.2)}';
  h+='.meta-item{padding:16px 20px 16px 0;border-bottom:1px solid rgba(10,30,61,0.2);border-right:1px solid rgba(10,30,61,0.2)}';
  h+='.meta-item:nth-child(3n){border-right:none}';
  h+='.meta-item .ml{font-size:10px;color:#64748B;text-transform:uppercase;letter-spacing:1.3px;font-weight:700;margin-bottom:6px}';
  h+='.meta-item .mv{font-size:14px;color:#E2E8F0;font-weight:600}';
  h+='.page-wrap{padding:24px 48px 64px}';
  h+='.page{background:#121826;border:1px solid rgba(30,41,59,0.6);border-radius:12px;padding:48px 56px;box-shadow:0 12px 32px rgba(0,0,0,0.3)}';
  h+='.page-intro{font-size:10px;color:#64748B;text-transform:uppercase;letter-spacing:2px;font-weight:800;margin-bottom:20px;padding-bottom:16px;border-bottom:2px solid #D4303C;display:inline-block}';
  h+='.page p{font-size:15px;line-height:1.9;color:#D1D5DB;margin-bottom:20px;text-align:left}';
  h+='.url{display:inline-block;font-family:"SF Mono",Menlo,monospace;font-size:11px;color:#60A5FA;background:rgba(30,58,95,0.3);padding:2px 8px;border-radius:5px;word-break:break-all;max-width:100%}';
  h+='.prazo-banner{background:linear-gradient(135deg,rgba(212,48,60,0.12) 0%,rgba(212,48,60,0.04) 100%);border:1px solid rgba(212,48,60,0.3);border-left:4px solid #D4303C;border-radius:10px;padding:20px 28px;margin-bottom:24px;display:flex;align-items:center;justify-content:space-between}';
  h+='.prazo-banner .pb-l{font-size:10px;color:#D4303C;text-transform:uppercase;letter-spacing:2px;font-weight:800}';
  h+='.prazo-banner .pb-v{font-size:32px;color:#E84855;font-weight:800;letter-spacing:-1.2px;line-height:1;margin-top:4px}';
  h+='.side{padding:48px 32px;position:sticky;top:0;height:100vh;overflow-y:auto;border-left:1px solid rgba(30,41,59,0.6);background:#0F1724}';
  h+='.btn-primary{display:block;text-align:center;padding:14px 20px;background:linear-gradient(135deg,#0A1E3D,#1E3A5F);color:#FFF;border:none;border-radius:10px;text-decoration:none;font-size:13px;font-weight:700;letter-spacing:0.3px;box-shadow:0 4px 12px rgba(10,30,61,0.4);transition:all .2s}';
  h+='.btn-primary:hover{transform:translateY(-1px);box-shadow:0 6px 16px rgba(10,30,61,0.5)}';
  h+='.btn-ghost{display:block;text-align:center;padding:10px 16px;color:#D4303C;text-decoration:none;font-size:11px;margin-top:10px;font-weight:600;border:1px solid rgba(212,48,60,0.3);border-radius:999px;background:rgba(212,48,60,0.04);transition:all .15s;letter-spacing:0.3px}';
  h+='.btn-ghost:hover{border-color:#D4303C;background:rgba(212,48,60,0.12)}';
  h+='.side-section{margin-bottom:32px}';
  h+='.side-title{font-size:10px;color:#64748B;text-transform:uppercase;letter-spacing:2px;font-weight:800;margin-bottom:16px;padding-bottom:8px;border-bottom:1px solid rgba(30,41,59,0.6)}';
  h+='.ia-regra{font-size:19px;color:#D4303C;font-weight:700;line-height:1.25;letter-spacing:-0.3px;margin-bottom:16px}';
  h+='.ia-chips{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:24px}';
  h+='.ia-chip{padding:5px 12px;border-radius:16px;font-size:11px;font-weight:700;background:rgba(30,41,59,0.6);color:#D1D5DB;border:1px solid rgba(30,41,59,0.8)}';
  h+='.ia-chip.alta{background:rgba(16,185,129,0.1);color:#10B981;border-color:rgba(16,185,129,0.3)}';
  h+='.ia-chip.media{background:rgba(245,158,11,0.1);color:#F59E0B;border-color:rgba(245,158,11,0.3)}';
  h+='.ia-chip.baixa{background:rgba(239,68,68,0.1);color:#EF4444;border-color:rgba(239,68,68,0.3)}';
  h+='.ia-chip.prazo{background:rgba(212,48,60,0.1);color:#E84855;border-color:rgba(212,48,60,0.3)}';
  h+='.info-block{margin-bottom:20px}';
  h+='.info-block .ib-l{font-size:10px;color:#64748B;text-transform:uppercase;letter-spacing:1.2px;font-weight:700;margin-bottom:8px}';
  h+='.info-block .ib-v{font-size:13px;color:#D1D5DB;line-height:1.7}';
  h+='.info-block .ib-v.quote{font-size:12px;color:#94A3B8;font-style:italic;padding-left:14px;border-left:2px solid #D4303C}';
  h+='.dados-row{display:flex;justify-content:space-between;padding:10px 0;border-bottom:1px solid rgba(30,41,59,0.6)}';
  h+='.dados-row:last-child{border:none}';
  h+='.dados-row .dr-k{font-size:11px;color:#64748B;font-weight:600}';
  h+='.dados-row .dr-v{font-size:12px;color:#D1D5DB;font-weight:600;text-align:right;max-width:65%}';
  h+='</style></head><body>';
  h+='<div class="topbar"><img src="'+LOGO_SRC+'" alt="ADVISIAN"><div class="titlebar">Publicação DJEN · Controller de Prazos</div></div>';
  h+='<div class="layout"><div class="main"><div class="hero">';
  h+='<div class="crumb">'+r.data+'<span>/</span>'+r.natureza+'<span>/</span>'+r.tribunal+'</div>';
  h+='<h1 class="titulo">'+r.processo+'</h1>';
  h+='<div class="subt"><strong>'+r.tipo_doc+'</strong> &middot; '+r.natureza+'</div>';
  h+='<div class="meta-grid">';
  h+='<div class="meta-item"><div class="ml">Cliente</div><div class="mv">'+(r.cliente||'-')+'</div></div>';
  if(r.adverso)h+='<div class="meta-item"><div class="ml">Adverso</div><div class="mv">'+r.adverso+'</div></div>';
  h+='<div class="meta-item"><div class="ml">Natureza</div><div class="mv">'+r.natureza+'</div></div>';
  if(r.tipo_acao)h+='<div class="meta-item"><div class="ml">Ação</div><div class="mv">'+r.tipo_acao+'</div></div>';
  if(r.tipo_processo)h+='<div class="meta-item"><div class="ml">Tipo</div><div class="mv">'+r.tipo_processo+'</div></div>';
  if(r.valor_causa)h+='<div class="meta-item"><div class="ml">Valor da Causa</div><div class="mv" style="color:#10B981;font-weight:700">R$ '+r.valor_causa+'</div></div>';
  if(r.fase_atual)h+='<div class="meta-item"><div class="ml">Fase atual</div><div class="mv">'+r.fase_atual+'</div></div>';
  h+='<div class="meta-item"><div class="ml">Tribunal</div><div class="mv">'+r.tribunal+'</div></div>';
  h+='</div></div>';
  h+='<div class="page-wrap"><div class="page">';
  h+='<div class="page-intro">Teor da Intimação</div>';
  if(r.prazo)h+='<div class="prazo-banner"><div><div class="pb-l">Prazo identificado</div><div class="pb-v">'+r.prazo+' dias</div></div><div style="font-size:40px;opacity:0.3">⏱</div></div>';
  frases.forEach(function(f){h+='<p>'+f+'</p>'});
  h+='</div></div></div>';
  h+='<div class="side">';
  if(r.dj_url)h+='<a class="btn-primary" href="'+r.dj_url+'" target="_blank">Abrir no DataJuri →</a>';
  if(r.djen_link)h+='<a class="btn-ghost" href="'+r.djen_link+'" target="_blank">Ver documento DJEN</a>';
  h+='<div class="side-section" style="margin-top:32px">';
  h+='<div class="side-title">Classificação I<span style="color:#D4303C">A</span></div>';
  h+='<div class="ia-regra">'+(r.regra||'Pendente')+'</div>';
  h+='<div class="ia-chips">';
  if(r.confianca)h+='<span class="ia-chip '+r.confianca.toLowerCase()+'">'+r.confianca+'</span>';
  if(r.prazo)h+='<span class="ia-chip prazo">'+r.prazo+' dias</span>';
  h+='</div>';
  if(r.justificativa)h+='<div class="info-block"><div class="ib-l">Justificativa</div><div class="ib-v">'+r.justificativa+'</div></div>';
  if(r.observacoes)h+='<div class="info-block"><div class="ib-l">Observações</div><div class="ib-v">'+r.observacoes+'</div></div>';
  if(r.flags)h+='<div class="info-block"><div class="ib-l">Alertas</div><div class="ib-v" style="color:#F59E0B">'+r.flags+'</div></div>';
  h+='</div>';
  if(r.raciocinio)h+='<div class="side-section"><div class="side-title">Raciocínio</div><div class="info-block"><div class="ib-v quote">'+r.raciocinio+'</div></div></div>';
  h+='<div class="side-section"><div class="side-title">Processo</div>';
  h+='<div class="dados-row"><span class="dr-k">Número</span><span class="dr-v">'+r.processo+'</span></div>';
  h+='<div class="dados-row"><span class="dr-k">Data</span><span class="dr-v">'+r.data+'</span></div>';
  h+='<div class="dados-row"><span class="dr-k">Tribunal</span><span class="dr-v">'+r.tribunal+'</span></div>';
  if(r.assunto_dj)h+='<div class="dados-row"><span class="dr-k">Assunto</span><span class="dr-v">'+r.assunto_dj+'</span></div>';
  h+='<div class="dados-row"><span class="dr-k">Cliente</span><span class="dr-v">'+(r.cliente||'-')+'</span></div>';
  if(r.adverso)h+='<div class="dados-row"><span class="dr-k">Adverso</span><span class="dr-v">'+r.adverso+'</span></div>';
  h+='</div></div></div></body></html>';
  w.document.write(h);
  w.document.close();
}

function render(rows){
  var tb=document.getElementById('tb');
  if(!rows.length){tb.innerHTML='<tr><td colspan="11" class="empty">Nenhuma publicação encontrada</td></tr>';return;}
  var h='';
  for(var i=0;i<rows.length;i++){
    var r=rows[i];var oi=D.indexOf(r);
    var rc=r.regra.indexOf('MANUAL')>=0||r.regra.indexOf('NENHUMA')>=0?'rm':r.confianca=='BAIXA'?'rb':'';
    var dj=r.dj_url?'<a class="dj" href="'+r.dj_url+'" target="_blank" onclick="event.stopPropagation()">'+r.processo+'</a>':r.processo;
    var dl=r.djen_link?' <a href="'+r.djen_link+'" target="_blank" onclick="event.stopPropagation()" style="font-size:10px;color:#64748B">[DJEN]</a>':'';
    var teor=(r.texto||'').replace(/<[^>]+>/g,' ').replace(/\\s+/g,' ').trim();
    if(teor.length>280)teor=teor.substring(0,280)+'…';
    var gtHtml='';
    if(r.gt_status==='CONCORDA')gtHtml='<span class="b b-a" title="GT confirma: '+r.gt_regra+'">✓ '+r.gt_sim+'</span>';
    else if(r.gt_status==='CONFLITO')gtHtml='<span class="b b-b" title="GT sugere: '+r.gt_regra+' (sim: '+r.gt_sim+')">⚠ '+r.gt_sim+'</span>';
    else if(r.gt_status==='PRECEDENTE_FRACO')gtHtml='<span class="b b-p" title="Precedente fraco">~</span>';
    h+='<tr class="'+rc+'" onclick="openVL('+oi+')"><td>'+dj+dl+'</td><td style="white-space:nowrap">'+r.data+'</td><td>'+r.natureza+'</td><td>'+r.tribunal+'</td><td>'+r.tipo_doc+'</td><td>'+rg(r.regra)+'</td><td>'+bg(r.confianca)+'</td><td style="font-weight:800;color:#D4303C">'+(r.prazo?r.prazo+'d':'')+'</td><td>'+gtHtml+'</td><td class="obs">'+teor+'</td><td class="flag">'+r.flags+'</td></tr>';
  }
  tb.innerHTML=h;
  updateStats(rows);
}

function updateStats(rows){
  var pend=['PENDENTE','PENDENTE_CLASSIFICACAO','','ERRO_CLASSIFICACAO'];
  var excl=pend.concat(['INFORMATIVO_SEM_PRAZO']);
  document.getElementById('st').textContent=rows.length;
  document.getElementById('sw').textContent=rows.filter(function(r){return r.regra&&excl.indexOf(r.regra)<0&&r.regra.indexOf('MANUAL')<0&&r.regra.indexOf('NENHUMA')<0}).length;
  document.getElementById('sr').textContent=rows.filter(function(r){return r.regra.indexOf('MANUAL')>=0||r.regra.indexOf('NENHUMA')>=0}).length;
  document.getElementById('si').textContent=rows.filter(function(r){return r.regra=='INFORMATIVO_SEM_PRAZO'}).length;
  document.getElementById('sp').textContent=rows.filter(function(r){return pend.indexOf(r.regra)>=0}).length;
  if(document.getElementById('sgc'))document.getElementById('sgc').textContent=rows.filter(function(r){return r.gt_status==='CONCORDA'}).length;
  if(document.getElementById('sgk'))document.getElementById('sgk').textContent=rows.filter(function(r){return r.gt_status==='CONFLITO'}).length;
}

function applyFilters(){
  var busca=document.getElementById('fb').value.toLowerCase();
  var r=D.filter(function(x){
    if(filters.fn.length>0&&filters.fn.indexOf(x.natureza)<0)return false;
    if(filters.fc.length>0&&filters.fc.indexOf(x.confianca)<0)return false;
    if(filters.ft.length>0&&filters.ft.indexOf(x.tribunal)<0)return false;
    if(filters.ftd.length>0&&filters.ftd.indexOf(x.tipo_doc)<0)return false;
    if(filters.fd.length>0&&filters.fd.indexOf(x.data)<0)return false;
    if(filters.fr.length>0&&filters.fr.indexOf(x.regra)<0)return false;
    if(busca&&x.processo.toLowerCase().indexOf(busca)<0)return false;
    var pend=['PENDENTE','PENDENTE_CLASSIFICACAO','','ERRO_CLASSIFICACAO'];
    var excl=pend.concat(['INFORMATIVO_SEM_PRAZO']);
    if(cardFilter){
      if(cardFilter==='all')return true;
      if(cardFilter==='workflow'&&(!x.regra||excl.indexOf(x.regra)>=0||x.regra.indexOf('MANUAL')>=0||x.regra.indexOf('NENHUMA')>=0))return false;
      if(cardFilter==='regra:MANUAL'&&x.regra.indexOf('MANUAL')<0&&x.regra.indexOf('NENHUMA')<0)return false;
      if(cardFilter==='regra:INFORMATIVO_SEM_PRAZO'&&x.regra!='INFORMATIVO_SEM_PRAZO')return false;
      if(cardFilter==='regra:PENDENTE'&&pend.indexOf(x.regra)<0)return false;
      if(cardFilter==='gt:CONCORDA'&&x.gt_status!=='CONCORDA')return false;
      if(cardFilter==='gt:CONFLITO'&&x.gt_status!=='CONFLITO')return false;
    }
    return true;
  });
  render(r);
}
function f(){applyFilters();}

document.querySelectorAll('.sc').forEach(function(c){
  c.addEventListener('click',function(){
    var filter=c.dataset.filter;
    if(cardFilter===filter){cardFilter=null;document.querySelectorAll('.sc').forEach(function(x){x.classList.remove('active')});}
    else{cardFilter=filter;document.querySelectorAll('.sc').forEach(function(x){x.classList.remove('active')});c.classList.add('active');}
    applyFilters();
  });
});

function buildMultiSelect(id,values){
  var c=document.getElementById('opts-'+id);c.innerHTML='';
  values.forEach(function(v){
    var opt=document.createElement('div');opt.className='multi-opt';
    opt.innerHTML='<input type="checkbox" data-val="'+v+'"><span class="lb-opt">'+v+'</span>';
    opt.addEventListener('click',function(e){
      if(e.target.tagName!=='INPUT'){var cb=opt.querySelector('input');cb.checked=!cb.checked;}
      updateMultiFilter(id);
    });
    c.appendChild(opt);
  });
}

function updateMultiFilter(id){
  var checked=Array.from(document.querySelectorAll('#opts-'+id+' input:checked')).map(function(cb){return cb.dataset.val});
  filters[id]=checked;
  var btn=document.querySelector('.multi-btn[data-filter="'+id+'"]');
  if(checked.length===0){btn.textContent='Todas';btn.classList.remove('has-val');}
  else if(checked.length===1){btn.textContent=checked[0];btn.classList.add('has-val');}
  else{btn.textContent=checked.length+' selecionados';btn.classList.add('has-val');}
  document.querySelectorAll('#opts-'+id+' .multi-opt').forEach(function(o){
    var cb=o.querySelector('input');if(cb.checked)o.classList.add('selected');else o.classList.remove('selected');
  });
  applyFilters();
}

function selectAll(id){document.querySelectorAll('#opts-'+id+' input').forEach(function(cb){cb.checked=true});updateMultiFilter(id);}
function clearAll(id){document.querySelectorAll('#opts-'+id+' input').forEach(function(cb){cb.checked=false});updateMultiFilter(id);}
function clearAllFilters(){['fn','fc','ft','ftd','fd','fr'].forEach(function(id){clearAll(id)});document.getElementById('fb').value='';cardFilter=null;document.querySelectorAll('.sc').forEach(function(x){x.classList.remove('active')});applyFilters();}

document.querySelectorAll('.multi-btn[data-filter]').forEach(function(btn){
  btn.addEventListener('click',function(e){
    e.stopPropagation();var dd=btn.nextElementSibling;
    document.querySelectorAll('.multi-dropdown.open').forEach(function(x){if(x!==dd)x.classList.remove('open')});
    dd.classList.toggle('open');
  });
});
document.addEventListener('click',function(){document.querySelectorAll('.multi-dropdown.open').forEach(function(x){x.classList.remove('open')});});

function s(col){
  if(sc==col)sa=!sa;else{sc=col;sa=true;}
  var k=['processo','data','natureza','tribunal','tipo_doc','regra','confianca','prazo'];
  D.sort(function(a,b){var va=a[k[col]]||'',vb=b[k[col]]||'';return sa?va.localeCompare(vb):vb.localeCompare(va);});
  applyFilters();
}

var tribs=[...new Set(D.map(function(r){return r.tribunal}).filter(Boolean))].sort();
var datas=[...new Set(D.map(function(r){return r.data}).filter(Boolean))].sort().reverse();
var regras=[...new Set(D.map(function(r){return r.regra}).filter(Boolean))].sort();
var tipos=[...new Set(D.map(function(r){return r.tipo_doc}).filter(Boolean))].sort();
var natur=[...new Set(D.map(function(r){return r.natureza}).filter(Boolean))].sort();
buildMultiSelect('fn',natur);
buildMultiSelect('fc',['ALTA','MEDIA','BAIXA']);
buildMultiSelect('ft',tribs);
buildMultiSelect('ftd',tipos);
buildMultiSelect('fd',datas);
buildMultiSelect('fr',regras);
render(D);
</script>
</body>
</html>"""

# Criar tambem o index.html (copia) pra Netlify abrir direto na URL raiz
with open("dashboard_prazos.html", "w", encoding="utf-8") as f:
    f.write(html)
with open("index.html", "w", encoding="utf-8") as f:
    f.write(html)

print(f"ADVISIAN Dashboard: {total} | Workflows:{workflows} Manual:{manual} Info:{info} Pendentes:{pendentes}")
print(f"GT: Concorda={gt_concorda} Conflito={gt_conflito}")
print(f"Arquivos gerados: dashboard_prazos.html + index.html")
