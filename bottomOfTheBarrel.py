from requests import get
from requests.exceptions import RequestException
from contextlib import closing
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import re
import time
import pymongo

#TODO: Finalise Item structue for future database implementation
priceRegex = '\$[0-9]+\.[0-9]+\s'
class Item:
    name = ""
    bottle = True
    prices = {}

class Size:
    price = -1
    size = -1


if __name__ == '__main__':
    myclient = pymongo.MongoClient("mongodb://localhost:27017/")
    mydb = myclient["BottomOfTheBarrel"]
    mycol = mydb["DanMurphys"]




    driver = webdriver.Chrome()
    #Currently use this sleep time to manually navigate the Dan Murphy's webpage to close the geo-request.
    #TODO: Programme a click on consistent popup. 
    time.sleep(5)

    pageCount = 1
    while True:
        driver.get('https://www.danmurphys.com.au/beer/all?page=' + str(pageCount) + '&size=200')
        pageCount += 1

        #Currently use this sleep time to manually navigate the Dan Murphy's webpage to close the geo-request.
        #TODO: Programme a click on consistent popup. 
        time.sleep(5)   

        html = driver.execute_script("return document.body.innerHTML") #returns the inner HTML as a string
        if (re.search('No products found', html)):
            break
        products = driver.find_element_by_class_name("product-list")
        products = products.find_elements_by_tag_name("li")
        organisedProducts = []
        for x in products:
            #beer = x.find_elements_by_class_name("title")
            #if (beer):
                #print(beer.text)
            productInfo = x.text.split('\n')
            count = 0
            #beer = Item()
            beer = {}
            beer['Prices'] = {}
            beer['Bottle'] = True
            for i in productInfo:
                #print(i)
                if count == 1:
                    if 'DIRECT FROM SUPPLIER' in i:
                        count -= 1
                    else:
                        beer['Brand'] = i.strip()
                elif count == 2:
                    if 'DIRECT FROM SUPPLIER' not in i:
                        beer['Name'] = i.strip()
                elif count >= 3:
                    if (re.search('pack of', i)):
                        size = re.search('(\d+)(?!.*\d)', i)
                        result = re.search(priceRegex, i)
                        if result and size:
                            beer['Prices'][str(size.group(0))] = result.group(0).strip()
                        #beer.price6 = i
                    elif (re.search('case of', i)):
                        size = re.search('(\d+)(?!.*\d)', i)
                        result = re.search(priceRegex, i)
                        if result and size:
                            beer['Prices'][str(size.group(0))] = result.group(0).strip()
                        #beer.price24 = i
                    elif (re.search('per bottle', i)):
                        #beer.price1 = i
                        result = re.search(priceRegex, i)
                        if result:
                            beer['Prices']['1'] = result.group(0).strip()
                        beer['Bottle'] = True
                    elif (re.search('per pack', i)):
                        #beer.price1 = i
                        result = re.search(priceRegex, i)
                        if result:
                            beer['Prices']['1'] = result.group(0).strip()
                    elif (re.search('can', i)):
                        beer['Bottle'] = False
                    elif (re.search('of [0-9][0-9]', i)):
                        beer['Bottle'] = False
                count += 1
            #print(beer)
            if ('Name' in beer and beer['Name'] != "Shopping at Dan Murphy's just got even easier. Order online, select your local store, and we'll have your drinks ready to go in 30 minutes."):
                if ('Brand' in beer and beer['Brand'] != "Shopping at Dan Murphy's just got even easier. Order online, select your local store, and we'll have your drinks ready to go in 30 minutes."):
                    result = re.search('\sCans\b', beer['Name'])
                    if result:
                        beer['Bottle'] = False
                    print(beer)
                    c = mycol.insert_one(beer)

            #print("Name == " + beer.name)
            #print("case == " + str(beer.price24))
            #print("pack == " + str(beer.price6))
            #print("bott == " + str(beer.price1))

    driver.close()