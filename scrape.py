import requests
from lxml import html
import json
import os
from pprint import pprint
from lxml.etree import XPathEvalError

queries = {
	'sephora': ('http://www.sephora.com/brand-list',
				'//a[@class="c-Link c-BrandGroup-Link"]/span[@class="c-Link-txt"]/text()',
				'//span[text()=\"%s\"]/../@href'),
	'ulta': ('http://www.ulta.com/global/nav/allbrands.jsp',
			'//ul[@class="all-brands-sublisting"]/li/ul/li/a/text()',
			'//ul[@class="all-brands-sublisting"]/li/ul/li/a[text()=\"%s\"]/@href',
			'//p[@class="prod-desc"]/a/text()',
			'//p[@class="prod-desc"]/a[text()=\"%s\"]/@href')
}

# convert hrefs to complete urls
def convert_url(store, url):
	path = url.split('/')[-1].split('?')[0]
	if store == 'sephora':
		# Brand's product list page (view all)
		return 'http://www.sephora.com/%s?products=all&pageSize=-1' % path
	if store == 'ulta':
		brand_page = requests.get('http://www.ulta.com/brand/%s' % path)
		# Ulta has different links for bigger brands
		# if 'Shop This Brand' in brand_page.content:
		tree = html.fromstring(brand_page.content)
		link = tree.xpath('//a[text()="Shop This Brand"]/@href')
		if link:
			return 'http://www.ulta.com' + link[0]
		return 'http://www.ulta.com/brand/%s' % path

def get_brands(store):
	results = {}
	brands_page = requests.get(queries[store][0])
	brands_page.encoding = 'utf-8'
	tree = html.fromstring(brands_page.content)
	brands = tree.xpath(queries[store][1])
	for brand in brands:
		url = tree.xpath(queries[store][2] % brand)[0]
		results[str(brand)] = convert_url(store, url)
		# Replace weird letters and add again
		# if '\u' in brand:
	return results

def get_sephora_products(url):
	products_page = requests.get(url)
	tree = html.fromstring(products_page.content)
	# Sephora returns search results inside a json defined in a script block
	try:
		response_str = tree.xpath('//script[@id="searchResult"]/text()')[0]
		products_found = json.loads(response_str)['products']
	except (IndexError, KeyError):
		return []
	products = []
	for p in products_found:
		product = {
			'name': p['display_name'],
			'url': 'http://www.sephora.com' + p['product_url']
		}
		if 'list_price' in p['derived_sku']:
			product['price'] = '$%.2f' % float(p['derived_sku']['list_price'])
		elif 'list_price_min' in p['derived_sku'] and 'list_price_max' in p['derived_sku']:
			product['price'] = '$%.2f - $%.2f' % \
				(p['derived_sku']['list_price_min'], p['derived_sku']['list_price_max'])
		products.append(product)
	return products

def get_ulta_products(url):
	products_page = requests.get(url)
	tree = html.fromstring(products_page.content)
	products_found = tree.xpath('//p[@class="prod-desc"]/a/text()')
	# Ulta doesn't have a view all page, so use next page links
	nextPage = tree.xpath('//li[@class="next-prev floatl-span"]/a[text()="Next"]/@href')
	products = []
	while True:
		# Ulta links look like: 
		# <p class="prod-desc">
		# 	<a href="/repair-sculpting-night-cream?productId=xlsImpprod11771005">
		# 		Repair Sculpting Night Cream</a>
		# </p>
		for p in products_found:
			if 'FREE' in p:
				continue
			try:
				product = {
					'name': p.strip().replace('Online Only ', ''),
					'url': 'http://www.ulta.com' + tree.xpath('//p[@class="prod-desc"]/a[text()=\"%s\"]/@href' % p)[0],
					'price': tree.xpath('//p[@class="prod-desc"]/a[text()=\"%s\"]/../../p[@class="price"]/a/div/span/text()' \
						% p)[0].strip()
				}
				products.append(product)
			# if the product name has special characters, these errors are raised
			# then just skip it for now
			except (IndexError, XPathEvalError):
				continue
		if len(nextPage) > 0:
			nextPage = url + nextPage[0]
			# get elements from the next page
			products_page = requests.get(nextPage)
			tree = html.fromstring(products_page.content)
			products_found = tree.xpath('//p[@class="prod-desc"]/a/text()')
			nextPage = tree.xpath('//li[@class="next-prev floatl-span"]/a[text()="Next"]/@href')
		else:
			return products

def save_products(store, brand, url):
	if not os.path.exists(os.path.relpath('product_info')):
		os.mkdir(os.path.relpath('product_info'))
		os.mkdir(os.path.relpath('product_info/sephora'))
		os.mkdir(os.path.relpath('product_info/ulta'))

	with open('product_info/%s/%s' % (store, brand), 'w+') as products_file:
		if store == 'sephora':
			json.dump(get_sephora_products(url), products_file, indent=2)
		elif store == 'ulta':
			json.dump(get_ulta_products(url), products_file, indent=2)

def save_brand_list():
	links = {}
	links['sephora'] = get_brands('sephora')
	links['ulta'] = get_brands('ulta')

	with open('brands.json', 'w') as output:
		json.dump(links, output, indent=2)

def save_product_list():
	with open('brands.json', 'r') as brands_json:
		links = json.load(brands_json)
	for brand in links['sephora']:
		print(brand)
		url = links['sephora'][brand]
		save_products('sephora', brand, url)
	for brand in links['ulta']:
		print(brand)
		url = links['ulta'][brand]
		save_products('ulta', brand, url)

def match_product(store, brand, name):
	with open('product_info/%s/%s' % (store, brand), 'r') as products_file:
		products = json.load(products_file)
		for p in products:
			if p['name'].lower() == name.lower():
				return p
	return None

if __name__ == '__main__':
	# print(get_brands('sephora'))
	# print(get_brands('ulta'))
	# print(match_sephora_products('http://www.sephora.com/benefit-cosmetics?products=all&pageSize=-1', 'Gimme Brow'))
	# print(match_ulta_products('http://www.ulta.com/brand/clinique?N=1z12lx1Z1z141cp', 'Smart Broad Spectrum SPF 15 Custom-Repair Moisturizer For Very Dry Skin'))
	save_brand_list()
	save_product_list()


