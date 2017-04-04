import praw
from praw.models import MoreComments
import scrape
import re
import json
from pprint import pprint
from datetime import datetime, timedelta
import shelve
import os
import time

with open('brands.json', 'r') as f:
	links = json.load(f)
	sephora_links = links['sephora']
	ulta_links = links['ulta']

def get_products(text):
	text = text.lower()
	text = re.sub('[^A-Za-z0-9 \-\n]+', '', text)
	text = text.replace('\n', ' ')
	products = {}
	for link_list in links.values():
		for brand in link_list:
			if brand.lower() in text:
				# get the words following brand name
				found = text.partition(brand.lower())[2].split('.')[0].split()
				product = ''
				# we will search products using up to 5 words following brand name
				name_length = min(5, len(found))
				for word in found[:name_length]:
					word = word.replace('-', '')
					word = word.replace('.', '')
				try:
					products[brand].append(found[:name_length])
				except KeyError:
					products[brand] = []
					products[brand].append(found[:name_length])
	if len(products) > 0:
		return products

def find_product_links(products):
	result = {}
	for brand in products:
		for product_name in products[brand]:
			if brand in sephora_links:
				# try using all 5 words first and then chop up by single word from the back
				for i in range(5, 1, -1):
					found = scrape.match_product('sephora', brand, ' '.join(product_name[:i]))
					if found is not None:
						title = '%s - %s' % (brand, found['name'])
						try:
							result[title]['sephora'] = found
						except KeyError:
							result[title] = {}
							result[title]['sephora'] = found
						break
			if brand in ulta_links:
				for i in range(5, 1, -1):
					found = scrape.match_product('ulta', brand, ' '.join(product_name[:i]))
					if found:
						title = '%s - %s' % (brand, found['name'])
						# search Sephora list to see if there are same products with different cases
						for sephora_product in result:
							if title.lower() == sephora_product.lower():
								title = sephora_product
						try:
							result[title]['ulta'] = found
						except KeyError:
							result[title] = {}
							result[title]['ulta'] = found
						break
	if len(result) > 0:
		return result
	else:
		return None

def generate_comment(search_result):
	comment = ''
	for product in search_result:
		details = search_result[product]
		comment += '**%s:**' % product
		if 'sephora' in details:
			sephora_details = details['sephora']
			comment += ' %s at [Sephora](%s) ' % (sephora_details['price'], sephora_details['url'])
		if 'sephora' in details and 'ulta' in details:
			comment += '/'
		if 'ulta' in details:
			ulta_details = details['ulta']
			comment += ' %s at [Ulta](%s)' % (ulta_details['price'], ulta_details['url'])
		comment += '\n\n'
	comment += '^I ^am ^a ^bot. ^Send ^me ^a ^PM ^to ^report ^bugs ^or ^suggest ^improvements.'
	return comment

def search_comment(comment):
	products = get_products(comment.body)
	if not products:
		return
	search_result = find_product_links(products)
	if not search_result:
		return
	return search_result

def reply_to_comment(comment, search_result):
	reply_body = generate_comment(search_result)
	new_comment = comment.reply(reply_body)
	return new_comment

def run_manual():
	reddit = praw.Reddit('MakeupFinderBot')
	# sr = reddit.subreddit('muacjdiscussion')
	# private sub for testing
	sr = reddit.subreddit('MakeupFinderBot')

	start_time = datetime.now() - timedelta(hours=24)
	start_time = int(start_time.strftime('%s'))

	if not os.path.exists('replied.db'):
		with shelve.open('replied') as new_shelve:
			new_shelve['comments'] = []

	with shelve.open('replied') as replied_shelve:
		replied_comments = replied_shelve['comments']
		for submission in sr.submissions(start=start_time):
			print('Submission: ' + submission.title)
			submission.comments.replace_more(limit=0)
			top_comments = submission.comments
			if len(top_comments) == 0:
				pass
			for comment in top_comments:
				if comment.id in replied_shelve:
					continue
				search_result = search_comment(comment)
				if search_result:
					print(search_result)
					new_comment = reply_to_comment(comment, search_result)
					replied_comments.append(new_comment.id)
				replied_comments.append(comment.id)
				replied_shelve['comments'] = replied_comments

def run_stream():
	reddit = praw.Reddit('MakeupFinderBot')
	# sr = reddit.subreddit('muacjdiscussion')
	# private sub for testing
	sr = reddit.subreddit('MakeupFinderBot')

	ignore = 0

	for comment in sr.stream.comments():
		# ignore the first 100
		if ignore < 100:
			ignore += 1
		else:
			print(comment.body)
			search_result = search_comment(comment)
			if search_result:
				print(search_result)
				reply_to_comment(comment, search_result)

			time.sleep(15)

if __name__ == '__main__':
	run_stream()