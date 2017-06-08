########Similarity plotting of search
import time
from aiohttp import ClientSession
import asyncio
import numpy as np
import scipy.sparse as sp

import xml.etree.ElementTree as ET
import requests
from math import ceil
from urllib.parse import quote
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.decomposition import TruncatedSVD
from sklearn.manifold import TSNE, SpectralEmbedding
from bokeh.plotting import figure, show, output_notebook, ColumnDataSource
from bokeh.layouts import column, layout
from bokeh.models import HoverTool, CustomJS, OpenURL, TapTool, Range1d
from bokeh.models.widgets import TextInput, Button
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
    async with ClientSession() as session:
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

def getCitedFromPMIDs(rids):
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
    loop = asyncio.get_event_loop()
    future = asyncio.ensure_future(runCited(cited_post,rids))
    res = loop.run_until_complete(future)

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

# def getCitedFromPMIDXML(r):
#     ids = []
#     cids = []

#     cited_post = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/elink.fcgi"
#     post_vars = {"dbfrom":"pubmed", "linkname":"pubmed_pubmed_refs","id":[]}

#     #loop over all articles and grab set cited papers (see cited_rosetta for paper structure)
#     for tid in r[0][1].iter('Id'):
#         post_vars['id'].append(tid.text)

#     pre = time.time()
#     cited_fetch = requests.post(cited_post, data=post_vars)
#     print("References Retrieved:"+str(time.time()-pre))
#     croot = ET.fromstring(cited_fetch.text)

#     for linkset in croot.iter('LinkSet'):
#         tlinks = []
#         ttid = linkset.find('IdList')[0]
#         if(len(list(linkset))>2):
#             for link in linkset.find('LinkSetDb').iter('Link'):
#                 tlid = link[0]
#                 tlinks.append(tlid.text)
#             cids.append(tlinks)
#             ids.append(int(ttid.text))
#     return ids, cids



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

########CHANGE CODE BELOW need to grab all ids summary to get the title, authors, pubdate for each
# def getPMIDInfo(ids):
#     #use full journal name
#     titles = []
#     dates = []
#     authors = []
#     journals = []

#     #https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&version=2.0&id=27656642,24923681
#     info_base = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&version=2.0&id="
#     info_post = info_base

#     #loop over all PMIDs
#     for tid in ids:
#         if((len(info_post)+len(str(tid))+4)>2083):

#             #print("fetching")
#             info_post = info_post[:-1]
#             info_fetch = requests.post(info_post)
#             info_post = info_base+str(tid)+","
#             croot = ET.fromstring(info_fetch.text)

#             #get data from croot
#             for doc in croot[0].iter('DocumentSummary'):
#                 titles.append(doc.find('Title').text)
#                 dates.append(doc.find('PubDate').text)
#                 journals.append(doc.find('FullJournalName').text)
#                 aus = ""
#                 for auth in doc.find('Authors').iter('Author'):
#                     aus += auth.find('Name').text+", "
#                 authors.append(aus[:-2])

#         else:
#             info_post += str(tid)+","

#     #for grabbing last set of Links

#     info_post = info_post[:-1]
#     info_fetch = requests.post(info_post)
#     croot = ET.fromstring(info_fetch.text)

#     for doc in croot[0].iter('DocumentSummary'):
#         titles.append(doc.find('Title').text)
#         dates.append(doc.find('PubDate').text)
#         journals.append(doc.find('FullJournalName').text)
#         aus = ""
#         for auth in doc.find('Authors').iter('Author'):
#             aus += auth.find('Name').text+", "
#         authors.append(aus[:-2])
#     return titles, dates, authors, journals


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

        print("TSNE calc")
        pre = time.time()
        tsn = TSNE(n_components=2, random_state=0)
        Y = tsn.fit_transform(Xr);
        print("TSNE time:"+str(time.time()-pre))
    else:
        print("TSNE calc")
        tsn = TSNE(n_components=2, random_state=0)

        pre = time.time()
        Y = tsn.fit_transform(X);
        print("TSNE time:"+str(time.time()-pre))

    return Y

# print("xmax "+str(np.amax(Y[:,0])))
# print("xmin "+str(np.amin(Y[:,0])))
# print("ymax "+str(np.amax(Y[:,1])))
# print("ymin "+str(np.amin(Y[:,1])))
def similarityGraph(si, sy, ey):
    pres = time.time()
    ss = quote(si)

    print("Searching for PMIDs")
    rids = PMIDsFromSearch(ss, sy, ey)

    print("Getting Cited PMIDs")
    ids, cids = getCitedFromPMIDs(rids)

    print("Getting Info of PMIDs")
    titles, dates, authors, journals, pmccites = getPMIDInfo(ids)

    print("Performing sparse cosine similarity")
    pre = time.time()
    carr = returnCosine(cids)
    print("Cosine similarity time:"+str(time.time()-pre))

    print("Performing TSNE")
    Y = calcTSNE(carr)
    print("Total Time:"+str(time.time()-pres))



    #convert authors list of lists to list of strings for display
    authors_str = []
    for auths in authors:
        authors_str.append(", ".join(auths))


    colors = ['blue']*len(ids)
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
                colors=colors,
                alphas=alphas,
                pmccites=pmccites
            )
        )

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
            data.colors[i]='blue'
            data.alphas[i]= 1
        }
        source.trigger('change')
    """)

    textCallback = CustomJS(args=dict(source=source), code="""
        var data = source.get('data')
        var value = cb_obj.get('value')
        var words = value.split(" ")
        for (i=0; i < data.titles.length; i++) {
            data.alphas[i]= 0.3
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


    TOOLS = 'pan,wheel_zoom,tap,reset'
    p = figure(plot_width=900, plot_height=600, title="'"+si+"' tSNE similarity", tools=[TOOLS,hover], active_scroll='wheel_zoom')

    p.circle('x', 'y',fill_color='colors', fill_alpha='alphas', size=12, source=source)

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


    url = "https://www.ncbi.nlm.nih.gov/pubmed/@PMID"
    taptool = p.select(type=TapTool)
    taptool.callback = OpenURL(url=url)


    word_input = TextInput(title="Search for term(s) in graph", placeholder="Enter term to highlight", callback=textCallback)
    reset = Button(label="Clear Highlighting", callback=resetCallback, width=150)

    lt = layout([[word_input],[reset], [p]])

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
