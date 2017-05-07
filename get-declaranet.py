#!/usr/bin/python2.7
# -*- coding: utf-8 -*-

"""Declaranet.py.
    ToDo(refactoring, código Terrible)

    Esta función crawlea de la página de declaranet.gob.mx los currículums históricos de los 
    funcionarios. Este código debe ser usado en el producto de datos #Compranet.

    El código asume que el archivo se encuentra en la carpeta ./data/servidores_crawl/

    Ejemplo:
            $ ipython ./pipelines/Ingest/declaranet.py  "Funcionario 1, Funcionario 2, ..." 

    Atributos:
        Nombre-documento (str): Nombre del documento que tiene a los funcionarios por buscar.

        E.g.
            Isaac Cinta Sánchez,  Hector Merlin Marcial,  Lorenzo Gomez Vega,  Jaqueline Ramirez Galvan,  
            Arturo Daniel Almada Iberri,  Mario Zamora Gastelum,  Monica Romero Hernandez,  
            Luis Alberto Rodriguez Reyes,  Alfredo Torres Martinez,  Jose Luis  Velasquez  Salas ,  
            Miguel Angel  Gomez  Castillo ,  Mariana Lopez Suck,  Emilio Fueyo Saldaña

        Puedes descargar los nombres y acomodarlos para esta función de esta forma:
            "SELECT  nombre || primer_apellido || segundo_apellido  FROM raw.funcionarios \
            WHERE institucion LIKE '% SECRETARÍA DE COMUNICACIONES Y TRANSPORTES%';" | \
            uniq | awk 1 ORS=',' |  sed -e "s/[,| *,*]$//g;s/^//g;s/,$//g;" > \
            ./data/servidores_crawl/temp.txt
"""

import argparse
import os
import time
import sys
import zipfile
import requests
import xvfbwrapper 
import subprocess
from random import randint
from time import sleep
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException
import signal
import boto3
from cStringIO import StringIO
import datetime
import click
import unicodedata

class TimeoutException(Exception):   # Custom exception class
    pass

def timeout_handler(signum, frame):   # Custom signal handler
    raise TimeoutException

def clean_name(text):
    """
    Strip accents from input String.

    :param text: The input string.
    :type text: String.

    :returns: The processed String.
    :rtype: String.
    """
    if isinstance(text,unicode):
        text = unicodedata.normalize('NFD', text)
        text = text.encode('ascii', 'ignore')
        text = text.decode("utf-8")

    elif isinstance(text,str):
        print("is unicode 1")
        text = unicode(text, 'utf-8')
        text = unicodedata.normalize('NFD', text)
        text = text.encode('ascii', 'ignore')
        text = text.decode("utf-8")
    else:
        print("Niidea")
    return text

