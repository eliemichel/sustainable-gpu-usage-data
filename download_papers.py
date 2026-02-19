import os
from os.path import dirname, join, isfile
import json
from urllib.parse import urlencode
import shutil
import logging
logger = logging.getLogger(__name__)

import requests
import requests_cache
from lxml import etree
from tqdm import tqdm

# Not using API key actually (it's just making things slower, but it is still fast enough)
"""
try:
    from secret import SEMANTIC_SCHOLAR_API_KEY
except ImportError:
    print("Error: You must copy 'secret.template.py' into 'secret.py' and fill it in with your own API key!")
    print("Once you are done with that, you may run this script again.")
    exit(1)
"""

# User agant claimed when issuing HTTP requests
FAKE_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:132.0) Gecko/20100101 Firefox/132.0"
PAPER_TITLE_SEARCH_URL = "https://api.semanticscholar.org/graph/v1/paper/search/match"

#######################################

def make_parser():
    import argparse

    parser = argparse.ArgumentParser(
        prog='download_papers.py',
        description='Download as many siggraph papers as possible, using Semantic Scholar API.',
    )

    parser.add_argument(
        '-o', '--output',
        type = str,
        default = join(dirname(__file__), "data", "raw", "papers"),
        help = "Directory where to store downloaded papers and metadata.",
    )

    parser.add_argument(
        '-c', '--cache',
        type = str,
        default = join(dirname(__file__), "data", "cache", "http-cache"),
        help = "SQLite file where to cache the response of memorized HTTP queries.",
    )

    return parser

#######################################

def main(args):
    request_session = setup(args)

    meta = load_metadata(args)
    
    collect_paper_download_urls(args, request_session, meta)

    #try_fixing_errors(args, meta)

    #log_stats_per_venue(meta)
    download_all_papers(args, meta)

    #save_metadata(args, meta)


#######################################

def setup(args):
    logging.basicConfig(level=logging.INFO)
    os.makedirs(args.output, exist_ok=True)
    request_session = requests_cache.CachedSession(args.cache)
    return request_session

#######################################

