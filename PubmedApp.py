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

q2 = Queue()
tq = Queue()
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
        return redirect(url_for('countsView'), code=307)



@app.route('/counts', methods=['GET','POST'])
def countsView():
    session['curpage'] = "counts"
    if 'countsData' not in session['vars']:
        if request.method == 'GET':
            #return to homepage if data isn't here and user got the url
            return redirect(url_for('index'), code=307)

        #app.vars['countsData'] = rstr
        session['vars']['countsData'] = True

#         while True:
#             try:
#                 app.yearplot = yearGraph(app.vars['searchStr'])
#                 break
#             except:
#                 print("Error getting year data")
        rstr = ''
        for idx in range(20):
            rstr += rnd.choice(st.ascii_letters + st.digits)
        #rstr = ''.join(rnd.choices(st.ascii_letters + st.digits, k=20))
        #app.yearplot = yearGraph(app.vars['searchStr'],1975,2017)
        yearplot = pdp.yearGraph(session['vars']['searchStr'],1975,2017)
        script, session['yeardiv'] = components({'yearplot': yearplot})

        session['yearscript'] = rstr+".js"
        with open("static/bokehscripts/"+session['yearscript'],"w") as file:
                #remove JS tags
                file.write(script[32:-9])
                file.close()


        ######render
        return render_template('pubview.html', searchstring=session['vars']['searchStr'], script=script, div=session['yeardiv'], curpage=session['curpage'], nav_id=session['nav_id'], nav_name=session['nav_name'],firstload="True")
    else:

        ######render
        return render_template('pubview.html', searchstring=session['vars']['searchStr'], script=session['yearscript'], div=session['yeardiv'], curpage=session['curpage'], nav_id=session['nav_id'], nav_name=session['nav_name'],firstload="False")




@app.route('/geo', methods=['GET','POST'])
def geoView():
    session['curpage'] = "geo"
    if 'geoData' not in session['vars']:

        if request.method == 'GET':
            #return to homepage if data isn't here and user got the url
            return redirect(url_for('index'), code=307)

        session['vars']['geoData'] = True

        #connect to Pubmed and try to get data, if fail restart
#         while True:
#             try:
#                 app.stateplot, app.stateplotnorm = stateGraph(app.vars['searchStr'])
#                 break
#             except:
#                 print("Error getting state data")
        #app.stateplot = stateGraph(app.vars['searchStr'],"1975/01/01","2016/12/31")

        rstr = ''
        for idx in range(20):
            rstr += rnd.choice(st.ascii_letters + st.digits)

        #rstr = ''.join(rnd.choices(st.ascii_letters + st.digits, k=20))
        #app.yearplot = yearGraph(app.vars['searchStr'],1975,2017)
        stateplot = sg.stateGraph(session['vars']['searchStr'],"1975/01/01","2016/12/31")
        script, session['statediv'] = components({'stateplot': stateplot})

        ###########MODIFY CODE IN OTHER AREAS TO DO SAME THING, ALSO ADD RANDOM KEY FOR FILE STORAGE INSTEAD OF 'outputtemp.js'
        session['statescript'] = rstr+".js"
        with open("static/bokehscripts/"+session['statescript'],"w") as file:
                #remove JS tags
                file.write(script[32:-9])
                file.close()


        ######render
        return render_template('pubview.html', searchstring=session['vars']['searchStr'], script=script, div=session['statediv'], curpage=session['curpage'], nav_id=session['nav_id'], nav_name=session['nav_name'],firstload="True")
    else:

        ######render
        return render_template('pubview.html', searchstring=session['vars']['searchStr'], script=session['statescript'], div=session['statediv'], curpage=session['curpage'], nav_id=session['nav_id'], nav_name=session['nav_name'],firstload="False")


def similarityCalc(ss,sy,ey,lp,rstr):

    simplot = smp.similarityGraph(ss,sy,ey,lp)
    script, outdiv = components({'simplot': simplot})

    ###########MODIFY CODE IN OTHER AREAS TO DO SAME THING, ALSO ADD RANDOM KEY FOR FILE STORAGE INSTEAD OF 'outputtemp.js'
    outscript = rstr+".js"

    with open("static/bokehscripts/"+outscript,"w") as file:
            #remove JS tags
            file.write(script[32:-9])
            file.close()
    print("Finished sim calc", flush=True)

    global q2
    q2.put(rstr)
    q2.put(outdiv)
    q2.put(outscript)

@app.route('/similarity', methods=['GET','POST'])
def similarityView():
    session['curpage'] = "similarity"
    if 'similarity' not in session['vars']:

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

            rstr = ''
            for idx in range(20):
                rstr += rnd.choice(st.ascii_letters + st.digits)

            session['vars']['qid'] = rstr

            t = Thread(target=similarityCalc,args=(session['vars']['searchStr'],'1975','2017',loop,rstr))
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
        if q2.empty():
            print("Reloaded, waiting for queue generation")
            script = ""

            #waiting for calculations to finish, load dummy info into the page
            waiting = {"simplot":"<br><br><br><center><b>Similarity Plot is being calculated, page will load when completed.</b><br><img src='/static/loading.gif' /></center>"}
            return render_template('pubview.html', searchstring=session['vars']['searchStr'], script=script, div=waiting, curpage=session['curpage'], nav_id=session['nav_id'], nav_name=session['nav_name'],firstload="False")
        else:
            print("Q2 found")
            while not q2.empty():
                #loop through queue to find data, sorta hacky but I don't want to implement celery with gunicorn
                qid = q2.get()
                sd = q2.get()
                ss = q2.get()
                if(qid == session['vars']['qid']):
                    session['simdiv'] = sd
                    session['simscript'] = ss
                    break
                else:
                    tq.put(qid)
                    tq.put(sd)
                    tq.put(ss)
            #refill queue for other users queries
            while not tq.empty():
                q2.put(tq.get())

            #this conditional checks if there is another users info in the queue, but it hasn't been picked up yet. Shouldn't occur too frequently but need to check
            if('simdiv' not in session):
                waiting = {"simplot":"<br><br><br><center><b>Similarity Plot is being calculated, page will load when completed.</b><br><img src='/static/loading.gif' /></center>"}
                return render_template('pubview.html', searchstring=session['vars']['searchStr'], script=script, div=waiting, curpage=session['curpage'], nav_id=session['nav_id'], nav_name=session['nav_name'],firstload="False")
            else:
                session['vars']['similarity'] = True
                return render_template('pubview.html', searchstring=session['vars']['searchStr'], script=session['simscript'], div=session['simdiv'], curpage=session['curpage'], nav_id=session['nav_id'], nav_name=session['nav_name'],firstload="False")
    else:
        ######render
        return render_template('pubview.html', searchstring=session['vars']['searchStr'], script=session['simscript'], div=session['simdiv'], curpage=session['curpage'], nav_id=session['nav_id'], nav_name=session['nav_name'],firstload="False")



if __name__ == "__main__":
    app.run(port=33507)
