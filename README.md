# Portfolio
This repository includes short descriptions and links to programs I have written in Python while employed as a post-doctoral researcher.  These programs are all related to research on multiple myeloma.  


## BCL2 Drug Response
This Jupyter Notebook was generated while investigating whether expression levels of pro-sruvival factors in certain types of cancer cell lines would show any correlation to survival after treatment with drugs that target said pro-survival factors.

## CTG Analysis
A common experiment in our lab is to treat human myeloma cell lines (HMCLs) with increasing doses of a drug to determine the relative sensitivity/resistance each HMCL has to said drug.  In this process, each experiment with each HMCL produces an xls sheet with several measurements.  The ctg_analysis.py file is a Python script that automates our analysis of each xls file.  Briefly, ctg_analysis.py can take in an unlimited number of xls sheets, one for each cell line, parses the data to save plots of each experiment, calculate area under the curve, and store the raw and processed data in separate PostgreSQL tables for later use.
