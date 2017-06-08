###Main page: PubmedApp
#mainspot


#import string as st
from flask import Flask, render_template, request, redirect
from bokeh.embed import components
import PubDatePlotting as pdp
import StateGraph as sg
import SimilarityPlot as smp

#####started kv insertion##########
import redis
#from flask import Flask
from flask_kvsession import KVSessionExtension
from simplekv.memory.redisstore import RedisStore

store = RedisStore(redis.StrictRedis())

app = Flask(__name__)
KVSessionExtension(store, app)
####end kv insertion, uncomment flask(__name__) below if needed########
# output_notebook()

#app = Flask(__name__)

app.vars = {}

#setting up navigation info

app.nav_id = {'counts':'counts','geo':'geo','similarity':'similarity'}
app.nav_name = {'counts':'Raw Counts','geo':'Geographic','similarity':'Visualize Article Similarity'}


@app.route('/', methods=['GET', 'POST'])
def index():
    # nquestions=app_lulu.nquestions
    if request.method == 'GET':
        return render_template('pubsearch.html')
    else:

        del app.vars

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
        app.vars = {}
        return render_template('pubsearch.html')
    else:
        app.vars = {}
        app.vars['searchStr'] = request.form['searchterm']
        return countsView()



@app.route('/counts', methods=['POST'])
def countsView():
    app.curpage = "counts"
    if 'countsData' not in app.vars:

        #generate random 20 char string as identifier
        #rstr = ''.join(random.choices(string.ascii_letters + string.digits, k=20))
        #app.vars['countsData'] = rstr
        app.vars['countsData'] = True

#         while True:
#             try:
#                 app.yearplot = yearGraph(app.vars['searchStr'])
#                 break
#             except:
#                 print("Error getting year data")
        #app.yearplot = yearGraph(app.vars['searchStr'],1975,2017)
        app.yearplot = pdp.yearGraph(app.vars['searchStr'],1975,2017)
        plots = {'yearplot': app.yearplot}
        script, div = components(plots)


        ######render
        return render_template('pubview.html', searchstring=app.vars['searchStr'], script=script, div=div, curpage=app.curpage, nav_id=app.nav_id, nav_name=app.nav_name)
    else:


        plots = {'yearplot': app.yearplot}
        script, div = components(plots)

        ######render
        return render_template('pubview.html', searchstring=app.vars['searchStr'], script=script, div=div, curpage=app.curpage, nav_id=app.nav_id, nav_name=app.nav_name)




@app.route('/geo', methods=['POST'])
def geoView():
    app.curpage = "geo"
    if 'geoData' not in app.vars:
        app.vars['geoData'] = True

        #connect to Pubmed and try to get data, if fail restart
#         while True:
#             try:
#                 app.stateplot, app.stateplotnorm = stateGraph(app.vars['searchStr'])
#                 break
#             except:
#                 print("Error getting state data")
        #app.stateplot = stateGraph(app.vars['searchStr'],"1975/01/01","2016/12/31")
        app.stateplot = sg.stateGraph(app.vars['searchStr'],"1975/01/01","2016/12/31")
        plots = {'stateplot': app.stateplot}
        script, div = components(plots)

        ######render
        return render_template('pubview.html', searchstring=app.vars['searchStr'], script=script, div=div, curpage=app.curpage, nav_id=app.nav_id, nav_name=app.nav_name)
    else:

        plots = {'stateplot': app.stateplot}
        script, div = components(plots)

        ######render
        return render_template('pubview.html', searchstring=app.vars['searchStr'], script=script, div=div, curpage=app.curpage, nav_id=app.nav_id, nav_name=app.nav_name)




@app.route('/similarity', methods=['POST'])
def similarityView():
    app.curpage = "similarity"
    if 'similarity' not in app.vars:
        app.vars['similarity'] = True

        #app.simplot = similarityGraph(app.vars['searchStr'], '1975', '2017')
        app.simplot = smp.similarityGraph(app.vars['searchStr'], '1975', '2017')
        script, div = components({'column_div': app.simplot})
        ######render
        return render_template('pubview.html', searchstring=app.vars['searchStr'], script=script, div=div, curpage=app.curpage, nav_id=app.nav_id, nav_name=app.nav_name)
    else:
        script, div = components({'column_div': app.simplot})
        ######render
        return render_template('pubview.html', searchstring=app.vars['searchStr'], script=script, div=div, curpage=app.curpage, nav_id=app.nav_id, nav_name=app.nav_name)



if __name__ == "__main__":
    app.run(port=33507)
