########Similarity plotting of search

from aiohttp import ClientSession
from aiohttp import TCPConnector

import time
import asyncio
import pandas as pd
import numpy as np
import scipy.sparse as sp
import colorsys
import re
import sqlite3


import xml.etree.ElementTree as ET
import requests
from math import ceil
from urllib.parse import quote

import pickle
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.decomposition import TruncatedSVD
from sklearn.manifold import TSNE, SpectralEmbedding

from bokeh.plotting import figure, show, output_notebook, ColumnDataSource
from bokeh.layouts import column, layout
from bokeh.models import HoverTool, CustomJS, OpenURL, TapTool, Range1d
from bokeh.models.widgets import TextInput, Button, DataTable, TableColumn, Slider, Div
from bokeh.models.glyphs import Text

#output_notebook()

#Articles that a given article cites
#https://eutils.ncbi.nlm.nih.gov/entrez/eutils/elink.fcgi?dbfrom=pubmed&linkname=pubmed_pubmed_refs&id=24923681
#add to end of elink post: &query_key=<key>&WebEnv=<webenv string>
#Parks Stone Pubmed ID 24923681

# UID list. Either a single UID or a comma-delimited list of UIDs may be provided.
# All of the UIDs must be from the database specified by dbfrom.
# There is no set maximum for the number of UIDs that can be passed to ELink,
# but if more than about 200 UIDs are to be provided, the request should be made using the HTTP POST method.

#similarity score for comparing sets, ie cited articles
#see http://dataconomy.com/2015/04/implementing-the-five-most-popular-similarity-measures-in-python/
#

# def returnJaccard(cids):
#     lenList = len(cids)
#     jarr = np.zeros([lenList,lenList])
#     for ix in range(lenList):
#         for jx in range(lenList):
#             if(ix>jx):
#                 jc = jaccard(cids[ix],cids[jx])
#                 jarr[ix][jx] = jc
#                 jarr[jx][ix] = jc
#     print(jarr[:5])
#     return jarr

# def jaccard(x,y):

#     intersection_cardinality = len(set.intersection(*[set(x), set(y)]))
#     union_cardinality = len(set.union(*[set(x), set(y)]))
#     return intersection_cardinality/float(union_cardinality)

### Get ids (PMID) for papers in search
def PMIDsFromSearch(s,sy,ey):
    pre = time.time()

    search_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term="+s+"&mindate="+sy+"/01/01&maxdate="+ey+"/12/31&usehistory=y&retmode=json"
    #pre = time.time()
    search_r = requests.post(search_url)
    #print("Web Env retrieved:"+str(time.time()-pre))

    search_data = search_r.json()
    web_env = search_data['esearchresult']['webenv']
    query_key = search_data["esearchresult"]['querykey']
    total_count = search_data["esearchresult"]['count']


    maxIds = 100000 #maximum defined by pubmed
    rids = []
    #loop over all articles and grab set cited papers (see cited_rosetta for paper structure)
    for i in range(ceil(int(total_count)/maxIds)):

        id_url = ("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term="+s+
                                "&mindate="+sy+"/01/01&maxdate="+ey+"/12/31&usehistory=y&retmode=json&retstart="+
                                str(i*maxIds)+"&retmax="+str(i*maxIds+maxIds-1))
        id_r = requests.get(id_url)
        id_data = id_r.json()
        id_list = id_data["esearchresult"]['idlist']
        for tid in id_list:
            rids.append(int(tid))

    #deletes duplicate entries
    rids = list(set(rids))
    print(str(len(rids))+" Articles Found:"+str(time.time()-pre))

    return rids


#fetch async requests
async def fetchCited(url,postdata, session):
    async with session.post(url,data=postdata) as response:
        return await response.text()

