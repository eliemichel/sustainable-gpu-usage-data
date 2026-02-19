import os
from os.path import dirname, join, isfile
import requests_cache
from lxml import etree
import csv
import logging
import time
import re
logger = logging.getLogger(__name__)

#######################################

CACHE_PATH = join(dirname(__file__), "data", "cache", "download_gpu_database")
OUTPUT_PAGE_CSV_DIRECTORY = join(dirname(__file__), "data", "cache", "gpu-database", "pages")
OUTPUT_GLOBAL_CSV_PATH = join(dirname(__file__), "data", "raw", "devices", "all-gpus.csv")
ENDPOINT = "https://www.techpowerup.com/gpu-specs"
FAKE_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:132.0) Gecko/20100101 Firefox/132.0"

HTTP_HEADERS = {
    "User-Agent": FAKE_USER_AGENT,
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "X-Requested-With": "XMLHttpRequest",
}

#######################################

def make_parser():
    import argparse

    parser = argparse.ArgumentParser(
        prog='download_gpu_database.py',
        description='Download GPU data from techpowerup.com',
    )

    parser.add_argument(
        '-p', '--price',
        default = False,
        action='store_true',
        help = "Will launch one extra query per GPU to also grab the launch price if available. Note: this will trigger many captchas...",
    )

    return parser

#######################################

def main(args):
    """
    NB: You'll probably need to restart the script multiple time because of 429 errors,
    and/or go to techpowerup.com to solve captchas manually from time to time.
    """
    logging.basicConfig(level=logging.INFO)
    os.makedirs(OUTPUT_PAGE_CSV_DIRECTORY, exist_ok=True)
    os.makedirs(dirname(OUTPUT_GLOBAL_CSV_PATH), exist_ok=True)
    request_session = requests_cache.CachedSession(CACHE_PATH)
    request_session.hooks['response'].append(make_throttle_hook(5.0))

    log_price = args.price

    with open(OUTPUT_GLOBAL_CSV_PATH, 'w', newline='', encoding="utf-8") as f:
        global_csv_writer = make_csv_writer(f, log_price)

        for year in year_options:
            url = f"{ENDPOINT}/?released={year}&sort=name&ajax=1"
            mfgr_options = scrap_filter_options(url, "mfgr", request_session)
            print(f"year {year}: mfgr_options = {mfgr_options}")

            for mfgr in mfgr_options:
                url = f"{ENDPOINT}/?mfgr={mfgr}&released={year}&sort=name&ajax=1"
                memsize_options = scrap_filter_options(url, "memsize", request_session)
                print(f"year {year}, mfgr {mfgr}: memsize_options = {memsize_options}")

                for memsize in memsize_options:
                    page_name = f"{year}-{mfgr}-{memsize}"
                    url = f"{ENDPOINT}/?mfgr={mfgr}&released={year}&memsize={memsize}&sort=name&ajax=1"
                    scrap_page(url, page_name, request_session, global_csv_writer, log_price)

#######################################

def scrap_filter_options(url, filter_name, request_session):
    """Get the list of options for a given filter"""
    logger.info(f"Scraping page '{url}'...")
    response = request_session.get(url, headers=HTTP_HEADERS)
    response.raise_for_status()
    html = etree.HTML(response.json()['filters'])
    option_nodes = html.xpath("//select[@id='" + filter_name + "']/option")
    options = [
        node.text.split("(")[0].strip()
        for node in option_nodes
        if node.text != "All"
    ]
    return options

#######################################

