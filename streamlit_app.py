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

"""
# Productivity Analysis
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
    st.subheader('Introduction')
    
    st.markdown(
    """
    You have been collecting Active Window Tracking data for some time now.
    In addition, you filled in a daily survey, where you gave scores for the following:
    - :blue-background[Productivity] How productive do you feel you were today? 
    - :blue-background[Vigor] Today, I felt bursting with energy. 
    - :blue-background[Dedication] Today, I was enthusiastic about my job. 
    - :blue-background[Absorption] Today, I was immersed in my work. 
    """
    )

    # Ensure Begin and End are datetime columns
    dataframe_awt['Begin'] = pd.to_datetime(dataframe_awt['Begin'], format='%Y-%m-%d %H:%M:%S')
    dataframe_awt['End'] = pd.to_datetime(dataframe_awt['End'], format='%Y-%m-%d %H:%M:%S')

    # Calculate the duration (End - Begin) in seconds
    dataframe_awt['Duration'] = (dataframe_awt['End'] - dataframe_awt['Begin']).dt.total_seconds()

    # Group by 'App' and sum the durations for each app
    # app_time_spent = dataframe_awt.groupby('App')['Duration'].sum()

    # Get the top 5 apps with the most time spent
    # top_5_time_spent_apps = app_time_spent.nlargest(5)

    # Convert duration from seconds to a more readable format (hours, minutes, or keep in seconds)
    # top_5_time_spent_apps_readable = top_5_time_spent_apps / 3600  # Converts seconds to hours

    # Display the result
    # st.write("Top 5 Apps with Most Time Spent (in hours):")
    # st.write(top_5_time_spent_apps_readable)

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

    # Calculate the number and share of unique titles for each day
    # (1) Count how many times each date occurs in dataframe_awt
    date_counts = dataframe_awt.groupby('Date').size().reset_index(name='Title_count')

    # (2) Count unique titles for each day
    unique_titles_count = dataframe_awt.groupby('Date')['Title'].nunique().reset_index(name='Unique Titles')

    # (3) Calculate the share of unique titles across the total number of titles
    # Calculate the total number of titles (same as the number of occurrences for each date in this context)
    share_unique_titles = unique_titles_count.copy()
    share_unique_titles['Share of Unique Titles'] = share_unique_titles['Unique Titles'] / date_counts['Title_count']

    # Merge the calculated columns with dataframe_days
    dataframe_days = dataframe_days.merge(date_counts, on='Date', how='left')
    dataframe_days = dataframe_days.merge(unique_titles_count, on='Date', how='left')
    dataframe_days = dataframe_days.merge(share_unique_titles[['Date', 'Share of Unique Titles']], on='Date', how='left')

    dataframe_days['Title count per hour on computer'] = dataframe_days['Title_count'] / dataframe_days['Total Time Spent (hours)']

    # Check the most occurring titles
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
    max_duration_info = title_duration.loc[title_duration.groupby('Date')['Duration'].idxmax()]
    max_duration_info = max_duration_info[['Date', 'Title', 'Duration']]
    max_duration_info.rename(columns={'Title': 'Title with Longest Duration', 'Duration': 'Duration of Longest Title'}, inplace=True)

    # Step 3: Merge the title with the longest duration with the dataframe_days
    dataframe_days = dataframe_days.merge(max_duration_info, on='Date')

    # Extract the date from the Begin column
    dataframe_awt['Date'] = dataframe_awt['Begin'].dt.date

    # Step 1: Pivot the data to get total duration spent in each App for each day
    pivot_table_duration = dataframe_awt.pivot_table(index='Date', columns='App', values='Duration', aggfunc='sum', fill_value=0)

    # Add prefix to each of the app duration columns
    pivot_table_duration = pivot_table_duration.add_prefix('Time in ')

    # Step 2: Pivot the data to get the count of occurrences for each App for each day
    pivot_table_count = dataframe_awt.pivot_table(index='Date', columns='App', values='Duration', aggfunc='count', fill_value=0)

    # Add prefix to each of the app count columns
    pivot_table_count = pivot_table_count.add_prefix('Count of ')

    # Step 3: Merge both pivot tables with dataframe_days
    pivot_table_duration = pivot_table_duration.reset_index()
    pivot_table_count = pivot_table_count.reset_index()

    dataframe_days = dataframe_days.merge(pivot_table_duration, on='Date', how='left')
    dataframe_days = dataframe_days.merge(pivot_table_count, on='Date', how='left')

    # Ensure that Begin and End are datetime columns in dataframe_merged_awt
    dataframe_merged_awt['Begin'] = pd.to_datetime(dataframe_merged_awt['Begin'], format='%Y-%m-%d %H:%M:%S')
    dataframe_merged_awt['End'] = pd.to_datetime(dataframe_merged_awt['End'], format='%Y-%m-%d %H:%M:%S')

    # Calculate the duration (End - Begin) in seconds
    dataframe_merged_awt['Duration'] = (dataframe_merged_awt['End'] - dataframe_merged_awt['Begin']).dt.total_seconds()

    # Extract the date from the Begin column
    dataframe_merged_awt['Date'] = dataframe_merged_awt['Begin'].dt.date

    # Step 1: Calculate the midpoint of each work slot
    dataframe_merged_awt['Midpoint'] = dataframe_merged_awt['Begin'] + (dataframe_merged_awt['End'] - dataframe_merged_awt['Begin']) / 2

    # Step 2: Convert the midpoint to a decimal representation of the time of day (hours since midnight)
    dataframe_merged_awt['Midpoint_Hours'] = dataframe_merged_awt['Midpoint'].dt.hour + dataframe_merged_awt['Midpoint'].dt.minute / 60

    # Step 3: Calculate the median of these midpoints for each day
    median_time_of_day = dataframe_merged_awt.groupby('Date')['Midpoint_Hours'].median().reset_index(name='Median Time of Day')

    # Step 4: Merge this metric into the existing dataframe_days
    dataframe_days = dataframe_days.merge(median_time_of_day, on='Date', how='left')

    # Calculate total number of work slots per day
    work_slots_count = dataframe_merged_awt.groupby('Date').size().reset_index(name='Total Work Slots')

    # Calculate average duration of work slots per day
    average_duration = dataframe_merged_awt.groupby('Date')['Duration'].mean().reset_index(name='Average Work Slot Duration')

    # Merge these calculations with the existing dataframe_days
    dataframe_days = dataframe_days.merge(work_slots_count, on='Date', how='left')
    dataframe_days = dataframe_days.merge(average_duration, on='Date', how='left')

    # Sort dataframe by Date and Begin time
    dataframe_merged_awt = dataframe_merged_awt.sort_values(by=['Date', 'Begin'])

    # Calculate the end time of the previous work slot for each row
    dataframe_merged_awt['Previous End'] = dataframe_merged_awt.groupby('Date')['End'].shift(1)

    # Calculate the break duration (in seconds) as the difference between the current slot's start and the previous slot's end
    dataframe_merged_awt['Break Duration'] = (dataframe_merged_awt['Begin'] - dataframe_merged_awt['Previous End']).dt.total_seconds()

    # Consider only positive break durations (where there actually is a break)
    valid_breaks = dataframe_merged_awt[dataframe_merged_awt['Break Duration'] > 0]

    # Calculate the number of breaks per day
    breaks_count = valid_breaks.groupby('Date').size().reset_index(name='Total Breaks')

    # Calculate the average duration of breaks per day
    average_break_duration = valid_breaks.groupby('Date')['Break Duration'].mean().reset_index(name='Average Break Duration')

    # Merge these break calculations with the existing dataframe_days
    dataframe_days = dataframe_days.merge(breaks_count, on='Date', how='left')
    dataframe_days = dataframe_days.merge(average_break_duration, on='Date', how='left')

    dataframe_days['Relative break time'] = dataframe_days['Average Break Duration'] / (dataframe_days['Duration'])

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

    dataframe_days['Date'] = pd.to_datetime(dataframe_days['Date'], format='%d-%m-%Y').dt.strftime('%Y-%m-%d')

    # Merge the dataframes on the 'Date' column
    merged_dataframe = dataframe_days.merge(dataframe_survey, on='Date', how='left')

    # Drop days where no survey was filled in
    merged_dataframe = merged_dataframe.dropna(subset=['Productivity'])

    # Automatically select only numeric columns
    numeric_columns = merged_dataframe.select_dtypes(include='number').columns

    # Generalized function to calculate Pearson correlation, t-statistic, and significance
    def calculate_significance(data, numeric_columns, target_columns):
        results = []
        n = len(data)  # Sample size
        
        for target in target_columns:
            for col in numeric_columns:
                if col != target:
                    # Calculate Pearson correlation between the target variable and the other column
                    r = data[target].corr(data[col])
                    
                    # Calculate t-statistic
                    if abs(r) < 1.0:
                        t_stat = r * np.sqrt((n - 2) / (1 - r**2))
                    else:
                        t_stat = float('inf')  # Handle perfect correlations
                    
                    # Approximate p-value significance
                    significance = 'High' if abs(t_stat) > 2 else 'Low'
                    
                    results.append({
                        'Variable': col,
                        f'Correlation with {target}': r,
                        f'T-Statistic with {target}': t_stat,
                        f'Significance with {target}': significance
                    })
        
        return pd.DataFrame(results)

    # Specify the target columns
    target_columns = ['Productivity', 'Absorption', 'Vigor', 'Dedication']

    # Calculate correlation and significance with each target column
    productivity_results = calculate_significance(merged_dataframe, numeric_columns, target_columns)

    # Merge results into one dataframe
    productivity_results = productivity_results.groupby('Variable', as_index=False).first()

    st.write('Let\'s see how your scores correlate with your AWT data. We\'ll first explore the 6 productivity types below and see the extent to which you align with each of them.')

    st.divider()

    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["🐶 Social scientist", "🐺 Lone scientist", 
                                                  "🐱 Focused scientist", "🐨 Balanced scientist", "🐯 Leading scientist", 
                                                  "🐘 Goal-oriented scientist"])
    data = np.random.randn(10, 1)

    with tab1:
        st.subheader("Description")
        st.write("*Feels productive when helping coworkers, collaborating and doing code reviews [providing feedback]. To get things done, they come early to work or work late and try to focus on a single task*")

        st.subheader("Scores")
        # Variables to check
        variables_to_check = [
            'Time in Microsoft Teams',
            'Start Time (Decimal)',
            'End Time (Decimal)',
            'Share of Unique Titles',
            'Total Time Spent (hours)',
            'Time in Microsoft Word',
            'Duration of Longest Title'
        ]

        # Filter the dataframe for the selected variables
        filtered_data = productivity_results[productivity_results['Variable'].isin(variables_to_check)]

        # Display results for each variable
        for _, row in filtered_data.iterrows():
            variable = row['Variable']
            correlation_value = row['Correlation with Productivity']

            if variable == 'Time in Microsoft Teams':
                # Display correlation with productivity
                if correlation_value > 0.1:
                    st.markdown(f'✅ **More time spent in Teams (helping coworkers, collaborating) feels more productive**: {correlation_value:f}')
                else:
                    st.markdown(f'❌ **More time spent in Teams (helping coworkers, collaborating) feels more productive**: {correlation_value:f}')

            elif variable == 'Start Time (Decimal)':
                # Check the value and display results
                if correlation_value < -0.1:
                    st.markdown(f'✅ **Starting earlier feels more productive**: {correlation_value:f} ')
                else:
                    st.markdown(f'❌ **Starting earlier feels more productive**: {correlation_value:f} ')

            elif variable == 'End Time (Decimal)':
                # Check the value and display results
                if correlation_value > 0.1:
                    st.markdown(f'✅ **Ending later feels more productive**: {correlation_value:f} ')
                else:
                    st.markdown(f'❌ **Ending later feels more productive**: {correlation_value:f} ')

            #elif variable == 'Share of Unique Titles':
                # Check the value and display results
            #    if correlation_value < -0.1:
            #        st.markdown(f'✅ **Less variety in tasks feels more productive**: {correlation_value:f} ')
            #    else:
            #        st.markdown(f'❌ **Less variety in tasks feels more productive**: {correlation_value:f}')

            #elif variable == 'Total Time Spent (hours)':
                # Check the value and display results
            #    if correlation_value > 0.1:
            #        st.markdown(f'✅ **More time spent on computer feels more productive**: {correlation_value:f} ')
            #    else:
            #        st.markdown(f'❌ **More time spent on computer feels more productive**: {correlation_value:f}')

            #elif variable == 'Time in Microsoft Word':
                # Check the value and display results
            #    if correlation_value > 0.1:
            #        st.markdown(f'✅ **More time spent in Word feels more productive**: {correlation_value:f} ')
            #    else:
            #        st.markdown(f'❌ **More time spent in Word feels more productive**: {correlation_value:f}')

            elif variable == 'Duration of Longest Title':
                # Check the value and display results
                if correlation_value > 0.1:
                    st.markdown(f'✅ **Spending a long time on one task feels more productive**: {correlation_value:f} ')
                else:
                    st.markdown(f'❌ **Spending a long time on one task feels more productive**: {correlation_value:f}')


        if filtered_data.empty:
            st.write('No data available for the selected variables.')

        st.subheader("Job crafting")
        st.write("If you tick a lot of boxes here, you might consider seeking more interactions, e.g., by going to the office to work, or scheduling office hours for your daily chats.")

    with tab2: 
        st.subheader("Description")
        st.write("*Avoids disruptions such as noise, email, meetings, and code reviews [feedback sessions]. They feel most productive when they have little to no social interactions and when they can work on solving problems, fixing bugs or coding features [writing] in quiet and without interruptions. To reflect about work, they are mostly interested in knowing the frequency and duration of interruptions they encountered.*")

        st.subheader("Scores")
        # Variables to check
        variables_to_check = [
            'Count of Microsoft Teams',
            'Count of Microsoft Outlook',
            'Average Work Slot Duration_x',
            'Total Time Spent (hours)',
            'Time in Microsoft Word',
            'Average Break Duration',
            'Total Breaks'
        ]

        # Filter the dataframe for the selected variables
        filtered_data = productivity_results[productivity_results['Variable'].isin(variables_to_check)]

        # Display results for each variable
        for _, row in filtered_data.iterrows():
            variable = row['Variable']
            correlation_value = row['Correlation with Productivity']

            if variable == 'Count of Microsoft Teams':
                # Display correlation with productivity
                if correlation_value < -0.1:
                    st.markdown(f'✅ **Less times opening Teams feels more productive**: {correlation_value:f}')
                else:
                    st.markdown(f'❌ **Less times opening Teams feels more productive**: {correlation_value:f}')

            elif variable == 'Count of Microsoft Outlook':
                # Check the value and display results
                if correlation_value < -0.1:
                    st.markdown(f'✅ **Less times opening Outlook feels more productive**: {correlation_value:f}')
                else:
                    st.markdown(f'❌ **Less times opening Outlook feels more productive**: {correlation_value:f}')

            elif variable == 'Average Work Slot Duration_x':
                # Check the value and display results
                if correlation_value > 0.1:
                    st.markdown(f'✅ **Longer work slots feel more productive**: {correlation_value:f} ')
                else:
                    st.markdown(f'❌ **Longer work slots feel more productive**: {correlation_value:f}')

            elif variable == 'Total Time Spent (hours)':
                # Check the value and display results
                if correlation_value > 0.1:
                    st.markdown(f'✅ **More time spent on computer feels more productive**: {correlation_value:f} ')
                else:
                    st.markdown(f'❌ **More time spent on computer feels more productive**: {correlation_value:f}')

            elif variable == 'Average Break Duration':
                # Check the value and display results
                if correlation_value < -0.1:
                    st.markdown(f'✅ **Longer breaks feel less productive**: {correlation_value:f} ')
                else:
                    st.markdown(f'❌ **Longer breaks feel less productive**: {correlation_value:f}')

            elif variable == 'Total Breaks':
                # Check the value and display results
                if correlation_value < -0.1:
                    st.markdown(f'✅ **More breaks feel less productive**: {correlation_value:f} ')
                else:
                    st.markdown(f'❌ **More breaks feel less productive**: {correlation_value:f}')

        if filtered_data.empty:
            st.write('No data available for the selected variables.')

        st.subheader("Job crafting")
        st.write("If you tick a lot of boxes here, you might consider tuning down possible interruptions, i.e., by blocking messages and finding quiet working spaces.")

    with tab3: 
        st.subheader("Description")
        st.write("*Feels most productive when they are working efficiently and concentrated on a single task at a time. They are feeling unproductive when they are wasting time and spend too much time on a task, because they are stuck or working slowly. They are interested in knowing the number of interruptions and focused time.*")
    
        st.subheader("Scores")
        # Variables to check
        variables_to_check = [
            'Share of Work Slots with Most Frequent Title',
            'Title count per hour on computer',
            'Average Work Slot Duration_x',
            'Duration of Longest Title',
            'Total Breaks'
        ]

        # Filter the dataframe for the selected variables
        filtered_data = productivity_results[productivity_results['Variable'].isin(variables_to_check)]

        # Display results for each variable
        for _, row in filtered_data.iterrows():
            variable = row['Variable']
            correlation_value = row['Correlation with Productivity']

            if variable == 'Share of Work Slots with Most Frequent Title':
                # Display correlation with productivity
                if correlation_value < -0.1:
                    st.markdown(f'✅ **More work slots spent on the same task feels unproductive**: {correlation_value:f} ')
                else:
                    st.markdown(f'❌ **More work slots spent on the same task feels unproductive**: {correlation_value:f} ')

            elif variable == 'Title count per hour on computer':
                # Check the value and display results
                if correlation_value < -0.1:
                    st.markdown(f'✅ **Less switching between tasks feels more productive**: {correlation_value:f} ')
                else:
                    st.markdown(f'❌ **Less switching between tasks feels more productive**: {correlation_value:f}')

            elif variable == 'Average Work Slot Duration_x':
                # Check the value and display results
                if correlation_value > 0.1:
                    st.markdown(f'✅ **Longer work slots feel more productive**: {correlation_value:f} ')
                else:
                    st.markdown(f'❌ **Longer work slots feel more productive**: {correlation_value:f}')

            elif variable == 'Duration of Longest Title':
                # Check the value and display results
                if correlation_value < -0.1:
                    st.markdown(f'✅ **Long work on a single task feels unproductive**: {correlation_value:f} ')
                else:
                    st.markdown(f'❌ **Long work on a single task feels unproductive**: {correlation_value:f}')

            elif variable == 'Total Breaks':
                # Check the value and display results
                if correlation_value < -0.1:
                    st.markdown(f'✅ **More breaks feel less productive**: {correlation_value:f} ')
                else:
                    st.markdown(f'❌ **More breaks feel less productive**: {correlation_value:f}')
        
        if filtered_data.empty:
            st.write('No data available for the selected variables.')

        st.subheader("Job crafting")
        st.write("If you tick a lot of boxes here, you might consider blocking time for particular tasks, which you have to finish before moving on to the next. Finding a quiet office space might help.")
        
    with tab4: 
        st.subheader("Description")
        st.write("*Is less affected by disruptions. They are less likely to come early to work or work late. They are feeling unproductive, when tasks are unclear or irrelevant, they are unfamiliar with a task, or when tasks are causing overhead.*")

        st.subheader("Scores")
        # Variables to check
        variables_to_check = [
            'Start Time (Decimal)',
            'Total Breaks',
            'End Time (Decimal)',
            'Average Work Slot Duration_x',
            'Time in Microsoft Teams',
            'Time in Microsoft Outlook'
        ]

        # Filter the dataframe for the selected variables
        filtered_data = productivity_results[productivity_results['Variable'].isin(variables_to_check)]

        # Display results for each variable
        for _, row in filtered_data.iterrows():
            variable = row['Variable']
            correlation_value = row['Correlation with Productivity']

            if variable == 'Start Time (Decimal)': 
                # Check the value and display results
                if correlation_value > -0.1:
                    st.markdown(f'✅ **Starting earlier does not increase the feeling of productivity**: {correlation_value:f}')
                else:
                    st.markdown(f'❌ **Starting earlier does not increase the feeling of productivity**: {correlation_value:f}')

            elif variable == 'Total Breaks':
                # Check the value and display results
                if correlation_value > -0.1:
                    st.markdown(f'✅ **More breaks do not decrease the feeling of productivity**: {correlation_value:f} ')
                else:
                    st.markdown(f'❌ **More breaks do not decrease the feeling of productivity**: {correlation_value:f}')

            elif variable == 'End Time (Decimal)':
                # Check the value and display results
                if correlation_value < 0.1:
                    st.markdown(f'✅ **Ending later does not increase the feeling of productivity**: {correlation_value:f}')
                else:
                    st.markdown(f'❌ **Ending later does not increase the feeling of productivity**: {correlation_value:f}')

            #elif variable == 'Average Work Slot Duration_x':
                # Check the value and display results
            #    if correlation_value < 0.1:
            #        st.markdown(f'✅ **Length of work slots does not affect the feeling of productivity**: {correlation_value:f} ')
            #    else:
            #        st.markdown(f'❌ **Length of work slots does not affect the feeling of productivity**: {correlation_value:f} ')

            elif variable == 'Time in Microsoft Outlook':
                # Check the value and display results
                if correlation_value < -0.1:
                    st.markdown(f'✅ **Less time spent in Outlook feels more productive**: {correlation_value:f}')
                else:
                    st.markdown(f'❌ **Less time spent in Outlook feels more productive**: {correlation_value:f}')

            elif variable == 'Time in Microsoft Teams':
                # Check the value and display results
                if correlation_value < -0.1:
                    st.markdown(f'✅ **Less time spent in Teams feels more productive**: {correlation_value:f}')
                else:
                    st.markdown(f'❌ **Less time spent in Teams feels more productive**: {correlation_value:f}')

        if filtered_data.empty:
            st.write('No data available for the selected variables.')

        st.subheader("Job crafting")
        st.write("If you tick a lot of boxes here, you might consider varying your daily tasks and taking sufficient breaks to avoid boredom and tiredness.")

    with tab5: 
        st.subheader("Description")
        st.write("*Is more comfortable with meetings and emails and feel less productive with coding [writing] activities than other developers [scientists]. They feel more productive in the afternoon and when they can write and design things. They don’t like broken builds and blocking tasks [?], preventing them (or the team) from doing productive work.*")

        st.subheader("Scores")
        # Variables to check
        variables_to_check = [
            'Time in Microsoft Teams',
            'Time in Microsoft Outlook',
            'Average Work Slot Duration_x',
            'Total Time Spent (hours)',
            'Median Time of Day'
        ]

        # Filter the dataframe for the selected variables
        filtered_data = productivity_results[productivity_results['Variable'].isin(variables_to_check)]

        # Display results for each variable
        for _, row in filtered_data.iterrows():
            variable = row['Variable']
            correlation_value = row['Correlation with Productivity']

            if variable == 'Time in Microsoft Teams':
                # Display correlation with productivity
                if correlation_value > -0.1:
                    st.markdown(f'✅ **More time spent in Teams does not decrease the feeling of productivity**: {correlation_value:f}')
                else:
                    st.markdown(f'❌ **More time spent in Teams does not decrease the feeling of productivity**: {correlation_value:f}')

            elif variable == 'Time in Microsoft Outlook':
                # Check the value and display results
                if correlation_value > -0.1:
                    st.markdown(f'✅ **More time spent in Outlook does not decrease the feeling of productivity**: {correlation_value:f}')
                else:
                    st.markdown(f'❌ **More time spent in Outlook does not decrease the feeling of productivity**: {correlation_value:f}')

            #elif variable == 'Average Work Slot Duration_x':
                # Check the value and display results
            #    if correlation_value < -0.1:
            #        st.markdown(f'✅ **Shorter work slots do not affect the feeling of productivity**: {correlation_value:f}')
            #    else:
            #        st.markdown(f'❌ **Shorter work slots do not affect the feeling of productivity**: {correlation_value:f}')

            #elif variable == 'Total Time Spent (hours)':
                # Check the value and display results
            #    if correlation_value < -0.1:
            #        st.markdown(f'✅ **More time spent away from computer feels more productive**: {correlation_value:f} ')
            #    else:
            #        st.markdown(f'❌ **More time spent away from computer feels more productive**: {correlation_value:f}')

            elif variable == 'Median Time of Day':
                # Check the value and display results
                if correlation_value > 0.1:
                    st.markdown(f'✅ **Working later in the day mostly, feels more productive**: {correlation_value:f}')
                else:
                    st.markdown(f'❌ **Working later in the day mostly, feels more productive**: {correlation_value:f}')

        if filtered_data.empty:
            st.write('No data available for the selected variables.')

        st.subheader("Job crafting")
        st.write("If you tick a lot of boxes here, you might consider mostly scheduling meetings in the morning, with sufficient time in between, and block time for creation in the afternoons.")

    with tab6: 
        st.subheader("Description")
        st.write("*Feels productive when they complete or make progress on tasks. They feel less productive when they multi-task, are goal-less or are stuck. They are more open to meetings and emails compared to the other clusters, in case they help them achieve their goals.*")
    
        st.subheader("Scores")
        # Variables to check
        variables_to_check = [
            'Title count per hour on computer',
            'Average Work Slot Duration_x',
            'Time in Microsoft Teams',
            'Time in Microsoft Outlook'
        ]

        # Filter the dataframe for the selected variables
        filtered_data = productivity_results[productivity_results['Variable'].isin(variables_to_check)]

        # Display results for each variable
        for _, row in filtered_data.iterrows():
            variable = row['Variable']
            correlation_value = row['Correlation with Productivity']

            if variable == 'Title count per hour on computer':
                # Display correlation with productivity
                if correlation_value < -0.1:
                    st.markdown(f'✅ **Less switching between tasks feels more productive**: {correlation_value:f} ')
                else:
                    st.markdown(f'❌ **Less switching between tasks feels more productive**: {correlation_value:f} ')

            elif variable == 'Time in Microsoft Teams':
                # Display correlation with productivity
                if correlation_value > -0.1:
                    st.markdown(f'✅ **More time spent in Teams (meetings) does not decrease the feeling of productivity**: {correlation_value:f}')
                else:
                    st.markdown(f'❌ **More time spent in Teams (meetings) does not decrease the feeling of productivity**: {correlation_value:f}')

            elif variable == 'Time in Microsoft Outlook':
                # Display correlation with productivity
                if correlation_value > -0.1:
                    st.markdown(f'✅ **More time spent in Outlook (emails) does not decrease the feeling of productivity**: {correlation_value:f}')
                else:
                    st.markdown(f'❌ **More time spent in Outlook (emails) does not decrease the feeling of productivity**: {correlation_value:f}')

            elif variable == 'Average Work Slot Duration_x':
                # Check the value and display results
                if correlation_value > 0.1:
                    st.markdown(f'✅ **Longer work slots feel more productive**: {correlation_value:f} ')
                else:
                    st.markdown(f'❌ **Longer work slots feel more productive**: {correlation_value:f}')

        if filtered_data.empty:
            st.write('No data available for the selected variables.')

        st.subheader("Job crafting")
        st.write("If you tick a lot of boxes here, you might consider turning down or re-scheduling meetings without a clear goal, or steering the meeting towards a goal yourself.")

    st.divider()

    with st.expander('AWT variable descriptions'):
        st.markdown(
            """
            **General**
            - Start time: first time a window was active
            - End time: last time a window was active
            - Total time spent: sum of all time spent in windows
            - Median time of day: midpoint of all the work that took place in terms of the time of day

            **Work slots**
            - Total work slots: count of all slots with consecutive titles
            - Average work slot duration: average duration of work slots (see total work slots)
            - Share of work slots with most frequent title

            **Apps**
            - Count of [App]: number of times a title corresponding with this app was active
            - Time in [App]: total time a title corresponding with this app was active

            **Titles**
            - Title count: total count of windows per day
            - Unique titles: total number of unique titles per day
            - Longest duration of title: duration of title in which most time was spent 
            - Share of unique titles: unique titles divided by total number of windows
            - Title count per hour on computer: number of titles relative to the total time spent on the computer

            **Breaks**
            - Total breaks: count of all breaks between work slots
            - Average break duration: average duration of breaks (see total breaks)
            - Relative break time: duration of breaks relative to the total time spent on the computer
            """
            )

    with st.expander("Detailed data"):
        st.write("Data per day")
        merged_dataframe

        st.write("Correlations")
        productivity_results

        # Filter for strong correlations (>= 0.4) and high significance
        filtered_results = productivity_results[
            ((productivity_results['Correlation with Productivity'] >= 0.2) | 
            (productivity_results['Correlation with Productivity'] <= -0.2)) & 
            (productivity_results['Significance with Productivity'] == 'High')
        ]
        # filtered_results

        # Function to create scatterplots for significant correlations
        def create_scatterplots(data, filtered_results):
            charts = []
            
            for _, row in filtered_results.iterrows():
                variable = row['Variable']
                
                # Create scatterplot
                scatterplot = alt.Chart(data).mark_point().encode(
                    x=alt.X('Productivity:Q', title='Productivity'),
                    y=alt.Y(f'{variable}:Q', title=variable),
                    tooltip=['Productivity', variable]
                ).properties(
                    title=f'Scatterplot of Productivity vs {variable}'
                )
                
                charts.append(scatterplot)
            
            return alt.vconcat(*charts)

        # Generate scatterplots
        scatterplots = create_scatterplots(merged_dataframe, filtered_results)

        # Function to create box plots for significant correlations
        def create_box_plots(data, filtered_results):
            charts = []
            
            for _, row in filtered_results.iterrows():
                variable = row['Variable']
                
                # Create box plot
                box_plot = alt.Chart(data).mark_boxplot().encode(
                    x=alt.X('Productivity:O', title='Productivity'),
                    y=alt.Y(f'{variable}:Q', title=variable),
                    tooltip=['Productivity', variable]
                ).properties(
                    title=f'Box Plot of {variable} by Productivity'
                )
                
                charts.append(box_plot)
            
            return alt.vconcat(*charts)

        # Generate box plots
        box_plots = create_box_plots(merged_dataframe, filtered_results)

        # Display box plots in Streamlit
        st.altair_chart(box_plots, use_container_width=True)

        # Step 1: Define the columns and rows of interest
        columns_of_interest = ['Absorption', 'Dedication', 'Productivity', 'Vigor']
        rows_of_interest = [
            'Start Time (Decimal)', 'End Time (Decimal)', 'Total Time Spent (hours)',
            'Median Time of Day',
            'Total Work Slots_x', 'Average Work Slot Duration_x',
            'Share of Work Slots with Most Frequent Title', 
            'Time in Google Chrome', 'Time in Microsoft Outlook', 'Time in Adobe Acrobat ', 
            'Time in Microsoft Excel', 
            'Time in Microsoft Word', 'Count of Google Chrome', 'Count of Microsoft Outlook', 
            'Count of Adobe Acrobat ', 'Count of Microsoft Excel', 
            'Count of Microsoft Word', 'Title_count', 'Unique Titles',
            'Duration of Longest Title', 'Share of Unique Titles',
            'Title count per hour on computer', 'Total Breaks',
            'Average Break Duration', 'Relative break time'
        ]

        # Step 2: Extract the subset of data
        subset_data = merged_dataframe[columns_of_interest + rows_of_interest]

        # Step 3: Calculate the correlation matrix
        correlation_matrix = subset_data.corr().loc[rows_of_interest, columns_of_interest]

        correlation_matrix

        # Step 4: Convert the correlation matrix into a long format for Altair
        correlation_df = correlation_matrix.reset_index().melt(id_vars='index', var_name='Column', value_name='Correlation')
        correlation_df = correlation_df.rename(columns={'index': 'Row'})

        # Step 5: Create a heatmap using Altair
        heatmap = alt.Chart(correlation_df).mark_rect().encode(
            x=alt.X('Column:O', title=''),
            y=alt.Y('Row:O', title='', sort=rows_of_interest, axis=alt.Axis(labelPadding=10)),
            color=alt.Color('Correlation:Q', scale=alt.Scale(scheme='redblue', domain=[-1, 1])),
            tooltip=['Row', 'Column', 'Correlation']
        ).properties(
            width=100,
            height=800,
            title='Correlation Matrix of Selected Features'
        )

        # Add text to the heatmap to display correlation values
        text = heatmap.mark_text(baseline='middle').encode(
            text=alt.Text('Correlation:Q', format=".2f"),
            color=alt.condition(
                alt.datum.Correlation > 0.5, 
                alt.value('white'),  # High positive correlations will have black text
                alt.value('black')   # Low or negative correlations will have white text
            )
        )

        # Display the heatmap with the text overlay in Streamlit
        st.altair_chart(heatmap + text, use_container_width=True)