###get subsets of ids in async fashion############
async def runCited(url,ids):
    tasks = []

    # Fetch all responses within one Client session,
    # keep connection alive for all requests.
    async with ClientSession(connector = TCPConnector(limit=10)) as session:
        for ix in ids:
            post_vars = {"dbfrom":"pubmed", "linkname":"pubmed_pubmed_refs"}
            post_vars["id"] = ix;
            task = asyncio.ensure_future(fetchCited(url, post_vars, session))
            tasks.append(task)

        responses = await asyncio.gather(*tasks)

        # you now have all response bodies in this variable
        #responses can be converted to json, originally were strings
        #print(json.loads(responses[0]))
    return responses

def getCitedFromPMIDs(rids, lp):
    ids = []
    cids = []


    cited_post = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/elink.fcgi"
    #example of get fetch "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/elink.fcgi?dbfrom=pubmed&linkname=pubmed_pubmed_refs&id=

    #nreqs is number of ids to put into each async op, eg 1200 ids will result in 12 async ops, currently set to 100 requests total
    nreqs = ceil(len(rids)/100)

    if(nreqs>1):
        rids = [rids[i*100:i*100+100] for i in range(0, nreqs)]

    #timer
    pre = time.time()

    #get the async references, connecs can fail, try 10 times before error
    asyncio.set_event_loop(lp)
    future = asyncio.ensure_future(runCited(cited_post,rids))
    res = lp.run_until_complete(future)

    print("References Retrieved:"+str(time.time()-pre))

    ##Only adds those articles that have citations listed in LinkSetDb (ie articles that are listed in PMC)c
    for r in res:
        #print(r)
        croot = ET.fromstring(r)
        for linkset in croot.iter('LinkSet'):
            tlinks = []
            ttid = linkset.find('IdList')[0]
            if(len(list(linkset))>2):
                for link in linkset.find('LinkSetDb').iter('Link'):
                    tlid = link[0]
                    tlinks.append(tlid.text)
                cids.append(tlinks)
                ids.append(int(ttid.text))
    return ids, cids

#query sql database for matching citations
def getCitedFromSQL(pids,db):
    conn = sqlite3.connect(db)

    sql_query = 'SELECT * FROM citations WHERE pmid IN (' + ','.join(map(str,pids)) + ')'
    sqlpd = pd.read_sql_query(sql_query,conn)

    return sqlpd
########Grabs all ids summary to get the title, authors, pubdate for each PMID
def getPMIDInfo(ids):
    #use full journal name
    titles = []
    dates = []
    authors = []
    journals = []
    pmccites = []

    #https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&version=2.0&id=27656642,24923681
    info_base = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
    info_data = {"db":"pubmed", "version":"2.0"}
    info_str = ""
    info_post = info_base

    #loop over all PMIDs
    for tid in ids:
        info_str += str(tid)+","

    info_str = info_str[:-1]
    info_data["id"] = info_str
    #print(info_str)

    pre = time.time()
    info_fetch = requests.post(info_post, data=info_data)
    print("Info Retrieved:"+str(time.time()-pre))

    croot = ET.fromstring(info_fetch.text)

    for doc in croot[0].iter('DocumentSummary'):
        titles.append(doc.find('Title').text)
        dates.append(doc.find('PubDate').text)
        journals.append(doc.find('FullJournalName').text)
        pmccites.append(doc.find('PmcRefCount').text)

        tempAuths = []
        for auth in doc.find('Authors').iter('Author'):
            tempAuths.append(auth.find('Name').text)
        authors.append(tempAuths)


    return titles, dates, authors, journals, pmccites

def returnCosine(cids):
    column = np.hstack(cids).astype(np.float)
    row = np.hstack([np.ones(len(arr))*i for i, arr in enumerate(cids)]).astype(np.float)
    vals = np.empty(column.size)
    vals.fill(1)
    mat = sp.csc_matrix((vals, (row, column)))


    jarr = cosine_similarity(mat)
    #print(jarr[:5])
    return jarr


def calcTSNE(X):
    print(len(X))
