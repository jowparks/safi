#############ASYCIO PubByDate

from aiohttp import ClientSession
import asyncio
import urllib
from urllib.parse import quote
#import concurrent.futures
#import requests

import json
from bokeh.sampledata import us_states
from bokeh.plotting import figure, show, output_notebook


years = list(range(1975, 2017))

async def fetchYears(url, session):
    async with session.get(url) as response:
        return await response.text()

###add years correlating with responses############
async def runYears(yrs, ss):
    tasks = []

    # Fetch all responses within one Client session,
    # keep connection alive for all requests.
    async with ClientSession() as session:
        for y in yrs:
            tu = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term="+ss+"&mindate="+str(y)+"/01/01&maxdate="+str(y)+"/12/31&usehistory=y&retmode=json"
            task = asyncio.ensure_future(fetchYears(tu, session))
            tasks.append(task)

        responses = await asyncio.gather(*tasks)

        # you now have all response bodies in this variable
        #responses can be converted to json, originally were strings
        #print(json.loads(responses[0]))
    return responses

# gets data from each state while string : ss=searchstring
def getYears(ss):

    yearcounts = []
    #start threads and create queue of URLs
    loop = asyncio.get_event_loop()
    future = asyncio.ensure_future(runYears(years,ss))
    res = loop.run_until_complete(future)
    #print(res)
    for idx, y in enumerate(years):
        search_data = json.loads(res[idx])
        #webenv = search_data["esearchresult"]['webenv']
        total_records = int(search_data["esearchresult"]['count'])
        yearcounts.append(total_records)
        #print(total_records)
    return yearcounts


def yearGraph(si):
    ss = quote(si)
    p = figure(title="Articles containing: "+si, plot_width=400, plot_height=400, x_axis_label="Year", y_axis_label="Total Articles")

    ##FOR SEARCHING YOU WILL NEED TO ESCAPE SPACES AND SPECIAL CHARS
    yearcounts = getYears(ss)
#     for state in us_states:
#         print(state)
#         print(us_states[state]["count"])

    # unnormalized to money version
    p.line(years, yearcounts, color='blue')

    #show(p)
    return p