def scrap_page(url, page_name, request_session, global_csv_writer, log_price=False):
    logger.info(f"Scraping page '{url}'...")
    response = request_session.get(url, headers=HTTP_HEADERS)

    response.raise_for_status()
    html = etree.HTML(response.json()['list'])

    path = join(OUTPUT_PAGE_CSV_DIRECTORY, f"{page_name}.csv")
    with open(path, 'w', newline='', encoding="utf-8") as f:
        csv_writer = make_csv_writer(f, log_price)

        table_row_nodes = html.xpath("//table[@class='processors']//tr")
        for row in table_row_nodes:
            cell_nodes = row.xpath("td")
            csv_cells = []
            details_page_url = None
            for i, cell in enumerate(cell_nodes):
                if cell.text.startswith("No graphics cards found."):
                    break
                if i == 0:
                    link = cell.getchildren()[0]
                    csv_cells.append(link.text)
                    csv_cells.append(link.attrib["href"])
                    csv_cells.append(cell.attrib["class"][7:])
                    details_page_url = f"https://www.techpowerup.com{link.attrib['href']}"
                elif i == 1:
                    link = cell.getchildren()[0]
                    csv_cells.append(link.text)
                    csv_cells.append(link.attrib["href"])
                elif i == 7:
                    shaders, tmu, rops = cell.text.split("/", 2)
                    csv_cells.append(shaders.strip())
                    csv_cells.append(tmu.strip())
                    csv_cells.append(rops.strip())
                else:
                    csv_cells.append(cell.text)

            # Query for price if available
            if log_price and details_page_url is not None:
                price = scrap_gpu_price(details_page_url, request_session)

                if price is not None:
                    csv_cells.append(price)
                else:
                    csv_cells.append("unknown")
            
            if csv_cells:
                csv_writer.writerow(csv_cells)
                global_csv_writer.writerow(csv_cells)

def scrap_gpu_price(url, request_session):
    logger.info(f"Scraping page (GPU details) '{url}'...")
    response = request_session.get(url, headers=HTTP_HEADERS)
    response.raise_for_status()
    html = etree.HTML(response.content)

    details_row_nodes = html.xpath("//section[@class='details']//dl")

    price = None

    for row in details_row_nodes:
        title_node = row.xpath("dt")
        if re.search(r'[Pp]rice', title_node[0].text):
            price = row.xpath("dd")[0].text.replace(",", "")
            break

    return price
    


#######################################

def make_csv_writer(file, log_price=False):
    csv_writer = csv.writer(file, delimiter=';', quotechar='"', quoting=csv.QUOTE_MINIMAL)
    col_titles = [
        "Product Name",
        "Product URL",
        "Vendor",
        "GPU Chip",
        "GPU Chip URL",
        "Release",
        "Bus",
        "Memory",
        "GPU clock",
        "Memory clock",
        "Shaders",
        "TMU",
        "ROPs",
    ]

    if log_price:
       col_titles.append("Launch price")

    csv_writer.writerow(col_titles)

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

mfgr_options = [
    "NVIDIA",
    "AMD",
    "3dfx",
    "ATI",
    "Intel",
    "Matrox",
    "Sony",
    "XGI",
]

year_options = range(2024, 1986-1, -1)

memsize_options = [
    "System Shared",
    "1 MB",
    "2 MB",
    "4 MB",
    "8 MB",
    "12 MB",
    "16 MB",
    "32 KB",
    "32 MB",
    "64 MB",
    "64 KB",
    "128 MB",
    "256 KB",
    "256 MB",
    "320 MB",
    "384 MB",
    "512 MB",
    "512 KB",
    "640 MB",
    "768 MB",
    "896 MB",
    "1024 MB",
    "1280 MB",
    "1536 MB",
    "1792 MB",
    "2 GB",
    "2.5 GB",
    "3 GB",
    "3.75 GB",
    "4 GB",
    "5 GB",
    "6 GB",
    "8 GB",
    "10 GB",
    "11 GB",
    "12 GB",
    "16 GB",
    "20 GB",
    "24 GB",
    "28 GB",
    "32 GB",
    "40 GB",
    "48 GB",
    "64 GB",
    "80 GB",
    "96 GB",
    "128 GB",
    "192 GB",
    "288 GB",
]

parser = make_parser()
main(parser.parse_args())
