from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import numpy as np
import pandas as pd
from bs4 import BeautifulSoup as bs
import re
from datetime import datetime, timedelta
import time

import EDCS_Extract

url = 'https://db.edcs.eu/epigr/epi.php?s_sprache=de'
name = "p_edcs_id"


def open_database():
    """
    Starting from today, looks for the most recent version of the
    database containing all EDCS inscriptions ('EDCS_complete_Date.csv').
    Once found, opens and returns it.
    """
    edcs = None
    searching = True
    date = datetime.today()
    tries = 0
    while searching:
        date_str = date.strftime('%Y-%m-%d')
        filename = 'EDCS_complete_' + date_str + '.csv'
        try:
            edcs = pd.read_csv(filename)
            searching = False
        except FileNotFoundError:
            date = (date - timedelta(days=1))
        tries += 1
        if tries > 365:
            break
    if edcs is not None:
        return edcs


def get_sourcetext(edcs_id, driver):
    """
    Takes in a string with the EDCS-ID and the Selenium driver.
    Connects to the EDCS, finds the search field for the EDCS-ID,
    enters the ID of interest, and loads the data from the database.
    Downloads and returns he sourcetext from the result page.
    """
    driver.get(url)
    search_bar = driver.find_element(By.NAME, name)
    search_bar.clear()
    search_bar.send_keys(edcs_id)
    search_bar.send_keys(Keys.RETURN)
    sourcetext = driver.page_source
    return sourcetext


def minimise(sourcetext):
    """
    Takes in the sourcetext of the database entry for one EDCS-ID.
    Removes unnecessary fields and HTML.
    Returns reduced sourcetext.
    """
    textlist = sourcetext.split('\n')
    textlist.reverse()
    newtext = ''
    for line in textlist:
        newtext += line + '\n'
    text = re.sub(r'<hr.*', '', newtext, flags=re.DOTALL).strip()
    textlist2 = text.split('\n')
    textlist2.reverse()
    finaltext = ''
    for line in textlist2:
        finaltext += line + '\n'
    return finaltext


def get_list(sourcetext):
    """
    Takes in minimised sourcetext of database entry for one EDCS-ID.
    Using BeautifulSoup, the text is parsed and each content element
    which is not empty is written into a list.
    Returns the list.
    """
    soup = bs(sourcetext, 'html.parser')
    content = soup.find_all(text=True)
    inscriptions = []
    for element in content:
        if not element == '\n' and not element == ' ':
            nelement = element.replace("\xa0", "")
            if nelement != '':
                inscriptions.append(nelement)
    return inscriptions


def get_dict(insc, ident):
    """
    Takes in a list containing the inscription and a string with the EDCS-ID.
    Loops over list, searching for all known elements, and if found,
    enters them in a dictionary.
    Checks whether the found EDCS-ID matches the original one, and if yes,
    returns the dictionary containing the inscription,
    else it is flagged as an error and returned.
    """
    edcs_id = -1
    publication = "n/a"
    time_from = np.nan
    time_to = np.nan
    findspot = "n/a"
    find_lat = np.nan
    find_long = np.nan
    province = "n/a"
    text = "n/a"
    cleantext = "n/a"
    keywords = "n/a"
    material = "n/a"
    place = "n/a"
    dump = insc
    date_idx = -1
    edcs_idx = -1
    comment = False
    text_unknown = True

    if 'Kommentar' in insc:
        comment = True
    for idx, elem in enumerate(insc):
        if elem == "Publikation:":
            publication = insc[idx + 1].strip()
        elif elem == "Datierung:":
            date_idx = idx + 1
        elif elem == "EDCS-ID:":
            edcs_id = insc[idx + 1].strip()
            edcs_idx = idx
        elif elem == "Provinz:":
            province = insc[idx + 1].strip()
        elif elem == "Ort:" and insc[idx + 1].strip() != '?':
            place = insc[idx + 1].strip()
        elif elem == "Inschriftengattung / Personenstatus:":
            keywords = ", ".join(insc[idx + 1].strip().split(';'))
        elif elem == "Material:":
            material = ", ".join(insc[idx + 1].strip().split(';'))
        elif text_unknown and elem[0] == '\n' and "javascript" not in elem:
            text = insc[idx].strip()
            text_unknown = False

    if 0 < date_idx < edcs_idx - 1:
        dates = []
        for i in range(date_idx, edcs_idx):
            try:
                date = insc[i].strip().replace(";", "")
                date = date.replace(":", "")
                dates.append(int(date))
            except ValueError:
                pass
        if dates:
            time_from = min(dates)
            time_to = max(dates)
    if '<!--' in place:
        find_lat = EDCS_Extract.get_lat(place)
        find_long = EDCS_Extract.get_long(place)
        findspot = EDCS_Extract.get_findspot(place)
        province = EDCS_Extract.get_province(place)
    else:
        findspot = place.strip()

    if text != "n/a":
        cleantext = EDCS_Extract.get_cleantext(text)

    if edcs_id != ident:  # check if correct inscription was scraped
        publication = "error"

    inscription = {
        "publication": publication,
        "edcs-id": edcs_id,
        "time_from": time_from,
        "time_to": time_to,
        "province": province,
        "findspot": findspot,
        "find_lat": find_lat,
        "find_long": find_long,
        "text": text,
        "cleantext": cleantext,
        "keywords": keywords,
        "material": material,
        "dump": dump,
    }
    return inscription