# plot didn't look very good with spectral embedding
#     if(len(X)>3000):
#         print("SVD calc")
#         #X = jarr
#         pre = time.time()
#         svd = TruncatedSVD(n_components=20, n_iter=7, random_state=42)
#         Xr = svd.fit_transform(X)
#         print("SVD runtime:"+str(time.time()-pre))

#         print("Spectral Embedding")
#         #X = jarr
#         pre = time.time()
#         se = SpectralEmbedding(n_components=2, random_state=0, eigen_solver="arpack")
#         Y = se.fit_transform(Xr)
#         print("Spectral Embedding runtime:"+str(time.time()-pre))

    if(len(X)>1000):
        print("SVD calc")
        #X = jarr
        pre = time.time()
        svd = TruncatedSVD(n_components=20, n_iter=7, random_state=42)
        Xr = svd.fit_transform(X)
        print("SVD runtime:"+str(time.time()-pre))

        del X
        print("TSNE calc")
        pre = time.time()
        tsn = TSNE(n_components=2, random_state=0)
        Y = tsn.fit_transform(Xr)
        print("TSNE time:"+str(time.time()-pre))
    else:
        print("TSNE calc")
        tsn = TSNE(n_components=2, random_state=0)

        Y = tsn.fit_transform(X);


    return Y

#for scaling color of graph
def pseudocolor(val, minval, maxval):
    # convert val in range minval..maxval to the range 240-360 degrees which
    # correspond to the colors red..green in the HSV colorspace
    maxc = 240
    minc = 180
    h = (maxc-minc)*(val-minval)/(maxval-minval)+minc
    #reverse the values, comment to prevent reverse
    h = abs(h-maxc)+minc
    # convert hsv color (h,1,1) to its rgb equivalent
    # note: the hsv_to_rgb() function expects h to be in the range 0..1 not 0..360
    r, g, b = colorsys.hsv_to_rgb(h/360, 0.4, 1.)
    return "rgb("+str(int(round(r*255)))+", "+str(int(round(g*255)))+", "+str(int(round(b*255)))+")"


#function for scaling the sizes of the points in the plot based on input values
def getScaledSizes(unscaledi,minw,maxw):
    umin = min(unscaledi)
    umax = max(unscaledi)
    scaled = [(maxw-minw)*(pt-umin)/(umax-umin)+minw for pt in unscaledi]
    return scaled

def getScaledColors(rawinput):
    yearre = re.compile("([0-9]){4}")
    inputi = []
    for inp in rawinput:
        #print(yearre.search(inp))
        tyear = int(yearre.search(inp).group(0))
        inputi.append(tyear)
    mini = min(inputi)
    maxi = max(inputi)
    coloroutput = [pseudocolor(tin,mini,maxi) for tin in inputi]
    return coloroutput


def kmeansClustering(pts,nc):
    kms = KMeans(n_clusters=nc, random_state=0).fit(pts)
    return kms.cluster_centers_,kms.labels_

def tfidfClusters(clusts,tits):
    combclusts = []
    for cid in list(set(clusts)):
        ts = []

        for idx,cn in enumerate(clusts):
            if(cn == cid):
                ts.append(tits[idx])

        combclusts.append(" ".join(ts))
    tf = TfidfVectorizer(analyzer='word', ngram_range=(1,2), min_df=2, max_df=len(combclusts)-1,stop_words = 'english')
    tfidf_matrix =  tf.fit_transform(combclusts)

    feature_array = np.array(tf.get_feature_names())
    # print(feature_array[:5])
    # print(tfidf_matrix.toarray())
    # tfidf_sorting = np.argsort(tfidf_matrix.toarray()).flatten()[::-1]
    topn = feature_array[np.argmax(tfidf_matrix.toarray(),axis=1)]
    # print("np features:")
    # print(topn)
    # print(len(feature_array))
    return topn


