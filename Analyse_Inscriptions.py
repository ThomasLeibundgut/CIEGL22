import numpy as np
import pandas as pd
import haversine as hs
import statistics
from matplotlib import pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta


def open_database(date, name):
    """
    Takes in a date object with today's date.
    Starting from today, looks for the most recent version of the
    EDCS master database file ('EDCS_Master_DATE.csv').
    Once found, opens and returns it.
    """
    filename = None
    edcs = None
    searching = True
    while searching:
        date_str = date.strftime('%Y-%m-%d')
        filename = name + date_str + '.csv'
        try:
            edcs = pd.read_csv(filename)
            searching = False
        except FileNotFoundError:
            date = (date - timedelta(days=1))
    print(f"Read database; filename: {filename}.")
    if edcs is None:
        print("Some Error has occurred. Terminating programme...")
        quit()
    edcs.rename(columns={"Unnamed: 0": "Index"}, inplace=True)
    return edcs


def save_databse(database, name_tag, today, idx):
    """
    Takes in a pandas dataframe, today's date, a name_tag, and a bool (idx).
    Saves it using the name-tag and date as a csv, with or without index.
    """
    filename = name_tag + "_" + today.strftime('%Y-%m-%d') + ".csv"
    database.to_csv(filename, index=idx, encoding="utf-8")
    print(f"Saved {name_tag} database to csv.")


def set_gender(row):
    if row['m'] == 1 and row['f'] == 0:
        return 0
    elif row['f'] == 1 and row['m'] == 0:
        return 1
    else:
        return 2


def add_gender_names(row):
    if row['funerary'] == 1:
        non_names = {"Dis", "Manibus"}
        male_names = {"Agrippa", "Aquila", "Caracalla", "Nerva", "Scaevola",
                      "Seneca"}
        male_suffix = {"us", "os", "er", "i", "o"}
        words = row['cleantext']
        if isinstance(words, str):
            words = row['cleantext'].split()
            for word in words:
                try:
                    word.encode('ascii')
                except UnicodeEncodeError:  # contains Greek / non-Latin letters
                    continue
                if len(word) > 2 and word[0].isupper() and \
                        word[1].islower() and word not in non_names:
                    if word in male_names or word[-2] in male_suffix or \
                            word[-1] in male_suffix:
                        return 0
                    elif word[-2:] == "ae" or word[-1] == "a":
                        return 1
    return 2


def add_gender_keywords(edcs):
    """
    Takes in a pandas dataframe containing the EDCS.
    Where keywords include "vir", it sets column "viri" to 1, else to 0.
    Where keywords include "mulier", it sets column "mulieres" to 1, else to 0
    Returns dataframe.
    """
    edcs['viri'] = np.where(edcs['keywords'].str.contains('vir'), 1, 0)
    edcs['mulieres'] = np.where(edcs['keywords'].str.contains('mulier'), 1, 0)
    edcs['m'] = np.where((edcs['viri'] == 1) |
                         (edcs['gender_main_pers'] == 0), 1, 0)
    edcs['f'] = np.where((edcs['mulieres'] == 1) |
                         (edcs['gender_main_pers'] == 1), 1, 0)
    edcs['gender'] = edcs.apply(lambda row: set_gender(row), axis=1)

    edcs['gender_of_1st_Word'] = edcs.apply(lambda row: add_gender_names(row),
                                            axis=1)

    print(f"Added gender keyword columns ({edcs['viri'].sum()} viri, "
          f"{edcs['mulieres'].sum()} mulieres.)")
    return edcs


def add_distance(row):
    """
    Takes in a dataframe row.
    If the field in column 'origo_LatLong' contains coordinates,
    it creates a coordinates-tuple of both findspot and origo,
    calculates the distance in between, and returns it if > 10km.
    If 'origo_LatLong' doesn't contain coordinates, returns NaN.
    """
    if isinstance(row['origo_LatLong'], str):
        findspot = (row['find_lat'], row['find_long'])
        origo = (row['origo_lat'], row['origo_long'])
        distance = hs.haversine(findspot, origo)
        if distance > 10:
            return distance
    return np.nan


