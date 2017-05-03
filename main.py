import datetime
import sqlite3 as sql
import json
from math import pi
import pandas as pd
import feedparser as fp
from bokeh.plotting import figure
from bokeh.charts import Horizon, output_file, show
from bokeh.embed import file_html
import bokeh.models
from validate_email import validate_email
from passlib.hash import bcrypt
from flask import Flask, render_template, request, session
app = Flask(__name__)
app.secret_key = bcrypt.hash("2pacisalive")
sqlitedb = 'ssw215.db'

@app.route('/')
def index():
	logCheck = 0
	sid = session.get('uid');
	titleArray = []
	if sid:
		logCheck = sid
	else:
		logCheck = 0
	try:
		dbconn = sql.connect(sqlitedb)
		cur = dbconn.cursor()
		sel = cur.execute("SELECT `ticker` FROM `favs` WHERE `ownerid` = (?) AND `type` = ?", (sid, 0))
		test = sel.fetchall()
		favtemp = []
		rsstemp = []
		rectemp = []
		for fav in test:
			favtemp.append(fav[0]) #outputs an array of all of the fav'd tickers [WMT, GOOG, etc]
			
		sel2 = cur.execute("SELECT `ticker` FROM `favs` WHERE `ownerid` = (?) AND `type` = ?", (sid, 1))
		test2 = sel2.fetchall()
		for rec in test2:
			rectemp.append(rec[0])	
			
		rssfeed = fp.parse("https://finance.yahoo.com/rss/topfinstories")
		rsstitle = rssfeed.entries[0].title_detail.value
		rssdesc = rssfeed.entries[0].summary
		for x in range(10):
			rsstemp.append([rssfeed.entries[x].title_detail.value, rssfeed.entries[x].link])
	
		dbconn.close()
	except:
		test = "DB Connection Failure"
	return render_template('index.html', favs=favtemp, recent=rectemp, name='index', logcheck=logCheck, titleA=rsstemp)	
	
@app.route('/register', methods=['POST'])
def register():
	final = 0
	email = request.form.get('email')
	password1 = request.form.get('pw1')
	try:
		dbconn = sql.connect(sqlitedb)
		dbconn.text_factory = str
		cur = dbconn.cursor()
		sel = cur.execute("SELECT * FROM `users` WHERE `email` = ? ", (email,))
		finder = sel.fetchone()
		eCheck = validate_email(email)
		if session.get('uid'):
			final = "You are already logged in."
		elif finder:
			final = "An account with that email already exists."
		elif not eCheck:
			final = "Invalid email."
		else:
			hashedPass = bcrypt.hash(password1)
			final = "registered"
			insertU = cur.execute("INSERT INTO `users` (email, pass) VALUES (?, ?)", (email, hashedPass))
			dbconn.commit()

		dbconn.close()
	except:
			final = "Couldn't connect to the database. Please reload."
		
	return final
@app.route('/login', methods=['POST'])
def login():
	final = 0
	email = request.form.get('email')
	password = request.form.get('pw')
	try:
		dbconn = sql.connect(sqlitedb)
		dbconn.text_factory = str
		cur = dbconn.cursor()
		sel = cur.execute("SELECT * FROM `users` WHERE `email` = (?) ", (email,))
		finder = sel.fetchone()
		if session.get('uid'):
			final = "You are already logged in."
		elif not finder:
			final = "Sorry, that E-mail doesn't exist."
		elif not bcrypt.verify(password, finder[2]):
			final = "Sorry, that is the wrong password."
		elif bcrypt.verify(password, finder[2]) and finder:
			final = "logged"
			session['uid'] = finder[0]
		else:
			final = "An unexpected error occured. Please try again."
		dbconn.close()
	except:
		final = "Couldn't connect to the database. Please reload."
		
	return final
	
@app.route('/logout')
def logout():
	final = ""
	session.pop('uid', None)
	return final

