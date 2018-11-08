from requests import get
from requests.exceptions import RequestException
from contextlib import closing
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import re
import time

#TODO: Finalise Item structue for future database implementation
class Item:
    name = ""
    bottle = True
    price1 = -1
    price6 = -1
    price24 = -1
    caseSize = -1


if __name__ == '__main__':
    driver = webdriver.Chrome()
    driver.get('https://www.danmurphys.com.au/beer/all?size=200')

    #Currently use this sleep time to manually navigate the Dan Murphy's webpage to close the geo-request.
    #TODO: Programme a click on consistent popup. 
    time.sleep(5)

    html = driver.execute_script("return document.body.innerHTML") #returns the inner HTML as a string
    
    products = driver.find_element_by_class_name("product-list")
    products = products.find_elements_by_tag_name("li")
    organisedProducts = []
    for x in products:
        #beer = x.find_elements_by_class_name("title")
        #if (beer):
            #print(beer.text)
        productInfo = x.text.split('\n')
        count = 0
        beer = Item()
        for i in productInfo:
            #print(i)
            if count == 1:
                beer.name = i
            elif count == 2:
                beer.name = beer.name + ' ' + i
            elif count >= 3:
                if (re.search('pack of 6', i)):
                    beer.price6 = i
                elif (re.search('case of', i)):
                    beer.price24 = i
                elif (re.search('per bottle', i)):
                    beer.price1 = i
                    beer.bottle = True
                elif (re.search('can', i)):
                    beer.bottle = False
                elif (re.search('of [0-9][0-9]', i)):
                    beer.bottle = False
            count += 1

        print("Name == " + beer.name)
        print("case == " + str(beer.price24))
        print("pack == " + str(beer.price6))
        print("bott == " + str(beer.price1))
        #print(text)

    #print(products)
    #print(html)

    driver.close()