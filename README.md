# CIEGL22
Code used in preparation for the CIEGL22 presentation.
The Code is presented as-is, and will not be updated. The final code used in the dissertation will be made available at a future date. Nevertheless, any comments are welcome.

## Workflow
1. Scrape_EDCS.py is used to download all the data in HTML format from the Epigraphik Datenbank Clauss Slaby and save it to a txt file.
2. EDCS_Extract.py converts the raw HTML to a more or less neat table, with one line for each inscription, and all information in specific columns.
3. clean_EDCS.py then checks all inscriptions for conversion errors and, where necessary, pulls the needed information form the EDCS.
4. Find_Migrants.py, on the basis of the Pleiades Names database () looks for toponyms in the inscription text, thus identifying migrants.
5. Analyse_Inscriptions.py provides the analysis of the migrants and draws the graphs.

## Corrections
Please note that the code contains some errors which were only identified after the presentation. The files 'Find_Migrants.py' and 'Analyse_Inscriptions.py' therefore don't produce the expected results.
