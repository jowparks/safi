#########ASYNCIO version of StateGraph

# StateGraph -  used to pull data from pubmed through an api
from aiohttp import ClientSession
import asyncio
import urllib
from urllib.parse import quote
#import concurrent.futures
#import requests

import json
from bokeh.sampledata import us_states
from bokeh.plotting import figure, show, output_notebook, ColumnDataSource
from bokeh.models import HoverTool, CustomJS, OpenURL, TapTool, Range1d
import pickle

dataDir = "./static/"
moneyFile = "FundingPerState2016.pkl"

# affiliation = AD
searchField = "[AD]"
us_states = us_states.data.copy()
del us_states["HI"]
del us_states["AK"]

state_xs = [us_states[code]["lons"] for code in us_states]
state_ys = [us_states[code]["lats"] for code in us_states]

async def fetchStates(url, session):
    async with session.get(url) as response:
        return await response.text()

###add states correlating with responses############
async def runStates(states, ss):
    tasks = []

    # Fetch all responses within one Client session,
    # keep connection alive for all requests.
    async with ClientSession() as session:
        for state in states:
            tu = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term=" + state + searchField+"+AND+" +ss+"&mindate=2012/01/01&maxdate=2016/12/31&usehistory=y&retmode=json"
            task = asyncio.ensure_future(fetchStates(tu, session))
            tasks.append(task)

        responses = await asyncio.gather(*tasks)

        # you now have all response bodies in this variable
        #responses can be converted to json, originally were strings
        #print(json.loads(responses[0]))
    return responses

# gets data from each state while string : ss=searchstring
def getStates(ss):
    #start threads and create queue of URLs
    loop = asyncio.get_event_loop()
    states = [us_states[state]["name"] for state in us_states]
    future = asyncio.ensure_future(runStates(states,ss))
    res = loop.run_until_complete(future)
    #print(res)
    for idx, state in enumerate(us_states):
        search_data = json.loads(res[idx])
        #webenv = search_data["esearchresult"]['webenv']
        total_records = int(search_data["esearchresult"]['count'])
        us_states[state]["count"] = total_records
        #print(total_records)


def stateGraph(si):
    ss = quote(si)


    ##FOR SEARCHING YOU WILL NEED TO ESCAPE SPACES AND SPECIAL CHARS
    getStates(ss)
#     for state in us_states:
#         print(state)
#         print(us_states[state]["count"])

    # unnormalized to money version
    state_counts = [us_states[code]["count"] for code in us_states]
    state_names = [us_states[code]["name"] for code in us_states]

    state_counts_norm = state_counts
    state_raw_counts = state_counts
    max_state_counts = max(state_counts)
    if(max_state_counts > 0):
        state_counts = [x / max_state_counts for x in state_counts]
    else:
        state_counts = [x for x in state_counts]

    # normalized to money
    fbs = pickle.load(open(dataDir + moneyFile, "rb"))
    state_counts_norm = [us_states[code]["count"] / fbs[us_states[code]["name"]] for code in us_states]
    max_state_counts_norm = max(state_counts_norm)
    if(max_state_counts_norm > 0):
        state_counts_norm = [x / max_state_counts_norm for x in state_counts_norm]
    else:
        state_counts_norm = [x for x in state_counts_norm]


    stateSource = ColumnDataSource(
            data=dict(
                x=state_xs,
                y=state_ys,
                state_names = state_names,
                state_raw_counts = state_raw_counts,
                alphas = state_counts
            )
        )
    stateNormSource = ColumnDataSource(
            data=dict(
                x=state_xs,
                y=state_ys,
                state_names = state_names,
                state_raw_counts = state_raw_counts,
                alphas = state_counts_norm
            )
        )
    hoverState = HoverTool(
            tooltips="""
            <div>
                <div style="max-width: 400px;">
                    <span style="font-size: 12px; font-weight: bold;">@state_names</span>
                </div>
                <div style="max-width: 400px;">
                    <span style="font-size: 12px; color: #966;">Total number of articles:</span>
                    <span style="font-size: 12px; color: #966;">@state_raw_counts</span>
                <div>
            </div>
            """
        )
    hoverStateNorm = HoverTool(
            tooltips="""
            <div>
                <div style="max-width: 400px;">
                    <span style="font-size: 12px; font-weight: bold;">@state_names</span>
                </div>
                <div style="max-width: 400px;">
                    <span style="font-size: 12px; color: #966;">Total Number of Articles:</span>
                    <span style="font-size: 12px; color: #966;">@state_raw_counts</span>
                <div>
                <div style="max-width: 400px;">
                    <span style="font-size: 12px; color: #966;">Fractional publication rate (norm. by funding):</span>
                    <span style="font-size: 12px; color: #966;">@alphas</span>
                <div>
            </div>
            """
        )

    TOOLS = 'pan,wheel_zoom,tap,reset'
    p = figure(title="Publications containing: " + si,
               toolbar_location="left", plot_width=800, plot_height=510, tools=[TOOLS,hoverState], active_scroll='wheel_zoom')
    p2 = figure(title="Publications containing: "+si+" (Normalized by NIH funding)",
                toolbar_location="left", plot_width=800, plot_height=510, tools=[TOOLS,hoverStateNorm], active_scroll='wheel_zoom')
    p.xaxis.visible = False
    p.xgrid.visible = False
    p.yaxis.visible = False
    p.ygrid.visible = False

    p2.xaxis.visible = False
    p2.xgrid.visible = False
    p2.yaxis.visible = False
    p2.ygrid.visible = False


    #p.circle('x', 'y',fill_color='colors', fill_alpha='alphas', size=12, source=source)
    p.patches('x', 'y', fill_color="#377BA8", fill_alpha='alphas',
              line_color="#884444", line_width=1.5, source=stateSource)

    p2.patches('x', 'y', fill_color="#377BA8", fill_alpha='alphas',
               line_color="#884444", line_width=1.5, source=stateNormSource)

    #show(p)
    #show(p2)
    return p, p2

# p, p2 = stateGraph("prc2")
# show(p)
# show(p2)
# stateGraph("lung")
# stateGraph("breast")
