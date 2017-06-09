###Main page: PubmedApp
#mainspot


import string as st
import random
from flask import Flask, render_template, request, redirect, session
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

#setting up navigation info


@app.route('/', methods=['GET', 'POST'])
def index():
    # nquestions=app_lulu.nquestions
    if request.method == 'GET':

        session['nav_id'] = {'counts':'counts','geo':'geo','similarity':'similarity'}
        session['nav_name'] = {'counts':'Raw Counts','geo':'Geographic','similarity':'Visualize Article Similarity'}

        return render_template('pubsearch.html')
    else:

        session['vars']  = {}

#         app.vars['cancertype'] = request.form['cancertype']

#         p1 = pdp.pubByDate(app.vars['cancertype'], False)
#         p2 = pdp.pubByDate(app.vars['cancertype'], True)
#         p3, p4 = stateGraph(app.vars['cancertype'])
#         plots = {'p1': p1, 'p2': p2, 'p3': p3, 'p4': p4}
#         script, div = components(plots)

        #return render_template('pubsearch.html', script=script, div=div, ctype=app.vars['cancertype'])
        return render_template('pubsearch.html')



@app.route('/search', methods=['GET', 'POST'])
def searchView():
    if request.method == 'GET':
        session['vars'] = {}
        return render_template('pubsearch.html')
    else:
        session['vars'] = {}
        session['vars']['searchStr'] = request.form['searchterm']
        return countsView()



@app.route('/counts', methods=['POST'])
def countsView():
    session['curpage'] = "counts"
    if 'countsData' not in session['vars']:

        #generate random 20 char string as identifier

        #app.vars['countsData'] = rstr
        session['vars']['countsData'] = True

#         while True:
#             try:
#                 app.yearplot = yearGraph(app.vars['searchStr'])
#                 break
#             except:
#                 print("Error getting year data")

        rstr = ''.join(random.choices(st.ascii_letters + st.digits, k=20))
        #app.yearplot = yearGraph(app.vars['searchStr'],1975,2017)
        yearplot = pdp.yearGraph(session['vars']['searchStr'],1975,2017)
        script, session['yeardiv'] = components({'yearplot': yearplot})

        ###########MODIFY CODE IN OTHER AREAS TO DO SAME THING, ALSO ADD RANDOM KEY FOR FILE STORAGE INSTEAD OF 'outputtemp.js'
        session['yearscript'] = rstr+".js"
        with open("static/bokehscripts/"+session['yearscript'],"w") as file:
                #remove JS tags
                file.write(script[32:-9])
                file.close()


        ######render
        return render_template('pubview.html', searchstring=session['vars']['searchStr'], script=session['yearscript'], div=session['yeardiv'], curpage=session['curpage'], nav_id=session['nav_id'], nav_name=session['nav_name'])
    else:

        ######render
        return render_template('pubview.html', searchstring=session['vars']['searchStr'], script=session['yearscript'], div=session['yeardiv'], curpage=session['curpage'], nav_id=session['nav_id'], nav_name=session['nav_name'])




@app.route('/geo', methods=['POST'])
def geoView():
    session['curpage'] = "geo"
    if 'geoData' not in session['vars']:
        session['vars']['geoData'] = True

        #connect to Pubmed and try to get data, if fail restart
#         while True:
#             try:
#                 app.stateplot, app.stateplotnorm = stateGraph(app.vars['searchStr'])
#                 break
#             except:
#                 print("Error getting state data")
        #app.stateplot = stateGraph(app.vars['searchStr'],"1975/01/01","2016/12/31")

        rstr = ''.join(random.choices(st.ascii_letters + st.digits, k=20))
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
        return render_template('pubview.html', searchstring=session['vars']['searchStr'], script=session['statescript'], div=session['statediv'], curpage=session['curpage'], nav_id=session['nav_id'], nav_name=session['nav_name'])
    else:

        ######render
        return render_template('pubview.html', searchstring=session['vars']['searchStr'], script=session['statescript'], div=session['statediv'], curpage=session['curpage'], nav_id=session['nav_id'], nav_name=session['nav_name'])




@app.route('/similarity', methods=['POST'])
def similarityView():
    session['curpage'] = "similarity"
    if 'similarity' not in session['vars']:
        session['vars']['similarity'] = True

        #app.simplot = similarityGraph(app.vars['searchStr'], '1975', '2017')
        #app.simplot = smp.similarityGraph(app.vars['searchStr'], '1975', '2017')
        #app.script, app.div = components({'column_div': app.simplot})

        rstr = ''.join(random.choices(st.ascii_letters + st.digits, k=20))
        #app.yearplot = yearGraph(app.vars['searchStr'],1975,2017)
        simplot = smp.similarityGraph(session['vars']['searchStr'],'1975', '2017')
        script, session['simdiv'] = components({'column_div': simplot})

        ###########MODIFY CODE IN OTHER AREAS TO DO SAME THING, ALSO ADD RANDOM KEY FOR FILE STORAGE INSTEAD OF 'outputtemp.js'
        session['simscript'] = rstr+".js"
        with open("static/bokehscripts/"+session['simscript'],"w") as file:
                #remove JS tags
                file.write(script[32:-9])
                file.close()

        ######render
        return render_template('pubview.html', searchstring=session['vars']['searchStr'], script=session['simscript'], div=session['simdiv'], curpage=session['curpage'], nav_id=session['nav_id'], nav_name=session['nav_name'])
    else:
        ######render
        return render_template('pubview.html', searchstring=session['vars']['searchStr'], script=session['simscript'], div=session['simdiv'], curpage=session['curpage'], nav_id=session['nav_id'], nav_name=session['nav_name'])



if __name__ == "__main__":
    app.run(port=33507)
