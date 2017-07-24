#############ASYNCIO PubByDate

import asyncio
import urllib
import time
import json
import xml.etree.ElementTree as ET
import pandas as pd

from aiohttp import ClientSession
from aiohttp import TCPConnector
from urllib.parse import quote
from collections import Counter
from bokeh.models.widgets import DataTable, DateFormatter, TableColumn, Div, HTMLTemplateFormatter
from bokeh.models import CustomJS
from bokeh.plotting import figure, show, output_notebook, ColumnDataSource
from bokeh.layouts import layout
from SimilarityPlot import getPMIDInfo

async def fetchYears(url, session):
    async with session.get(url) as response:
        return await response.text()

###add years correlating with responses############
async def runYears(yrs, ss):
    tasks = []

    # Fetch all responses within one Client session,
    # keep connection alive for all requests.
    async with ClientSession(connector = TCPConnector(limit=10)) as session:
        for y in yrs:
            tu = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term="+ss+"&mindate="+str(y)+"/01/01&maxdate="+str(y)+"/12/31&usehistory=y&retmode=json&retmax=100000"
            task = asyncio.ensure_future(fetchYears(tu, session))
            tasks.append(task)

        responses = await asyncio.gather(*tasks)

        # you now have all response bodies in this variable
        #responses can be converted to json, originally were strings
        #print(json.loads(responses[0]))
    return responses

# gets data from each state while string : ss=searchstring
def getYears(ss,yrs):

    yearcounts = []
    #start threads and create queue of URLs
    loop = asyncio.get_event_loop()
    future = asyncio.ensure_future(runYears(yrs,ss))
    res = loop.run_until_complete(future)
    #print(res)
    rids =[]
    for idx, y in enumerate(yrs):
        search_data = json.loads(res[idx])
        #webenv = search_data["esearchresult"]['webenv']
        total_records = int(search_data["esearchresult"]['count'])
        yearcounts.append(total_records)

        id_list = search_data["esearchresult"]['idlist']
        for tid in id_list:
            rids.append(int(tid))

    return yearcounts, rids