def similarityGraph(si, sy, ey, lp, db):
    pres = time.time()
    ss = quote(si)

    print("Searching for PMIDs")
    rids = PMIDsFromSearch(ss, sy, ey)
    #stop search if too broad, prevent from breaking
    if(len(rids)>15500):
        return len(rids)

    #retrieve primary info from built database
    print("Querying db for citations")
    pre = time.time()
    cdf = getCitedFromSQL(rids, db)
    print(str(len(cdf.index))+"/"+str(len(rids))+" citations found")

    #clean up, delete ids without citation data
    cdfc = cdf.dropna()
    print(str(len(cdfc.index))+"/"+str(len(cdf.index))+" have citation data")
    print("Retrieved in "+str(time.time()-pre)+" seconds")

    # SHOULD POTENTIALLY ADD THIS BACK, OTHERWISE WILL MISS SOME PUBLICATIONS, difference between what was in database and what was returned by pubmed
    # nrids = list(set(cdf['pmid']).symmetric_difference(set(rids)))
    # print("Retrieving remaining "+str(len(nrids))+" publications")
    #
    # print("Getting Cited PMIDs")
    # ###MODIFY nrids to be the citation data from database!!!!!!!!!!!
    # ids, cids = getCitedFromPMIDs(nrids, lp)
    # print("New ids :"+str(len(ids)))

    #build citation arrays for cosine calcutation
    ids = list(cdfc['pmid'])
    cids = []
    for index,row in cdfc.iterrows():
        cids.append(row['citationids'].split(','))

    print("Getting Info of PMIDs")
    titles, dates, authors, journals, pmccites = getPMIDInfo(ids)


    print("Performing sparse cosine similarity")
    pre = time.time()
    carr = returnCosine(cids)
    print("Cosine similarity time:"+str(time.time()-pre))

    print("Performing TSNE")
    pre = time.time()
    Y = calcTSNE(carr)



    print("Performing Kmeans TFIDF Clustering")
    #print("Performing TF-IDF on Clusters")
    pre = time.time()
    kcenters = []
    topwords = []

    minc = 7
    maxc = 20
    for idx in list(range(minc,maxc)):
        kc, cof = kmeansClustering(Y,idx)
        kcenters.append(kc)

        tw = tfidfClusters(cof,titles)
        topwords.append(tw)
    print("TF-IDF Kmeans Time:"+str(time.time()-pre))


    print("Total Time:"+str(time.time()-pres))




    #convert authors list of lists to list of strings for display
    authors_str = []
    for auths in authors:
        authors_str.append(", ".join(auths))

    #calcualte a scaled pt size based on citation quantity
    minw = 8
    maxw = 30

    # with open('citespkl.p','wb') as f:
    #     pickle.dump(list(map(int,pmccites)),f)
    ptsizes = getScaledSizes(list(map(int,pmccites)),minw,maxw)


    #create colors based on years published
    colors = getScaledColors(dates)

    #colors = ['blue']*len(ids)
    alphas = [1]*len(ids)
    source = ColumnDataSource(
            data=dict(
                x=Y[:,0],
                y=Y[:,1],
                PMID=ids,
                titles=titles,
                authors=authors_str,
                journals=journals,
                dates=dates,
                alphas=alphas,
                pmccites=pmccites,
                ptsizes=ptsizes,
                colors=colors,
                colorsperm=colors
            )
        )

    ########publication view table from selected on tsne plot
    pubview_data = dict(
        titles = ["Title"],
        dates = ["Date"],
        journals = ["Journal"],
        authors = ["Author"],
        pmccites = ["PMC Citations"],
        PMID = ["pmids"]
    )

    pubview_source = ColumnDataSource(pubview_data)

    pubview_columns = [
            TableColumn(field="titles", title="Article Title",width = 400),
            TableColumn(field="authors", title="Authors",width=50),
            TableColumn(field="journals", title="Journal",width=50),
            TableColumn(field="dates", title="Date",width = 80),
            TableColumn(field="pmccites", title="PMC Citations", width =80),
            TableColumn(field="PMID", title="PMIDS", width =0),
        ]

    pubview_table = DataTable(source=pubview_source, columns=pubview_columns, width=930, height=400)

    source.callback = CustomJS(args=dict(pubview_table = pubview_table), code="""
        var selecteddata = cb_obj.selected["1d"].indices
        var count = 0
        var s1 = cb_obj.get('data');
        var d2 = pubview_table.get('source').get('data');
        d2.index = []
        d2.authors = []
        d2.titles = []
        d2.journals = []
        d2.dates = []
        d2.pmccites = []
        d2.PMID = []
        for(k = 0; k < selecteddata.length; k++){
            tind = selecteddata[k]
            d2.index.push(count)
            d2.authors.push(s1.authors[tind])
            d2.titles.push(s1.titles[tind])
            d2.journals.push(s1.journals[tind])
            d2.dates.push(s1.dates[tind])
            d2.pmccites.push(parseInt(s1.pmccites[tind]))
            d2.PMID.push(s1.PMID[tind])
            count += 1
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
    #######END TABLE DISPLAY CODE#####


    #####max-width IS IMPORTANT FOR PROPER WRAPPING OF TEXT
    hover = HoverTool(
            tooltips="""
            <div>
                <div style="max-width: 400px;">
                    <span style="font-size: 12px; font-weight: bold;">@titles</span>
                </div>
                <div style="max-width: 400px;">
                    <span style="font-size: 12px; color: #966;">@authors</span>
                <div>
                <div style="max-width: 400px;">
                    <span style="font-size: 12px; font-style: italic;">@journals, @dates</span>
                <div style="max-width: 400px;">
                    <span style="font-size: 10px;">PMID</span>
                    <span style="font-size: 10px; color: #696;">@PMID</span>
                </div>
                <div style="max-width: 400px;">
                    <span style="font-size: 10px;">PMC Citations</span>
                    <span style="font-size: 10px; color: #696;">@pmccites</span>
                </div>
            </div>
            """
        )

    resetCallback = CustomJS(args=dict(source=source), code="""
        var data = source.get('data')
        var titles = data['titles']
        for (i=0; i < titles.length; i++) {
            data.colors[i]=data.colorsperm[i]
            data.alphas[i]= 1
        }
        source.trigger('change')
    """)
    #move function from reset callback to below so stuff updates automatically on textbox change
    textCallback = CustomJS(args=dict(source=source), code="""
        var data = source.get('data')
        var value = cb_obj.get('value')
        var words = value.split(" ")
        for (i=0; i < data.titles.length; i++) {
            data.alphas[i]= 0.3
            data.colors[i]=data.colorsperm[i]
        }
        for (i=0; i < data.titles.length; i++) {
            for(j=0; j < words.length; j++){
                if (data.titles[i].toLowerCase().indexOf(words[j].toLowerCase()) !== -1) {
                    if(j == words.length-1){
                        data.colors[i]='orange'
                        data.alphas[i]= 1
                    }
                }else if(data.authors[i].toLowerCase().indexOf(words[j].toLowerCase()) !== -1){
                    if(j == words.length-1){
                        data.colors[i]='orange'
                        data.alphas[i]= 1
                    }
                }else if(data.journals[i].toLowerCase().indexOf(words[j].toLowerCase()) !== -1){
                    if(j == words.length-1){
                        data.colors[i]='orange'
                        data.alphas[i]= 1
                    }
                }else{
                    break
                }
            }
        }
        source.trigger('change')
    """)


    TOOLS = 'pan,lasso_select,wheel_zoom,tap,reset'
    p = figure(plot_width=900, plot_height=600, title="'"+si+"' tSNE similarity", tools=[TOOLS,hover], active_scroll='wheel_zoom', active_drag="lasso_select")

    p.circle('x', 'y',fill_color='colors', fill_alpha='alphas', size='ptsizes', line_color="#000000",line_alpha=0.2,source=source)

    #word labeles for plots
    wordsources = []
    for idx in list(range(len(topwords))):
        wordsources.append(ColumnDataSource(dict(x=kcenters[idx][:,0], y=kcenters[idx][:,1], text=topwords[idx])))

    wordglyph = Text(x="x", y="y", text="text", text_color="#000000",text_font_style="bold", text_font_size="14pt")
    #5 is used for initial slider set below
    initialclust = 5
    wordholdsource = ColumnDataSource(dict(x=kcenters[initialclust][:,0], y=kcenters[initialclust][:,1], text=topwords[initialclust]))
    p.add_glyph(wordholdsource, wordglyph)

    # source = ColumnDataSource(data=dict(x=x, y=y))
    #
    # plot = Figure(plot_width=400, plot_height=400)
    # plot.line('x', 'y', source=source, line_width=3, line_alpha=0.6)
    args = {}
    args["wordholdsource"] = wordholdsource
    for idx in list(range(len(topwords))):
        args["wordsource"+str(idx+minc)] = wordsources[idx]

    #had to use eval hack because of limitations on the type of objects that can be passed into the callback, limited by bokeh backend
    slidercallback = CustomJS(args=args, code="""
        var f = cb_obj.value
        var ndata = eval('wordsource' + f.toString()).data;
        wordholdsource.data.x = ndata.x
        wordholdsource.data.y = ndata.y
        wordholdsource.data.text = ndata.text
        wordholdsource.trigger('change');
    """)

    wslider = Slider(start=minc, end=maxc, value=minc+initialclust, step=1, title="# of labels")
    # slider = Slider(start=0.1, end=4, value=1, step=.1, title="power", callback=callback)
    wslider.js_on_change('value', slidercallback)


    #formatting plot
    p.xaxis.axis_label = "Hover to view publication info, Click to open Pubmed link"
    p.xaxis.major_tick_line_color = None  # turn off x-axis major ticks
    p.xaxis.minor_tick_line_color = None  # turn off x-axis minor ticks
    p.yaxis.major_tick_line_color = None  # turn off y-axis major ticks
    p.yaxis.minor_tick_line_color = None
    p.xaxis.major_label_text_font_size = '0pt'  # turn off x-axis tick labels
    p.yaxis.major_label_text_font_size = '0pt'
    left, right, bottom, top = np.amin(Y[:,0])*1.1, np.amax(Y[:,0])*1.1, np.amin(Y[:,1])*1.1, np.amax(Y[:,1])*1.1
    p.x_range=Range1d(left, right)
    p.y_range=Range1d(bottom, top)

    #tap tool callback
    url = "https://www.ncbi.nlm.nih.gov/pubmed/@PMID"
    taptool = p.select(type=TapTool)
    taptool.callback = OpenURL(url=url)

    #work input callback
    word_input = TextInput(title="Search for term(s) in graph", placeholder="Enter term to highlight", callback=textCallback)
    reset = Button(label="Clear Highlighting", callback=resetCallback, width=150)


    spdiv = Div(text="&nbsp;",width = 100, height=20)
    tit1 = Div(text="<h1>"+si+" similarity plot</h1><br><h5>(displaying "+str(len(cdfc.index))+"/"+str(len(rids))+" articles with citation data)</h5>",width=930)
    lt = layout([[tit1], [word_input],[reset,spdiv,wslider],[p],[pubview_table]])

    return lt

# ss = "telomerase rna"
# syear = "1975"
# eyear = "2017"
# lt = similarityGraph(ss,syear,eyear)
# show(lt)

# print(jarr[:5])
# print(ids[:5])
# print(cids[:5])
# print(titles[:5])
# print(authors[:5])
# print(dates[:5])
# print(journals[:5])


# cited_fetch = requests.post(cited_post)
# cited_xml += cited_fetch.text
# f = open("cited_"+ss+".xml", 'w')
# f.write(cited_xml)
# f.close()
