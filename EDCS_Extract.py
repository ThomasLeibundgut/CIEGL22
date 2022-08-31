import numpy as np
import pandas as pd
from bs4 import BeautifulSoup as bs
import time
import csv
from datetime import datetime, timedelta
import re


def get_lat(place):
    """
    Takes in some html code with details about the findspot.
    Searches for the latitude-tag.
    From the end of it until the end of the string, it appends
    all numeric characters, full stops, and minus signs to the result.
    Once it encounters something else,
    it tries to return the result as a float, or as a string.
    """
    result = ''
    start = place.find("latitude=")
    if start == -1:
        return np.nan
    for i in range(start + 9, len(place)):
        if place[i].isnumeric() or place[i] == "." or place[i] == "-":
            result += place[i]
        else:
            try:
                return float(result)
            except ValueError:
                return result


def get_long(place):
    """
    Takes in some html code with details about the findspot.
    Searches for the longitude-tag.
    From the end of it until the end of the string, it appends
    all numeric characters, full stops, and minus signs to the result.
    Once it encounters something else,
    it tries to return the result as a float, or as a string.
    """
    result = ''
    start = place.find("longitude=")
    if start == -1:
        return np.nan
    for i in range(start + 10, len(place)):
        if place[i].isnumeric() or place[i] == "." or place[i] == "-":
            result += place[i]
        else:
            try:
                return float(result)
            except ValueError:
                return result


def get_findspot(place):
    """
    Takes in some html code with details about the findspot.
    Searches for a ">", indicating the beginning of the place name.
    From there until it finds the closing tag ("<"),
    it appends everything (i.e. the complete name of the findspot)
    to the result. Once it finds the closing tag, it returns the result.
    """
    result = ""
    start = place.find(">")
    if start == -1:
        return 'error'
    for i in range(start + 1, len(place)):
        if place[i] == "<":
            return result
        else:
            result += place[i]
    """        
        if place[i].isalnum() or place[i].isspace() or place[i] == "/" or \
                place[i] == "-":
            result += place[i]
        else:
            return result
    """


def get_province(place):
    """
    Takes in some html code with details about the findspot.
    Searches for the province-tag.
    From the end of it until the end of the string,
    it appends all alphanumeric characters,
    spaces, and forward slashes to the result.
    Once it encounters something else, it returns the result.
    """
    result = ""
    start = place.find("provinz=")
    if start == -1:
        return 'error'
    for i in range(start + 8, len(place)):
        if place[i].isalnum() or place[i].isspace() or place[i] == "/":
            result += place[i]
        else:
            return result
    return result


def missing(text, i):
    """
    Takes in an inscription text as a string and an index i.
    Checks if at this index, the code is dealing with an indication
    of missing letters (e.g. "[3]" etc.), and if so, returns True.
    In all other cases, it returns False.
    """
    if i < len(text) - 2:
        if text[i] == '[' and text[i + 1].isnumeric() and text[i + 2] == ']':
            return True
        if text[i - 1] == '[' and text[i].isnumeric and text[i + 1] == ']':
            return True
        if text[i - 2] == '[' and text[i - 1].isnumeric() and text[i] == ']':
            return True
    return False


def correct_text(text):
    """
    Takes in the text of an inscription with corrected letters as a string.
    Searches for opening square brackets and their matching closing counterparts,
    as well as all equal signs, adding them to a list each.
    For each of these pairs, the square brackets and the incorrect letter
    are removed from the text, and once all incorrect letters are removed,
    the cleaned text is returned.
    """
    corrected = ''

    opens = text.find("<")
    opening_list = []
    equals_list = []
    closing_list = []
    while opens != -1 and opens + 1 < len(text):
        equals = text.find("=", opens)
        closes = text.find(">", opens)
        opening_list.append(opens)
        equals_list.append(equals)
        closing_list.append(closes)
        opens = text.find("<", opens + 1)

    closing = 0
    for i in range(len(opening_list)):
        for j in range(closing, opening_list[i]):
            corrected += text[j]
        closing = closing_list[i] + 1
        for k in range(opening_list[i] + 1, equals_list[i]):
            corrected += text[k].lower()
    for x in range(closing, len(text)):
        corrected += text[x]
    return corrected