def calc_distance(edcs):
    """
    Takes in a pandas dataframe.
    Calculates the distance between origo and findspot using add_distance().
    Returns dataframe.
    """
    edcs['distance'] = edcs.apply(lambda row: add_distance(row), axis=1)
    print("Calculated distance between findspot and origo.")
    return edcs


def get_analysis(edcs):
    """
    Takes in a pandas dataframe containing the EDCS.
    Calculates descriptive statistics and prints them to the console.
    Returns the dataframe.
    """
    edcs = ignore_duplicates(edcs)
    num_def_migrants = edcs[edcs['ignore'] == 0]['migrant'].sum()
    num_poss_migrants = edcs[edcs['ignore'] == 0]['possible_migrant'].sum()
    num_prob_migrants = edcs[edcs['ignore'] == 0]['probable_migrant'].sum()
    num_inscs = len(edcs.index) - edcs['ignore'].sum()
    prop_migrants = 100 / num_inscs * num_def_migrants
    distance_min = edcs[edcs['ignore'] == 0]['distance'].min(skipna=True)
    distance_max = edcs[edcs['ignore'] == 0]['distance'].max()
    distance_mean = edcs[edcs['ignore'] == 0]['distance'].mean()
    distance_median = edcs[edcs['ignore'] == 0]['distance'].median()
    distance_mode = edcs[edcs['ignore'] == 0]['distance'].mode(dropna=True)
    distance_stdev = edcs[edcs['ignore'] == 0]['distance'].std()
    f_num = len(edcs[(edcs['distance'] >= 10) &
                     ((edcs['mulieres'] == 1) |
                      (edcs['gender_main_pers'] == 1))])
    m_num = len(edcs[(edcs['distance'] >= 10) &
                     ((edcs['viri'] == 1) |
                      (edcs['gender_main_pers'] == 0))])
    num = len(edcs[edcs['distance'] >= 10])
    funerary = edcs[edcs['ignore'] == 0]['funerary'].sum()

    f_num_migr = edcs[(edcs['ignore'] == 0) &
                      ((edcs['mulieres'] == 1) |
                       (edcs['gender_main_pers'] == 1))]['migrant'].sum()
    f_distance_mean = edcs[(edcs['ignore'] == 0) &
                           ((edcs['mulieres'] == 1) |
                            (edcs['gender_main_pers'] == 1))]['distance'].mean()
    f_distance_median = edcs[(edcs['ignore'] == 0) &
                             ((edcs['mulieres'] == 1) |
                              (edcs['gender_main_pers'] ==
                               1))]['distance'].median()
    f_distance_mode = edcs[(edcs['ignore'] == 0) &
                           ((edcs['mulieres'] == 1) |
                            (edcs['gender_main_pers'] ==
                             1))]['distance'].mode(dropna=True)
    f_distance_stdev = edcs[(edcs['ignore'] == 0) &
                            ((edcs['mulieres'] == 1) |
                            (edcs['gender_main_pers'] == 1))]['distance'].std()
    f_distance_min = edcs[(edcs['ignore'] == 0) &
                          ((edcs['mulieres'] == 1) |
                           (edcs['gender_main_pers'] ==
                            1))]['distance'].min(skipna=True)
    f_distance_max = edcs[(edcs['ignore'] == 0) &
                          ((edcs['mulieres'] == 1) |
                           (edcs['gender_main_pers'] == 1))]['distance'].max()
    f_funerary = edcs[(edcs['ignore'] == 0) &
                      ((edcs['mulieres'] == 1) |
                       (edcs['gender_main_pers'] == 1))]['funerary'].sum()

    m_num_migr = edcs[(edcs['ignore'] == 0) &
                      ((edcs['viri'] == 1) |
                       (edcs['gender_main_pers'] == 0))]['migrant'].sum()
    m_distance_mean = edcs[(edcs['ignore'] == 0) &
                           ((edcs['viri'] == 1) |
                            (edcs['gender_main_pers'] == 0))]['distance'].mean()
    m_distance_median = edcs[(edcs['ignore'] == 0) &
                             ((edcs['viri'] == 1) |
                              (edcs['gender_main_pers'] ==
                               0))]['distance'].median()
    m_distance_mode = edcs[(edcs['ignore'] == 0) &
                           ((edcs['viri'] == 1) |
                            (edcs['gender_main_pers'] ==
                             0))]['distance'].mode(dropna=True)
    m_distance_stdev = edcs[(edcs['ignore'] == 0) &
                            ((edcs['viri'] == 1) |
                             (edcs['gender_main_pers'] == 0))]['distance'].std()
    m_distance_min = edcs[(edcs['ignore'] == 0) &
                          ((edcs['viri'] == 1) |
                           (edcs['gender_main_pers'] ==
                            0))]['distance'].min(skipna=True)
    m_distance_max = edcs[(edcs['ignore'] == 0) &
                          ((edcs['viri'] == 1) |
                           (edcs['gender_main_pers'] == 0))]['distance'].max()
    m_funerary = edcs[(edcs['ignore'] == 0) &
                      ((edcs['viri'] == 1) |
                       (edcs['gender_main_pers'] == 0))]['funerary'].sum()

    print("Calculated descriptive statistics.\n")
    print(f"Ca. {m_num} inscriptions refer to men, and ca. {f_num} to women.")
    print(f"There are {num_def_migrants} definitive migrants in the database",
          f"out of {num_inscs} inscriptions in the database",
          f"(ca. {round(prop_migrants, 2)}%).")
    print(f"{num_poss_migrants} possible, {num_prob_migrants} probable migrants;"
          f" {funerary} funerary inscriptions.\n")

    print(f"All migrants (N={num}): \nMean: {distance_mean}, "
          f"Median: {distance_median}",
          f"Mode: {distance_mode}, St. Dev.: {distance_stdev}, "
          f"Min: {distance_min}, Max: {distance_max}.\n")

    print(f"Women Migrants (N={f_num_migr}): \nMean: Mean: {f_distance_mean},",
          f"Median: {f_distance_median}, Mode: {f_distance_mode}, ",
          f"St. Dev.: {f_distance_stdev}, Min: {f_distance_min}, "
          f"Max: {f_distance_max}; {f_funerary} funerary inscriptions.\n")

    print(f"Men Migrants (N={m_num_migr}): \nMean: Mean: {m_distance_mean}, "
          f"Median: {m_distance_median}, Mode: {m_distance_mode}, "
          f"St. Dev.: {m_distance_stdev}, Min: {m_distance_min}, "
          f"Max: {m_distance_max}; {m_funerary} funerary inscriptions..\n")

    print("Mode all distances: ", statistics.mode(edcs['distance']))
    print("Mode women: ", statistics.mode(edcs[(edcs['ignore'] == 0) &
                                               ((edcs['mulieres'] == 1) |
                                                (edcs['gender_main_pers'] ==
                                                 1))]['distance']))
    print("Mode men: ", statistics.mode(edcs[(edcs['ignore'] == 0) &
                                             ((edcs['viri'] == 1) |
                                              (edcs['gender_main_pers'] ==
                                               0))]['distance']))

    return edcs


