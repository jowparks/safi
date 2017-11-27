###Controller for python/flask web app, main analysis functions are inside of referenced files

from flask import Flask, render_template, request, redirect, session, url_for
from bokeh.embed import components
from threading import Thread
from pathlib import Path

import time
import asyncio
import hashlib
import pickle
import logging
import os



import PubDatePlotting as pdp
import StateGraph as sg
import SimilarityPlot as smp
import AbstractSearch as absr


app = Flask(__name__)
app.secret_key = 'VA&Dnadf8%$$#JK9SDA64asf54@!^&'

if(os.path.isfile('/Users/jowparks/Data/pubmed.db')):
    app.sqldb = '/Users/jowparks/Data/pubmed.db'
else:
    app.sqldb = 'static/pubmed.db'

#loop = asyncio.get_event_loop()

log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

@app.route('/', methods=['GET', 'POST'])
def index():
    # nquestions=app_lulu.nquestions
    curpage=session['curpage'] = '/'
    if request.method == 'GET':

        #### CHANGE TO ORDERED DICT OR LIST SO THAT INFO IS SENT IN ORDER, NAV ORDER IS CHANGING AFTER PAGE LOAD
        #session['nav_id'] = {'counts':'counts','geo':'geo','similarity':'similarity'}
        #session['nav_name'] = {'counts':'Raw Counts','geo':'Geographic','similarity':'Visualize Article Similarity'}
        session['nav_id'] = ['similarity','similarityab','counts','geo','about']#,'abstractsearch']
        session['nav_name'] = ['Visualize Citation Similarity','Visualize Abstract Similarity','Statistics','Geography','About']#,'Abstract Search']
        return render_template('pubsearch.html', searchstring="", curpage=session['curpage'], nav_id=session['nav_id'], nav_name=session['nav_name'])
    else:

        #session['vars']  = {}
        return render_template('pubsearch.html', searchstring="", curpage=session['curpage'], nav_id=session['nav_id'], nav_name=session['nav_name'])



@app.route('/search', methods=['GET', 'POST'])
def searchView():
    if request.method == 'GET':

        curpage=session['curpage'] = '/'
        session['vars'] = {}
        return render_template('pubsearch.html',curpage=session['curpage'])
    else:
        session['vars'] = {}
        print(request.form)
        session['vars']['searchStr'] = request.form['searchterm']

        #hash the filename for uniqueness
        rstr = hashlib.sha256(session['vars']['searchStr'].lower().encode('utf8')).hexdigest()
        session['vars']['hid'] = rstr

        #return countsView()
        return similarityView()



@app.route('/counts', methods=['GET','POST'])
def countsView():


    #if button is clicked before search is performed
    if 'vars' not in session:
        #return to homepage if data isn't here and user got the url
        return redirect(url_for('index'), code=307)

    session['curpage'] = "counts"


    d_file = Path('static/bokehscripts/'+session['vars']['hid']+'yeardiv.p')
    s_file = Path('static/bokehscripts/'+session['vars']['hid']+'yearscript.js')

    #delete file if user asks to delete
    if 'delete' in request.form:
        if s_file.is_file():
            os.remove(s_file)
        if d_file.is_file():
            os.remove(d_file)

    if not s_file.is_file() or not d_file.is_file():
        if request.method == 'GET':
            #return to homepage if data isn't here and user got the url
            return redirect(url_for('index'), code=307)

        #app.vars['countsData'] = rstr

