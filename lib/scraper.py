import urllib.request, json, datetime, re
import pandas as pd
import numpy as np

from bs4 import BeautifulSoup

def get_tables():
    #We use the Radio-Canada API to get the Quebec-wide and region-specific data on confirmed cases, deaths, and recovered cases.
    #The data is in JSON format.
    url = r'https://kustom.radio-canada.ca/coronavirus/canada_quebec'
    with urllib.request.urlopen(url) as page:
        qc_data = json.load(page)[0]

    #First, the table for all of Quebec.
    tables = {}
    tables[qc_data['Name']] = pd.DataFrame(qc_data['History'])
    tables[qc_data['Name']]['Date'] = tables[qc_data['Name']]['Date'].map(lambda x: datetime.datetime.strptime(x, '%Y-%m-%d').date())
    tables[qc_data['Name']] = tables[qc_data['Name']].set_index('Date').astype('float')

    #Then do the region-specific tables using their Api address from the Quebec-wide file.
    for region in qc_data['Regions']:
        with urllib.request.urlopen(region['Api']) as page:
            region_data = json.load(page)[0]
            tables[region_data['Name']] = pd.DataFrame(region_data['History'])
            tables[region_data['Name']]['Date'] = tables[region_data['Name']]['Date'].map(lambda x: datetime.datetime.strptime(x, '%Y-%m-%d').date())
            tables[region_data['Name']] = tables[region_data['Name']].set_index('Date').astype('float')

    #Use data on Wikipedia for tests, and active cases by gravity.
    #The data that interests us is contained in table "COVID-19 cases in Quebec by health region" on the Wikipedia page with the url below.
    #We pull the HTML page parse it with BeautifulSoup, and find the table.
    url = r'https://en.wikipedia.org/wiki/2020_coronavirus_pandemic_in_Quebec'
    with urllib.request.urlopen(url) as page:
        soup = BeautifulSoup(page, features='lxml')
        table = soup.find('table',{'class':'wikitable','style':'margin-left:15px; text-align:center'})

    #The useful data for us starts on the 4th row and end 3 rows before the end of the table. So we can remove the superfluous rows.
    #We also reverse the order to match the Radio-Canada format
    rows = table.findAll('tr')[3:-3]
    rows.reverse()

    #We are looking for the contents of the rows under two headers: "Active" and "Tests".
    #The content is contained in rows below those headers, under <th> tags. So we can skip all the <tr> tags.
    #The dates are in the first <th>

    #The Active data is contained in the 4th ('Mild'), 5th ('Hospitalized') and 6th ('ICU') <th> tags on each row.
    #The Tests data is contained in the 11th ('Negative') and 12th ('Pending') <th> tags on each row.
    active = []
    tests = []
    #Helper function to extract integer from cell
    def th_to_int (th):
        val = re.sub('\n','',th.getText())
        val = int(val) if val else None
        return val

    for tr in rows:
        ths = tr.findAll('th')
        #Find the date and convert to datetime format.
        date = datetime.datetime.strptime(ths[0].abbr['title'].lower(), '%B %d, %Y').date()
        #Find the cell value for the three severity categories and two tests categories.
        mild, hospitalized, icu = th_to_int(ths[3]), th_to_int(ths[4]), th_to_int(ths[5])
        negative, pending = th_to_int(ths[10]), th_to_int(ths[11])

        active.append({'Date':date,'Mild':mild,'Hospitalized':hospitalized,'ICU':icu})
        tests.append({'Date':date,'Negative':negative,'Pending':pending})

    tables['Active'] = pd.DataFrame(active).set_index('Date').astype('float')
    tables['Tests'] = pd.DataFrame(tests).set_index('Date').astype('float')
    return tables