def load_metadata(args):
    meta_filepath = join(args.output, "metadata.json")
    if isfile(meta_filepath):
        with open(meta_filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    else:
        return {}

def save_metadata(args, meta):
    meta_filepath = join(args.output, "metadata.json")
    with open(meta_filepath + ".part", "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)
    shutil.move(meta_filepath + ".part", meta_filepath)

#######################################

def collect_paper_download_urls(args, request_session, meta):
    for year in range(2018,2024+1):
        ensure_papers_by_venue(request_session, meta, "SIGGRAPH", year)
        save_metadata(args, meta)

        ensure_papers_by_venue(request_session, meta, "SIGGRAPH Asia", year)
        save_metadata(args, meta)

        ensure_papers_by_venue(request_session, meta, "Eurographics", year)
        save_metadata(args, meta)

#######################################

def try_fixing_errors(args, meta):
    """Where semantic scholar failed, we try Google Scholar"""
    for venue, by_year in meta.items():
        for year, report in by_year.items():
            for paper_report in report["papers"]:
                title = paper_report["title"]
                error = paper_report["error"]
                if error is not None:
                    print(title)
                    # TODO

#######################################

def log_stats_per_venue(meta):
    for venue, by_year in meta.items():
        for year, report in by_year.items():
            found = report["found"]
            errors = report["errors"]
            total = report["total"]
            logger.info(f"{venue} {year}:")
            logger.info(f" - found: {found}/{total} ({100*found/total}%)")
            logger.info(f" - errors: {errors}/{total} ({100*errors/total}%)")

#######################################

def download_all_papers(args, meta):
    for venue, by_year in meta.items():
        for year, report in by_year.items():
            for paper_report in report["papers"]:
                try:
                    download_paper(args, paper_report)
                except Exception as err:
                    logger.error(err)

#######################################

def download_paper(args, paper_report):
    title = paper_report["title"]
    pdf_info = paper_report["pdf_info"]
    raw_data = paper_report["raw_data"]
    if pdf_info is None:
        return
    for entry in raw_data["data"]:
        if entry["openAccessPdf"] is not None:
            pdf_info = entry["openAccessPdf"]
            paper_id = entry["paperId"]
            break
    filepath = join(args.output, f"{paper_id}.pdf")
    if isfile(filepath):
        return
    logger.info(filepath)
    logger.info(title)
    logger.info(pdf_info["url"])
    # NB: We do NOT use the cached session here, PDFs are too heavy
    response = requests.get(pdf_info["url"])
    with open(filepath + ".part", "wb") as f:
        for data in tqdm(response.iter_content()):
            f.write(data)
    shutil.move(filepath + ".part", filepath)

#######################################

def ensure_papers_by_venue(request_session, meta, venue, year):
    year = str(year)
    if venue not in meta:
        meta[venue] = {}
    if year in meta[venue]:
        return meta[venue][year]
    else:
        report = fetch_papers_by_venue(request_session, venue, year)
        meta[venue][year] = report

#######################################

def fetch_papers_by_venue(request_session, venue, year):
    """
    Get index from kesen, then paper metadata from semantic scholar
    """
    logger.info(f"Fetching papers from venue '{venue}', year {year}...")
    url_end = {
        "SIGGRAPH": "sig{year}.html",
        "SIGGRAPH Asia": "siga{year}Papers.htm",
        "Eurographics": "eg{year}Papers.htm",
    }[venue].format(year=year)
    url = f"https://www.realtimerendering.com/kesen/{url_end}"
    logger.debug(f"url={url}")
    
    headers = { "User-Agent": FAKE_USER_AGENT }
    response = request_session.get(url, headers=headers)
    html = etree.HTML(response.text)
    all_title_nodes = html.xpath("//dl/dt/b")

    found = 0
    errors = 0
    total = len(all_title_nodes)
    all_paper_reports = []
    for node in all_title_nodes:
        paper_report = fetch_paper_pdf_info_by_title(request_session, node.text)

        err = paper_report["error"]
        if err is not None:
            logger.error(f"Could not find info for paper '{node.text}': {err}")
            errors += 1

        pdf_info = paper_report["pdf_info"]
        if pdf_info is not None:
            logger.info(pdf_info)
            found += 1

        all_paper_reports.append(paper_report)

    if total == 0:
        logger.warning(f"Could not extract any paper title from url '{url}'")
    else:
        logger.info(f"found: {found}/{total} ({100*found/total}%)")
        logger.info(f"errors: {errors}/{total} ({100*errors/total}%)")

    report = {
        "venue": venue,
        "year": year,
        "url": url,
        "status": response.status_code,
        "papers": all_paper_reports,
        "found": found,
        "found_percentage": 100*found/total,
        "errors_percentage": 100*errors/total,
        "errors": errors,
        "total": total,
    }
    return report

def fetch_paper_pdf_info_by_title(request_session, title):
    params = {
        "query": title,
        "fields": "title,url,venue,year,openAccessPdf",
    }

    headers = { "User-Agent": FAKE_USER_AGENT }
    url = f"{PAPER_TITLE_SEARCH_URL}?{urlencode(params)}"

    response = request_session.get(url, headers=headers)

    error = None
    pdf_info = None

    data = response.json()
    if "data" not in data:
        error = "Unexpected JSON:\n" + json.dumps(data, indent=2)
    else:
        for entry in data["data"]:
            if entry["openAccessPdf"] is not None:
                pdf_info = entry["openAccessPdf"]
                break

    report = {
        "title": title,
        "url": url,
        "status": response.status_code,
        "raw_data": data,
        "error": error,
        "pdf_info": pdf_info,
    }
    return report

#######################################

if __name__ == "__main__":
    parser = make_parser()
    main(parser.parse_args())