def remove_superficial_letters(text):
    """
    Takes in the text of an inscription with superficial letters as a string.
    Searches for opening curly braces and their matching closing counterparts,
    adding them to a list each.
    For each of these pairs, the curly braces and whatever is within them
    are removed from the text, and once all superficial letters are removed,
    the cleaned text is returned.
    """
    result = ''

    opens = text.find('{')
    opening_list = []
    closing_list = []
    while opens != -1 and opens + 1 < len(text):
        closes = text.find('}', opens)
        opening_list.append(opens)
        closing_list.append(closes)
        opens = text.find('{', opens + 1)

    closing = 0
    for i in range(len(opening_list)):
        for j in range(closing, opening_list[i]):
            result += text[j]
        closing = closing_list[i] + 1
    for k in range(closing, len(text)):
        result += text[k]
    return result


def get_cleantext(text):
    """
    Takes in the text of an inscription as a string.
    Searches for equal signs and curly braces (which indicate edits)
    and if it findes such, corrects the text and / or removes
    superficial letters.
    Then, all inscriptionese (e.g. '/', brackets, etc) is removed,
    and all spaces, characters, and missing indicators (i.e. "[3]" etc.)
    are added to the result, which is split at whitespace,
    and joined with a whitespace, and then returned.
    """
    result = ''
    equals = text.find('=')  # text contains corrected letters
    curly = text.find('{')  # text contains superficial letters
    if equals != -1:  # text contains corrected letters
        text = correct_text(text)
    if curly != -1:  # text contains superficial letters
        text = remove_superficial_letters(text)
    for i in range(len(text)):  # remove all inscriptionese (e.g. '/', brackets)
        if text[i].isspace() or text[i].isalpha() or missing(text, i):
            result += text[i]

    result = " ".join(result.split())
    return result


def clean(insc):
    """
    Takes in the html sourcetext of an inscription.
    Parses the html using beautifulsoup,
    and creates a content variable containing all text without tags.
    For each element in content, if it is not a line break, empty,
    a colon, or the EDCS-ID, the element is stripped of non-breaking spaces,
    split at whitespace, and joined with a whitespace.
    If the element now is not empty, it is appended to a result,
    and once all elements in content are cleaned, result is returned.
    """
    soup = bs(insc, 'html.parser')
    content = soup.find_all(text=True)
    result = []
    for element in content:
        if not element == '\n' and not element == ' ' and not element == ':' \
                and not element == 'EDCS-ID:':
            nelement = element.replace("\xa0", "")
            melement = " ".join(nelement.split())
            if melement != '':
                result.append(melement)
    return result


def get_list(sourcetext):
    """
    Takes in the sourcetext as raw html.
    Splits sourcetext at '<p>'-tag, as each new inscription
    is encoded as a paragraph in the EDCS.
    If element is not empty, it is cleaned using the clean-function,
    and then appended to a list of inscriptions.
    As this takes a long time, progress is printed
    to the console once every 1000 inscriptions.
    When done, returns the list with all inscriptions.
    """
    inscs = sourcetext.split('</p>')
    print("Inscriptions split")
    inscs_cleaned = []
    counter = 0
    total = 533000
    for insc in inscs[1:]:  # first line is static content
        if insc != '':
            cleaned = clean(insc)
            if cleaned:
                inscs_cleaned.append(cleaned)
        counter += 1
        if counter % 1000 == 0:
            print(f'Included in list: {counter} inscriptions ',
                  f'(ca. {round(100 / total * counter, 2)}%)')
    return inscs_cleaned


