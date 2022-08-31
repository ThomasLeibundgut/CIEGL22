import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import requests
import urllib3


def open_edcs(date):
    """
    Takes in a date object with today's date.
    Starting from today, looks for the most recent version of the
    EDCS database file ('EDCS_corrected_DATE.csv').
    Once found, opens and returns it.
    """
    filename = None
    edcs = None
    searching = True
    while searching:
        date_str = date.strftime('%Y-%m-%d')
        filename = 'EDCS_corrected_' + date_str + '.csv'
        try:
            edcs = pd.read_csv(filename)
            searching = False
        except FileNotFoundError:
            date = (date - timedelta(days=1))
    print(f"Read EDCS database; filename: {filename}.")
    if edcs is None:
        print("Some Error has occurred. Terminating programme...")
        quit()
    return edcs


def open_pleiades_names():
    """
    Opens the pleiades names database. Removes superfluous columns.
    Returns database as a pandas dataframe.
    """
    names = pd.read_csv('pleiades-names.csv')
    # names.drop(['authors', 'bbox', 'created', 'creators', 'currentVersion',
    #              'extent', 'modified', 'tags', 'timePeriodsKeys',
    #              'timePeriodsRange', 'uid'], axis=1, inplace=True)
    print("Read Pleiades names file.")
    return names


def save_database(database, today, name_tag, idx):
    """
    Takes in a pandas dataframe, today's date, a name_tag, and a bool (idx).
    Saves it using the name-tag and date as a csv, with or without index.
    """
    filename = name_tag + "_" + today.strftime('%Y-%m-%d') + ".csv"
    database.to_csv(filename, index=idx, encoding="utf-8")
    print(f"Saved {name_tag} database to csv.")


def get_name_set():
    """
    Opens the Prosopographia Imperii Romani database.
    Creates a name_list with the most common abbreviated names.
    Each name in the PIR database is cleaned up and added to the name_list.
    Returns name_list.
    """
    # https://github.com/telota/PIR/blob/public/data/pir_export_2021-05-07.csv
    pir = pd.read_csv('pir_export_2021-05-07.csv')
    name_set = {"Aulus", "Appius", "Gaius", "Gnaeus", "Decimus", "Lucius",
                "Marcus", "Manius", "Publius", "Quintus", "Sergius", "Sextus",
                "Spurius", "Titus", "Tiberius", "Aelia", "Aelius", "Aurelia",
                "Aurelius", "Claudia", "Claudius", "Flavia", "Flavius",
                "Iulia", "Iulius", "Valeria", "Valerius", "Caius", "Cnaeus"}
    for idx, name in enumerate(pir['annotated']):
        name = no_tags(name)
        no_words = {"...", "..", "(", ")", "[", "]", "-", "?"}
        for elem in no_words:
            name = name.replace(elem, "")
        name = name.replace("vel", " ")
        parts = name.split()
        for part in parts:
            if part[-1] != "." and part[0].isupper() and len(part) > 3:
                name_set.add(part)
    return name_set


def get_name(row, name_set):
    """
    Takes in a series (=row) of a pandas dataframe containing one inscription
    and the list of all names in the PIR.
    For each word in the cleantext which is sufficiently long, starts with a
    capital letter, and is not in the non_names list, the word is converted
    to its nominative case, and then looked up in the word list.
    Each match is attached to a string, which is finally returned.
    """
    names = ""
    words = row['cleantext']
    if isinstance(words, str):
        words = row['cleantext'].split()
        non_names = ["Dis", "Manibus"]
        for word in words:
            try:
                word.encode('ascii')
            except UnicodeEncodeError:  # contains Greek / non-Latin letters
                continue
            if len(word) > 2 and word[0].isupper() and word[1].islower() and \
                    word not in non_names:
                if word[-2:] == "ae":
                    word = word[:-1]
                elif word[-1] == "i" or word[-1] == "o":
                    word = word[:-1] + "us"
            if word in name_set:
                names += word + ", "
        if "," in names:
            names = names[:-2]
    return names