def yearGraph(si,sy,ey):
    years = list(range(sy, ey))

    ss = quote(si)
    p = figure(title="Articles containing: "+si, plot_width=600, plot_height=300, x_axis_label="Year", y_axis_label="Total Articles")

    ##FOR SEARCHING YOU WILL NEED TO ESCAPE SPACES AND SPECIAL CHARS
    yearcounts, ids = getYears(ss,years)
    pre = time.time()
    titles, dates, authors, journals, pmccites = getPMIDInfo(ids)
    print("Gathered PMID Summary for counts:"+str(time.time()-pre))

    p.line(years, yearcounts, color='blue')

    #Parse out statisitcs about returned data
    authors_str = []
    for auths in authors:
        authors_str.append(", ".join(auths))
    pmidPD = pd.DataFrame(data={'titles':titles,'dates':dates,'authors':authors,'authors_str':authors_str,'journals':journals,'pmccites':list(map(int,pmccites))})

    #print(pmidPD[:5])
    topPmids = pmidPD.nlargest(10,'pmccites')
    #####ADD CODE TO DISPLAY TABLE NEXT TO PLOT, determine how good a proxy pmccites is for real number of citation
    #print(topPmids)

    total_authors = Counter(auth for auths in pmidPD['authors'] for auth in auths)
    total_authors_norm = Counter()
    for idx, auths in enumerate(pmidPD['authors']):
        for auth in auths:
            total_authors_norm[auth] += pmidPD['pmccites'][idx]

    total_journals = Counter(jour for jour in pmidPD['journals'])

    #get data ready for display in bokeh
    #display nent number of entries
    nent = 100

    topauths = total_authors.most_common(nent)
    topauths_norm = total_authors_norm.most_common(nent)
    topjournals = total_journals.most_common(nent)

    #for displaying authors based on citations and papers
    paper_data = dict(
        numpapers = [n[1] for n in topauths],
        auths = [n[0] for n in topauths]
    )
    cite_data = dict(
        numcites = [n[1] for n in topauths_norm],
        authscites = [n[0] for n in topauths_norm]
    )
    journal_data = dict(
        numpapers = [n[1] for n in topjournals],
        journals = [n[0] for n in topjournals]
    )
    #print(len(titles),len(dates),len(journals),len(authors_str),len(pmccites))
    #print(journals)
    pub_data = dict(
        titles = titles,
        dates = dates,
        journals = journals,
        authors = authors_str,
        pmccites = pmccites,
        PMID = ids
    )

    pubview_data = dict(
        titles = ["Title"],
        dates = ["Date"],
        journals = ["Journal"],
        authors = ["Author"],
        pmccites = ["PMC Citations"],
        PMID = ["PMID"]
    )
    #publication table that will be populated by

    paper_source = ColumnDataSource(data = paper_data)
    cite_source = ColumnDataSource(data = cite_data)
    journal_source = ColumnDataSource(data = journal_data)

    pub_source = ColumnDataSource(pub_data)
    pubview_source = ColumnDataSource(pubview_data)

    paper_columns = [
            TableColumn(field="numpapers", title="# Papers",width=100),
            TableColumn(field="auths", title="Author",width=150),
        ]
    cite_columns = [
            TableColumn(field="numcites", title="# PMC Citations",width=130),
            TableColumn(field="authscites", title="Author",width=150),
        ]

    journal_columns = [
            TableColumn(field="numpapers", title="# Papers",width=80),
            TableColumn(field="journals", title="Journal", width=220),
        ]


    template="""
    <div style="background:red
        color: white">
    <%= value %>\ninfo</div>
    """

    formatter =  HTMLTemplateFormatter(template=template)

    pubview_columns = [
            TableColumn(field="titles", title="Article Title",formatter=formatter),
            TableColumn(field="authors", title="Authors"),
            TableColumn(field="journals", title="Journal"),
            TableColumn(field="dates", title="Date",width = 80),
            TableColumn(field="pmccites", title="PMC Citations", width =80),
        ]


    paper_table = DataTable(source=paper_source, columns=paper_columns, width=250, height=210)
    cite_table = DataTable(source=cite_source, columns=cite_columns, width=280, height=210)
    journal_table = DataTable(source=journal_source, columns=journal_columns, width=300, height=210)

    tit0 = Div(text="<h1>General statistics for "+si+"</h1>",width=930)
    tit1 = Div(text="<h1>Common Authors and Journals</h1>\n<h5>(Select author(s) or journal(s) to display related publications)</h5>",width=930)
    tit2 = Div(text="<h1>Related Publications</h1>\n<h5>(click publication to visit pubmed entry)</h5>", width=930)

    spacer = figure(plot_width=50, plot_height=210, logo = None, toolbar_location = None, outline_line_color = None)
    spacer2 = figure(plot_width=50, plot_height=210, logo = None, toolbar_location = None, outline_line_color = None)

    #create table updated by clicks in above tables, for viewing related publications


    pubview_table = DataTable(source=pubview_source, columns=pubview_columns, width=930, height=400)

    # callbacks for each of the table selections


    #JScallback for setting up publications table
    #curspot
    paper_source.callback = CustomJS(args=dict(paper_source = paper_source, pub_source = pub_source, pubview_table = pubview_table), code="""
        var authordata = paper_source.selected["1d"].indices
        var author = 'test'
        var count = 0
        var s1 = paper_source.get('data');
        var d1 = pub_source.get('data');
        var d2 = pubview_table.get('source').get('data');
        d2.index = []
        d2.authors = []
        d2.titles = []
        d2.journals = []
        d2.dates = []
        d2.pmccites = []
        d2.PMID = []
        for(j = 0; j < d1.authors.length; j++){
            for(k = 0; k < authordata.length; k++){
                if (d1.authors[j].toLowerCase().indexOf(s1.auths[authordata[k]].toLowerCase()) !== -1) {
                    d2.index.push(count)
                    d2.authors.push(d1.authors[j])
                    d2.titles.push(d1.titles[j])
                    d2.journals.push(d1.journals[j])
                    d2.dates.push(d1.dates[j])
                    d2.pmccites.push(parseInt(d1.pmccites[j]))
                    d2.PMID.push(d1.PMID[j])
                    count += 1
                    break;
                }
            }
        }
        console.log(d2)
        pubview_table.trigger('change');
        """)

    cite_source.callback = CustomJS(args=dict(cite_source = cite_source, pub_source = pub_source, pubview_table = pubview_table), code="""
        var authordata = cite_source.selected["1d"].indices
        var author = 'test'
        var count = 0
        var s1 = cite_source.get('data');
        var d1 = pub_source.get('data');
        var d2 = pubview_table.get('source').get('data');
        d2.index = []
        d2.authors = []
        d2.titles = []
        d2.journals = []
        d2.dates = []
        d2.pmccites = []
        d2.PMID = []
        for(j = 0; j < d1.authors.length; j++){
            for(k = 0; k < authordata.length; k++){
                if (d1.authors[j].toLowerCase().indexOf(s1.authscites[authordata[k]].toLowerCase()) !== -1) {
                    d2.index.push(count)
                    d2.authors.push(d1.authors[j])
                    d2.titles.push(d1.titles[j])
                    d2.journals.push(d1.journals[j])
                    d2.dates.push(d1.dates[j])
                    d2.pmccites.push(parseInt(d1.pmccites[j]))
                    d2.PMID.push(d1.PMID[j])
                    count += 1
                    break;
                }
            }
        }
        console.log(d2)
        pubview_table.trigger('change');
        """)
    journal_source.callback = CustomJS(args=dict(journal_source = journal_source, pub_source = pub_source, pubview_table = pubview_table), code="""
        var journaldata = journal_source.selected["1d"].indices
        var author = 'test'
        var count = 0
        var s1 = journal_source.get('data');
        var d1 = pub_source.get('data');
        var d2 = pubview_table.get('source').get('data');
        d2.index = []
        d2.authors = []
        d2.titles = []
        d2.journals = []
        d2.dates = []
        d2.pmccites = []
        d2.PMID = []
        for(j = 0; j < d1.journals.length; j++){
            for(k = 0; k < journaldata.length; k++){
                //checks to make sure journal name exists, seems like certain publications have no journal name in pubmed
                if(d1.journals[j]){
                    if (d1.journals[j].toLowerCase() == s1.journals[journaldata[k]].toLowerCase()) {
                        d2.index.push(count)
                        d2.authors.push(d1.authors[j])
                        d2.titles.push(d1.titles[j])
                        d2.journals.push(d1.journals[j])
                        d2.dates.push(d1.dates[j])
                        d2.pmccites.push(parseInt(d1.pmccites[j]))
                        d2.PMID.push(d1.PMID[j])
                        count += 1
                        break;
                    }
                }
            }
        }
        console.log(d2)
        pubview_table.trigger('change');
        """)


    pubview_source.callback = CustomJS(code="""
        var selecteddata = cb_obj.selected["1d"].indices
        var s1 = cb_obj.get('data');
        var url = "https://www.ncbi.nlm.nih.gov/pubmed/"+s1.PMID[selecteddata[0]]
        window.open(url,'_blank');

    """)
    ###### write callbacks for other two tables as well


    yearslayout = layout([[tit0],[p],[tit1],[paper_table,spacer,cite_table,spacer2,journal_table],[tit2],[pubview_table]])



    #show(yearslayout)

#     print(total_authors.most_common(10))
#     print(total_authors_norm.most_common(10))
#     print(total_authors['Harley CB'], total_authors['Thomson JA'])


    #show(p)
    return yearslayout
# yp = yearGraph("telomerase rna",2000,2017)
# show(yp)
