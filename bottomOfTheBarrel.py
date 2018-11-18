from requests import get
from requests.exceptions import RequestException
from contextlib import closing
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import re
import time
import pymongo

priceRegex = '\$[0-9]+\.[0-9]+\s'

if __name__ == '__main__':
    myclient = pymongo.MongoClient("mongodb://localhost:27017/")
    mydb = myclient["BottomOfTheBarrel"]
    danMurphysDb = mydb["DanMurphys"]

    driver = webdriver.Chrome()
    # Currently use this sleep time to manually navigate the Dan Murphy's webpage to close the geo-request.
    # Only need to do this for page 1
    # TODO: Programme a click on consistent popup. 
    time.sleep(5)

    pageCount = 1
    while True:
        driver.get('https://www.danmurphys.com.au/beer/all?page=' + str(pageCount) + '&size=200')
        pageCount += 1

        # Wait for Dan Murphys to call internal API's via javascript. 
        # TODO: Programme a click on consistent popup. 
        time.sleep(5)   

        html = driver.execute_script("return document.body.innerHTML") #returns the inner HTML as a string
        if (re.search('No products found', html)):
            break
        products = driver.find_element_by_class_name("product-list")
        products = products.find_elements_by_tag_name("li")
        for itemCard in products:
            productInfo = itemCard.text.split('\n')
            elementCount = 0
            beer = {}
            beer['Prices'] = {}
            beer['Bottle'] = True
            #Loop through the elements of HTML displayed in a product 'card'
            for i in productInfo: 
                if elementCount == 1:
                    if 'DIRECT FROM SUPPLIER' in i:
                        elementCount -= 1
                    else:
                        beer['Brand'] = i.strip()
                elif elementCount == 2:
                    if 'DIRECT FROM SUPPLIER' not in i:
                        beer['Name'] = i.strip()
                elif elementCount >= 3:
                    if (re.search('pack of', i)):
                        size = re.search('(\d+)(?!.*\d)', i)
                        result = re.search(priceRegex, i)
                        if result and size:
                            beer['Prices'][str(size.group(0))] = result.group(0).strip()
                    elif (re.search('case of', i)):
                        size = re.search('(\d+)(?!.*\d)', i)
                        result = re.search(priceRegex, i)
                        if result and size:
                            beer['Prices'][str(size.group(0))] = result.group(0).strip()
                    elif (re.search('per bottle', i)):
                        result = re.search(priceRegex, i)
                        if result:
                            beer['Prices']['1'] = result.group(0).strip()
                        #beer['Bottle'] = True #This is currently a default
                    elif (re.search('per pack', i)):
                        result = re.search(priceRegex, i)
                        if result:
                            beer['Prices']['1'] = result.group(0).strip()
                    elif (re.search('can', i)):
                        beer['Bottle'] = False
                elementCount += 1
            if ('Name' in beer and beer['Name'] != "Shopping at Dan Murphy's just got even easier. Order online, select your local store, and we'll have your drinks ready to go in 30 minutes."):
                if ('Brand' in beer and beer['Brand'] != "Shopping at Dan Murphy's just got even easier. Order online, select your local store, and we'll have your drinks ready to go in 30 minutes."):
                    result = re.search('\sCans\b', beer['Name'])
                    if result:
                        beer['Bottle'] = False
                    print(beer)
                    c = danMurphysDb.insert_one(beer)

    driver.close()