def get_gender(row):
    """
    Takes in a series (=row) of a pandas dataframe containing one inscription.
    If it has been determined that the inscription is no funerary one
    and does not contain a name, returns np.nan.
    Else, it loops over all names, looking if they are most likely male ("-us")
    or female ("-a"), and if the ratio between male and female names is
    sufficiently clear, returns probable gender (0=male, 1=female, 2=unclear).
    """
    if row['contains_name'] == 0 and row['funerary'] == 0:
        return np.nan
    male = 0
    female = 0
    male_names = {"Agrippa", "Aquila", "Caracalla", "Nerva", "Scaevola",
                  "Seneca"}
    male_suffix = {"us", "os", "er"}
    names = row['name'].split()
    for name in names:
        name = name.replace(",", "").strip()
        if name[-2:] in male_suffix or name in male_names or \
                (name[-2] == "is" and name[-5] != "ensis"):
            male += 1
        elif (name[-1] == "a" or name[-2:] == "oe") and name not in male_names:
            female += 1
    if male > 0 and female == 0:
        return 0
    elif male == 0 and female > 0:
        return 1
    elif male == 0 and female == 0:
        return np.nan
    else:
        if male / female >= 2:
            return 0
        elif female / male >= 2:
            return 0
        else:
            return 2


def add_metadata(edcs):
    """
    Takes in a pandas dataframe containing the EDCS database.
    Adds columns for the length of the text, whether or not an inscription is
    in all likelihood a funerary one, whether it contains a possible and
    a probable migrant, whether it contains a name, and if so, if that name
    is most likely male or female.
    Returns the thus altered dataframe.
    """
    edcs['text_length'] = edcs['cleantext'].str.len()

    text = edcs['cleantext'].str.lower()
    exp = 'faciend(?:[a-z]+) curav(?:[a-z]+)|dis manibus|sit(?:[a-z]+) est|' \
        'bene merenti|vixit|ex testamento|sit tibi terra levis|requiesc[a-z]t'
    edcs['funerary'] = np.where(text.str.contains(exp, regex=True) |
                                edcs['keywords'].str.contains("sepulcrales"),
                                1, 0)

    locs = r'(?:[A-Za-z]+)ensis|domo|origo'
    edcs['possible_migrant'] = np.where(text.str.contains(locs, regex=True),
                                        1, 0)

    edcs['probable_migrant'] = np.where((edcs['possible_migrant'] == 1) &
                                        (edcs["funerary"] == 1), 1, 0)

    edcs['migrant'] = 0

    name_set = get_name_set()
    edcs['name'] = edcs.apply(lambda row: get_name(row, name_set), axis=1)
    edcs['contains_name'] = np.where(edcs['name'].str.len() > 2, 1, 0)

    edcs['gender_main_pers'] = edcs.apply(lambda row: get_gender(row),
                                          axis=1)
    print("Added metadata to the EDCS database.")
    return edcs


def add_coordinates(names):
    """
    Takes in a pandas dataframe containing the Pleiades names database.
    Iterates over all rows, checking if row contains coordinates.
    If not, connects to the Pleiades API, downloads and adds them.
    Because there are some errors in the JSON files, the whole is wrapped
    in a try-except block and prints the index of all rows causing errors.
    Returns the thus modified dataframe.
    """
    # improved gps coordinate availability by some 16%.
    base_url = "https://pleiades.stoa.org"
    fixed = 0
    for idx, elem in names.iterrows():
        if idx != 0 and idx % 100 == 0:
            print(f"Checked {idx} entries in database",
                  f"(ca. {round(100 / len(names) * idx, 2)}%).",
                  f"Fixed {fixed} entries so far.")
        if isinstance(elem['reprLatLong'], float):
            try:
                url = base_url + elem['pid'] + "/json"
                response = requests.get(url)
                data = response.json()
                if 'reprPoint' in data.keys() and data['reprPoint']:
                    long = data['reprPoint'][0]
                    lat = data['reprPoint'][1]
                    names.at[idx, 'reprLat'] = lat
                    names.at[idx, 'reprLong'] = long
                    names.at[idx, 'reprLatLong'] = str(lat) + "," + str(long)
                elif 'features' in data.keys() and data['features'] and \
                        'geometry' in data['features'][0].keys() and \
                        data['features'][0]['geometry'] is not None and \
                        'type' in data['features'][0]['geometry'].keys() and \
                        data['features'][0]['geometry']['type'] == 'Point':
                    coordinates = data['features'][0]['geometry']['coordinates']
                    long = coordinates[0]
                    lat = coordinates[1]
                    names.at[idx, 'reprLat'] = lat
                    names.at[idx, 'reprLong'] = long
                    names.at[idx, 'reprLatLong'] = str(lat) + "," + str(long)
                    fixed += 1
                else:
                    continue
            except (TypeError, ValueError,
                    requests.exceptions.ChunkedEncodingError,
                    urllib3.exceptions.ProtocolError,
                    urllib3.exceptions.InvalidChunkLength):
                print(idx, elem['pid'])
    print("Added missing coordinates to Pleiades database.")
    return names