#         while True:
#             try:
#                 app.yearplot = yearGraph(app.vars['searchStr'])
#                 break
#             except:
#                 print("Error getting year data")

        #rstr = ''.join(rnd.choices(st.ascii_letters + st.digits, k=20))
        #app.yearplot = yearGraph(app.vars['searchStr'],1975,2017)
        yearplot = pdp.yearGraph(session['vars']['searchStr'],1975,2017)
        script, div = components({'yearplot': yearplot})

        outscript = session['vars']['hid']+"yearscript.js"
        with open("static/bokehscripts/"+outscript,"w") as file:
                file.write(script)
                file.close()

        outdiv = session['vars']['hid']+"yeardiv.p"
        with open("static/bokehscripts/"+outdiv,"wb") as file:
                pickle.dump(div, file)
                file.close()

        ######render
        return render_template('pubview.html', searchstring=session['vars']['searchStr'], script=script, div=div, curpage=session['curpage'], nav_id=session['nav_id'], nav_name=session['nav_name'])
    else:

        f = open('static/bokehscripts/'+session['vars']['hid']+'yeardiv.p', "rb")
        tdiv = pickle.load(f)
        tscript = open('static/bokehscripts/'+session['vars']['hid']+'yearscript.js','r').read()
        ######render
        return render_template('pubview.html', searchstring=session['vars']['searchStr'], script=tscript, div=tdiv, curpage=session['curpage'], nav_id=session['nav_id'], nav_name=session['nav_name'])



@app.route('/about', methods=['GET','POST'])
def aboutView():


    session['curpage'] = "about"
    ######render
    tdiv = open('static/aboutdiv.html','r').read()
    return render_template('pubview.html', searchstring="", div=tdiv, curpage=session['curpage'], nav_id=session['nav_id'], nav_name=session['nav_name'])



@app.route('/geo', methods=['GET','POST'])
def geoView():

    #if button is clicked before search is performed
    if 'vars' not in session:
        #return to homepage if data isn't here and user got the url
        return redirect(url_for('index'), code=307)

    session['curpage'] = "geo"



    d_file = Path('static/bokehscripts/'+session['vars']['hid']+'geodiv.p')
    s_file = Path('static/bokehscripts/'+session['vars']['hid']+'geoscript.js')

    #delete file if user asks to delete
    if 'delete' in request.form:
        if s_file.is_file():
            os.remove(s_file)
        if d_file.is_file():
            os.remove(d_file)

    if not s_file.is_file() or not d_file.is_file():

        if request.method == 'GET':
            #return to homepage if data isn't here and user got the url
            return redirect(url_for('index'), code=307)

        #connect to Pubmed and try to get data, if fail restart
#         while True:
#             try:
#                 app.stateplot, app.stateplotnorm = stateGraph(app.vars['searchStr'])
#                 break
#             except:
#                 print("Error getting state data")
        #app.stateplot = stateGraph(app.vars['searchStr'],"1975/01/01","2016/12/31")

        #rstr = ''.join(rnd.choices(st.ascii_letters + st.digits, k=20))
        #app.yearplot = yearGraph(app.vars['searchStr'],1975,2017)
        stateplot = sg.stateGraph(session['vars']['searchStr'],"1975/01/01","2016/12/31")
        script, div = components({'stateplot': stateplot})

        ###########MODIFY CODE IN OTHER AREAS TO DO SAME THING, ALSO ADD RANDOM KEY FOR FILE STORAGE INSTEAD OF 'outputtemp.js'
        outscript = session['vars']['hid']+"geoscript.js"

        with open("static/bokehscripts/"+outscript,"w") as file:
                #remove JS tags
                file.write(script)
                file.close()

        outdiv = session['vars']['hid']+"geodiv.p"
        with open("static/bokehscripts/"+outdiv,"wb") as file:
                #remove JS tags
                pickle.dump(div, file)
                file.close()

        ######render
        return render_template('pubview.html', searchstring=session['vars']['searchStr'], script=script, div=div, curpage=session['curpage'], nav_id=session['nav_id'], nav_name=session['nav_name'])
    else:

        f = open('static/bokehscripts/'+session['vars']['hid']+'geodiv.p', "rb")
        tdiv = pickle.load(f)
        tscript = open('static/bokehscripts/'+session['vars']['hid']+'geoscript.js','r').read()
        ######render
        return render_template('pubview.html', searchstring=session['vars']['searchStr'], script=tscript, div=tdiv, curpage=session['curpage'], nav_id=session['nav_id'], nav_name=session['nav_name'])