def ignore_duplicates(edcs):
    """
    Takes in a pandas dataframe containing the EDCS database.
    Identifies and marks duplicates.
    Returnes updated dataframe.
    """
    edcs.sort_values(by='edcs-id', inplace=True)
    edcs['ignore'] = 0
    for idx, elem in edcs.iterrows():
        if idx != 0 and idx % 100000 == 0:
            print(f"Searched {idx} elements for duplicates.")
        indexes = []
        distances = []
        if elem['migrant'] == 1:
            indexes.append(elem['Index'])
            distances.append(elem['distance'])

            i = 1
            while elem['edcs-id'] == edcs['edcs-id'].iloc[idx - i]:
                indexes.append(edcs['Index'].iloc[idx - i])
                distances.append(edcs['distance'].iloc[idx - i])
                i += 1
            j = 1
            while elem['edcs-id'] == edcs['edcs-id'].iloc[idx + j]:
                indexes.append(edcs['Index'].iloc[idx + j])
                distances.append(edcs['distance'].iloc[idx + j])
                j += 1

            if len(indexes) > 1:
                shortest = min(distances)
                index = distances.index(shortest)
                for i, v in enumerate(indexes):
                    if i != index:
                        edcs.at[i, 'ignore'] = 1
    duplicates = edcs['ignore'].sum()
    print(f"Marked duplicates (found {duplicates} duplicates).")
    return edcs


