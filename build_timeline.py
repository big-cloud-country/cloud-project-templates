import pandas as pd
import datetime
import json
import sys
import webbrowser
import os
from dateutil.parser import parse

DAY_RATE = 1500

#consume the csv
filename = sys.argv[1]
chart_html_page = 'timeline.html'
df = pd.read_csv(filename)

units = df['units'][0]

def days_to_milliseconds(days):
    return days * 24 * 60 * 60 * 1000

def weeks_to_milliseconds(weeks):
    return 7 * days_to_milliseconds(weeks)

def duration_to_milliseconds(duration):
    if units == 'days':
        return days_to_milliseconds(duration)
    if units == 'weeks':
        return weeks_to_milliseconds(duration)

def date_by_adding_business_days(from_date, add_days):
    business_days_to_add = add_days
    current_date = from_date
    while business_days_to_add > 0:
        current_date += datetime.timedelta(days=1)
        weekday = current_date.weekday()
        if weekday >= 5: # sunday = 6
            continue
        business_days_to_add -= 1
    return current_date

def calculate_relative_start_date(dt, duration, partial_start_percentage):
    offset = round(duration * (partial_start_percentage/100))
    if units == 'days':
        relative_start_date = date_by_adding_business_days(dt, offset)
        return relative_start_date
    if units == 'weeks':
        return dt + datetime.timedelta(weeks=offset)

def calculate_person_days(df):
    #for each task
    person_days = 0
    for index, row in df.iterrows():
        persons = 1 if pd.isna(row['resource']) else len(row['resource'].split(','))
        days = int(row['duration']) if units == 'days' else 5 * int(row['duration'])
        person_days += persons * days

    return person_days

def calculate_durations(data, start_date):
    end_dates = [d['end_date_dt'] for d in data]
    project_close_date = max(end_dates)
    project_days = (project_close_date - start_date).days
    project_weeks = round((project_days/5),1)
    return {
        'project_days': project_days,
        'project_weeks': project_weeks
    }


project_start_date = parse(df['start_date'][0])
df['start_date'] = project_start_date
#
# start_date_js = 'var startMonth = ' + str(start_date.month - 1) + ';\n'
# start_date_js += 'var startDay = ' + str(start_date.day) + ';\n'
# start_date_js += 'var startYear = ' + str(start_date.year) + ';\n'

data = []

#set all task start dates to the earliest start date

for index, row in df.iterrows():

    #figure out dependencies
    #dependencies = array
    raw_dependencies = str(row['dependencies']).split(',') #split the set of dependencies into an array
    dependency_durations = []
    #for each dependency in array
    dependencies = []
    partial_starts = []

    for raw in raw_dependencies:
        x = raw.split('%')
        dependencies.append(x[0])
        try:
            partial_starts.append(int(x[1]))
        except:
            partial_starts.append(100)

    for idx, dependency_id in enumerate(dependencies):

        #for each other row
        for other_index, other_row in df.iterrows():
            #if it's not the same row
            if other_index != index:
                #if dependency is in other_row(id)
                if dependency_id == str(other_row['id']):
                    #add the dependency duration to an array
                    relative_start_date = calculate_relative_start_date(other_row['start_date'], other_row['duration'],partial_starts[idx])

                    dependency_durations.append(relative_start_date)

        #find the max of the array - this is the earliest it can start (the latest completion of any dependency)
        if dependency_durations: #only if there are values in this array
            earliest_start_date = max(dependency_durations)
            df.at[index, 'start_date'] = earliest_start_date

for index, row in df.iterrows():

    item_id = str(row['id'])
    item_focus_area = row['focus_area']
    item_phase = row['phase'] if not pd.isna(row['phase']) else ''
    item_task = row['task'] if not pd.isna(row['task']) else ''
    item_description = row['description'] if not pd.isna(row['description']) else ''
    item_start_date = {
        'year': row['start_date'].year,
        'month': row['start_date'].month,
        'day': row['start_date'].day
    }
    end_date = calculate_relative_start_date(row['start_date'], row['duration'], 100)
    item_end_date = {
        'year': end_date.year,
        'month': end_date.month,
        'day': end_date.day
    }
    if pd.isna(row['duration']):
        item_duration = 0
    else:
        item_duration = duration_to_milliseconds(row['duration']) #duration

    item_resource = row['resource'] if not pd.isna(row['resource']) else ''

    # if pd.isna(row['start_date']):
    #     item.append(None) #start_date
    # else:
    #     dt = row['start_date']
    #     milliseconds = dt.timestamp() * 1000
    #     #item.append(milliseconds) #start_date
    #     #item.append(str(parse(row['start_date'])))
    #     #item.append('new Date(' + str(dt.year) + ',' + str(dt.month) + ',' + str(dt.day) + ')')
    #     item.append(None)

    #item.append(str(row['id']))
    #item.append(row['focus'])
    #item.append(row['phase'])


    if pd.isna(row['dependencies']):
        item_dependencies = None
    else:
        item_dependencies = str(row['dependencies']) #dependencies

    data.append({
        'id': item_id,
        'focus_area': item_focus_area,
        'phase': item_phase,
        'task': item_task,
        'description': item_description,
        'duration': item_duration,
        'resource': item_resource,
        'dependencies': item_dependencies,
        'start_date': item_start_date,
        'end_date': item_end_date,
        'end_date_dt': end_date,
    })

#also add in units, start_date, and project name, project manager, project owner

person_days = calculate_person_days(df)
project_cost = person_days * DAY_RATE

durations = calculate_durations(data, project_start_date)
monthly_cost = round(project_cost / (durations['project_weeks'] / 4))

#get rid of the end date
cleaned_data = []
for d in data:
    del d['end_date_dt']
    cleaned_data.append(d)

metadata = {
    'project_name': df['project_name'][0] if not pd.isna(df['project_name'][0]) else '',
    'project_owner': df['project_owner'][0] if not pd.isna(df['project_owner'][0]) else '',
    'project_manager': df['project_manager'][0] if not pd.isna(df['project_manager'][0]) else '',
    'units': df['units'][0],
    'start_date': {
        'year': project_start_date.year,
        'month': project_start_date.month,
        'day': project_start_date.day,
    },
    'person_days': person_days,
    'project_days': durations['project_days'],
    'project_weeks': durations['project_weeks'],
    'project_cost': project_cost,
    'monthly_cost': monthly_cost
}

metadata_js = 'var metadata = ' + json.dumps(metadata)

#paste it as a js file with variable var data=
file_contents = 'var data = ' + json.dumps(cleaned_data) + ';\n'
file_contents = file_contents + metadata_js

#write to file data.js
text_file = open("input.js", "w")
n = text_file.write(file_contents)
text_file.close()

#open the chart in a new tab
webbrowser.open('file://' + os.path.realpath(chart_html_page))