def similarityCalc(ss,sy,ey,rstr,abstractsim):

    simplot = smp.similarityGraph(ss,sy,ey,app.sqldb,abstractsim)
    # try_count = 0
    # while try_count<6:
    #     try_count += 1
    #     try:
    #         simplot = smp.similarityGraph(ss,sy,ey,lp,app.sqldb)
    #         break
    #     except Exception as e:
    #         print("Error getting similarity data")
    #         print(e)
    #         simplot = 0

    script, div = components({'simplot': simplot})

    if(abstractsim):
        outscript = rstr+"simabscript.js"
        outdiv = rstr+"simabdiv.p"
    else:
        outscript = rstr+"simscript.js"
        outdiv = rstr+"simdiv.p"

    with open("static/bokehscripts/"+outscript,"w") as file:
        #remove JS tags
        file.write(script)
        file.close()


    with open("static/bokehscripts/"+outdiv,"wb") as file:
        #remove JS tags
        pickle.dump(div, file)
        file.close()

    print("Finished sim calc", flush=True)

@app.route('/similarity', methods=['GET','POST'])
def similarityView():


    #if button is clicked before search is performed
    if 'vars' not in session:
        #return to homepage if data isn't here and user got the url
        return redirect(url_for('index'), code=307)

    session['curpage'] = "similarity"

    d_file = Path('static/bokehscripts/'+session['vars']['hid']+'simdiv.p')
    s_file = Path('static/bokehscripts/'+session['vars']['hid']+'simscript.js')

    #delete file if user asks to delete
    if 'delete' in request.form:

        if('calcsim' in session['vars']):
            del session['vars']['calcsim']
        if s_file.is_file():
            os.remove(s_file)
        if d_file.is_file():
            os.remove(d_file)

    if not s_file.is_file() or not d_file.is_file():
    #if 'similarity' not in session['vars']:

        if request.method == 'GET':
            #return to homepage if data isn't here and user got the url
            return redirect(url_for('index'), code=307)

        # session['vars']['similarity'] = True
        if 'calcsim' not in session['vars']:

            #global loop

            print("calc sim")
            # q1.put(session['vars']['searchStr'])
            # q1.put('1975')
            # q1.put('2017')

            t = Thread(target=similarityCalc,args=(session['vars']['searchStr'],'1800','3000',session['vars']['hid'],False))
            t.start()
            session['vars']['calcsim'] = True
        else:
            #print("waiting to reload")
            time.sleep(5)

        ######render, render with script instead of simscript first time, fixes issue with gcloud not loading file when it is generated immediately
            #waiting for calculations to finish, load dummy info into the page
        waiting = {"simplot":"<br><br><br><center><b>Similarity Plot is being calculated, page will load when completed.</b><br><img src='/static/loading.gif' /></center>"}
        return render_template('pubview.html', searchstring=session['vars']['searchStr'], script="reload", div=waiting, curpage=session['curpage'], nav_id=session['nav_id'], nav_name=session['nav_name'])
    else:
        #load in div and script info for the specified search
        f = open('static/bokehscripts/'+session['vars']['hid']+'simdiv.p', "rb")
        session['simdiv'] = pickle.load(f)
        script = open('static/bokehscripts/'+session['vars']['hid']+'simscript.js','r').read()

        ######render
        return render_template('pubview.html', searchstring=session['vars']['searchStr'], script=script, div=session['simdiv'], curpage=session['curpage'], nav_id=session['nav_id'], nav_name=session['nav_name'])

