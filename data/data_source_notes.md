# Data Source Notes

The dataset used in this project comes from the HDB resale flat price transactions collection on data.gov.sg.

Source: https://data.gov.sg/collections/189/view

The working dataset used in the report was updated as at 20 May 2026 and covers resale transactions from January 1990 to May 2026.

The raw data files were combined and cleaned before analysis. The main cleaned fields used in the project include transaction year, resale price, floor area, price per square metre, flat type, town, flat model, storey range and remaining lease years.

Because the official data.gov.sg collection continues to update, the frozen source files used for this report are included in `data/raw/`.

Included frozen source files:

- `Resale Flat Prices (Based on Approval Date), 1990 - 1999.csv`
- `Resale Flat Prices (Based on Approval Date), 2000 - Feb 2012.csv`
- `Resale Flat Prices (Based on Registration Date), From 2012 Mar to 2014 Dec.csv`
- `Resale Flat Prices (Based on Registration Date), From 2015 Jan to 2016 Dec.csv`
- `Resale Flat Prices (Based on Registration Date), From 2017 Jan onwards.csv`
- `Price Range of HDB Flats Offered.csv`
- `Footnotes in Annual Report for Price Range of HDB Flats Offered.pdf`

The larger combined working files are not uploaded because they exceed GitHub's normal file size limit:

- `Raw Data Combined.csv`
- `Raw Data Combined.xlsx`
- `Working File 2.xlsx`

Users can also download the latest official data directly from data.gov.sg, but newer downloads may not reproduce the exact same figures if additional transactions have been added after May 2026.
