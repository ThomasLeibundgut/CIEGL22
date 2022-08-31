from requests_html import HTMLSession
from datetime import datetime


url = 'https://db.edcs.eu/epigr/epi_ergebnis.php'

data = {
    "p_edcs_id": "",
    "p_belegstelle": "",
    "s_sprache": "",
    "p_provinz": "",
    "p_ort": "",
    "p_lingua": "",
    "p_episuch1": "",
    "r_auswahl": "und",
    "p_episuch2": "",
    "p_dat_von": "",
    "p_dat_bis": "",
    "p_material": "",
    "p_kommentar": "",
    "p_gattung1": "",
    "p_gattung2": "",
    "r_sortierung": "Provinz",
    "cmdsubmit": "Absenden"
}

headers = {
    "Host": "db.edcs.eu",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:97.0)" +
                  "Gecko/20100101 Firefox/97.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9," +
              "image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
    "Referer": "https://db.edcs.eu/epigr/epi.php?s_sprache=de",
    "Content-Type": "application/x-www-form-urlencoded",
    "Content-Length": "216",
    "Origin": "https://db.edcs.eu",
    "DNT": "1",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "same-origin",
    "Sec-GPC": "1",
}


def main():
    today = datetime.today().strftime('%Y-%m-%d')
    session = HTMLSession()
    r = session.post(url, data=data, timeout=86400, headers=headers)
    name = "EDCS_HTML_complete" + today + ".txt"
    with open(name, 'w', encoding="utf-8") as f:
        f.write(r.text)


if __name__ == '__main__':
    main()