def copy_coordinates(names):
    """
    Takes in a pandas dataframe containing the Pleiades names database.
    Sorts it by PID, and iterates over it.
    Whenever an empty LatLong-field is found, searches rows above and below
    until a new PID is found.
    Until then, checks if row above or below has GPS information, and if so,
    copies it to the current row and moves to next row.
    Once a new PID is found, moves on to next row.
    Returns modified names database.
    """
    names.sort_values(by='pid', inplace=True)
    idx = pd.Index(range(0, len(names), 1))
    names = names.set_index(idx)
    fixed = 0
    for idx, elem in names.iterrows():
        if isinstance(elem['reprLatLong'], float):
            searching = True
            i = 1
            while searching and elem['pid'] == names['pid'].iloc[idx - i]:
                if isinstance(names['reprLatLong'].iloc[idx - i], str):
                    lat = names['reprLat'].iloc[idx - i]
                    long = names['reprLong'].iloc[idx - i]
                    latlong = names['reprLatLong'].iloc[idx - i]
                    names.at[idx, 'reprLat'] = lat
                    names.at[idx, 'reprLong'] = long
                    names.at[idx, 'reprLatLong'] = latlong
                    fixed += 1
                    searching = False
                else:
                    i += 1
            j = 1
            while searching and elem['pid'] == names['pid'].iloc[idx + j]:
                if isinstance(names['reprLatLong'].iloc[idx + j], str):
                    lat = names['reprLat'].iloc[idx + j]
                    long = names['reprLong'].iloc[idx + j]
                    latlong = names['reprLatLong'].iloc[idx + j]
                    names.at[idx, 'reprLat'] = lat
                    names.at[idx, 'reprLong'] = long
                    names.at[idx, 'reprLatLong'] = latlong
                    fixed += 1
                    searching = False
                else:
                    j += 1
    print(f"Copied {fixed} empty coordinates in Pleiades database.")
    return names


def no_brackets(elem):
    """
    Takes in a string.
    Searches for opening or closing parentheses. If none found, returns string.
    If found, checks if it is an omission ("(...)"), and if so, removes it;
    checks if it is an entire word, and if so, removes it;
    if it is neither (i.e. a spelling variant), creates both readings.
    Repeats until no more parentheses are found.
    Returns string without all elements in parentheses.
    """
    opening = elem.find("(")
    variants = False
    while opening != -1:
        closing = elem.find(")", opening)
        remove = elem[opening:closing + 1]
        if remove == "(...)":
            elem = elem.replace(remove, "")
        elif opening > 0 and elem[opening - 1].isspace():
            remove = elem[opening:closing + 1]
            elem = elem.replace(remove, "")
        else:
            variants = True
        opening = elem.find("(", opening + 1)
    elem = elem.replace("  ", " ").replace(" ,", ",")

    if variants:
        result = []
        words = elem.split(" ")
        for word in words:
            opening = word.find("(")
            if opening == -1:
                result.append(word)
            while opening != -1:
                closing = word.find(")", opening)
                variant = word[opening:closing + 1]
                word_without = word.replace(variant, "")
                result.append(word_without)
                word_with = word.replace("(", "").replace(")", "")
                result.append(word_with)

                opening = word.find("(", opening + 1)
        elem = " ".join(result)

    return elem


