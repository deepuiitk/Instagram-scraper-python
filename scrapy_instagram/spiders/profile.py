# -*- coding: utf-8 -*-
import scrapy
import json
import time
import os.path
import requests
import getpass
from scrapy.exceptions import CloseSpider

from scrapy_instagram.items import Post

import sys
BASE_URL = 'https://www.instagram.com/'
LOGIN_URL = BASE_URL + 'accounts/login/ajax/'
STORIES_UA = 'Instagram 9.5.2 (iPhone7,2; iPhone OS 9_3_3; en_US; en-US; scale=2.00; 750x1334) AppleWebKit/420+'

class InstagramSpider(scrapy.Spider):
    name = "profile"  # Name of the Spider, required value
    custom_settings = {
        'FEED_URI': './scraped/%(name)s/%(profile)s/%(date)s',
    }
    checkpoint_path = './scraped/%(name)s/%(profile)s/.checkpoint'
    session = requests.Session()
    cookies = None
    username = ''
    ssap = ''
    # def closed(self, reason):
    #     self.logger.info('Total Elements %s', response.url)

    def __init__(self, profile=sys.argv[0]):
        self.profile = profile
        if profile == '':
            self.profile = str(raw_input("Name of the profile? "))
        if self.username == '':
            self.username = str(raw_input("Enter Your Username :"))
        if self.ssap == '':
            self.ssap = str(getpass.getpass())
        # self.start_urls = ["https://www.instagram.com/accounts/login/ajax/"]##["https://www.instagram.com/"+self.profile+"/?__a=1"]
        self.date = time.strftime("%d-%m-%Y_%H")
        self.checkpoint_path = './scraped/%s/%s/.checkpoint' % (self.name, self.profile)
        self.readCheackpoint()

    def readCheackpoint(self):
        filename = self.checkpoint_path
        if not os.path.exists(filename):
            self.last_crawled = ''
            return
        self.last_crawled = open(filename).readline().rstrip()


    def start_requests(self):
        """Logs in to instagram."""
        self.session.headers.update({'Referer': BASE_URL, 'user-agent': STORIES_UA})
        req = self.session.get(BASE_URL)

        self.session.headers.update({'X-CSRFToken': req.cookies['csrftoken']})

        login_data = {'username': self.username, 'password': self.ssap}
        login = self.session.post(LOGIN_URL, data=login_data, allow_redirects=True)
        self.session.headers.update({'X-CSRFToken': login.cookies['csrftoken']})
        self.cookies = login.cookies
        login_text = json.loads(login.text)
        print login.text
        if login_text.get('authenticated') and login.status_code == 200:
            urle = "https://www.instagram.com/"+self.profile+"/?__a=1"
            print self.cookies
            yield scrapy.Request(urle, headers=self.session.headers, cookies=requests.utils.dict_from_cookiejar(self.cookies), callback=self.parse_htag)
        
            

    # Entry point for the spider
    def parse(self, response):
        return self.parse_htag(response)

    def getvarurl(self,id,end_cursor):
        stri = '{"id":"%s","first":50,"after":"%s"}'%(id, end_cursor)
        return stri

    # Method for parsing a hastag
    def parse_htag(self, response):
 
        #Load it as a json object
        print "parse_htag satya"
        graphql = json.loads(response.text)
        # print "graphql--satya",graphql
        if not 'graphql' in graphql:
            graphqll = graphql['data'] 
        else:
            graphqll = graphql['graphql']
        has_next = graphqll['user']['edge_owner_to_timeline_media']['page_info']['has_next_page']
        edges = graphqll['user']['edge_owner_to_timeline_media']['edges']
        if not hasattr(self, 'starting_shorcode') and len(edges):
            self.starting_shorcode = edges[0]['node']['shortcode']
            filename = self.checkpoint_path
            f = open(filename, 'w')
            f.write(self.starting_shorcode)

        for edge in edges:
            node = edge['node']
            shortcode = node['shortcode']
            if(self.checkAlreadyScraped(shortcode)):
                return
            yield scrapy.Request("https://www.instagram.com/p/"+shortcode+"/?__a=1",headers=self.session.headers, cookies=requests.utils.dict_from_cookiejar(self.cookies), callback=self.parse_post)

        if has_next:
            end_cursor = graphqll['user']['edge_owner_to_timeline_media']['page_info']['end_cursor']
            get_var_url = self.getvarurl(graphqll['user']['id'],end_cursor)
            yield scrapy.Request(BASE_URL +"graphql/query/?query_hash=42323d64886122307be10013ad2dcc44&variables="+get_var_url,headers=self.session.headers, cookies=requests.utils.dict_from_cookiejar(self.cookies), callback=self.parse_htag)



    def checkAlreadyScraped(self,shortcode):
        return self.last_crawled == shortcode
           
    def parse_post(self, response):
        graphql = json.loads(response.text)
        media = graphql['graphql']['shortcode_media']
        location = media.get('location', {})
        if location is not None:
            loc_id = location.get('id', 0)
            request = scrapy.Request("https://www.instagram.com/explore/locations/"+loc_id+"/?__a=1",headers=self.session.headers, cookies=requests.utils.dict_from_cookiejar(self.cookies), callback=self.parse_post_location, dont_filter=True)
            request.meta['media'] = media
            yield request
        else:
            media['location'] = {}
            yield self.makePost(media)         

    def parse_post_location(self, response):
        media = response.meta['media']
        location = json.loads(response.text)
        location = location['graphql']['location']
        media['location'] = location
        yield self.makePost(media)

    def makePost(self, media):
        location = media['location']
        caption = ''
        if len(media['edge_media_to_caption']['edges']):
            caption = media['edge_media_to_caption']['edges'][0]['node']['text']
        return Post(id=media['id'],
                    shortcode=media['shortcode'],
                    caption=caption,
                    display_url=media['display_url'],
                    loc_id=location.get('id', 0),
                    loc_name=location.get('name',''),
                    loc_lat=location.get('lat',0),
                    loc_lon=location.get('lng',0),
                    owner_id =media['owner']['id'],
                    owner_name = media['owner']['username'],
                    taken_at_timestamp= media['taken_at_timestamp'])