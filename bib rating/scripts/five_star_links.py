import os, re, csv, time, urllib.parse
from typing import Optional, Dict, Any, List
import requests
import bibtexparser
from dotenv import load_dotenv

# ====== CONFIG ======
BIB_PATH = "output_remove_duplicates_workingcopy.bib"
OUT_CSV  = "five_star_links.csv"
TIMEOUT  = 45
SLEEP    = 0.4      # polite delay between requests
HEADERS  = {"User-Agent": "bib-download-linker/1.0"}
# =====================

def read_bib(path: str):
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return bibtexparser.load(f)

def norm_rating(v: Optional[str]) -> Optional[str]:
    if v is None: return None
    return re.sub(r"[{} ]", "", str(v))

def is_five_star(entry: Dict[str, Any]) -> bool:
    return norm_rating(entry.get("relevance_rating")) == "5"

def clean(s: Optional[str]) -> str:
    return (s or "").replace("\n", " ").strip()

def get(e: Dict[str, Any], *keys) -> Optional[str]:
    for k in keys:
        if k in e and e[k]: return e[k]
    return None

def doi_from_entry(e: Dict[str, Any]) -> Optional[str]:
    doi = get(e, "doi", "DOI")
    if not doi: return None
    return doi.strip().lstrip("doi:").strip()

def arxiv_id_from_entry(e: Dict[str, Any]) -> Optional[str]:
    eprinttype = (get(e, "eprinttype", "archivePrefix") or "").lower()
    eprint     = (get(e, "eprint") or "").strip()
    if "arxiv" in eprinttype and eprint:
        return eprint
    # 0704.0001, 2101.01234v2, or category/9901001
    if re.fullmatch(r"(\d{4}\.\d{4,5}(v\d+)?)|([a-z\-]+/\d{7}(v\d+)?)", eprint, re.I):
        return eprint
    return None

def looks_like_pdf_url(u: str) -> bool:
    return bool(re.search(r"\.pdf($|\?)", u, re.I))

def head_or_get(url: str, accept_pdf=False) -> Optional[requests.Response]:
    # Some servers dislike HEAD; try HEAD then fall back to GET(stream)
    try:
        headers = dict(HEADERS)
        if accept_pdf:
            headers["Accept"] = "application/pdf"
        r = requests.head(url, timeout=TIMEOUT, allow_redirects=True, headers=headers)
        if r.status_code >= 200 and r.status_code < 400:
            return r
    except Exception:
        pass
    try:
        headers = dict(HEADERS)
        if accept_pdf:
            headers["Accept"] = "application/pdf"
        r = requests.get(url, timeout=TIMEOUT, allow_redirects=True, headers=headers, stream=True)
        return r
    except Exception:
        return None

def is_pdf_response(resp: requests.Response) -> bool:
    ctype = (resp.headers.get("Content-Type") or "").lower()
    return "application/pdf" in ctype or ctype.endswith("/pdf")

def try_arxiv(e: Dict[str, Any]) -> Optional[str]:
    aid = arxiv_id_from_entry(e)
    if not aid: return None
    core = aid.split("v")[0]
    return f"https://arxiv.org/pdf/{core}.pdf"

def try_direct_pdf_url(e: Dict[str, Any]) -> Optional[str]:
    u = get(e, "url", "URL")
    return u if (u and looks_like_pdf_url(u)) else None

def try_doi_pdf(doi: Optional[str]) -> Optional[str]:
    if not doi: return None
    url = f"https://doi.org/{doi}"
    resp = head_or_get(url, accept_pdf=True)
    if resp is not None and resp.status_code == 200 and is_pdf_response(resp):
        return resp.url  # final redirected PDF URL
    return None

def try_unpaywall_pdf(doi: Optional[str], email: Optional[str]) -> Optional[str]:
    if not doi or not email: return None
    try:
        r = requests.get(
            f"https://api.unpaywall.org/v2/{urllib.parse.quote(doi)}",
            params={"email": email},
            timeout=TIMEOUT,
            headers=HEADERS,
        )
        if r.status_code != 200:
            return None
        data = r.json()
        # prefer best_oa_location.url_for_pdf, else any oa location
        loc = data.get("best_oa_location") or {}
        pdf = loc.get("url_for_pdf")
        if not pdf:
            for l in data.get("oa_locations") or []:
                if l.get("url_for_pdf"):
                    pdf = l["url_for_pdf"]; break
        return pdf
    except Exception:
        return None

def best_link_for_entry(e: Dict[str, Any], unpaywall_email: Optional[str]) -> (str, str, list):
    """
    Returns (status, chosen_url, tried_urls[])
    status in:
      - "arxiv-pdf"
      - "direct-pdf"
      - "doi-pdf"
      - "unpaywall-pdf"
      - "no-pdf-found"
    """
    tried = []

    # 1) arXiv
    arxiv_url = try_arxiv(e)
    if arxiv_url:
        tried.append(arxiv_url)
        return "arxiv-pdf", arxiv_url, tried

    # 2) direct .pdf in url
    direct_pdf = try_direct_pdf_url(e)
    if direct_pdf:
        tried.append(direct_pdf)
        # optionally verify content-type (light check)
        r = head_or_get(direct_pdf)
        if r is not None and r.status_code == 200 and is_pdf_response(r):
            return "direct-pdf", direct_pdf, tried
        # even if HEAD/GET didn’t say pdf, direct .pdf might still work — keep as fallback
        return "direct-pdf", direct_pdf, tried

    # 3) DOI → ask for PDF
    doi = doi_from_entry(e)
    doi_pdf = try_doi_pdf(doi)
    if doi_pdf:
        tried.append(doi_pdf)
        return "doi-pdf", doi_pdf, tried

    # 4) Unpaywall (if email provided)
    up_pdf = try_unpaywall_pdf(doi, unpaywall_email)
    if up_pdf:
        tried.append(up_pdf)
        return "unpaywall-pdf", up_pdf, tried

    # 5) Fallback: give the landing page if present
    landing = get(e, "url", "URL") or ""
    if landing:
        tried.append(landing)
    return "no-pdf-found", landing, tried

def main():
    load_dotenv()
    unpaywall_email = os.getenv("UNPAYWALL_EMAIL")  # optional but recommended

    db = read_bib(BIB_PATH)
    five = [e for e in db.entries if is_five_star(e)]
    print(f"Found {len(five)} papers with relevance_rating=5. Resolving links...")

    os.makedirs(os.path.dirname(OUT_CSV) or ".", exist_ok=True)
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([
            "bibkey","title","year","doi","url",
            "link_status","download_url","all_tried_links","comment"
        ])
        for e in five:
            key   = e.get("ID","<no-key>")
            title = clean(e.get("title"))
            year  = clean(e.get("year"))
            doi   = doi_from_entry(e) or ""
            url   = get(e, "url", "URL") or ""
            comment = clean(e.get("comment"))

            status, chosen, tried = best_link_for_entry(e, unpaywall_email)
            w.writerow([key, title, year, doi, url, status, chosen, " | ".join(tried), comment])
            print(f"[{key}] {status}: {chosen[:110]}")
            time.sleep(SLEEP)

    print(f"\nDone. Links written to: {OUT_CSV}")

if __name__ == "__main__":
    main()
