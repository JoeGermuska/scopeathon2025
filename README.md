Cooperation Racine Data Gathering
---------------------------------
Scope-a-thon 2024

- Goal: gather ACS data for the Census tracts within one mile of Cooperation Racine

## setup
This project uses [`uv`](https://github.com/astral-sh/uv) for dependency management. Check `uv` documentation for how to start working with a UV project. 

## `get_chicago_tracts.ipynb`

This notebook fetches Illinois tracts from the Census Bureau and filters them to those within a 1 mile radius of W. 71st and S. Racine. These are dumped to a CSV and GeoJSON file in the `generated/` directory.

This notebook also creates an HTML file, `chicago_tracts_map.html`, which shows the tracts and the circle.

## `fetch_census_data.py`

This depends upon `get_chicago_tracts.ipynb` having been run, or otherwise `tracts_within_1mile.csv` having been created. This script reads that file in and queries the Census API for certain data (mostly B18105 Ambulatory Disability by Sex and Age) and creates an annotated version of the tracts spreadsheet with that data.

Margins of error are disregarded for this project; totaling the tracts and/or deciding whether the percentage of some tracts is too small to include is left as an exercise for the next person to use the data.
