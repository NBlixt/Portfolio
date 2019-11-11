# Version 3.1
# This script was designed to work with a single DMSO control and 9 drug doses.
# Takes an .xls from a CellTiter-Glo assay analyzed on a plate reader
# and outputs graphs for each sheet in the .xls.  Raw data and processed data
# are stored in separate tables of a PostgreSQL database.  

# Pip Freeze:
# certifi==2019.9.11
# cycler==0.10.0
# kiwisolver==1.1.0
# matplotlib==3.1.1
# mkl-fft==1.0.14
# mkl-random==1.1.0
# mkl-service==2.3.0
# numpy==1.17.2
# pandas==0.25.2
# pyparsing==2.4.2
# python-dateutil==2.8.0
# pytz==2019.3
# six==1.12.0
# tornado==6.0.3
# xlrd==1.2.0

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
import sys
import argparse
import re
import psycopg2

# Set a loop or option to analyze all files in directory if desired
def file_selection(input_path=os.getcwd()):
    """
    input_path: The directory specified on the command line at initiation of 
    program.  Defaults to the current directory if not specified.

    Seaches for an .xls file to analyze in the following locations: first,
    the provided input path from the command line; second, the current
    directory; third, a directory specified in the input if the previous two
    locations do not contain the correct file."""

    # Generates a list of possible files in the provided path
    files = sorted([file for file in os.listdir(input_path)
                    if file.endswith(".xls") or file.endswith(".xlsx")],
                    reverse=True)
    file_dict = {}
    if files == []:
        print("No files were found.")
        path = input(
            "Enter the full path of the file's location to load or 'exit' to abort.")
        if path == "exit":  # Abort the process if "exit" entered.
            print("Process aborted")
            sys.exit()
        while True:  # Attempt to find .xls files from the provided path
            try:
                files = sorted([file for file in os.listdir(
                    path) if file.endswith(".xls") or file.endswith(".xlsx")])
                break
            except FileNotFoundError:
                print("No such file or directory.")

    # Enumerate current data files and add them to file_dict for calling later by number
    print("Current files available")
    for i, file in enumerate(files):
        print(i, file)
        file_dict[i] = file

    # Request file number and verify input or abort
    while True:
        chosen_file_number = input("\nEnter a file number to analyze or 'exit' to abort.\n")
        if chosen_file_number.isdigit():
            if int(chosen_file_number) in range(0, len(files)):
                chosen_file = file_dict[int(chosen_file_number)]
                print(chosen_file)
                break
        elif chosen_file_number == "exit":
            print("Process aborted")
            sys.exit()
        else:
            print("Your answer was not an appropriate number.")

    print("\nChosen file: ", chosen_file)

    final_check = input(
        "\nIf the above information is correct, press 'enter.'  Otherwise, type anything to abort.")
    if final_check == "":
        print(f"\nContinuing with analysis using {chosen_file}.")
        return os.path.join(input_path, chosen_file)
    else:
        print("\nProcess aborted\n")
        sys.exit()


def experimental_parameter_check():
    """Sets variables for drug, doses, and units depending on the drug used for the experiment."""

    drug = None
    drug_list = ["A-1155463", "AMG-176", "Venetoclax"]

    while True:
        # Set up options for choosing drug used in experiment
        drug_option_dict = {}
        for i, drug_used in enumerate(drug_list):
            print(i, drug_used)
            drug_option_dict[i] = drug_used
        # Ask for input to select correct drug
        drug_number = input(
            "\nEnter the number above corresponding to the correct drug, or type 'exit' to abort.\n")
        if drug_number.isnumeric():
            if int(drug_number) in range(0, len(drug_list)):
                drug = drug_option_dict[int(drug_number)]
                break

        elif drug_number.lower() == "exit":
            print("Process aborted")
            sys.exit()

    # Set doses and unit for proper drug
    if drug in ["AMG-176", "Venetoclax"]:
        doses = [0, 5, 16, 48, 144, 432, 1296, 3888, 11666, 35000]
        unit = "nM"

    elif drug == "A-1155463":
        doses = []
        unit = "nM"

    # Print experimental parameters for final check
    print("\n" + "Experimental Parameters:")
    print("Drug:", drug)
    print("Unit:", unit)
    print("Dose range:", doses)
    experiment_information_check = input(
        "\nIf the above information is correct, press 'enter.'  Otherwise, type anything to abort.")
    if experiment_information_check == "":
        print("\nContinuing with analysis\n")
        return doses, unit, drug
    else:
        print("Process aborted")
        sys.exit()


