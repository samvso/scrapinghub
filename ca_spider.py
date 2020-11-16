import re
import json
import scrapy

from scrapers.items import ProductItem


class CaWalmartSpider(scrapy.Spider):
   
	name = "ca_walmart"
	allowed_domains = ["walmart.ca"]
	start_urls = ["https://www.walmart.ca/en/grocery/fruits-vegetables/fruits/N-3852"]

	header = {
		'Host': 'www.walmart.ca',
		'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:77.0) Gecko/20100101 Firefox/77.0',
		'Accept': '*/*',
		'Accept-Language': 'en-US,en;q=0.5',
		'Accept-Encoding': 'gzip, deflate, br',
		'Content-Type': 'application/json',
		'Connection': 'keep-alive'
	}

	def parse(self, response):

		# Looping through product links
		for url in response.css('.product-link::attr(href)').getall():
			yield response.follow(url, callback=self.parse_html, cb_kwargs={'url': url})

		next_page = response.css('#loadmore::attr(href)').get()

		# Trying to go to the next page
		if next_page is not None:
			yield response.follow(next_page, callback=self.parse)

	def parse_html(self, response, url):

		item = ProductItem()
		
		# Stores to be scraped
		stores = {
				'3124': {
						'latitude':'48.415300',
						'longitude':'-89.242360'},
				'3106': {
						'latitude':'43.655830',
						'longitude':'-79.435360'}}

		info_json = json.loads(re.findall(r'(\{.*\})', response.xpath("/html/body/script[1]/text()").get())[0])
		product_json = json.loads(response.css('.evlleax2 > script:nth-child(1)::text').get())

		sku = product_json['sku']
		description = product_json['description']
		name = product_json['name']
		brand = product_json['brand']['name']
		image_url = product_json['image']
		upc = info_json['entities']['skus'][sku]['upc']
		category = info_json['entities']['skus'][sku]['facets'][0]['value']
		package = info_json['entities']['skus'][sku]['description']

		for i in range(3):
			category = ' | '.join([info_json['entities']['skus'][sku]['categories'][0]['hierarchy'][i]['displayName']['en'], category])

		item['store'] = 'Walmart'
		item['barcodes'] = ', '.join(upc)
		item['sku'] = sku
		item['brand'] = brand
		item['name'] = name
		item['description'] = description.replace('<br>', ' ')
		item['package'] = package
		item['image_url'] = ', '.join(image_url)
		item['category'] = category
		item['url'] = self.start_urls[0] + url

		for key in stores.keys():
			yield scrapy.http.Request(f'https://www.walmart.ca/api/product-page/find-in-store?latitude={stores[key]["latitude"]}&longitude={stores[key]["longitude"]}&lang=en&upc={upc[0]}',
									  callback=self.parse_api, cb_kwargs={'item': item},
									  meta={'handle_httpstatus_all': True},
									  dont_filter=False, headers=self.header)

	def parse_api(self, response, item):
	   
		store_json = json.loads(response.body)

		branch = store_json['info'][0]['id']
		stock = store_json['info'][0]['availableToSellQty']

		if 'sellPrice' not in store_json['info'][0]:
			price = 0
		else:
			price = store_json['info'][0]['sellPrice']
		
		item['stock'] = stock
		item['price'] = price
		item['branch'] = branch

		yield item
