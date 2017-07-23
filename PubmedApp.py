###Main page: PubmedApp
#mainspot

from threading import Thread
from queue import Queue

import time
import asyncio
import string as st
import random as rnd
print(rnd.__file__)
from flask import Flask, render_template, request, redirect, session, url_for
from bokeh.embed import components
import PubDatePlotting as pdp
import StateGraph as sg
import SimilarityPlot as smp
import hashlib
from pathlib import Path
import pickle
#####started kv insertion##########
#import redis
#from flask import Flask
#from flask_kvsession import KVSessionExtension
#from simplekv.memory.redisstore import RedisStore


#store = RedisStore(redis.StrictRedis())

#app = Flask(__name__)
#KVSessionExtension(store, app)
####end kv insertion, uncomment flask(__name__) below if needed########
# output_notebook()

app = Flask(__name__)
app.secret_key = 'VA&Dnadf8%$$#JK9SDA64asf54@!^&'

loop = asyncio.get_event_loop()

#setting up navigation info

@app.route('/', methods=['GET', 'POST'])
def index():
    # nquestions=app_lulu.nquestions
    if request.method == 'GET':

        #### CHANGE TO ORDERED DICT OR LIST SO THAT INFO IS SENT IN ORDER, NAV ORDER IS CHANGING AFTER PAGE LOAD
        #session['nav_id'] = {'counts':'counts','geo':'geo','similarity':'similarity'}
        #session['nav_name'] = {'counts':'Raw Counts','geo':'Geographic','similarity':'Visualize Article Similarity'}
        session['nav_id'] = ['counts','geo','similarity']
        session['nav_name'] = ['Raw Counts','Geographic','Visualize Article Similarity']

        return render_template('pubsearch.html')
    else:

        session['vars']  = {}
        return render_template('pubsearch.html')



@app.route('/search', methods=['GET', 'POST'])
def searchView():
    if request.method == 'GET':
        session['vars'] = {}
        return render_template('pubsearch.html')
    else:
        session['vars'] = {}
        session['vars']['searchStr'] = request.form['searchterm']

        #hash the filename for uniqueness
        rstr = hashlib.sha256(session['vars']['searchStr'].lower().encode('utf8')).hexdigest()
        session['vars']['hid'] = rstr

        return countsView()



@app.route('/counts', methods=['GET','POST'])
def countsView():
    session['curpage'] = "counts"


    d_file = Path('static/bokehscripts/'+session['vars']['hid']+'yeardiv.p')
    s_file = Path('static/bokehscripts/'+session['vars']['hid']+'yearscript.js')

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




@app.route('/geo', methods=['GET','POST'])
def geoView():
    session['curpage'] = "geo"



    d_file = Path('static/bokehscripts/'+session['vars']['hid']+'geodiv.p')
    s_file = Path('static/bokehscripts/'+session['vars']['hid']+'geoscript.js')

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


def similarityCalc(ss,sy,ey,lp,rstr):

    simplot = smp.similarityGraph(ss,sy,ey,lp)
    script, div = components({'simplot': simplot})

    ###########MODIFY CODE IN OTHER AREAS TO DO SAME THING, ALSO ADD RANDOM KEY FOR FILE STORAGE INSTEAD OF 'outputtemp.js'
    outscript = rstr+"simscript.js"

    with open("static/bokehscripts/"+outscript,"w") as file:
            #remove JS tags
            file.write(script)
            file.close()

    outdiv = rstr+"simdiv.p"
    with open("static/bokehscripts/"+outdiv,"wb") as file:
            #remove JS tags
            pickle.dump(div, file)
            file.close()

    print("Finished sim calc", flush=True)