def date_and_experimenter():
    """A simple function that asks for input to determine who generated the data and
    when.  This information will be added to the SQL table for each experiment."""

    # Loop to get correct date
    while True:
        date = input('What date was the plate read?  Format as yyyy-mm-dd.\n')
        regex_pattern = '^20\d{2}-\d{2}-\d{2}$'
        if re.search(regex_pattern, date):
            break
        else:
            print("""\nThat is not a valid date.\n
                        Use this format: 2019-03-25\n""")

    # Loop to get correct initials (2-3 characters)
    while True:
        experimenter = input('What are the initials of the person who generated the data?\n')
        if len(experimenter) <= 3:
            break
        else:
            print('Initials should not be longer than 3 letters.')

    return date, experimenter.upper()


def make_mean_df(means, stdev, cell_line):
    """
    means: The mean luminescence values from an xls document of a CTG experiment.

    stdev: The standard deviation values from an xls document of a CTG experiment.

    cell_line: The name of the cell line used for the experiment.  Determined
    from the sheet name using clean_sheet_name().

    Generates a normalized mean column using means,
    and concatenates the means, stdev, and normalized means
    into a data frame for plotting.
    """

    normalized_mean = pd.Series(means/means[0], name="normalized_mean")
    mean_df = pd.concat([means, stdev, normalized_mean], axis=1)
    mean_df.columns = [cell_line, 'stdev', 'normalized_mean']

    return mean_df


def clean_sheet_name(sheet, drug):
    """sheet: The name of the current xls sheet being analyzed.

    drug: The name of the drug used in the experiment.

    Takes a sheet name and attempts to remove the underscore and
    drug name if present.  If not present, the sheet name is unchanged.
    This name will be used in naming of plots and saving data in postgreSQL."""

    if drug == 'AMG-176':
        drug_index = sheet.lower().find('_amg')
        if drug_index != -1:
            sheet = sheet[:drug_index]

    elif drug == 'Venetoclax':
        drug_index = sheet.lower().find('_ven')
        if drug_index != -1:
            sheet = sheet[:drug_index]

    return sheet.lower()


def parse_luminescence(xls_data, sheet, cell_line, drug, doses, experiment_date, experimenter, viability_dictionary):
    """xls_data: Data from using pd.ExcelFile(path) on an xls file.

    sheet: The name of the current sheet being analyzed.

    cell_line: The name of the current cell line being analyzed.  Taken from sheet name.

    drug: The name of the drug used in the experiment.

    doses: List of doses used in experiment.

    experiment_date: The data that the experiment concluded.

    experimenter: The initials of the person who performed the experiment.

    viability_dictionary: A dictionary created from user input to add viability of cell line at start of experiment.

    Parses raw luminescence values from a CTG experiment.  Splits the
    luminescence data into rows based on the number of wells/replicates
    in the experiment.  Combines this with the cell line's name, drug
    used, and date the experiment was performed.  Stores the resulting
    data in a PostgreSQL table (raw_lum).

    Mean luminescence and standard deviation is calculated by the machine
    that generated the xls file.  These values are also saved and returned
    for use in constructing plots downstream and storing the mean values 
    with other processed data in a separate PostgreSQL table (lum_drug_sens).
    """

    # Parse xls for current sheet
    # If results do not start at row 1 in xls, skip_rows increments until the header is found
    skip_rows = 0
    while True:
        ctg_results = xls_data.parse(sheet, skiprows=skip_rows)
        if 'Lum' not in ctg_results.columns:
            skip_rows += 1
        else:
            break
    lum = list(ctg_results['Lum'])
    means = ctg_results['Mean'].dropna().reset_index(drop=True)
    stdev = ctg_results['Std Dev'].dropna().reset_index(drop=True)
    replicates = int(ctg_results['Count'][0]) # Number of replicates for each drug dose

    # Call make_mean_df to create a data frame for plotting luminescence
    mean_df = make_mean_df(means, stdev, cell_line)

    # Prepare raw_data list for insertion into PostgreSQL table
    # Make a nested list of experimental parameters and raw luminescence values for each well
    raw_data = []
    for n in range(0, replicates):
        # Make a list with experimental parameters
        experimental_parameters = [experiment_date, experimenter, drug, cell_line, 'well_' + str(n+1)]
        # Extend the list with raw luminescence for the respective well (every fourth value usually)
        experimental_parameters.extend(lum[n::replicates])
        raw_data.append(experimental_parameters)

    # Prepare processed_data list for insertion into lum_drug_sens table in PostgreSQL
    ausc = ausc_trapazoidal(mean_df, doses)
    viability = viability_dictionary[cell_line]
    mean_luminescence = mean_df.iloc[:, 0].values
    processed_data = [cell_line, experiment_date, experimenter, viability, drug, ausc]
    processed_data.extend(mean_luminescence) # Adds the mean luminescence values to the end of the listdir

    return mean_df, raw_data, processed_data