def no_tags(elem):
    """
    Takes in a string.
    Searches for opening angle bracket ("<"). If none is found, returns string.
    If brackets are found, searches for corresponding closing bracket,
    removes everything in between (=tag), and starts again.
    Returns string without tags.
    """
    opening = elem.find("<")
    while opening != -1:
        closing = elem.find(">")
        remove = elem[opening:closing + 1]
        elem = elem.replace(remove, "")
        opening = elem.find("<")
    return elem


def get_place_names(names):
    """
    Takes in the a pandas dataframe with the Pleiades names database.
    Creates a new column 'placenames'.
    For each location, removes html-tags, comments in brackets,
    checks for variants, and adds all variants 'placenames' column.
    Returns dataframe.
    """
    names['placenames'] = None
    ancient = "HRL"
    for idx, elem in enumerate(names['nameTransliterated']):
        relevant = False
        time_period = names['timePeriods'].iloc[idx]
        try:
            for letter in time_period:
                if letter in ancient:
                    relevant = True
                    break
        except TypeError:
            relevant = True
        if not relevant:
            continue
        place_names = set()
        elem = no_tags(elem)
        elem = elem.replace("?", "")
        elem = no_brackets(elem)
        comma = elem.find(",")
        if comma == -1:
            place_names.add(elem.replace("  ", " ").strip())
        else:
            locs = elem.split(",")
            for loc in locs:
                slash = loc.find("/")
                if slash == -1:
                    place_names.add(loc.replace("  ", " ").strip())
                else:
                    loks = loc.split("/")
                    for lok in loks:
                        place_names.add(lok.replace("  ", " ").strip())
        places = ", ".join(place_names)
        names.at[idx, 'placenames'] = places
    print("Added column with placenames to Pleiades database.")
    return names


def get_toponyms(place_names):
    """
    Takes in a pandas dataframe containing the modified Pleiades names database.
    Adds a column for toponyms.
    Loops over the 'placenames' column, and if there is a placename,
    splits it at spaces. Loops backward over each such word until first vowel,
    and from there replaces the rest of the word with "ensis";
    copies the thus created toponym to a list, and if there are other vowels,
    goes back one letter to create toponyms until a consonant is reached.
    Joins toponym list to a string, and writes it to toponym column.
    Once all placenames are converted, returns modified dataframe.
    """
    vowels = "aeiou"
    place_names['toponyms'] = None
    for idx, elem in enumerate(place_names['placenames']):
        if elem is not None:
            toponym_list = []
            locations = elem.split()
            for location in locations:
                for index, letter in enumerate(reversed(location)):
                    if letter in vowels:
                        i = len(location) - index - 1
                        if i <= 2:
                            break
                        else:
                            toponym_list.append(location[:i] + "ensis")
                            while location[i - 1] in vowels:
                                toponym_list.append(location[:i - 1] + "ensis")
                                i -= 1
                            break
            toponyms = ", ".join(toponym_list)
            place_names.at[idx, 'toponyms'] = toponyms
    print("Added toponyms to Pleiades database.")
    return place_names


