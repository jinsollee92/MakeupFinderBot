import requests
from lxml import html
import json
from pprint import pprint

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

def match_sephora_products(pageUrl, name):
	matched = {}
	products_page = requests.get(pageUrl)
	tree = html.fromstring(products_page.content)
	# Sephora returns search results inside a json defined in a script block
	response_str = tree.xpath('//script[@id="searchResult"]/text()')[0]
	products = json.loads(response_str)['products']
	for product in products:
		product_name = product['display_name']
		product_url = product['product_url']
		if product_name.lower().startswith(name.lower()):
			matched['name'] = product_name
			matched['url'] = 'http://www.sephora.com' + product_url
			more_info = product['derived_sku']
			if 'list_price' in more_info:
				matched['price'] = '$%.2f' % float(more_info['list_price'])
			elif 'list_price_min' in more_info and 'list_price_max' in more_info:
				matched['price'] = '$%.2f - $%.2f' % \
					(float(more_info['list_price_min']), float(more_info['list_price_max']))
			return matched
	return None

def match_ulta_products(pageUrl, name):
	matched = {}
	products_page = requests.get(pageUrl)
	tree = html.fromstring(products_page.content)
	products = tree.xpath('//p[@class="prod-desc"]/a/text()')
	# Ulta doesn't have a view all page, so use next page links
	nextPage = tree.xpath('//li[@class="next-prev floatl-span"]/a[text()="Next"]/@href')
	while True:
		# Ulta links look like: 
		# <p class="prod-desc">
		# 	<a href="/repair-sculpting-night-cream?productId=xlsImpprod11771005">
		# 		Repair Sculpting Night Cream</a>
		# </p>
		for product in products:
			product_name = product.strip().replace('Online Only ', '')
			if name.lower() in product_name.lower():
				matched['name'] = product_name
				product_url = tree.xpath('//p[@class="prod-desc"]/a[text()=\"%s\"]/@href' % product)[0]
				matched['url'] = 'http://www.ulta.com' + product_url
				product_price = tree.xpath('//p[@class="prod-desc"]/a[text()=\"%s\"]/../../p[@class="price"]/a/div/span/text()' \
					% product)[0].strip()
				matched['price'] = product_price
				return matched
		if len(nextPage) > 0:
			nextPage = pageUrl + nextPage[0]
			# get elements from the next page
			products_page = requests.get(nextPage)
			tree = html.fromstring(products_page.content)
			products = tree.xpath('//p[@class="prod-desc"]/a/text()')
			nextPage = tree.xpath('//li[@class="next-prev floatl-span"]/a[text()="Next"]/@href')
		else:
			break
	return None

if __name__ == '__main__':
	# print(get_brands('sephora'))
	# print(get_brands('ulta'))
	# print(match_sephora_products('http://www.sephora.com/benefit-cosmetics?products=all&pageSize=-1', 'Gimme Brow'))
	# print(match_ulta_products('http://www.ulta.com/brand/clinique?N=1z12lx1Z1z141cp', 'Smart Broad Spectrum SPF 15 Custom-Repair Moisturizer For Very Dry Skin'))
	links = {}
	links['sephora'] = get_brands('sephora')
	links['ulta'] = get_brands('ulta')

	with open('brands.json', 'w') as output:
		json.dump(links, output, indent=2)
