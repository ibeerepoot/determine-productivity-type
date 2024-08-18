import numpy as np
import pandas as pd
import streamlit as st
import json
from io import StringIO
from datetime import datetime, timedelta
import re
import csv
import altair as alt
import zipfile
import matplotlib.pyplot as plt
import seaborn as sns

"""
# Let's determine what productivity type you are!
"""

# Sidebar for accepting input parameters
with st.sidebar:
    # Load AWT data
    st.header('Upload your data')
    st.markdown('**1. AWT data**')
    awt_uploaded_file = st.file_uploader("Upload your Tockler data here. You can export your data by going to Tockler > Search > Set a time period > Export to CSV.")

    # Load Survey results data
    st.markdown('**2. Survey results**')
    survey_uploaded_file = st.file_uploader("Upload your survey results here. The CSV should contain 5 columns: Date, Productivity, Vigor, Dedication, Absorption.")

# Main section for processing AWT data
if awt_uploaded_file is not None:
    try:
        # Read the uploaded CSV file into a dataframe
        awt_stringio = StringIO(awt_uploaded_file.getvalue().decode('latin1'))
        
        # Explicitly set the delimiter as semicolon
        dataframe_awt = pd.read_csv(awt_stringio, delimiter=';')

        # Drop the 'Type' column if it exists
        if 'Type' in dataframe_awt.columns:
            dataframe_awt = dataframe_awt.drop(columns=['Type'])

        # Display the first 5 rows of the dataframe
        #st.write("Snippet of the raw AWT data:")
        #st.write(dataframe_awt)

        # Remove rows where 'Begin' is empty
        dataframe_awt = dataframe_awt.dropna(subset=['Begin'])
        dataframe_awt = dataframe_awt[dataframe_awt['Begin'] != '']

        # Remove rows where 'Title' is 'NO_TITLE'
        dataframe_awt = dataframe_awt[~dataframe_awt['Title'].isin(['NO_TITLE', 'Windows Default Lock Screen'])]

        # Initialize lists to store merged rows
        merged_rows = []

        # Convert 'App' column to string
        dataframe_awt['App'] = dataframe_awt['App'].astype(str)

        # Convert 'Title' column to string
        dataframe_awt['Title'] = dataframe_awt['Title'].astype(str)

        # Iterate over the DataFrame to merge consecutive rows
        current_row = None
        for index, row in dataframe_awt.iterrows():
            if current_row is None:
                current_row = row
            else:
                # Check if the current row is consecutive with the previous row
                if row['Begin'] == current_row['End']:
                    # Merge titles and update End time
                    current_row['App'] += '; ' + row['App']
                    current_row['Title'] += '; ' + row['Title']
                    current_row['End'] = row['End']
                else:
                    # Append the current merged row to the list
                    merged_rows.append(current_row)
                    # Start a new merged row
                    current_row = row

        # Append the last merged row
        if current_row is not None:
            merged_rows.append(current_row)

        # Create a new DataFrame with the merged rows
        dataframe_merged_awt = pd.DataFrame(merged_rows)

        # Filter out rows with unwanted titles
        dataframe_merged_awt = dataframe_merged_awt[~dataframe_merged_awt['Title'].isin(['NO_TITLE', 'Windows Default Lock Screen'])]

        # Reset the index of the new DataFrame
        dataframe_merged_awt.reset_index(drop=True, inplace=True)

        # Define a custom function to find the most occurring title in a semicolon-separated string
        def find_most_occurring_title(merged_titles):
            titles = merged_titles.split(';')
            title_counts = pd.Series(titles).value_counts()
            most_occuring_title = title_counts.idxmax()
            return most_occuring_title

        # Apply the custom function to each row in the DataFrame and create a new column
        dataframe_merged_awt['Most_occuring_title'] = dataframe_merged_awt['Title'].apply(find_most_occurring_title)

        #st.write("AWT data merged to continued work slots:")
        #st.write(dataframe_merged_awt.head())

    except pd.errors.ParserError as e:
        st.error(f"Error parsing AWT CSV file: {e}")
    except Exception as e:
        st.error(f"An unexpected error occurred: {e}")

# Check if a Survey results file has been uploaded
if survey_uploaded_file is not None:
    try:
        # Read the uploaded CSV file into a dataframe
        survey_stringio = StringIO(survey_uploaded_file.getvalue().decode('utf-8'))
        dialect = csv.Sniffer().sniff(survey_stringio.read(1024))
        survey_stringio.seek(0)
        dataframe_survey = pd.read_csv(survey_stringio, delimiter=dialect.delimiter)

        # Display the first 5 rows of the dataframe
        # st.write("Snippet of the survey results data:")
        # st.write(dataframe_survey.head())

        # Convert survey date format to match
        dataframe_survey['Date'] = pd.to_datetime(dataframe_survey['Date'], format='%d-%m-%Y').dt.strftime('%Y-%m-%d')

        #dataframe_survey

    except pd.errors.ParserError as e:
        st.error(f"Error parsing Survey CSV file: {e}")
    except Exception as e:
        st.error(f"An unexpected error occurred: {e}")