def data_to_sql(raw_data, processed_data):
    """
    raw_data: a list of lists containing raw luminescence values for each well of a CTG experiment
    and some experimental parameters.

    processed_data: a list of experimental parameters, area under the curve (AUSC),
    viability of the cell line, and mean luminescence values.

    Returns nothing.  Inserts raw_data into the raw_lum SQL table, and inserts processed_data
    into the lum_drug_sens SQL table.
    """
    # Connect to postgres database
    with psycopg2.connect('dbname=mcl1 user=blixt007') as conn:
        cur = conn.cursor()
        
        # Insert the raw luminescence data into raw_lum from the nested list
        for row in raw_data:
            # Add column names to avoid inserting into first column (auto-increment)
            cur.execute("""INSERT INTO raw_lum( 
            created_on, created_by, drug, cell_line_str, well,
            dose_1, dose_2, dose_3, dose_4, dose_5, dose_6, dose_7, dose_8, dose_9, dose_10)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);""", tuple(row))

        # Insert the processed data into lum_drug_sens
        cur.execute("""INSERT INTO lum_drug_sens
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);""", tuple(processed_data))

    return


def vbar_luminescence_plot(mean_df, doses, drug, unit, path):
    """Creates a vertical bar plot in Matplotlib.pyplot using the
    raw luminescence values from the mean_df.  Saves a PNG file."""
    # Create a new series without the drug name but with dose and unit
    x_axis_labels = [str(dose) + ' nM' for dose in doses]

    bar_plot = plt.bar(x=x_axis_labels, height=mean_df.iloc[:,0], # Data
                  yerr=mean_df["stdev"], capsize=5, # Error bar settings
                  color="blue", edgecolor="black", alpha=0.5 # Color of bars and outline
                 )

    # Set font style
    plt.rc("font", family="Times New Roman")

    # Adjust ticks and labels
    plt.xticks(rotation=45, ha="right") # ha='right' helps keep labels aligned
    plt.ylabel("Luminescence", size=20)
    plt.xlabel("Treatment", size=20)
    plt.tick_params(axis="both", labelsize=17)
    plt.grid(axis="y", color="grey",linewidth=0.5)

    # Prepare cell line's name for title of plot
    cell_line = mean_df.columns[0].upper()
    plot_title = f"{cell_line} Treated With {drug}"
    plt.title(plot_title, size=20)

    plt.savefig(os.path.join(path, cell_line + "_bar_plot.png"), bbox_inches="tight")
    plt.close('all') # Closes all plots to avoid overlap in subsequent plots

    return


def survival_plot(mean_df, doses, drug, unit, path):
    """Make a survival plot using the normalized mean values
    from the mean_df.  The x-axis is in log scale, and the y-axis
    shows percentage of survival from 0-100%.

    A .png file is saved in the subdirectory with the other data.
    """
    # Adds one to every value so log scale can be used (log 1 = 0)
    x_axis_labels = [x+1 for x in doses]

    # Make the figure, ax, and plot
    fig = plt.figure()
    ax = fig.add_subplot(1, 1, 1)
    line_plot = ax.plot(x_axis_labels, mean_df["normalized_mean"], # Data
                        linestyle='-', color='dodgerblue', marker='o',# Line and marker specs
                        )
    # Set font
    plt.rc("font", family="Times New Roman")

    # Adjust scale, labels and ticks
    plt.ylabel("Survival", size=20)
    ax.set_ylim(ymin=0)
    plt.xlabel(f"{drug} ({unit})", size=20)
    ax.set_xscale('log')
    plt.tick_params(axis="both", labelsize=17)
    plt.grid(axis="y", color="grey",linewidth=0.5)

    # Convert y-scale to percentage
    y_tick_values = ax.get_yticks()
    ax.set_yticklabels(['{:,.0%}'.format(x) for x in y_tick_values])

    # Prepare cell line name and title of plot
    cell_line = mean_df.columns[0].upper()
    plot_title = f"{cell_line} Survival Plot"
    plt.title(plot_title, size=20)

    plt.savefig(os.path.join(path, cell_line + "_survival_plot.png"), bbox_inches="tight")
    plt.close('all') # Closes all plots to avoid overlap in subsequent plots

    return


def ausc_trapazoidal(mean_df, doses):
    """Performs numerical integration using the trapazoidal rule
    to determine the area under the survival curve (AUSC)
    for the drug respose.

    The only argument, mean_df, is a data frame made from make_mean_std().
    """
    y = mean_df.normalized_mean
    x = doses
    ausc = np.trapz(y, x)

    return round(ausc, 2)


