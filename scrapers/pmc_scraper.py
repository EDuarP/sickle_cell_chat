"""
Scraper de PubMed Central vía NCBI E-utilities.

Usa la API oficial (no HTML scraping). Parsea XML JATS para extraer
título, abstract, body y año de publicación.

Rate limits NCBI:
- Sin API key: 3 req/s
- Con API key:  10 req/s
"""
import time
import logging
import datetime
from typing import List, Dict

from Bio import Entrez
from bs4 import BeautifulSoup

from config import NCBI_EMAIL, NCBI_API_KEY

log = logging.getLogger(__name__)

if not NCBI_EMAIL:
    raise RuntimeError(
        "NCBI_EMAIL no configurado en .env. NCBI exige un email real para usar Entrez."
    )

Entrez.email = NCBI_EMAIL
if NCBI_API_KEY:
    Entrez.api_key = NCBI_API_KEY
    _SLEEP = 0.11
else:
    _SLEEP = 0.35

current_year = datetime.datetime.now().year


def search_pmc(
    query: str,
    retmax: int = 30,
    mindate: str = str(current_year - 5),
    maxdate: str = str(current_year),
) -> List[str]:
    """Devuelve lista de PMCIDs ordenados por relevancia."""
    log.info(f"PMC esearch: query='{query}' rango={mindate}-{maxdate} retmax={retmax}")
    handle = Entrez.esearch(
        db="pmc",
        term=query,
        retmax=retmax,
        mindate=mindate,
        maxdate=maxdate,
        datetype="pdat",
        sort="relevance",
    )
    rec = Entrez.read(handle)
    handle.close()
    ids = rec.get("IdList", [])
    log.info(f"PMC esearch -> {len(ids)} resultados")
    return ids


def _parse_jats(xml: bytes, pmcid: str) -> Dict:
    """Parsea el XML JATS de un artículo PMC."""
    soup = BeautifulSoup(xml, "xml")
    title = soup.find("article-title")
    abstract = soup.find("abstract")
    body = soup.find("body")
    pub_date = soup.find("pub-date")
    year = ""
    if pub_date and pub_date.find("year"):
        year = pub_date.find("year").get_text(strip=True)
    return {
        "id": f"PMC{pmcid}",
        "url": f"https://pmc.ncbi.nlm.nih.gov/articles/PMC{pmcid}/",
        "title": title.get_text(" ", strip=True) if title else "",
        "abstract": abstract.get_text(" ", strip=True) if abstract else "",
        "body": body.get_text(" ", strip=True) if body else "",
        "year": year,
    }


def fetch_pmc_articles(pmcids: List[str]) -> List[Dict]:
    """Descarga JATS XML de cada artículo y devuelve dicts limpios."""
    out = []
    for i, pmcid in enumerate(pmcids, 1):
        time.sleep(_SLEEP)
        try:
            h = Entrez.efetch(db="pmc", id=pmcid, rettype="xml", retmode="text")
            xml = h.read()
            h.close()
            art = _parse_jats(xml, pmcid)
            out.append(art)
            n = len(art["body"]) + len(art["abstract"])
            log.info(f"  [{i}/{len(pmcids)}] PMC{pmcid}: OK ({n} chars)")
        except Exception as e:
            log.warning(f"  [{i}/{len(pmcids)}] PMC{pmcid}: {e}")
    return out


if __name__ == "__main__":
    # Smoke test: corre `python -m scrapers.pmc_scraper` para probar solo este módulo
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    ids = search_pmc("sickle cell anemia", retmax=3)
    arts = fetch_pmc_articles(ids)
    for a in arts:
        print(f"\n--- {a['id']} ({a['year']}) ---")
        print(f"Title: {a['title'][:120]}")
        print(f"Abstract: {a['abstract'][:200]}...")