if survey_uploaded_file is not None and awt_uploaded_file is not None:
    # Ensure Begin and End are datetime columns
    dataframe_awt['Begin'] = pd.to_datetime(dataframe_awt['Begin'], format='%d-%m-%Y %H:%M:%S')
    dataframe_awt['End'] = pd.to_datetime(dataframe_awt['End'], format='%d-%m-%Y %H:%M:%S')

    # Calculate the duration (End - Begin) in seconds
    dataframe_awt['Duration'] = (dataframe_awt['End'] - dataframe_awt['Begin']).dt.total_seconds()

    # Extract the date from the Begin column
    dataframe_awt['Date'] = dataframe_awt['Begin'].dt.date

    # Calculate total time spent on the computer for each day
    dataframe_days = dataframe_awt.groupby('Date')['Duration'].sum().reset_index()

    # Convert duration from seconds to hours (optional)
    dataframe_days['Total Time Spent (hours)'] = dataframe_days['Duration'] / 3600

    # Calculate the start time (earliest Begin time) for each day
    start_times = dataframe_awt.groupby('Date')['Begin'].min().reset_index()
    start_times.rename(columns={'Begin': 'Start Time'}, inplace=True)

    # Calculate the end time (latest End time) for each day
    end_times = dataframe_awt.groupby('Date')['End'].max().reset_index()
    end_times.rename(columns={'End': 'End Time'}, inplace=True)

    # Merge the start times and end times with the dataframe_days
    dataframe_days = dataframe_days.merge(start_times, on='Date')
    dataframe_days = dataframe_days.merge(end_times, on='Date')

    # Function to convert time to decimal hours
    def time_to_decimal(time):
        if pd.isna(time):
            return None
        hours = time.hour
        minutes = time.minute
        seconds = time.second
        decimal_hours = hours + (minutes / 60) + (seconds / 3600)
        return decimal_hours

    # Apply the conversion function to 'Start Time' and 'End Time'
    dataframe_days['Start Time (Decimal)'] = dataframe_days['Start Time'].apply(time_to_decimal)
    dataframe_days['End Time (Decimal)'] = dataframe_days['End Time'].apply(time_to_decimal)

    # (1) Count how many times each date occurs in dataframe_awt
    date_counts = dataframe_awt.groupby('Date').size().reset_index(name='Occurrences')

    # (2) Count unique titles for each day
    unique_titles_count = dataframe_awt.groupby('Date')['Title'].nunique().reset_index(name='Unique Titles')

    # (3) Calculate the share of unique titles across the total number of titles
    # Calculate the total number of titles (same as the number of occurrences for each date in this context)
    share_unique_titles = unique_titles_count.copy()
    share_unique_titles['Share of Unique Titles'] = share_unique_titles['Unique Titles'] / date_counts['Occurrences']

    # Merge the calculated columns with dataframe_days
    dataframe_days = dataframe_days.merge(date_counts, on='Date', how='left')
    dataframe_days = dataframe_days.merge(unique_titles_count, on='Date', how='left')
    dataframe_days = dataframe_days.merge(share_unique_titles[['Date', 'Share of Unique Titles']], on='Date', how='left')

    # Step 1: Calculate the most occurring title for each day
    title_counts = dataframe_awt.groupby(['Date', 'Title']).size().reset_index(name='Count')

    # Step 2: Identify the most occurring title for each day
    most_frequent_title = title_counts.loc[title_counts.groupby('Date')['Count'].idxmax()]
    most_frequent_title = most_frequent_title[['Date', 'Title']]
    most_frequent_title.rename(columns={'Title': 'Most Frequent Title'}, inplace=True)

    # Step 3: Merge the most frequent title with the dataframe_days
    dataframe_days = dataframe_days.merge(most_frequent_title, on='Date')

    # Step 1: Calculate the total time spent on each title for each day
    title_duration = dataframe_awt.groupby(['Date', 'Title'])['Duration'].sum().reset_index()

    # Step 2: Identify the title with the longest duration for each day
    max_duration_title = title_duration.loc[title_duration.groupby('Date')['Duration'].idxmax()]
    max_duration_title = max_duration_title[['Date', 'Title']]
    max_duration_title.rename(columns={'Title': 'Title with Longest Duration'}, inplace=True)

    # Step 3: Merge the title with the longest duration with the dataframe_days
    dataframe_days = dataframe_days.merge(max_duration_title, on='Date')

    # Extract the date from the Begin column
    dataframe_awt['Date'] = dataframe_awt['Begin'].dt.date

    # Step 1: Pivot the data to get total duration spent in each App for each day
    pivot_table = dataframe_awt.pivot_table(index='Date', columns='App', values='Duration', aggfunc='sum', fill_value=0)

    # Reset index to merge with dataframe_days
    pivot_table = pivot_table.reset_index()

    # Step 2: Merge the pivot table with dataframe_days
    dataframe_days = dataframe_days.merge(pivot_table, on='Date', how='left')

    # Ensure that Begin and End are datetime columns in dataframe_merged_awt
    dataframe_merged_awt['Begin'] = pd.to_datetime(dataframe_merged_awt['Begin'], format='%d-%m-%Y %H:%M:%S')
    dataframe_merged_awt['End'] = pd.to_datetime(dataframe_merged_awt['End'], format='%d-%m-%Y %H:%M:%S')

    # Calculate the duration (End - Begin) in seconds
    dataframe_merged_awt['Duration'] = (dataframe_merged_awt['End'] - dataframe_merged_awt['Begin']).dt.total_seconds()

    # Extract the date from the Begin column
    dataframe_merged_awt['Date'] = dataframe_merged_awt['Begin'].dt.date

    # Calculate total number of work slots per day
    work_slots_count = dataframe_merged_awt.groupby('Date').size().reset_index(name='Total Work Slots')

    # Calculate average duration of work slots per day
    average_duration = dataframe_merged_awt.groupby('Date')['Duration'].mean().reset_index(name='Average Work Slot Duration')

    # Merge these calculations with the existing dataframe_days
    dataframe_days = dataframe_days.merge(work_slots_count, on='Date', how='left')
    dataframe_days = dataframe_days.merge(average_duration, on='Date', how='left')

    # Count occurrences of each title for each day
    title_counts = dataframe_merged_awt.groupby(['Date', 'Most_occuring_title']).size().reset_index(name='Title Count')

    # Find the most frequent title for each day
    most_frequent_title = title_counts.loc[title_counts.groupby('Date')['Title Count'].idxmax()]

    # Merge the most frequent title information with work slots count
    most_frequent_title = most_frequent_title.rename(columns={'Most_occuring_title': 'Most Frequent Title'})
    most_frequent_title = most_frequent_title[['Date', 'Most Frequent Title', 'Title Count']]

    # Merge to get title counts with total work slots
    merged_slots = work_slots_count.merge(most_frequent_title, on='Date', how='left')

    # Calculate the share of work slots with the most frequent title
    merged_slots['Share of Work Slots with Most Frequent Title'] = (
        merged_slots['Title Count'] / merged_slots['Total Work Slots']
    )

    # Merge these calculations with the existing dataframe_days
    dataframe_days = dataframe_days.merge(work_slots_count, on='Date', how='left')
    dataframe_days = dataframe_days.merge(average_duration, on='Date', how='left')
    dataframe_days = dataframe_days.merge(merged_slots[['Date', 'Share of Work Slots with Most Frequent Title']], on='Date', how='left')

    # Display the resulting dataframe_days
    dataframe_days

    dataframe_days['Date'] = pd.to_datetime(dataframe_days['Date'], format='%d-%m-%Y').dt.strftime('%Y-%m-%d')

    # Merge dataframe_survey with dataframe_days on 'Date'
    merged_df = pd.merge(dataframe_survey, dataframe_days, on='Date')

    # Group by 'Productivity' and calculate the average of all relevant columns
    columns_to_average = [
        'Total Time Spent (hours)',
        'Start Time (Decimal)',
        'End Time (Decimal)',
        'Occurrences',
        'Unique Titles',
        'Share of Unique Titles',
        'Total Work Slots_x',
        'Average Work Slot Duration_x',
        'Share of Work Slots with Most Frequent Title',
        'Microsoft Outlook',
        'Google Chrome',
        'Microsoft Teams'
    ]

    productivity_scores_comparison = merged_df.groupby('Productivity')[columns_to_average].mean().reset_index()

    # Count the number of days for each Productivity score
    productivity_counts = dataframe_survey.groupby('Productivity').size().reset_index(name='Count')

    # Merge the count information into the productivity_scores_comparison DataFrame
    productivity_scores_comparison = pd.merge(productivity_scores_comparison, productivity_counts, on='Productivity', how='left')

    # Display the resulting productivity_scores_comparison DataFrame
    productivity_scores_comparison