def search_province(insc):
    """
    takes in a list containing the inscription.
    Loops over the list, checking if any element appears in province_list.
    If so, returns this element. Else, returns 'n/a'.
    """
    province_list = ['Achaia', 'Baetica', 'Galatia', 'Mauretania Tingitana',
                     'Regnum Bospori', 'Aegyptus', 'Barbaricum', 'Raetia',
                     'Gallia Narbonensis', 'Mesopotamia', 'Roma', 'Asia',
                     'Aemilia / Regio VIII', 'Belgica', 'Germania inferior',
                     'Moesia inferior', 'Samnium / Regio IV', 'Armenia',
                     'Africa proconsularis', 'Britannia', 'Germania superior',
                     'Moesia superior', 'Sardinia', 'Alpes Cottiae', 'Dacia',
                     'Bruttium et Lucania / Regio III', 'Hispania citerior',
                     'Noricum', 'Sicilia', 'Alpes Graiae', 'Cappadocia',
                     'Italia', 'Numidia', 'Syria', 'Alpes Maritimae', 'Arabia',
                     'Cilicia', 'Latium et Campania / Regio I', 'Palaestina',
                     'Thracia', 'Alpes Poeninae', 'Corsica', 'Macedonia',
                     'Liguria / Regio IX', 'Pannonia inferior', 'Dalmatia',
                     'Transpadana / Regio XI', 'Apulia et Calabria / Regio II',
                     'Creta et Cyrenaica', 'Lugudunensis', 'Pannonia superior',
                     'Umbria / Regio VI', 'Aquitania', 'Aquitanica' 'Cyprus',
                     'Lusitania', 'Picenum / Regio V', 'Pontus et Bithynia',
                     'Venetia et Histria / Regio X', 'Provincia incerta',
                     'Lycia et Pamphylia', 'Etruria / Regio VII',
                     'Mauretania Caesariensis', 'Aquitani(c)a']
    for idx, elem in enumerate(insc):
        if elem in province_list:
            return elem
        elif "|" in elem:
            parts = elem.split("|")
            for part in parts:
                if part.strip() in province_list:
                    return elem
    return 'n/a'