def viability_dict(sheets, drug):
    """Asks for the viability percentage of each cell line in the provided list (names)
    and creates a dictionary.  The name of each cell line is the key, and the viability
    as a percentage is the value.  The list of cell names will come from the
    sheet names on the provided .xls file in ctg_analysis()."""

    viability_dictionary = {}
    while True:
        for sheet in sheets:
            while True:
                cell_line = clean_sheet_name(sheet, drug)
                viability = input(f"What is the percent viability from 0-100 for {cell_line}?\n")
                regex_pattern = "^\d{2}$|^100$"
                if re.search(regex_pattern, viability):
                    viability_dictionary[cell_line] = int(viability)
                    break
                else:
                    print(f"{viability} is not a valid answer.")
                    # Adds a blank to the dictionary if the input wasn't a number
                    viability_dictionary[cell_line] = ""

        # Prints the viability_dictonary and asks user to verify the values are correct.  If not, re-enter viability numbers.
        for cell_line, viability in zip(viability_dictionary.keys(), viability_dictionary.values()):
            print(f"\n{cell_line}'s viability is {viability}%.")
        correct_viability = input(
            "\nIf the above numbers are incorrect, type anything.  Otherwise, press 'enter'.\n")
        if correct_viability == "":
            break

    return viability_dictionary


def ctg_analysis(file, doses, unit, drug, replicates=4):
    """Takes the raw luminescence data (Lum column) from a CellTiter-Glo (CTG) .xls
    document located at path/file and saves an individual .csv for
    each sheet in the .xls.  These files will be saved in a new folder
    within the same location as the original .xls file with the same name.
    Each .csv contains a table with the treatments (drug plus dose plus unit),
    doses (numerical values only), and luminescent reading for each well.

    Sheets in the .xls that begin with "Sheet" it will be ignored.

    Also makes a bar plot of raw luminescence and a survival plot of normalized luminescence using matplotlib.pyplot.

    File is the name of the file to be used and must contain the file extension (.xls).  This will
    either be supplied by file_selection() or a flag from the command line.

    Doses is a list of each dose used in the experiment.  These are
    numerical values only and includes 0, which represents the DMSO control.

    Drug is the name of the primary drug used in the dose range provided.  This will
    be provided by experimental_parameter_check().

    Replicates is the number of wells used per dose.  4 is the default.

    Note that this funtion will probably fail if the data table does not
    start at A1 in the provided .xls.  I plan to fix this in a future version."""

    # Load the excel file with the CTG results and list the name of the sheets.
    xls_data = pd.ExcelFile(file)
    sheets = xls_data.sheet_names
    # Remove unnamed sheets (Sheet1, Sheet2, etc.)
    sheets = [sheet for sheet in sheets if not sheet.startswith("Sheet")]
    # Removes the file extension and adds "_data" for creating the directory name
    sub_dir = file[:-4] + "_data"


#### Change so it asks if the folder should be deleted if present
#### Make a separate function to call??
    # Make a new directory for storing plots
    try:
        os.mkdir(sub_dir)
    # Asks to overwrite files if directory already exists
    except FileExistsError:
        while True:
            print("This file has already been analyzed.")
            print("Should the data be overwritten?")
            overwrite_answer = input('Y/N? ')
            if overwrite_answer.lower() == "y":
                print("Data will be overwritten.")
                break
            elif overwrite_answer.lower() == "n":
                print("Aborting process.")
                sys.exit()

    # Call the viability_dict function to obtain the viability for each cell line
    viability_dictionary = viability_dict(sheets, drug)

    # Determine date of creation and experimenter who created the data
    experiment_date, experimenter = date_and_experimenter()

    # Iterate over the sheets to process raw data and make graphs
    for sheet in sheets:
        cell_line = clean_sheet_name(sheet, drug)
        # Functions to process each cell line's data
        mean_df, raw_data, processed_data = parse_luminescence(
            xls_data, sheet, cell_line, drug, doses, experiment_date, experimenter, viability_dictionary)
        data_to_sql(raw_data, processed_data)
        # SET UP ARGPARSE FLAG TO SKIP GRAPHS IF DESIRED
        vbar_luminescence_plot(mean_df, doses, drug, unit, sub_dir)
        survival_plot(mean_df, doses, drug, unit, sub_dir)

    return


if __name__ == "__main__":
    # Create parser for running script on command line
    ctg_parser = argparse.ArgumentParser(description="Provides the input path for analysis.")
    ctg_parser.add_argument("-i",
                            dest="input",
                            help="The path containing data to be analyzed.")
    args = ctg_parser.parse_args()
    input_path = args.input

    # Process data
    while True:
        file = file_selection(input_path)
        doses, unit, drug = experimental_parameter_check()
        ctg_analysis(file, doses, unit, drug)
        print('Would you like to analyze another file?')
        continue_analysis = input('Y/N: ')
        if continue_analysis.lower() == 'n': # Repeat analysis if not 'n'
            break