@app.route('/similarityab', methods=['GET','POST'])
def similarityAbstractView():


    #if button is clicked before search is performed
    if 'vars' not in session:
        #return to homepage if data isn't here and user got the url
        return redirect(url_for('index'), code=307)

    session['curpage'] = "similarityab"

    d_file = Path('static/bokehscripts/'+session['vars']['hid']+'simabdiv.p')
    s_file = Path('static/bokehscripts/'+session['vars']['hid']+'simabscript.js')

    #delete file if user asks to delete
    if 'delete' in request.form:

        if('calcabsim' in session['vars']):
            del session['vars']['calcabsim']
        if s_file.is_file():
            os.remove(s_file)
        if d_file.is_file():
            os.remove(d_file)

    if not s_file.is_file() or not d_file.is_file():
    #if 'similarity' not in session['vars']:

        if request.method == 'GET':
            #return to homepage if data isn't here and user got the url
            return redirect(url_for('index'), code=307)

        # session['vars']['similarity'] = True
        if 'calcabsim' not in session['vars']:

            #global loop

            print("calc sim")

            t = Thread(target=similarityCalc,args=(session['vars']['searchStr'],'1800','3000',session['vars']['hid'],True))
            t.start()
            session['vars']['calcabsim'] = True
        else:
            #print("waiting to reload")
            time.sleep(5)


        waiting = {"simplot":"<br><br><br><center><b>Similarity Plot is being calculated, page will load when completed.</b><br><img src='/static/loading.gif' /></center>"}
        return render_template('pubview.html', searchstring=session['vars']['searchStr'], script="reload", div=waiting, curpage=session['curpage'], nav_id=session['nav_id'], nav_name=session['nav_name'])
    else:
        #load in div and script info for the specified search
        f = open('static/bokehscripts/'+session['vars']['hid']+'simabdiv.p', "rb")
        session['simabdiv'] = pickle.load(f)
        script = open('static/bokehscripts/'+session['vars']['hid']+'simabscript.js','r').read()

        ######render
        return render_template('pubview.html', searchstring=session['vars']['searchStr'], script=script, div=session['simabdiv'], curpage=session['curpage'], nav_id=session['nav_id'], nav_name=session['nav_name'])


@app.route('/abstractsearch', methods=['GET','POST'])
def abstractSearchView():

    session['curpage'] = "abstractsearch"

    if 'abstract' not in request.form:
        #return search page for user, haven't completed search
        print("Sending to search page")
        return redirect(url_for('enterAbstract'), code=307)

    else:

        #checks if search term is present to pass along, might not be there for abstract search
        if 'vars' in session:
            if 'searchStr' in session['vars']:
                ss = session['vars']['searchStr']
            else:
                ss = ''
        else:
            ss = ''

        if 'abstract_thread' not in session:

            session['abstract_in'] = request.form['abstract']
            rstr = hashlib.sha256(session['abstract_in'].lower().encode('utf8')).hexdigest()
            session['abfile'] = 'static/abstractdivs/'+rstr+'abstractdiv.html'

            print("Finding similar abstracts")
            #change variable here
            t = Thread(target=absr.abstractSearch,args=(app.sqldb,session['abfile'],session['abstract_in']))
            t.start()
            session['abstract_thread'] = True
        else:
            #print("waiting to reload")
            time.sleep(5)

        # f = open('static/bokehscripts/'+session['vars']['hid']+'yeardiv.p', "rb")
        # tdiv = pickle.load(f)
        # tscript = open('static/bokehscripts/'+session['vars']['hid']+'yearscript.js','r').read()
        ######render

        d_file = Path(session['abfile'])
        if not d_file.is_file():
            div = "<br><br><br><center><b>Similarity Plot is being calculated, page will load when completed.</b><br><img src='/static/loading.gif' /></center>"
            return render_template('pubview.html', searchstring=ss, script='reload', div=div, curpage=session['curpage'], nav_id=session['nav_id'], nav_name=session['nav_name'])
        else:
            div = open(session['abfile'],'r').read()
            return render_template('pubview.html', searchstring=ss, script='', div=div, curpage=session['curpage'], nav_id=session['nav_id'], nav_name=session['nav_name'])



@app.route('/enterabstract', methods=['GET','POST'])
def enterAbstract():

    session['curpage'] = 'enterabstract'

    try:
        del session['abstract_thread']
    except:
        pass

    tdiv = open('static/abstractdiv.html','r').read()
    tscript = 'none'

    #checks if search term is present to pass along, might not be there for abstract search
    if 'vars' in session:
        if 'searchStr' in session['vars']:
            ss = session['vars']['searchStr']
        else:
            ss = ''
    else:
        ss = ''


    #put div and script here for abstract search
    return render_template('pubview.html', searchstring=ss, script=tscript, div=tdiv, curpage=session['curpage'], nav_id=session['nav_id'], nav_name=session['nav_name'])


if __name__ == "__main__":
    app.run(port=33507)