def scrape_edcs(edcs_id, driver):
    """
    Takes in a string containing the EDCS-ID and the Selenium driver.
    Gets the sourcetext from the EDCS for the relevant entry,
    cleans it, converts it to a list and then to a dictionary,
    and then returns it.
    """
    sourcetext = get_sourcetext(edcs_id, driver)
    finaltext = minimise(sourcetext)
    insc_list = get_list(finaltext)
    inscription = get_dict(insc_list, edcs_id)
    return inscription


def replace_errors(edcs):
    """
    Takes in the database containing known errors.
    Starts a Selenium WebDriver in the background.
    Loops over the database, looking for all known errors;
    when one is found, its index and EDCS-ID is added to a list.
    For each such tuple, the EDCS is scraped to obtain correct data.
    The correct data is then written over the erroneous one.
    As this takes quite some time, a counter is printed to the console.
    Finally, the first column is renamed, and the corrected database returned.
    """
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()),
                              options=chrome_options)
    corrected = 0
    errors = []

    for i in range(len(edcs)):
        if edcs['publication'].iloc[i] == 'error' or \
                edcs['province'].iloc[i] == 'error' or \
                edcs['findspot'].iloc[i] == 'error' or \
                (edcs['findspot'].iloc[i] == "n/a" and
                 edcs['province'].iloc[i] != "n/a"):
            edcs_id = edcs['edcs-id'].iloc[i]
            temp = (i, edcs_id)
            errors.append(temp)

    total = len(errors)
    for elem in errors:
        idx = elem[0]
        edcs_id = elem[1]
        print(f"Starting {edcs_id}...")
        correct_data = scrape_edcs(edcs_id, driver)
        edcs.iloc[idx] = correct_data
        edcs.at[idx, 'Unnamed: 0'] = idx
        corrected += 1
        print(f"Corrected {corrected} of {total} inscriptions " +
              f"(ca. {round(100 / total * corrected, 2)}%). ")
    edcs.rename(columns={'Unnamed: 0': "ID"}, inplace=True)
    return edcs


def save_database(edcs):
    """
    Takes in the corrected database.
    Saves it to the filesystem as a csv.
    """
    today = datetime.today().strftime('%Y-%m-%d')
    filename = "EDCS_corrected_" + today + ".csv"
    edcs.to_csv(filename, index=False, encoding="utf-8")


def correct_errors():
    """
    Opens the database using the open_database function.
    Hands the database to the replace_errors function,
    wherein the errors are corrected.
    Once it receives the corrected database back,
    it then saves it to the filesystem using the save_database function.
    """
    edcs = open_database()
    print("Read database.")

    edcs_corrected = replace_errors(edcs)

    print("Creating csv file...")
    save_database(edcs_corrected)
    print('Saved cleaned database.')


def main():
    """
    Main function. Calls function to correct known errors in database.
    """
    start_time = time.time()
    correct_errors()
    end_time = time.time()
    print('It took me', round((end_time - start_time) / 60, 2),
          'minutes to run the complete code')


if __name__ == '__main__':
    main()
