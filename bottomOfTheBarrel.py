from requests import get
from requests.exceptions import RequestException
from contextlib import closing
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from re import sub
from decimal import Decimal
import re
import time
import pymongo

priceRegex = '\$[0-9]+\.[0-9]+\s'
dbName = "BottomOfTheBarrel"

def getLiquorLandProductList(driver):
    try:
        WebDriverWait(driver, 3).until(EC.presence_of_element_located((By.CLASS_NAME, 'productList')))
        print("Page is ready!")
    except TimeoutException:
        print("Loading took too much time!")

    products = driver.find_element_by_class_name("productList")
    products = products.find_elements_by_tag_name("li")

    return products
# Iterates through the LiquorLand Beers&Ciders product list, clicking on each product
# and analyzing the data on the inididual product page  
def UpdateLiquorLand():
    myclient = pymongo.MongoClient("mongodb://localhost:27017/")
    mydb = myclient[dbName]
    liquorLandDb = mydb["LiquorLand"]

    driver = webdriver.Chrome()
    pageCount = 1
    driver.get('https://www.liquorland.com.au/Beer?show=60&page=' + str(pageCount))
    pageCount += 1
    itemCount = 0
    i = 0

    products = getLiquorLandProductList(driver)

    while itemCount < 60 and i < len(products):
        products = getLiquorLandProductList(driver)
        
        while i < len(products) and products[i].text == '':
            i += 1
        
        if i >= len(products):
            break
        
        products[i].click()
        itemCount += 1

        try:
            WebDriverWait(driver, 3).until(EC.presence_of_element_located((By.CLASS_NAME, 'brand_r1')))
            print("Page is ready!")
        except TimeoutException:
            print("Loading took too much time!")

        beer = {}
        beer['Prices'] = {}
        
        brand = driver.find_element_by_class_name("brand_r1")
        name = driver.find_element_by_class_name("title_r1")
        price = driver.find_element_by_class_name("price")
        description = driver.find_element_by_class_name("productDescription")

        details = re.search(r"•.*((B|b)ottle|(C|c)an)", description.text)
        # Details usually occur after a product description and look like this:
        # '• Carton of 24 x 355mL Bottles •' however consistency varies. 

        if details:
            extractSizeAndVolume = re.search('[0-9]+\sx\s[0-9]*(mL|L)', details.group(0))
            extractSizeAndVolume = extractSizeAndVolume.group(0).split()
            size = extractSizeAndVolume[0]
            volume = extractSizeAndVolume[2]
            beer['Prices'][size] = float(sub(r'[^\d.]', '', price.text))
            beer['Volume'] = volume

            expandedDetailsButton = description.find_elements_by_xpath('//a[@class="glyph"]')
            expandedDetailsButton[0].click()
            time.sleep(1)
            expandedDetails = description.find_elements_by_xpath('//div[@class="expandable full-width"]/ul/li/div')
            for itemKeyIndex in range(0, len(expandedDetails), 3):
                if expandedDetails[itemKeyIndex].text == "Packaging":
                    if expandedDetails[itemKeyIndex+2].text == "Bottle":
                        beer['Bottle'] = True
                    else:
                        beer['Bottle'] = False
                elif expandedDetails[itemKeyIndex].text == "Product Code":
                    continue
                else:
                    beer[expandedDetails[itemKeyIndex].text] = expandedDetails[itemKeyIndex+2].text
                print("Test" + expandedDetails[itemKeyIndex].text)
                print("Test" + expandedDetails[itemKeyIndex+2].text)
        else:
            val = float(sub(r'[^\d.]', '', price.text))
            beer['Prices']['1'] = val

        beer['Brand'] = brand.text
        beer['Name'] = name.text
        beer['ProductPage'] = driver.current_url

        print(brand.text)
        print(name.text)
        print(float(sub(r'[^\d.]', '', price.text)))
        print(size)
        print(volume)
        print(str(driver.current_url))
        liquorLandDb.insert_one(beer)
        driver.execute_script("window.history.go(-1)")

        if itemCount == 60:
            itemCount = 0
            i = -1
            pageCount += 1
            driver.get('https://www.liquorland.com.au/Beer?show=60&page=' + str(pageCount))
        i += 1

    driver.close()
# Iterates through the DanMurphys Beers product list and extracts data from there,
# without going deeper into the inidivdual products
def UpdateDanMurphys():
    myclient = pymongo.MongoClient("mongodb://localhost:27017/")
    mydb = myclient[dbName]
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
        try:
            myElem = WebDriverWait(driver, 3).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'product-list')))
            print("Page is ready!")
        except TimeoutException:
            print("Loading took too much time!")

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
                            beer['Prices'][str(size.group(0))] = float(sub(r'[^\d.]', '', result.group(0).strip()))
                    elif (re.search('case of', i)):
                        size = re.search('(\d+)(?!.*\d)', i)
                        result = re.search(priceRegex, i)
                        if result and size:
                            beer['Prices'][str(size.group(0))] = float(sub(r'[^\d.]', '', result.group(0).strip()))
                    elif (re.search('per bottle', i)):
                        result = re.search(priceRegex, i)
                        if result:
                            beer['Prices']['1'] = float(sub(r'[^\d.]', '', result.group(0).strip()))
                            
                    elif (re.search('per pack', i)):
                        result = re.search(priceRegex, i)
                        if result:
                            beer['Prices']['1'] = float(sub(r'[^\d.]', '', result.group(0).strip()))
                    elif (re.search('can', i)):
                        beer['Bottle'] = False
                elementCount += 1
            if ('Name' in beer and beer['Name'] != "Shopping at Dan Murphy's just got even easier. Order online, select your local store, and we'll have your drinks ready to go in 30 minutes."):
                if ('Brand' in beer and beer['Brand'] != "Shopping at Dan Murphy's just got even easier. Order online, select your local store, and we'll have your drinks ready to go in 30 minutes."):
                    result = re.search('\sCans\b', beer['Name'])
                    if result:
                        beer['Bottle'] = False
                    print(beer)
                    danMurphysDb.insert_one(beer)

    driver.close()

if __name__ == '__main__':
   #UpdateDanMurphys()
   UpdateLiquorLand()
   print("All done!")