@app.route('/favs', methods=['POST'])
def favs():
	final = 0
	dbconn = sql.connect(sqlitedb)
	dbconn.text_factory = str
	cur = dbconn.cursor()
	tickPost = request.form.get('ticker')
	typePost = request.form.get('type')
	sid = session.get('uid');
	if typePost == 'fav':
		sel = cur.execute("SELECT * FROM `favs` WHERE `ownerid` = ? AND `ticker` = ? AND `type` = ?", (sid, tickPost, 0))
		duplicate = sel.fetchall()
		if not duplicate:
			insertU = cur.execute("INSERT INTO `favs` (ownerid, ticker) VALUES (?, ?)", (sid, tickPost))
			dbconn.commit()
			final = "Added to favorites."
		else:
			final = "Already in your favorites!"
	elif typePost == 'ufav':
		deleteU = cur.execute("DELETE FROM `favs` WHERE `ownerid` = ? AND `ticker` = ?", (sid, tickPost))
		dbconn.commit()
		final = "Deleted from favorites."
	else:
		final = "There was an error."
	return final

@app.route('/rec')
def rec():
    return render_template('index.html', name='rec')
	
@app.route('/stock/<stockid>')
def stocks(stockid):
	y1 = request.args.get('y1')	#older year
	y2 = request.args.get('y2')	#more recent year
	m1 = request.args.get('m1')	#month
	m2 = request.args.get('m2')
	fcolor = "#31A354"
	dbconn = sql.connect(sqlitedb)
	dbconn.text_factory = str
	cur = dbconn.cursor()
	sid = session.get('uid');
	
	try:
		url = "http://ichart.yahoo.com/table.csv?s=" + stockid + "&a=" + m1 + "&b=01&c=" + y1 + "&d=" + m2 + "&e=01&f=" + y2	#pulls numbers for graphs from icharts with fill-in-the-blanks
		stock = pd.read_csv(url, parse_dates=['Date'])	#parses data by date
		title = stockid + " Price (USD)"	#graph title
		data = dict([
			(stockid, stock['Adj Close']),
			('Date', stock['Date'])
		])
	
		hover = bokeh.models.HoverTool(		#this creates tooltips, and this is for the price (y-axis), the dates are not all there so don't bother with dates
			tooltips=[
				("Price", "$y USD"),
			]
		)

		total = 0
		for z in range(5):
			total = total + stock['Adj Close'][z]	#calculates 5day average and if average>current, it's obviously decreasing, average<current, increasing
		 
		if(stock['Adj Close'][0] <= total/5):
			fcolor = "#DE2D26"
		else:
			fcolor = "#31A354"
		
		if sid:
			select = cur.execute("SELECT COUNT(*) FROM `favs` WHERE `ownerid` = ? AND `ticker` = ?", (sid, stockid))
			fetcher = select.fetchone()
			if fetcher[0] == 0:	#checks for fav/recent of this ticker already
				sel = cur.execute("SELECT COUNT(*) FROM `favs` WHERE `ownerid` = ? AND `type` = ?", (sid, 1))		#recents, if over 5 deletes oldest.
				fet = sel.fetchone()
				if fet[0] >= 5: #total recents >= 5 make room for new. 
					deleteU = cur.execute("DELETE FROM `favs` WHERE `fid` = (SELECT MIN(fid) FROM `favs` WHERE `ownerid` = (?) AND `type` = (?))", (sid, 1))

					dbconn.commit()
				insertU = cur.execute("INSERT INTO `favs` (ownerid, ticker, type) VALUES (?, ?, ?)", (sid, stockid, 1))
				dbconn.commit()
			
		inlineResources = bokeh.resources.Resources(mode='inline') #this fixes the issue of the first graph not loading, since it was loading it's resources from the CDN and not from the site itself
		#og color:#006400, my color = #31A354
		hp = Horizon(data, x='Date', toolbar_location='above', num_folds=1, pos_color=fcolor, tools=[hover, bokeh.models.ResetTool(), bokeh.models.BoxZoomTool(), bokeh.models.PanTool(), bokeh.models.ResizeTool(), bokeh.models.WheelZoomTool()], plot_width=800, plot_height=300, responsive=True, title=title)
		return file_html(hp, inlineResources, "myStock")	#needs inline resources to load on intial load, and it renames the page so we just keep it the same with "myStock"
	except:
		return "This  ticker doesn't exist"
	