def get_metadata(edcs):
    """
    Takes in a pandas dataframe containing the EDCS database.
    Calculates mean inscription dates and plots them as a histogram.
    """
    edcs['time_point'] = (edcs['time_from'] + edcs['time_to']) / 2

    fig, ax = plt.subplots()
    sns.histplot(data=edcs[edcs['migrant'] == 1], x='time_point', binwidth=20)
    ax.set(xlabel='Date of Inscription', ylabel='',
           title="Temporal Distribution of Inscription (mean date)")
    ax.set_xlim(-200, 700)
    plt.show()


def plot_graphs(edcs):
    """
    Takes in a pandas dataframe containing the EDCS database.
    Plots distance migrated dependend on gender in different plots.
    """
    sns.set()
    sns.set_style('white')

    fig, ax = plt.subplots()
    sns.kdeplot(data=edcs[edcs['gender_of_1st_Word'] == 0]['distance'], ax=ax)
    sns.kdeplot(data=edcs[edcs['gender_of_1st_Word'] == 1]['distance'], ax=ax)
    ax.set(yticklabels=[], xlabel='Distance (km)', ylabel='Density',
           title='Distance Migrated')
    ax.legend(loc='upper right')
    plt.legend(labels=['male', 'female'])
    plt.show()

    fig, ax = plt.subplots()
    sns.kdeplot(data=edcs[-(edcs['gender_of_1st_Word'] == 2)], x='distance',
                hue='gender_of_1st_Word', ax=ax)
    ax.set(yticklabels=[], xlabel='Distance (km)', ylabel='Density',
           title='Distance Migrated')
    ax.legend(loc='upper right', labels=['male', 'female'])
    plt.show()

    fig, ax = plt.subplots()
    sns.histplot(data=edcs[-(edcs['gender_of_1st_Word'] == 2)], x='distance',
                 hue='gender_of_1st_Word', ax=ax)
    ax.set(xlabel='Distance (km)', ylabel='', title='Distance Migrated')
    ax.legend(loc='upper right', labels=['male', 'female'])
    plt.show()

    fig, ax = plt.subplots()
    sns.histplot(data=edcs[-(edcs['gender_of_1st_Word'] == 2)], x='distance',
                 hue='gender_of_1st_Word', ax=ax)
    ax.set(xlabel='Distance (km)', ylabel='', title='Distance Migrated')
    ax.set_xlim(0, 2000)
    ax.legend(loc='upper right', labels=['male', 'female'])
    plt.show()


def analyse_inscriptions():
    """
    Organising function.
    Opens EDCS master database, adds gender data to it,
    and calculates the distances between origo and findspot, where available.
    Saves database.
    """
    today = datetime.today()
    edcs = open_database(today, 'EDCS_Master_')
    edcs_gender = add_gender_keywords(edcs)
    edcs_dist = calc_distance(edcs_gender)
    edcs_analysis = get_analysis(edcs_dist)
    get_metadata(edcs_analysis)
    plot_graphs(edcs_analysis)
    save_databse(edcs_analysis, "EDCS_Analysis", today, False)


def main():
    """
    Main function. Starts the search for migrants.
    """
    analyse_inscriptions()


if __name__ == "__main__":
    main()
