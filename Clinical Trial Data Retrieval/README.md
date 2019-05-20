# Goal
The goal of this project is to identify clinical trials and the treatment arms within the trials in which a higher percentage of participants (minimum 25%) report experiencing neuropathy-related adverse events.  This is an initial portion of a larger project that attempts to determine how genetics increase or decrease susceptibility to neuropathy-related adverse events. 

# Data
The data for this project includes .xml files downloaded from [clinicaltrials.gov](https://clinicaltrials.gov/).  Specifically, studies on multiple myeloma that were completed and had results were downloaded in [bulk](https://clinicaltrials.gov/ct2/results?cond=Multiple+Myeloma&term=&cntry=&state=&city=&dist=&Search=Search&recrs=e&rslt=With).

# Process
The overall process for this project involves scraping clinical trials to obtain percentages of neuropathies reported for each treatment arm in each trial and storing this and other data in a SQLite database.  Then querying the database to obtain treatments and trial numbers that resulted in higher than 25 percent of participants reporting neuropathy-related adverse events.  

More specifically:

    1) Scrape all the provided .xml files to create a DataFrame containing trial number (NCT ID), trial start and end dates, enrollment, and more basic information.
    
    2) Filter trials that report lower than 25 percent of participants in all treatment arms experiencing neuropathy-related adverse events.
    
    3) Use the remaining trials to create another DataFrame reporting the percentage of participants reporting each type of neuropathy-related adverse event indexed by trial number(NCT ID) and treatment-arm number.
    
    4) Create a final DataFrame showing each treatment for all arms of every study.
    
    5) Add all DataFrames as separate tables to an SQLite database.
    
    6) Query the database to obtain treatments and NCT ID values from each treatment with reported neuropathy-related adverse events above 25 percent.
