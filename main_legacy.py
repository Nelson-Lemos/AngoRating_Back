from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import uuid, math, random

app = FastAPI(title="AngoRating API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Models ──────────────────────────────────────────────────────────────────

class ReviewCreate(BaseModel):
    entity_id: str
    author: str
    score: float          # 1-10
    comment: str
    categories: dict      # {"atendimento": 8, "rapidez": 7, ...}

class VoteRequest(BaseModel):
    entity_id: str
    type: str             # "up" | "down"

# ─── Seed data ───────────────────────────────────────────────────────────────

SECTORS = {
    "bancario":       {"label": "Bancário",         "icon": "🏦", "color": "#f59e0b"},
    "saude":          {"label": "Saúde",             "icon": "🏥", "color": "#14b8a6"},
    "educacao":       {"label": "Educação",          "icon": "🎓", "color": "#3b82f6"},
    "tecnologia":     {"label": "Tecnologia",        "icon": "💻", "color": "#10b981"},
    "hotelaria":      {"label": "Hotelaria",         "icon": "🏨", "color": "#f97316"},
    "restauracao":    {"label": "Restauração",       "icon": "🍽️", "color": "#e11d48"},
    "publico":        {"label": "Público / Gov.",    "icon": "🏛️", "color": "#8b5cf6"},
    "telecomunicacoes":{"label": "Telecomunicações", "icon": "📡", "color": "#06b6d4"},
    "transportes":    {"label": "Transportes",       "icon": "✈️", "color": "#64748b"},
    "energia":        {"label": "Energia",           "icon": "⚡", "color": "#eab308"},
    "retalho":        {"label": "Retalho",           "icon": "🛒", "color": "#ec4899"},
    "seguros":        {"label": "Seguros",           "icon": "🛡️", "color": "#0ea5e9"},
}

ENTITIES = [
    {"id":"bic","name":"Banco BIC","sector":"bancario","province":"Luanda","score":8.4,"votes":1240,"pos":980,"neg":260,"trending":True,"verified":True,"founded":1991,"desc":"Um dos maiores bancos privados de Angola.","categories":{"atendimento":82,"rapidez":78,"confianca":90,"preco":70,"infraestrutura":85}},
    {"id":"sagrada","name":"Clínica Sagrada Esperança","sector":"saude","province":"Luanda","score":8.1,"votes":890,"pos":720,"neg":170,"trending":True,"verified":True,"founded":2000,"desc":"Clínica de referência em saúde privada em Angola.","categories":{"atendimento":85,"rapidez":70,"confianca":86,"preco":60,"infraestrutura":88}},
    {"id":"unitel","name":"Unitel","sector":"telecomunicacoes","province":"Nacional","score":7.9,"votes":2100,"pos":1650,"neg":450,"trending":False,"verified":True,"founded":2001,"desc":"Principal operadora de telecomunicações móveis de Angola.","categories":{"atendimento":74,"rapidez":82,"confianca":80,"preco":68,"infraestrutura":86}},
    {"id":"uan","name":"Univ. Agostinho Neto","sector":"educacao","province":"Luanda","score":7.7,"votes":670,"pos":520,"neg":150,"trending":False,"verified":True,"founded":1962,"desc":"Principal universidade pública de Angola.","categories":{"atendimento":76,"rapidez":72,"confianca":82,"preco":88,"infraestrutura":74}},
    {"id":"pres","name":"Hotel Presidente","sector":"hotelaria","province":"Luanda","score":8.6,"votes":540,"pos":470,"neg":70,"trending":True,"verified":True,"founded":1975,"desc":"Hotel 5 estrelas icónico de Luanda.","categories":{"atendimento":90,"rapidez":85,"confianca":88,"preco":50,"infraestrutura":94}},
    {"id":"bfa","name":"BFA","sector":"bancario","province":"Nacional","score":7.5,"votes":980,"pos":740,"neg":240,"trending":False,"verified":True,"founded":1993,"desc":"Banco de Fomento Angola, parceria BPI/Isabel dos Santos.","categories":{"atendimento":72,"rapidez":74,"confianca":77,"preco":68,"infraestrutura":80}},
    {"id":"multiperfil","name":"Clínica Multiperfil","sector":"saude","province":"Luanda","score":7.2,"votes":430,"pos":310,"neg":120,"trending":False,"verified":True,"founded":2010,"desc":"Clínica com especialidades múltiplas em Luanda.","categories":{"atendimento":70,"rapidez":68,"confianca":74,"preco":62,"infraestrutura":76}},
    {"id":"sonangol","name":"Sonangol","sector":"energia","province":"Nacional","score":6.8,"votes":1560,"pos":1060,"neg":500,"trending":False,"verified":True,"founded":1976,"desc":"Empresa estatal petrolífera de Angola.","categories":{"atendimento":62,"rapidez":65,"confianca":74,"preco":72,"infraestrutura":78}},
    {"id":"belmondo","name":"Restaurante Belmondo","sector":"restauracao","province":"Luanda","score":8.9,"votes":360,"pos":340,"neg":20,"trending":True,"verified":False,"founded":2015,"desc":"Restaurante de gastronomia internacional em Luanda.","categories":{"atendimento":92,"rapidez":88,"confianca":90,"preco":65,"infraestrutura":90}},
    {"id":"movicel","name":"Movicel","sector":"telecomunicacoes","province":"Nacional","score":7.1,"votes":1320,"pos":940,"neg":380,"trending":False,"verified":True,"founded":2003,"desc":"Segunda maior operadora móvel de Angola.","categories":{"atendimento":68,"rapidez":74,"confianca":72,"preco":74,"infraestrutura":72}},
    {"id":"bai","name":"BAI","sector":"bancario","province":"Luanda","score":7.8,"votes":860,"pos":680,"neg":180,"trending":True,"verified":True,"founded":1997,"desc":"Banco Angolano de Investimentos, banco de excelência.","categories":{"atendimento":78,"rapidez":76,"confianca":80,"preco":66,"infraestrutura":82}},
    {"id":"intercont","name":"Hotel Intercontinental","sector":"hotelaria","province":"Luanda","score":9.1,"votes":480,"pos":455,"neg":25,"trending":True,"verified":True,"founded":2006,"desc":"Hotel de luxo 5 estrelas referência em Luanda.","categories":{"atendimento":94,"rapidez":90,"confianca":92,"preco":44,"infraestrutura":96}},
    {"id":"tpa","name":"TPA","sector":"publico","province":"Nacional","score":5.4,"votes":2400,"pos":1300,"neg":1100,"trending":False,"verified":True,"founded":1975,"desc":"Televisão Pública de Angola.","categories":{"atendimento":50,"rapidez":52,"confianca":58,"preco":80,"infraestrutura":56}},
    {"id":"amer","name":"Escola Americana","sector":"educacao","province":"Luanda","score":8.3,"votes":220,"pos":195,"neg":25,"trending":False,"verified":True,"founded":1998,"desc":"Escola internacional de referência com currículo americano.","categories":{"atendimento":86,"rapidez":80,"confianca":84,"preco":40,"infraestrutura":90}},
    {"id":"afrilink","name":"AfricaLink Tech","sector":"tecnologia","province":"Luanda","score":8.7,"votes":180,"pos":165,"neg":15,"trending":True,"verified":False,"founded":2018,"desc":"Startup de tecnologia e soluções digitais angolana.","categories":{"atendimento":88,"rapidez":90,"confianca":86,"preco":72,"infraestrutura":82}},
    {"id":"taag","name":"TAAG","sector":"transportes","province":"Nacional","score":6.2,"votes":1800,"pos":1100,"neg":700,"trending":False,"verified":True,"founded":1938,"desc":"Transportes Aéreos Angolanos, companhia aérea nacional.","categories":{"atendimento":58,"rapidez":60,"confianca":68,"preco":62,"infraestrutura":64}},
    {"id":"bpc","name":"BPC","sector":"bancario","province":"Nacional","score":6.5,"votes":760,"pos":495,"neg":265,"trending":False,"verified":True,"founded":1956,"desc":"Banco de Poupança e Crédito, banco estatal angolano.","categories":{"atendimento":60,"rapidez":62,"confianca":72,"preco":74,"infraestrutura":68}},
    {"id":"bengplaza","name":"Benguela Plaza","sector":"hotelaria","province":"Benguela","score":7.6,"votes":210,"pos":165,"neg":45,"trending":False,"verified":False,"founded":2012,"desc":"Hotel boutique na cidade de Benguela.","categories":{"atendimento":78,"rapidez":74,"confianca":76,"preco":68,"infraestrutura":74}},
    {"id":"correios","name":"Correios de Angola","sector":"publico","province":"Nacional","score":4.8,"votes":920,"pos":400,"neg":520,"trending":False,"verified":True,"founded":1979,"desc":"Serviço postal nacional de Angola.","categories":{"atendimento":44,"rapidez":46,"confianca":52,"preco":78,"infraestrutura":48}},
    {"id":"kero","name":"Kero","sector":"retalho","province":"Nacional","score":7.0,"votes":1100,"pos":800,"neg":300,"trending":False,"verified":True,"founded":2009,"desc":"Cadeia de supermercados líder em Angola.","categories":{"atendimento":70,"rapidez":72,"confianca":68,"preco":76,"infraestrutura":72}},
    {"id":"zap","name":"ZAP","sector":"telecomunicacoes","province":"Nacional","score":7.4,"votes":680,"pos":510,"neg":170,"trending":True,"verified":True,"founded":2013,"desc":"Operadora de TV por satélite e banda larga.","categories":{"atendimento":72,"rapidez":76,"confianca":74,"preco":66,"infraestrutura":78}},
    {"id":"endiama","name":"Endiama","sector":"energia","province":"Nacional","score":6.6,"votes":340,"pos":220,"neg":120,"trending":False,"verified":True,"founded":1981,"desc":"Empresa Nacional de Diamantes de Angola.","categories":{"atendimento":62,"rapidez":64,"confianca":72,"preco":70,"infraestrutura":68}},
    {"id":"ucan","name":"Univ. Católica de Angola","sector":"educacao","province":"Luanda","score":8.0,"votes":390,"pos":310,"neg":80,"trending":True,"verified":True,"founded":1999,"desc":"Universidade Católica de Angola, excelência académica.","categories":{"atendimento":80,"rapidez":78,"confianca":84,"preco":56,"infraestrutura":86}},
    {"id":"salta","name":"Restaurante A Salta","sector":"restauracao","province":"Luanda","score":8.2,"votes":290,"pos":255,"neg":35,"trending":False,"verified":False,"founded":2017,"desc":"Restaurante de culinária tradicional angolana.","categories":{"atendimento":84,"rapidez":80,"confianca":84,"preco":72,"infraestrutura":78}},
    {"id":"ensa","name":"ENSA","sector":"seguros","province":"Nacional","score":6.9,"votes":420,"pos":290,"neg":130,"trending":False,"verified":True,"founded":1978,"desc":"Empresa Nacional de Seguros e Resseguros de Angola.","categories":{"atendimento":66,"rapidez":68,"confianca":72,"preco":68,"infraestrutura":70}},
]

# In-memory state
reviews_db: List[dict] = []
votes_db: dict = {}  # entity_id -> {up, down}

def score_label(s: float):
    if s >= 9: return "Excelente"
    if s >= 8: return "Muito bom"
    if s >= 7: return "Bom"
    if s >= 6: return "Razoável"
    if s >= 5: return "Fraco"
    return "Mau"

def enrich(e: dict):
    total = e["votes"] or 1
    return {
        **e,
        "score_label": score_label(e["score"]),
        "sentiment_pct": round(e["pos"] / total * 100),
        "sector_meta": SECTORS.get(e["sector"], {}),
        "review_count": sum(1 for r in reviews_db if r["entity_id"] == e["id"]),
    }

# ─── Routes ──────────────────────────────────────────────────────────────────

@app.get("/api/sectors")
def get_sectors():
    return list(SECTORS.items())

@app.get("/api/entities")
def get_entities(
    sector: Optional[str] = None,
    province: Optional[str] = None,
    q: Optional[str] = None,
    sort: str = "score",
    trending: Optional[bool] = None,
    limit: int = 50,
    offset: int = 0,
):
    items = [enrich(e) for e in ENTITIES]
    if sector and sector != "all":
        items = [e for e in items if e["sector"] == sector]
    if province and province != "Nacional":
        items = [e for e in items if e["province"] == province or e["province"] == "Nacional"]
    if q:
        ql = q.lower()
        items = [e for e in items if ql in e["name"].lower() or ql in e["sector"]]
    if trending is not None:
        items = [e for e in items if e["trending"] == trending]
    if sort == "score":
        items.sort(key=lambda x: -x["score"])
    elif sort == "votes":
        items.sort(key=lambda x: -x["votes"])
    elif sort == "sentiment":
        items.sort(key=lambda x: -x["sentiment_pct"])
    elif sort == "name":
        items.sort(key=lambda x: x["name"])
    total = len(items)
    return {"total": total, "items": items[offset:offset+limit]}

@app.get("/api/entities/{entity_id}")
def get_entity(entity_id: str):
    e = next((e for e in ENTITIES if e["id"] == entity_id), None)
    if not e:
        raise HTTPException(404, "Entity not found")
    enriched = enrich(e)
    enriched["reviews"] = [r for r in reviews_db if r["entity_id"] == entity_id][-10:]
    return enriched

@app.get("/api/stats")
def get_stats():
    items = [enrich(e) for e in ENTITIES]
    avg = sum(e["score"] for e in items) / len(items)
    total_votes = sum(e["votes"] for e in items)
    top = max(items, key=lambda x: x["score"])
    worst = min(items, key=lambda x: x["score"])
    trending = [e for e in items if e["trending"]]
    sector_stats = {}
    for s_key, s_meta in SECTORS.items():
        s_items = [e for e in items if e["sector"] == s_key]
        if s_items:
            sector_stats[s_key] = {
                "label": s_meta["label"],
                "color": s_meta["color"],
                "count": len(s_items),
                "avg_score": round(sum(e["score"] for e in s_items) / len(s_items), 1),
            }
    return {
        "total_entities": len(items),
        "avg_score": round(avg, 2),
        "total_votes": total_votes,
        "top_entity": {"name": top["name"], "score": top["score"]},
        "worst_entity": {"name": worst["name"], "score": worst["score"]},
        "trending_count": len(trending),
        "sector_stats": sector_stats,
    }

@app.post("/api/reviews")
def post_review(r: ReviewCreate):
    e = next((e for e in ENTITIES if e["id"] == r.entity_id), None)
    if not e:
        raise HTTPException(404, "Entity not found")
    review = {
        "id": str(uuid.uuid4())[:8],
        "entity_id": r.entity_id,
        "author": r.author,
        "score": max(1, min(10, r.score)),
        "comment": r.comment,
        "categories": r.categories,
        "date": datetime.now().isoformat(),
        "helpful": 0,
    }
    reviews_db.append(review)
    # Update entity score
    all_reviews = [rv for rv in reviews_db if rv["entity_id"] == r.entity_id]
    new_score = (e["score"] * e["votes"] + r.score) / (e["votes"] + 1)
    idx = next(i for i, x in enumerate(ENTITIES) if x["id"] == r.entity_id)
    ENTITIES[idx]["score"] = round(new_score, 1)
    ENTITIES[idx]["votes"] += 1
    if r.score >= 6:
        ENTITIES[idx]["pos"] += 1
    else:
        ENTITIES[idx]["neg"] += 1
    return review

@app.post("/api/vote")
def vote(v: VoteRequest):
    e = next((e for e in ENTITIES if e["id"] == v.entity_id), None)
    if not e:
        raise HTTPException(404, "Entity not found")
    idx = next(i for i, x in enumerate(ENTITIES) if x["id"] == v.entity_id)
    if v.type == "up":
        ENTITIES[idx]["pos"] += 1
    else:
        ENTITIES[idx]["neg"] += 1
    ENTITIES[idx]["votes"] += 1
    return {"ok": True}

@app.get("/api/provinces")
def get_provinces():
    provinces = list(set(e["province"] for e in ENTITIES))
    provinces.sort()
    return provinces

@app.get("/health")
def health():
    return {"status": "ok"}