@app.route('/similarity', methods=['GET','POST'])
def similarityView():


    session['curpage'] = "similarity"

    d_file = Path('static/bokehscripts/'+session['vars']['hid']+'simdiv.p')
    s_file = Path('static/bokehscripts/'+session['vars']['hid']+'simscript.js')

    if not s_file.is_file() or not d_file.is_file():
    #if 'similarity' not in session['vars']:

        if request.method == 'GET':
            #return to homepage if data isn't here and user got the url
            return redirect(url_for('index'), code=307)

        # session['vars']['similarity'] = True
        if 'calcsim' not in session['vars']:

            global loop

            print("calc sim")
            # q1.put(session['vars']['searchStr'])
            # q1.put('1975')
            # q1.put('2017')

            t = Thread(target=similarityCalc,args=(session['vars']['searchStr'],'1975','2017',loop,session['vars']['hid']))
            t.start()
            session['vars']['calcsim'] = True
        else:
            print("waiting to reload")
            time.sleep(5)

        # rstr = ''
        # for idx in range(20):
        #     rstr += rnd.choice(st.ascii_letters + st.digits)
        #
        # #rstr = ''.join(rnd.choices(st.ascii_letters + st.digits, k=20))
        # #app.yearplot = yearGraph(app.vars['searchStr'],1975,2017)
        # simplot = smp.similarityGraph(session['vars']['searchStr'],'1975', '2017')
        # script, session['simdiv'] = components({'column_div': simplot})
        #
        # ###########MODIFY CODE IN OTHER AREAS TO DO SAME THING, ALSO ADD RANDOM KEY FOR FILE STORAGE INSTEAD OF 'outputtemp.js'
        # session['simscript'] = rstr+".js"
        # with open("static/bokehscripts/"+session['simscript'],"w") as file:
        #         #remove JS tags
        #         file.write(script[32:-9])
        #         file.close()

        ######render, render with script instead of simscript first time, fixes issue with gcloud not loading file when it is generated immediately
            #waiting for calculations to finish, load dummy info into the page
        waiting = {"simplot":"<br><br><br><center><b>Similarity Plot is being calculated, page will load when completed.</b><br><img src='/static/loading.gif' /></center>"}
        return render_template('pubview.html', searchstring=session['vars']['searchStr'], script="", div=waiting, curpage=session['curpage'], nav_id=session['nav_id'], nav_name=session['nav_name'])
        # else:
        #     print("script found")

            #SHOULD DELETE THIS QUEUE CRAP AT SOME POINT AND SWITCH TO SOMETHING LIKE CELERY SO APP CAN SCALE
            # while not q2.empty():
            #     #loop through queue to find data, sorta hacky but I don't want to implement celery with gunicorn
            #     qid = q2.get()
            #     sd = q2.get()
            #     ss = q2.get()
            #     if(qid == session['vars']['qid']):
            #         session['simdiv'] = sd
            #         session['simscript'] = ss
            #         break
            #     else:
            #         tq.put(qid)
            #         tq.put(sd)
            #         tq.put(ss)
            # #refill queue for other users queries
            # while not tq.empty():
            #     q2.put(tq.get())

            #this conditional checks if there is another users info in the queue, but it hasn't been picked up yet. Shouldn't occur too frequently but need to check
            # if('simdiv' not in session):
            #     waiting = {"simplot":"<br><br><br><center><b>Similarity Plot is being calculated, page will load when completed.</b><br><img src='/static/loading.gif' /></center>"}
            #     return render_template('pubview.html', searchstring=session['vars']['searchStr'], script=script, div=waiting, curpage=session['curpage'], nav_id=session['nav_id'], nav_name=session['nav_name'],firstload="False")
            # else:
            # session['vars']['similarity'] = True
            # return render_template('pubview.html', searchstring=session['vars']['searchStr'], script=session['simscript'], div=session['simdiv'], curpage=session['curpage'], nav_id=session['nav_id'], nav_name=session['nav_name'],firstload="False")
    else:
        #load in div and script info for the specified search
        f = open('static/bokehscripts/'+session['vars']['hid']+'simdiv.p', "rb")
        session['simdiv'] = pickle.load(f)
        script = open('static/bokehscripts/'+session['vars']['hid']+'simscript.js','r').read()

        ######render
        return render_template('pubview.html', searchstring=session['vars']['searchStr'], script=script, div=session['simdiv'], curpage=session['curpage'], nav_id=session['nav_id'], nav_name=session['nav_name'])



if __name__ == "__main__":
    app.run(port=33507)
