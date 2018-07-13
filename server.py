from flask import Flask
BASE_DIR = '/Users/amarapalli.u/work/hacks/Hackday9-legion/'

app = Flask(__name__, template_folder=BASE_DIR)
from flask import request,render_template
import time,os,json
from gmplot import gmplot
import pandas as pd
import atexit, requests
from urllib2 import urlopen

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import logging, datetime
# import pymysql.cursors
import MySQLdb
# TYPEFORM_URL = "https://api.typeform.com/v1/form/%s?key=%s&completed=true&order_by[]=date_submit,desc&limit=20"
TYPEFORM_URL = "https://api.typeform.com/v1/form/%s?key=%s&completed=true&order_by[]=date_submit,desc&since=%s&&limit=20"
SCRAPED_DIR = BASE_DIR + 'scraped/profile/'

token = ""
api_key=""
google_key = ""
Filename = "maps/map_user_%d.html"
fetcher_timeout = 10
crawler_timeout = 30
parser_timeout = 50
# connection = pymysql.connect(host='localhost',
#                              user='root',
#                              password='',
#                              db='social_credit_legion',
#                              charset='utf8mb4',
#                              cursorclass=pymysql.cursors.DictCursor)
def __fetch_data(URI, data=None, headers={}):
	if not data:
		r = requests.get(URI, headers=headers)
	if r.status_code in (200,201):
		return 1,r.json()
	else:
		print r.text
		return -1,{}


def scrape_data():
	db = MySQLdb.connect('localhost','root','','social_credit_legion')
	tim = str(int(time.time()-fetcher_timeout))
	print "scraping data"+tim
	datetim = str(datetime.datetime.now())
	url = TYPEFORM_URL % (token, api_key, tim)
	status, data = __fetch_data(url)
	# try:
	cur = db.cursor()
	for response in data.get("responses", []):
		print response
		sql = "INSERT INTO users (username,instagram_id,created_at) VALUES (%s, %s, %s)"
		cur.execute(sql, (response.get("answers").get("email_jkPq5TCVv3tl", ""),response.get("answers").get("textfield_xdYWAbeGjMgv", ""),datetim))
		db.commit()
		sql1 = "INSERT INTO form_data(form_id, product_type, user_id, monthly_income, qualification, city) VALUES (%s, %s, (select id from users where username=%s limit 1), %s, %s, %s)"
		cur.execute(sql1, (response.get("token", ""),response.get("answers").get("list_tE1OOruHq9wv_choice", ""),response.get("answers").get("email_jkPq5TCVv3tl", ""),
			response.get("answers").get("list_En2c5nXlzMiN_choice", ""),response.get("answers").get("list_knDnIaaLNCwV_choice", ""),response.get("answers").get("textfield_yWZw4ZqYSFXL", "")))
		db.commit()
	# finally:
	cur.close()
	db.close()
	print "Saved successfully."

def crawler():
	db = MySQLdb.connect('localhost','root','','social_credit_legion')
	cur = db.cursor()
	print "crawler started"
	import subprocess
	query = 'select instagram_id,id from users where id in (select user_id from form_data where crawled=0)'
	cur.execute(query)
	bashCommand = "scrapy crawl profile -a profile=%s"
	for row in cur:
		command = bashCommand % row[0]
		process = subprocess.Popen(command.split(), stdout=subprocess.PIPE)
		output, error = process.communicate()
		print error, "satya_error"
		if not error:
			cur.execute("update form_data set crawled=1 where user_id=%s"%str(row[1]))
		else:
			cur.execute("update form_data set crawled=-1 where user_id=%s"%str(row[1]))
		db.commit()
	print "crawled successfully."
	cur.close()
	db.close()



def parser():
	db = MySQLdb.connect('localhost','root','','social_credit_legion')
	cur = db.cursor()
	query = 'select instagram_id,id from users where id in (select user_id from form_data where crawled=1 and parsed=0)'
	cur.execute(query)
	for row in cur:
		directory = SCRAPED_DIR + row[0]
		for filename in os.listdir(directory):
			try:
				data = pd.read_json(SCRAPED_DIR + row[0] +'/'+filename, lines=True)
			except Exception as e:
				continue
			sql = "insert into crawled_information(user_id,loc_name,lat,longi,image_url,taken_at_timestamp,caption,image_id) VALUES (%s, %s, %s,%s, %s, FROM_UNIXTIME(%s),%s, %s)"
			gmap = gmplot.GoogleMapPlotter(0, 0, 10)
			for elem in data.itertuples():
				if elem.loc_id!=0:
					gmap.marker(elem.loc_lat, elem.loc_lon, 'cornflowerblue')
				print sql%(row[1], elem.loc_name, elem.loc_lat, elem.loc_lon, elem.display_url, elem.taken_at_timestamp, elem.caption, elem.shortcode)
				cur.execute(sql, (row[1], elem.loc_name, elem.loc_lat, elem.loc_lon, elem.display_url, elem.taken_at_timestamp, elem.caption.encode('ascii',errors='ignore'), elem.shortcode))
				# db.commit()
			gmap.coloricon = "http://www.googlemapsmarkers.com/v1/%s/"
			gmap.draw(Filename%((row[1])))
		cur.execute("update form_data set parsed=1 where user_id=%s"%str(row[1]))
		db.commit()
	print "crawler finished"
	cur.close()
	db.close()


 

scheduler = BackgroundScheduler()
scheduler.start()
scheduler.add_job(
    func=crawler,
    trigger=IntervalTrigger(seconds=crawler_timeout),
    id='crawling',
    name='crawling Social media data of signed up users every 20 seconds',
    replace_existing=False)

scheduler.add_job(
    func=parser,
    trigger=IntervalTrigger(seconds=parser_timeout),
    id='parsing',
    name='parses details of signed up users every 20 seconds',
    replace_existing=False)

scheduler.add_job(
    func=scrape_data,
    trigger=IntervalTrigger(seconds=fetcher_timeout),
    id='scraping',
    name='Fetching form details of signed up users every five seconds',
    replace_existing=False)

atexit.register(lambda: scheduler.shutdown())
# atexit.register(lambda: connection.close())
log = logging.getLogger('apscheduler.executors.default')
log.setLevel(logging.INFO)  # DEBUG

fmt = logging.Formatter('%(levelname)s:%(name)s:%(message)s')
h = logging.StreamHandler()
h.setFormatter(fmt)
log.addHandler(h)


@app.route("/")
def default():
    return "Welcome to Python Flask App!"

@app.route("/show")
def show_map():
	db = MySQLdb.connect('localhost','root','','social_credit_legion')
	data = request.args
	if not data["email"]:
		return app.response_class(
	        response=json.dumps({"Msg":"email field not present", "Code":400}),
	        status=200,
	        mimetype='application/json'
	    )
	cur = db.cursor()
	cur.execute('select id from users where username="%s"'%(str(data["email"])))
	results = cur.fetchall()
	print results
	if len(results) == 0:
		return app.response_class(
	        response=json.dumps({"Msg":"User not Found", "Code":404}),
	        status=200,
	        mimetype='application/json'
	    )
	user_id = results[0][0]
	final_filename = Filename%user_id
	print final_filename
	cur.close()
	db.close()
	return render_template(final_filename)

if __name__ == "__main__":
    app.run()