#@click.option('--funcionarios_list')
def Declaranet(funcionarios_list,s3c,raw_bucket,bucket):    
    initial_url ="http://servidorespublicos.gob.mx"
    now = datetime.datetime.now()

    # Instancia el Driver
    display = xvfbwrapper.Xvfb()
    display.start()
    chromedriver = "/usr/lib/chromium-browser/chromium-browser"
    os.environ["webdriver.chrome.driver"] = chromedriver
    chromeOptions = webdriver.ChromeOptions()
    mime_types = "application/pdf,application/vnd.adobe.xfdf,application/vnd.fdf,application/vnd.adobe.xdp+xml"
    prefs = {"browser.download.folderList":2, "browser.download.dir": u'/home/ubuntu', 
        "browser.download.manager.showWhenStarting":False,"browser.helperApps.neverAsk.saveToDisk":mime_types,
        "pdfjs.disabled":"true","plugins.plugins_list": [{"enabled":False,"name":"Chrome PDF Viewer"}],
        "plugin.disable_full_page_plugin_for_types":mime_types}
    chromeOptions.add_argument('--no-sandbox')
    chromeOptions.add_experimental_option("prefs",prefs)
    #driver = webdriver.Chrome(chrome_options=chromeOptions)
    driver = webdriver.Chrome("/usr/lib/chromium-browser/chromedriver",chrome_options=chromeOptions)
    #driver = webdriver.Chrome()
    driver.implicitly_wait(100)
    driver.get(initial_url) 

    link = None
    while not link:
        try:
            link = driver.find_element_by_class_name('ui-icon-closethick')
            link.click()
        except NoSuchElementException, e:
            print "Unable to click, retrying"
        else:
            break

    for funcionario in funcionarios_list:

        try:
            print('intentando funcionario: ' + str(funcionario))
            # you'll have a list of names from the other table
            time.sleep(1)
            name = driver.find_element_by_id('form:nombresConsulta')        
            time.sleep(1)
            name.clear()
            name.send_keys(funcionario)
            time.sleep(3)
            #btn = driver.find_element_by_name('form:buscarCosnsulta')
            btn = driver.find_element_by_name('form:buscarCosnsulta')
            btn.click()
            #driver.execute_script("arguments[0].click();", btn)
            time.sleep(3)
            # Find all cases for that name
            results = driver.find_element_by_id('form:tblResultadoConsulta_data').find_elements_by_xpath("//tbody/tr/td")

            if results[0].text == 'Sin Datos':

                file = 'funcionarios_sin_declaracion_' + str(now.year) + '.txt'
                target_file = bucket + file

                with open(file, 'wb') as data:
                    s3c.download_fileobj(raw_bucket, target_file, data)                


                with open(file) as result:
                        uniqlines = list(result.readlines())
                        uniqlines.append(funcionario)
                        uniqlines = set(uniqlines)

                        with open(file, 'w') as temp:
                            temp.write('\n'.join(str(line) for line in uniqlines))
            else:
                n_results = int(len(results)/2)
                print(n_results)

                for result in range(n_results):
                    #result +=1 
                    print("iteration number" + str(result))
                    driver.implicitly_wait(160)

                    try: 
                        driver.find_element_by_id('form:tblResultadoConsulta:{0}:idLinkBack'.format(result)).click()
                    except:
                        driver.find_element_by_id('form:tblResultadoConsulta:{0}:j_idt53'.format(result)).click()

                    driver.implicitly_wait(60)
                    
                    cv_results = driver.find_element_by_id("form:tblResultado_data").find_elements_by_xpath("//tr[@data-ri]")
                    cv_n_results = int(len(cv_results))

                    for cv in range(cv_n_results):

                        print("iteration number" + str(result) + " - cv number: " + str(cv))
                        cve = funcionario +"_"+ cv_results[cv].text
                        # Clean Name
                        cve = cve.strip().replace(" ", "-").replace("/", "-")
                        driver.implicitly_wait(160)

                        signal.signal(signal.SIGALRM, timeout_handler)

                        try:
                            signal.alarm(70)  
                            driver.find_element_by_id('form:tblResultado:{0}:idButtonConsultaAcuse'.format(cv)).click()
                            driver.implicitly_wait(160)

                            cookies = {
                                'JSESSIONID': driver.get_cookies()[1]["value"],
                                '_ga': driver.get_cookies()[0]["value"],
                                '_gat': '1',
                            }
                            headers = {
                                'Accept-Encoding': 'gzip, deflate, sdch',
                                'Accept-Language': 'es-MX,es;q=0.8,es-419;q=0.6,en;q=0.4',
                                'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.87 Safari/537.36',
                                'Accept': '*/*',
                                'Referer': 'http://servidorespublicos.gob.mx/registro/consulta.jsf',
                                'Connection': 'keep-alive',
                                'Content-Type': 'charset=utf-8'
                            }

                            sleep(randint(200,800)/100)
                            print("intentando decodificar")
                            cve = clean_name(cve)
                            print(cve)
                            target_file = bucket +str(now.year)+ "/"+ cve + ".pdf"
                            target_file = target_file
                            fake_handle = StringIO(requests.get('http://servidorespublicos.gob.mx/consulta.pdf', headers=headers, cookies=cookies).content)
                            s3c.put_object(Bucket=raw_bucket, Key=target_file, Body=fake_handle.read())

                            time.sleep(5)
                            escape = driver.find_element_by_id("form:buscar")
                            escape.send_keys(Keys.ESCAPE)
                            signal.alarm(0)

                        except TimeoutException:
                            print("Timed out!")
                            continue # continue the for loop if function A takes more than 5 second

                        except Exception,e: 
                            print(str(e))
                            pass


                    driver.find_element_by_id("form:buscar").click()
                    
                    while not link:
                        try:
                            driver.find_element_by_id("form:buscar").click()
                        except NoSuchElementException:
                            print("looking for 'form:buscar'")
                            time.sleep(2)
                        else:
                            break

        except:
            file = 'funcionarios_sin_declaracion_' + str(now.year) + '.txt'
            target_file = bucket + file

            with open(file, 'wb') as data:
                s3c.download_fileobj(raw_bucket, target_file, data)                


            with open(file) as result:
                    uniqlines = list(result.readlines())
                    uniqlines.append(funcionario)
                    uniqlines = set(uniqlines)

                    with open(file, 'w') as temp:
                        temp.write('\n'.join(str(line) for line in uniqlines))

            with open(file, 'rb') as data:
                s3c.upload_fileobj(data, raw_bucket,target_file)

            pass


if __name__ == "__main__":

    funcionarios = sys.argv[1].split(',')
    funcionarios_list = [x for x in funcionarios]
    print(funcionarios_list)

    aws_access_key_id =  os.environ.get('AWS_ACCESS_KEY_ID')
    aws_secret_access_key = os.environ.get('AWS_SECRET_ACCESS_KEY')
    
    s3c = boto3.client(
        's3',
        aws_access_key_id = aws_access_key_id,
        aws_secret_access_key = aws_secret_access_key
    )

    raw_bucket = 'dpa-compranet'
    bucket = 'etl/declaranet/raw/'

    Declaranet(funcionarios_list,s3c,raw_bucket,bucket)