def search_toponyms(edcs, toponyms):
    """
    Takes in two dataframes: the EDCS and the modified Pleiades database.
    Creates a dataframe for migrants with same columns as EDCS.
    Loops over toponyms, and for each toponym, loops over the EDCS, searching
    if there is a match within the inscription text.
    If match is found, the respective line from the EDCS is copied to the
    migrants database, and toponym, GPS coordinates, and Pleiades ID is added.
    Once all toponyms have been searched for in all inscriptions,
    returns migrants database.
    """
    column_names = edcs.columns.values.tolist()
    migrants = pd.DataFrame(columns=column_names)
    row = 0
    found = 0
    length = len(toponyms)
    for idx, tops in enumerate(toponyms['toponyms']):
        if idx > 0 and idx % 10 == 0:
            print(f"Searched {idx} toponyms " +
                  f"(ca. {round(100 / length * idx, 2)}%). " +
                  f"Found {found} migrants so far.")
        if not isinstance(tops, str) or len(tops) < 6:
            continue
        tops = [top.strip() for top in tops.split(",")]
        for top in tops:
            for i, text in enumerate(edcs['cleantext']):
                if not isinstance(text, str):
                    continue
                if top in text:
                    migrants = pd.concat([migrants,
                                          pd.DataFrame(edcs.iloc[i]).T],
                                         ignore_index=True)
                    migrants.at[row, 'origo'] = toponyms['title'].iloc[idx]
                    migrants.at[row, 'origo_lat'] = \
                        toponyms['reprLat'].iloc[idx]
                    migrants.at[row, 'origo_long'] = \
                        toponyms['reprLong'].iloc[idx]
                    migrants.at[row, 'origo_LatLong'] = \
                        toponyms['reprLatLong'].iloc[idx]
                    migrants.at[row, 'path'] = toponyms['path'].iloc[idx]
                    migrants.at[row, 'pid'] = toponyms['pid'].iloc[idx]
                    migrants.at[row, 'migrant'] = 1
                    row += 1
                    found += 1
    migrants.index.name = "Index"
    migrants.drop_duplicates(subset=['edcs-id', 'origo_LatLong'], inplace=True)
    print("Searched all toponyms; " +
          f"migrants database created containing {len(migrants)} entries.")
    return migrants


def create_complete_db(edcs, migrants):
    """
    Takes in two pandas dataframes containing the migrants and EDCS databases.
    Creates a deep copy of the migrants database: the new master database.
    Loops over the EDCS database. Each entry whose EDCS-ID is not already
    in the master database is added to it.
    Drops the index, sorts by EDCS-ID and returns master database.
    """
    master = migrants.copy()
    length_edcs = len(edcs.index)
    counter = 0
    for index, insc in edcs.iterrows():
        counter += 1
        print(counter)
        if insc['edcs-id'] not in master['edcs-id'].unique():
            master.at[len(master.index)] = insc
            if counter % 1000 == 0:
                print(f"Added {counter} inscriptions " +
                      f"(ca. {round(100 / length_edcs * counter, 2)}%).")

    master.drop('Index', axis=1, inplace=True)
    master.sort_values(by='edcs-id', inplace=True)
    print("Finished EDCS master database.")
    return master


def find_migrants():
    """
    Organising function.
    Opens EDCS database, adds metadata to it, and saves it.
    Opens Pleiades database, adds missing coordinates, place names, & toponyms;
    saves it.
    Searches for all toponyms in all EDCS inscriptions.
    Saves database containing all possible migrants from the EDCS.
    Takes migrants database and adds all inscriptions not already therein;
    saves master database.
    """
    today = datetime.today()

    edcs = open_edcs(today)
    edcs_metadata = add_metadata(edcs)
    save_database(edcs_metadata, today, "EDCS_metadata", False)

    pleiades = open_pleiades_names()
    pleiades_coord = add_coordinates(pleiades)
    pleiades_coord_new = copy_coordinates(pleiades_coord)
    save_database(pleiades_coord_new, today, "Pleiades_coordinates", True)

    pleiades_places = get_place_names(pleiades_coord_new)
    pleiades_toponyms = get_toponyms(pleiades_places)
    save_database(pleiades_toponyms, today, "Pleiades_toponyms", False)

    migrants = search_toponyms(edcs, pleiades_toponyms)
    save_database(migrants, today, "EDCS_Migrants", True)

    edcs_master = create_complete_db(edcs_metadata, migrants)
    save_database(edcs_master, today, "EDCS_Master", True)


def main():
    """
    Main function. Starts the search for migrants.
    """
    find_migrants()


if __name__ == '__main__':
    main()
