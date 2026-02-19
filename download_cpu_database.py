import os
from os.path import dirname, join, isfile
import requests_cache
from lxml import etree
import csv
import time
import re
import logging
logger = logging.getLogger(__name__)

#######################################

CACHE_PATH = join(dirname(__file__), "data", "cache", "download_cpu_database")
OUTPUT_PAGE_CSV_DIRECTORY = join(dirname(__file__), "data", "cache", "cpu-database", "pages")
OUTPUT_GLOBAL_CSV_PATH = join(dirname(__file__), "data", "raw", "devices", "all-cpus.csv")
ENDPOINT = "https://www.techpowerup.com/cpu-specs"
FAKE_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:132.0) Gecko/20100101 Firefox/132.0"

HTTP_HEADERS = {
    "User-Agent": FAKE_USER_AGENT,
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "X-Requested-With": "XMLHttpRequest",
}

#######################################

def main():
    """
    NB: You'll probably need to restart the script multiple time because of 429 errors,
    and/or go to techpowerup.com to solve captchas manually from time to time.
    """
    logging.basicConfig(level=logging.INFO)
    os.makedirs(OUTPUT_PAGE_CSV_DIRECTORY, exist_ok=True)
    os.makedirs(dirname(OUTPUT_GLOBAL_CSV_PATH), exist_ok=True)
    request_session = requests_cache.CachedSession(CACHE_PATH)
    request_session.hooks['response'].append(make_throttle_hook(5.0))

    with open(OUTPUT_GLOBAL_CSV_PATH, 'w', newline='', encoding="utf-8") as f:
        global_csv_writer = make_csv_writer(f)

        url = f"{ENDPOINT}/?sort=name&ajax=1"
        year_options = scrap_filter_options(url, "released", request_session)
        logger.info(f"year_options = {year_options}")

        for year, amount in year_options:
            if amount < 100:
                mfgr_options = [ (None, amount) ]
            else:
                url = f"{ENDPOINT}/?released={year}&sort=name&ajax=1"
                mfgr_options = scrap_filter_options(url, "mfgr", request_session)
                logger.info(f"year {year}: mfgr_options = {mfgr_options}")

            for mfgr, amount in mfgr_options:
                if mfgr is None or amount < 100:
                    generation_options = [ (None, amount) ]
                else:
                    url = f"{ENDPOINT}/?mfgr={mfgr}&released={year}&sort=name&ajax=1"
                    generation_options = scrap_filter_options(url, "generation", request_session)
                    logger.info(f"year {year}, mfgr {mfgr}: generation_options = {generation_options}")

                for generation, amount in generation_options:
                    assert(amount < 100)
                    page_name = f"{year}-{mfgr}-{generation}"
                    filters = {
                        "mfgr": mfgr,
                        "released": year,
                        "generation": generation,
                        "sort": "name",
                        "ajax": "1",
                    }
                    url = f"{ENDPOINT}/?" + "&".join([
                        f"{key}={value}"
                        for key, value in filters.items()
                        if value is not None
                    ])
                    scrap_page(url, page_name, request_session, global_csv_writer)

#######################################

option_re = re.compile(r"^(.*) \((\d+)\)$")
def scrap_filter_options(url, filter_name, request_session):
    """Get the list of options for a given filter"""
    logger.info(f"Scraping page '{url}'...")
    response = request_session.get(url, headers=HTTP_HEADERS)
    response.raise_for_status()
    html = etree.HTML(response.json()['filters'])
    option_nodes = html.xpath("//select[@id='" + filter_name + "']/option")
    options = []
    for node in option_nodes:
        if node.text == "All":
            continue
        m = option_re.match(node.text)
        if m is None:
            raise Exception(f"Unexpected option form: '{node.text}'")
        value = m.group(1)
        amount = int(m.group(2))
        options.append((value, amount))
    return options

#######################################

def scrap_page(url, page_name, request_session, global_csv_writer):
    logger.info(f"Scraping page '{url}'...")
    response = request_session.get(url, headers=HTTP_HEADERS)
    response.raise_for_status()
    html = etree.HTML(response.json()['list'])

    path = join(OUTPUT_PAGE_CSV_DIRECTORY, f"{page_name}.csv")
    with open(path, 'w', newline='', encoding="utf-8") as f:
        csv_writer = make_csv_writer(f)

        table_row_nodes = html.xpath("//table[@class='processors']//tr")
        for row in table_row_nodes:
            cell_nodes = row.xpath("td")
            csv_cells = []
            for i, cell in enumerate(cell_nodes):
                if cell.text is not None and cell.text.startswith("No CPUs found."):
                    break
                if i == 0:
                    link = cell.getchildren()[0]
                    csv_cells.append(link.text)
                    csv_cells.append(link.attrib["href"])
                else:
                    csv_cells.append(cell.text)
            if csv_cells:
                csv_writer.writerow(csv_cells)
                global_csv_writer.writerow(csv_cells)

#######################################

def make_csv_writer(file):
    csv_writer = csv.writer(file, delimiter=';', quotechar='"', quoting=csv.QUOTE_MINIMAL)
    csv_writer.writerow([
        "Name",
        "URL",
        "Codename",
        "Cores",
        "Clock",
        "Socket",
        "Process",
        "L3 Cache",
        "TDP",
        "Released",
    ])
    return csv_writer

#######################################

def make_throttle_hook(timeout=1.0):
    """
    Make a request hook function that adds a custom delay for non-cached requests
    From https://requests-cache.readthedocs.io/en/stable/user_guide/advanced_requests.html
    """
    def hook(response, *args, **kwargs):
        if not getattr(response, 'from_cache', False):
            time.sleep(timeout)
        return response
    return hook

#######################################

main()