def get_insc_dict(inscriptions):
    """
    Takes in the list of inscriptions, each as a list itself.
    For each inscription (each list element), the function:
    1: searches for the EDCS-ID.
    2: gets publication and creation date.
    3: gets findspot data if available.
    4: gets keywords and materials if available.
    5: gets inscription text and creates a cleaned text.
    Once all this elements have been extracted from the list,
    they are added to a temporary dictionary.
    This dictionary is then appended to a master-dict,
    with the key being the respective EDCS-id,
    and the value being the temporary dictionary.
    As this takes a long time, progress is printed
    to the console once every 5000 inscriptions.
    When done, returns the master-dict with all inscriptions.
    """
    all_inscriptions = {}
    keyword_list = ['carmina', 'signacula', 'Augusti/Augustae',
                    'praenomen et nomen', 'defixiones', 'signacula medicorum',
                    'liberti/libertae', 'reges', 'diplomata militaria',
                    'termini', 'milites', 'sacerdotes christiani',
                    'inscriptiones christianae', 'tesserae nummulariae',
                    'mulieres', 'sacerdotes pagani', 'leges',
                    'tituli fabricationis', 'nomen singulare', 'servi/servae',
                    'litterae erasae ', 'tituli honorarii',
                    'officium/professio', 'seviri Augustales',
                    'litterae in litura', 'tituli operum', 'ordo decurionum',
                    'tria nomina', 'miliaria', 'tituli possessionis',
                    'ordo equester', 'viri', 'senatus consulta', 'tituli sacri',
                    'ordo senatorius', 'sigilla impressa', 'tituli sepulcrales']
    material_list = ['aes', 'cyprum', 'lignum', 'os', 'sucineus', 'argentum',
                     'ferrum', 'musivum', 'plumbum', 'tectorium', 'aurum',
                     'gemma', 'opus figlinae', 'rupes', 'textum', 'corium',
                     'lapis', 'orichalcum', 'steatitis', 'vitrum']

    counter = 0
    total = 533000
    for insc in inscriptions:
        id_unknown = True
        edcs_id = np.nan
        edcs_id_i = np.nan
        publication = "n/a"
        time_from = np.nan
        time_to = np.nan
        findspot = "n/a"
        findspot_i = np.nan
        find_lat = np.nan
        find_long = np.nan
        province = "n/a"
        text = "n/a"
        text_i = np.nan
        cleantext = "n/a"
        keywords = "n/a"
        keywords_i = np.nan
        material = "n/a"
        material_i = np.nan
        place = "n/a"
        place_i = np.nan
        dump = insc
        error = False

        for i in range(len(insc)):
            # find edcs-id (only field certain to be included in every
            # EDCS-inscription)
            if id_unknown and insc[i][:5] == 'EDCS-':
                edcs_id = insc[i]
                edcs_id_i = i
                id_unknown = False
            # get place (if known)
            elif insc[i][:4] == '<!--':
                place = insc[i]
                place_i = i
            # get keywords (if available)
            elif insc[i] in keyword_list:
                keywords = insc[i]
                keywords_i = i
            # get material (if available)
            elif insc[i] in material_list:
                material = insc[i]
                material_i = i
            elif ';' in insc[i]:
                elements = insc[i].split(';')
                for elem in elements:
                    if elem in keyword_list:
                        keywords = ", ".join(elements)
                        keywords_i = i
                    elif elem in material_list:
                        material = ", ".join(elements)
                        material_i = i

        # check if EDCS-ID has been found. If not, then it's most
        # likely a comment fragment, and can be ignored.
        if pd.isnull(edcs_id):
            continue

        # getting publication, date_from and date_to
        if edcs_id_i == 1:
            # id is second element, i.e. there is only publication but no dates
            publication = insc[0]
        # id is fourth element, i.e. there is publication, date_from, & date_to
        elif edcs_id_i == 3:
            publication = insc[0]
            # try to make an integer of time_from and time_to
            try:
                time_from = int(" ".join(insc[1].split()))
            except ValueError:
                error = True
            try:
                time_to = int(" ".join(insc[2].split()))
            except ValueError:
                error = True
        # id is sixth element or more, i.e. there is publication
        # but multiple time_from and time_to.
        elif edcs_id_i >= 5 and edcs_id_i % 2 == 1:
            publication = insc[0]
            nums = []
            for j in range(1, edcs_id_i):  # get all elements with numbers
                elem = insc[j].strip()
                for letter in elem:
                    if letter.isnumeric():
                        nums.append(elem)
            nums = list(dict.fromkeys(nums))  # remove duplicates
            dates = []
            for number in nums:
                try:
                    dates.append(int(number))
                except ValueError:
                    try:
                        numbers = re.split(r'[,;:]', number)
                        for n in numbers:
                            try:
                                dates.append(int(n))
                            except ValueError:
                                error = True
                                break
                    except TypeError:
                        error = True
                        break
            if error:
                publication = 'error'
            else:
                date_from = min(dates)
                date_to = max(dates)
        else:
            publication = 'error'  # if code gets to here,
            # inscription is highly irregular, additional check required

        # get text & cleantext
        if np.isfinite(keywords_i):
            text_i = int(keywords_i - 1)
            text = insc[text_i]
        else:
            if np.isfinite(material_i):
                text_i = int(material_i - 1)
                text = insc[text_i]
            else:
                if np.isfinite(place_i):
                    text_i = int(place_i + 2)
                    text = insc[text_i]
                else:  # might get comment, but very low chance
                    text_i = - 1
                    text = insc[text_i]
        if text != "n/a":
            cleantext = get_cleantext(text)

        # get findspot (incl. province and GPS-coordinates), if known.
        if '<!--' in place:
            findspot = get_findspot(place)
            find_lat = get_lat(place)
            find_long = get_long(place)
            province = get_province(place)
        else:
            province = search_province(insc)
            if np.isfinite(text_i) and len(insc) > 1:
                findspot_i = int(text_i - 1)
                findspot = insc[findspot_i]

            # double check if findspot is not something else
            for idx, elem in enumerate(insc):
                if elem == findspot:
                    if idx != findspot_i:
                        findspot = "n/a"
        # designate all unknown findspots as "n/a"
        if findspot == "?" or findspot == "":
            findspot = "n/a"

        # check if the EDCS-ID is only a reference in a comment
        if place == "n/a" and keywords == "n/a" and material == "n/a" and \
                findspot == "n/a" and province == "n/a" and \
                np.isnan(time_from) and np.isnan(time_to):
            continue

        # create dictionary for inscription
        inscription_data = {
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
        # add each inscription-dictionary to dictionary of all inscriptions,
        # with key == edcs_id
        all_inscriptions[counter] = inscription_data
        counter += 1
        if counter % 5000 == 0:
            print(f'Added to dictionary: {counter} inscriptions (ca. ',
                  f'{round(100 / total * counter, 2)}%)')
    return all_inscriptions


def create_csv(inscription_dict, today):
    """
    Takes in the dictionary of inscriptions.
    Saves it to a csv.
    """
    name = "EDCS_complete_" + today.strftime('%Y-%m-%d') + ".csv"
    output = pd.DataFrame(inscription_dict)
    output = output.transpose()
    output.to_csv(name)


def save_list(inscriptions, today):
    """
    Takes in the list of inscriptions.
    Saves it as a csv.
    """
    name = "output_" + today.strftime('%Y-%m-%d') + ".csv"
    with open(name, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows(inscriptions)


def open_list(date):
    searching = True
    while searching:
        date_str = date.strftime('%Y-%m-%d')
        filename = 'output_' + date_str + '.csv'
        try:
            with open(filename, newline="", encoding='utf-8') as f:
                reader = csv.reader(f)
                insc_list = list(reader)
                searching = False
        except FileNotFoundError:
            date = (date - timedelta(days=1))
    print(f"Read list; filename: {filename}.")
    return insc_list


def open_sourcecode(date):
    """
    Starting from today, looks for the most recent version of the
    EDCS sourcecode ('EDCS_HTML_complete_DATE.txt').
    Once found, opens and returns it.
    """
    searching = True
    while searching:
        date_str = date.strftime('%Y-%m-%d')
        filename = 'EDCS_HTML_complete_' + date_str + '.txt'
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                sourcecode = f.read()
            searching = False
        except FileNotFoundError:
            date = (date - timedelta(days=1))
    print(f"Read sourcecode; filename: {filename}.")
    return sourcecode


def extract():
    """
    Starts the extraction process.
    Opens the txt file where the EDCS database is saved to.
    Transforms the raw sourcecode into a list of incriptions,
    then saves this list to a csv.
    Transforms the created list to a dictionary of all inscriptions,
    and then saves this dict both as a csv and xlsx.
    """
    today = datetime.today()

    sourcecode = open_sourcecode(today)

    # transform sourcetext to a list of all inscriptions (each as a list itself)
    inscriptions = get_list(sourcecode)
    print(f'Got List; {len(inscriptions)} items.')

    # save inscription list to a csv
    save_list(inscriptions, today)
    print("Saved list.")

    # inscriptions = open_list(today)

    # transforms list of all inscriptions to a dictionary of inscriptions
    inscription_dict = get_insc_dict(inscriptions)
    print('Dictionary completed')

    print("Creating csv file...")
    create_csv(inscription_dict, today)
    print('CSV created.')


def main():
    """
    The main function.
    Sets a timer, the extracts all data from the downloaded EDCS database.
    Once it is done, sets a second timer and prints how long the process took.
    """
    start_time = time.time()
    extract()
    print('Finished')
    end_time = time.time()
    print('It took me', round((end_time - start_time) / 60, 2),
          'minutes to run the complete code')


if __name__ == '__main__':
    main()
