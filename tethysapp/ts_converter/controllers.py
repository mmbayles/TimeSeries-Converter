from django.shortcuts import render
from utilities import *
from tethys_sdk.gizmos import MessageBox
from tethys_gizmos.gizmo_options import *
from owslib.wps import WebProcessingService
from owslib.wps import printInputOutput
from owslib.wps import monitorExecution
from owslib.wps import WPSExecution
from django.core.servers.basehttp import FileWrapper
from django.http import HttpResponse
import shutil
#from tethys_apps.sdk import list_wps_service_engines
import xml.etree.ElementTree as ET
import sys
import unittest
import requests
import tempfile
import csv
from datetime import datetime
import urllib2
from .model import engine, SessionMaker, Base, URL,rscript,SessionMaker1,Base1,engine1
from hs_restclient import HydroShare, HydroShareAuthBasic
import dicttoxml
import ast
import zipfile
import StringIO

import random
import urllib
import json
import webbrowser
# -- coding: utf-8--

#Base_Url_HydroShare REST API
url_base='http://{0}.hydroshare.org/hsapi/resource/{1}/files/{2}'
##Call in Rest style
temp_dir = None

def restcall(request,branch,res_id,filename):

    url_wml= url_base.format(branch,res_id,filename)
    response = urllib2.urlopen(url_wml)
    html = response.read()
    timeseries_plot = chartPara(html,filename)
    context = {"timeseries_plot":timeseries_plot}
    return render(request, 'ts_converter/home.html', context)
#Normal Get or Post Request
#http://dev.hydroshare.org/hsapi/resource/72b1d67d415b4d949293b1e46d02367d/files/referencetimeseries-2_23_2015-wml_2_0.wml/

def View_R_Code(request):
    context = View_R()
    return render(request, 'ts_converter/View_R_Code.html', context)

def temp_waterml(request,folder,id):
    base_path = "/tmp/"
    file_path = base_path + folder+"/"+id
    response = HttpResponse(FileWrapper(open(file_path)), content_type='application/xml')
    return response

def delete_file(request):
    global temp_dir
    session = SessionMaker()
    urls = session.query(URL).all()#clears the database of the urls.
    for url in urls:
        session.delete(url)
        session.commit()
    session.close()
    # shutil.rmtree(temp_dir)#deletes the temp files associated with the zip file

def home(request):
    url_wml=None
    name = None
    show_time = False
    no_url = False
    output_converter = None
    number_ts = []#stores highcharts info of each time series
    Base.metadata.create_all(engine)
    url_list = []
    plot = None
    counter = 0
    r_script = None
    script_test =[]
    legend = []
    url_check =[]
    download_bool = False
    string_download = None
    url_data_validation=[]
    Current_r = "Select an R script"
    show_hydroshare = False
    show_waterml = False
    show_cuahsi = False
    timeseries_plot =None
    outside_input = False
    filename_zip = None
    url_zip =None
    zip_bool = False #checks if file is zipped
    global temp_dir
    error_message = None #stores any errors with the app
    show_input = False
    update_url = None
    cuahsi_split = None
    zipped_url =[]
    unit_types =[]

    user_id = request.user.username

    if user_id == None:
        user_id = random.random()

    if request.GET and 'res_id' in request.GET and 'src' in request.GET:
        outside_input = True
        if request.GET['src'] == "hydroshare":
            show_hydroshare = True
        elif request.GET['src']=='cuahsi':
            zip_string = "zip"
            show_cuahsi =True
            outside_input = True
            #if zip_string.find(request.GET['cuahsi']) != 0:
            zip_bool = True
            #Make a dictionary to hold the ids passed by CUAHSI
            cuahsi_data = request.GET['res_id']#retrieves ids from url
            cuahsi_split = cuahsi_data.split(',')#splits ideas by commma
    if request.POST and 'hydroshare' in request.POST:
        show_hydroshare = True
    if request.POST and 'water_ml' in request.POST:
        show_waterml = True
    if request.POST and 'show_input' in request.POST:
        show_input = True

    if request.POST:
        Current_r = request.POST['select_r_script']
      #new code for zip_file
    if zip_bool == True:
        session = SessionMaker()
        urls1 = session.query(URL).all()
        session.close()
        #urls1 =[]
        if urls1 != []:
            x=2
        else:
            base_temp_dir = tempfile.tempdir
            temp_dir = os.path.join(base_temp_dir, "cuahsi")
            if not os.path.exists(temp_dir):
                os.makedirs(temp_dir)
            for id in cuahsi_split:
                url_zip = "http://bcc-hiswebclient.azurewebsites.net/CUAHSI/HydroClient/WaterOneFlowArchive/"+id+'/zip'
                r = requests.get(url_zip)
                try:
                    z = zipfile.ZipFile(StringIO.StringIO(r.content))
                    file_list = z.namelist()

                    try:
                        for file in file_list:
                            joe1 = z.read(file)
                            #file_temp = tempfile.NamedTemporaryFile(delete = False, dir = temp_dir)
                            file_temp = open(temp_dir + "/" + id + ".xml", 'wb')
                            file_temp.write(joe1)
                            file_temp.close()
                            #getting the URL of the zip file
                            base_url = request.build_absolute_uri()
                            if "?" in base_url:
                                base_url = base_url.split("?")[0]

                            zipped_url.append(base_url + "temp_waterml" + file_temp.name[4:])
                            #url2 = URL(url = zipped_url)
                            # session = SessionMaker()
                            # session.add(url2)
                            # session.commit()
                            # session.close()


                    except etree.XMLSyntaxError as e: #checks to see if data is an xml
                        print "Error:Not XML"
                        #quit("not valid xml")
                    except ValueError, e: #checks to see if Url is valid
                        print "Error:invalid Url"
                    except TypeError, e: #checks to see if xml is formatted correctly
                        print "Error:string indices must be integers not str"
                except  zipfile.BadZipfile as e:
                        error_message = "Bad Zip File"
                        print "Bad Zip file"+ id

    # this block of code will add a time series to the legend and graph the result
    if (request.POST and "add_ts" in request.POST):

        if not outside_input:
            Current_r = request.POST['select_r_script']

        if request.POST.get('hydroshare_resource') != None and request.POST.get('hydroshare_file')!= None:
            try:
                #adding a hydroshare resource
                hs = HydroShare()
                hs_resource = request.POST['hydroshare_resource']
                hs_file = request.POST['hydroshare_file']
                #hs_text =hs.getResourceFile("b29ac5ce06914752aaac74685ba0f682","DemoReferencedTimeSeries-wml_1.xml")
                hs_text =hs.getResourceFile(hs_resource,hs_file)
                # hs_lst =[] This was an old methond to extract the data from the resource. Probably obsolete
                # for line in hs_text:
                #     hs_lst.append(line)
                # xml = ''.join(hs_lst)
                url_hs_resource = "https://www.hydroshare.org/resource/"+hs_resource+"/data/contents/"+hs_file
                #graph_original = Original_Checker(xml)
                session = SessionMaker()
                url1 = URL(url = url_hs_resource)
                session.add(url1)
                session.commit()
                session.close()
            except etree.XMLSyntaxError as e: #checks to see if data is an xml
                print "Error:Not XML"
                #quit("not valid xml")
            except ValueError, e: #checks to see if Url is valid
                print "Error:invalid Url"
            except TypeError, e: #checks to see if xml is formatted correctly
                print "Error:string indices must be integers not str"
         #adding data through cuahsi or from a water ml url
        if request.POST.get('url_name') != None:
            try:

                update_url = request.build_absolute_uri()+'?id='+request.POST.get('url_name')

                print update_url

                #webbrowser.open(update_url,new=0)

                # zip file name
                # html = response.read()
                # graph_original = Original_Checker(html)
                # url_data_validation.append(graph_original['site_name'])

                # session = SessionMaker()
                # session.add(url1)
                # session.commit()
                # session.close()
            except etree.XMLSyntaxError as e: #checks to see if data is an xml
                print "Error:Not XML"
                #quit("not valid xml")
            except ValueError, e: #checks to see if Url is valid
                print "Error:invalid Url"
            except TypeError, e: #checks to see if xml is formatted correctly
                print "Error:string indices must be integers not str"



    # session = SessionMaker()
    # urls = session.query(URL).all()
    # if cuahsi_split != None:
    #     for id in cuahsi_split:#creates a list of timeseries data and displays the results in the legend
    #             #look in temp dir for folder cuahsi and look for data
    #             base_url = request.build_absolute_uri()
    #             if "?" in base_url:
    #                 base_url = base_url.split("?")[0]
    #             zipped_url = base_url + "temp_waterml/cuahsi/" +id +'.xml'
    #             response = urllib2.urlopen(zipped_url)
    #             html = response.read()
    #             #url_list.append(url.url)
    #             # response = urllib2.urlopen(url.url)
    #             # html = response.read()
    #             #graph_original1 = ast.literal_eval(graph_original)#this displays the whole document
    #             graph_original1 = Original_Checker(html)
    #             legend.append(graph_original1['site_name'])
    #     # session.close()

    if cuahsi_split != None and "clear_all_ts" not in request.POST and error_message == None:
        for id in cuahsi_split:
            counter = counter +1#counter for testing
            #graphs the original time series
            base_url = request.build_absolute_uri()
            if "?" in base_url:
                base_url = base_url.split("?")[0]
            zipped_url1 = base_url + "temp_waterml/cuahsi/" +id +'.xml'
            response = urllib2.urlopen(zipped_url1)
            html = response.read()
            graph_original = Original_Checker(html)
            legend.append(graph_original['site_name'])
            units_space = ' '+graph_original['units']
            tooltip_units = {'valueSuffix': units_space}
            graph_type = 'spline'
            number_ts.append({'name':graph_original['site_name']+" "+graph_original['data_type'],'data':graph_original['for_highchart'],'tooltip':tooltip_units,'type':graph_type})
            unit_types.append(graph_original['units'])
        timeseries_plot = chartPara(graph_original,number_ts,unit_types)#plots graph data
        print 'graph'

    if request.POST and "clear_all_ts" in request.POST:
        session = SessionMaker()
        urls = session.query(URL).all()
        for url in urls:
             session.delete(url)
             session.commit()
        session.close()
        legend = None
        url_list =[]
        Current_r = request.POST['select_r_script']
        print 'clear'

    if request.POST and "select_r" in request.POST:
        session = SessionMaker1()
        script1 = session.query(rscript).all()
        for script in script1:
            session.delete(script)
            session.commit()
        script = rscript(rscript = request.POST['select_r_script'])
        session.add(script)
        session.commit()
        session.close()
        r = View_R()
        r1 = r['r_code']
        #code to locate the inputs of the r script
        test1 = "wps.in"
        Current_r = request.POST['select_r_script']
        for m in re.finditer(test1,r1):
            counter = counter+1

    if request.POST and "run" in request.POST:
        download_bool = True
        display_r=[]
        session = SessionMaker1()
        script1 = session.query(rscript).all()
        session.close()
        for script in script1:
            display_r.append(script.rscript)
        Current_r = display_r[0]
        #this is the default chart if no values are given
        if url_list is None:
            filename = 'KiWIS-WML2-Example.wml'
            url_wml='http://hydrodata.info/chmi-h/cuahsi_1_1.asmx/GetValuesObject?location=CHMI-H:140&variable=CHMI-H:TEPLOTA&startDate=2015-07-01&endDate=2015-07-10&authToken='
            no_url = True
            response = urllib2.urlopen(url_wml)
            html = response.read()
            graph_info = Original_Checker(html)
            number_ts1 = [{'name':"timeseries1", 'data':graph_info['for_highchart']}]
            timeseries_plot = chartPara(graph_info,number_ts1)
        # Plotting the altered time series
        else:
            for x in zipped_url:
                print x
                counter = counter +1#counter for testing
                #graphs the original time series
                response = urllib2.urlopen(x)
                html = response.read()
                graph_original = Original_Checker(html)
                url_user = str(graph_original['for_highchart'])
                #url_user = '[[datetime.datetime(2015, 3, 16, 12, 0), 0.4687637], [datetime.datetime(2015, 4, 16, 0, 0), 1.2060138], [datetime.datetime(2015, 5, 16, 12, 0), 2.3565671], [datetime.datetime(2015, 6, 16, 0, 0), 2.8779197], [datetime.datetime(2015, 7, 16, 12, 0), 0.97303045], [datetime.datetime(2015, 8, 16, 12, 0), 0.5432831], [datetime.datetime(2015, 9, 16, 0, 0), 1.811853], [datetime.datetime(2015, 10, 16, 12, 0), 2.2585738], [datetime.datetime(2014, 11, 16, 0, 0), 0.29075155], [datetime.datetime(2014, 12, 16, 12, 0), 0.10494206], [datetime.datetime(2015, 1, 16, 12, 0), 0.07379243], [datetime.datetime(2015, 2, 15, 0, 0), 0.05195976], [datetime.datetime(2015, 3, 16, 12, 0), 1.0816772], [datetime.datetime(2015, 4, 16, 0, 0), 1.0290958], [datetime.datetime(2015, 5, 16, 12, 0), 2.6539428], [datetime.datetime(2015, 6, 16, 0, 0), 3.4307652], [datetime.datetime(2015, 7, 16, 12, 0), 3.2504485], [datetime.datetime(2015, 8, 16, 12, 0), 2.5487366], [datetime.datetime(2015, 9, 16, 0, 0), 0.35241804], [datetime.datetime(2015, 10, 16, 12, 0), 2.4712648], [datetime.datetime(2014, 11, 16, 0, 0), 0.18294963], [datetime.datetime(2014, 12, 16, 12, 0), 0.13204327], [datetime.datetime(2015, 1, 16, 12, 0), 0.05318553], [datetime.datetime(2015, 2, 15, 0, 0), 0.34240192], [datetime.datetime(2015, 3, 16, 12, 0), 1.3678982], [datetime.datetime(2015, 4, 16, 0, 0), 0.44945353], [datetime.datetime(2015, 5, 16, 12, 0), 1.4077636], [datetime.datetime(2015, 6, 16, 0, 0), 0.65902823], [datetime.datetime(2015, 7, 16, 12, 0), 2.2765038], [datetime.datetime(2015, 8, 16, 12, 0), 2.093973], [datetime.datetime(2015, 9, 16, 0, 0), 2.714291], [datetime.datetime(2015, 10, 16, 12, 0), 0.35507312], [datetime.datetime(2014, 11, 16, 0, 0), 0.31254554], [datetime.datetime(2014, 12, 16, 12, 0), 0.022514295], [datetime.datetime(2015, 1, 16, 12, 0), 0.2022325], [datetime.datetime(2015, 2, 15, 0, 0), 0.51500654], [datetime.datetime(2015, 3, 16, 12, 0), 0.5644128], [datetime.datetime(2015, 4, 16, 0, 0), 0.7911287], [datetime.datetime(2015, 5, 16, 12, 0), 0.7695898], [datetime.datetime(2015, 6, 16, 0, 0), 3.2202513], [datetime.datetime(2015, 7, 16, 12, 0), 3.4671786], [datetime.datetime(2015, 8, 16, 12, 0), 0.5232663], [datetime.datetime(2015, 9, 16, 0, 0), 0.81560314], [datetime.datetime(2015, 10, 16, 12, 0), 0.5004286], [datetime.datetime(2014, 11, 16, 0, 0), 1.229176], [datetime.datetime(2014, 12, 16, 12, 0), 0.24215013], [datetime.datetime(2015, 1, 16, 12, 0), 0.641244], [datetime.datetime(2015, 2, 15, 0, 0), 0.033244014], [datetime.datetime(2015, 3, 16, 12, 0), 1.4303902], [datetime.datetime(2015, 4, 16, 0, 0), 0.97417426], [datetime.datetime(2015, 5, 16, 12, 0), 2.2388763], [datetime.datetime(2015, 6, 16, 0, 0), 1.1739765], [datetime.datetime(2015, 7, 16, 12, 0), 2.131405], [datetime.datetime(2015, 8, 16, 12, 0), 1.3522924], [datetime.datetime(2015, 9, 16, 0, 0), 1.850921], [datetime.datetime(2015, 10, 16, 12, 0), 2.5836248], [datetime.datetime(2014, 11, 16, 0, 0), 1.3244176], [datetime.datetime(2014, 12, 16, 12, 0), 0.20626609], [datetime.datetime(2015, 1, 16, 12, 0), 0.48686036], [datetime.datetime(2015, 2, 15, 0, 0), 0.56055295], [datetime.datetime(2015, 3, 16, 12, 0), 1.19279], [datetime.datetime(2015, 4, 16, 0, 0), 0.49651814], [datetime.datetime(2015, 5, 16, 12, 0), 1.2154142], [datetime.datetime(2015, 6, 16, 0, 0), 3.5210965], [datetime.datetime(2015, 7, 16, 12, 0), 2.9103389], [datetime.datetime(2015, 8, 16, 12, 0), 2.6708305], [datetime.datetime(2015, 9, 16, 0, 0), 0.9893299], [datetime.datetime(2015, 10, 16, 12, 0), 0.015304906], [datetime.datetime(2014, 11, 16, 0, 0), 0.24606898], [datetime.datetime(2014, 12, 16, 12, 0), 0.17924778], [datetime.datetime(2015, 1, 16, 12, 0), 0.5226817], [datetime.datetime(2015, 2, 15, 0, 0), 1.0992111], [datetime.datetime(2015, 3, 16, 12, 0), 1.0592027], [datetime.datetime(2015, 4, 16, 0, 0), 0.55345345], [datetime.datetime(2015, 5, 16, 12, 0), 2.43756], [datetime.datetime(2015, 6, 16, 0, 0), 1.2366621], [datetime.datetime(2015, 7, 16, 12, 0), 1.1939199], [datetime.datetime(2015, 8, 16, 12, 0), 3.5670526], [datetime.datetime(2015, 9, 16, 0, 0), 2.1513865], [datetime.datetime(2015, 10, 16, 12, 0), 0.17826281], [datetime.datetime(2014, 11, 16, 0, 0), 0.19185047], [datetime.datetime(2014, 12, 16, 0, 0), 0.33142585], [datetime.datetime(2015, 1, 16, 0, 0), 0.17706592], [datetime.datetime(2015, 2, 16, 0, 0), 0.12939842], [datetime.datetime(2015, 3, 16, 0, 0), 0.15770492], [datetime.datetime(2015, 4, 16, 0, 0), 0.5526809], [datetime.datetime(2015, 5, 16, 0, 0), 2.3036177], [datetime.datetime(2015, 6, 16, 0, 0), 0.6897724], [datetime.datetime(2015, 7, 16, 0, 0), 3.5882857], [datetime.datetime(2015, 8, 16, 0, 0), 0.4832196], [datetime.datetime(2015, 9, 16, 0, 0), 1.2909276], [datetime.datetime(2015, 10, 16, 0, 0), 2.0389023], [datetime.datetime(2014, 11, 16, 0, 0), 0.45220014], [datetime.datetime(2014, 12, 16, 0, 0), 0.13951139], [datetime.datetime(2015, 1, 16, 0, 0), 0.54272], [datetime.datetime(2015, 2, 16, 0, 0), 0.7042717], [datetime.datetime(2015, 3, 16, 0, 0), 1.3916432], [datetime.datetime(2015, 4, 16, 0, 0), 0.7334498], [datetime.datetime(2015, 5, 16, 0, 0), 2.4111311], [datetime.datetime(2015, 6, 16, 0, 0), 0.5632143], [datetime.datetime(2015, 7, 16, 0, 0), 3.6230378], [datetime.datetime(2015, 8, 16, 0, 0), 1.0739588], [datetime.datetime(2015, 9, 16, 0, 0), 0.6407836], [datetime.datetime(2015, 10, 16, 0, 0), 0.76491606], [datetime.datetime(2014, 11, 16, 0, 0), 0.60798514], [datetime.datetime(2014, 12, 16, 0, 0), 0.92295164], [datetime.datetime(2015, 1, 16, 0, 0), 1.956165], [datetime.datetime(2015, 2, 16, 0, 0), 0.12065205], [datetime.datetime(2015, 3, 16, 0, 0), 0.24137658], [datetime.datetime(2015, 4, 16, 0, 0), 0.7165153], [datetime.datetime(2015, 5, 16, 0, 0), 2.290265], [datetime.datetime(2015, 6, 16, 0, 0), 0.55367684], [datetime.datetime(2015, 7, 16, 0, 0), 0.48462275], [datetime.datetime(2015, 8, 16, 0, 0), 3.0355728], [datetime.datetime(2015, 9, 16, 0, 0), 0.28944403], [datetime.datetime(2015, 10, 16, 0, 0), 0.31943414], [datetime.datetime(2014, 11, 16, 0, 0), 0.4897593], [datetime.datetime(2014, 12, 16, 0, 0), 0.66060466], [datetime.datetime(2015, 1, 16, 0, 0), 0.58972883], [datetime.datetime(2015, 2, 16, 0, 0), 0.21849114], [datetime.datetime(2015, 3, 16, 0, 0), 1.7927823], [datetime.datetime(2015, 4, 16, 0, 0), 1.2815297], [datetime.datetime(2015, 5, 16, 0, 0), 2.580564], [datetime.datetime(2015, 6, 16, 0, 0), 1.3993183], [datetime.datetime(2015, 7, 16, 0, 0), 0.539018], [datetime.datetime(2015, 8, 16, 0, 0), 2.8998299], [datetime.datetime(2015, 9, 16, 0, 0), 0.6856699], [datetime.datetime(2015, 10, 16, 0, 0), 1.3357453], [datetime.datetime(2014, 11, 16, 0, 0), 0.48350984], [datetime.datetime(2014, 12, 16, 0, 0), 0.16278747], [datetime.datetime(2015, 1, 16, 0, 0), 0.85441273], [datetime.datetime(2015, 2, 16, 0, 0), 0.22092977], [datetime.datetime(2015, 3, 16, 0, 0), 0.3587158], [datetime.datetime(2015, 4, 16, 0, 0), 0.72462857], [datetime.datetime(2015, 5, 16, 0, 0), 2.2729144], [datetime.datetime(2015, 6, 16, 0, 0), 4.159633], [datetime.datetime(2015, 7, 16, 0, 0), 1.1491205], [datetime.datetime(2015, 8, 16, 0, 0), 0.753043], [datetime.datetime(2015, 9, 16, 0, 0), 1.7102681], [datetime.datetime(2015, 10, 16, 0, 0), 0.026214987]]'
                #number_ts.append({'name':graph_original['site_name'],'data':graph_original['for_highchart']})
                # url_user = str(x)
                # url_user = url_user.replace('=', '!')
                # url_user = url_user.replace('&', '~')
                if Current_r == "Time Series Converter":
                    interval = str(request.POST['select_interval'])
                    stat = str(request.POST['select_stat'])
                    process_id = 'org.n52.wps.server.r.timeSeriesConverter2'
                    input = [("url",url_user),("interval",interval),("stat",stat)]
                    output = "output"
                    #process_input = '<?xml+version="1.0"+encoding="UTF-8"+standalone="yes"?><wps:Execute+service="WPS"+version="1.0.0"++xmlns:wps="http://www.opengis.net/wps/1.0.0"+xmlns:ows="http://www.opengis.net/ows/1.1"++xmlns:xlink="http://www.w3.org/1999/xlink"+xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"++xsi:schemaLocation="http://www.opengis.net/wps/1.0.0++http://schemas.opengis.net/wps/1.0.0/wpsExecute_request.xsd">++<ows:Identifier>org.n52.wps.server.r.convert-time-series</ows:Identifier>++<wps:DataInputs>++++<wps:Input>++++++<ows:Identifier>url</ows:Identifier>++++++<wps:Data>++++++++<wps:LiteralData>'+url_user+'</wps:LiteralData>++++++</wps:Data>++++</wps:Input>++++<wps:Input>++++++<ows:Identifier>interval</ows:Identifier>++++++<wps:Data>++++++++<wps:LiteralData>'+interval+'</wps:LiteralData>++++++</wps:Data>++++</wps:Input>++++<wps:Input>++++++<ows:Identifier>stat</ows:Identifier>++++++<wps:Data>++++++++<wps:LiteralData>'+stat+'</wps:LiteralData>++++++</wps:Data>++++</wps:Input>++</wps:DataInputs>++<wps:ResponseForm>++++<wps:ResponseDocument+storeExecuteResponse="false">++++++<wps:Output+asReference="false">++++++++<ows:Identifier>output</ows:Identifier>++++++</wps:Output>++++</wps:ResponseDocument>++</wps:ResponseForm></wps:Execute>'
                elif Current_r =="Gap Filler":
                   process_id = 'org.n52.wps.server.r.timeSeriesGapFiller'
                   input = [("url",url_user)]
                   output = "output"
                   #process_input = '<?xml+version="1.0"+encoding="UTF-8"+standalone="yes"?><wps:Execute+service="WPS"+version="1.0.0"++xmlns:wps="http://www.opengis.net/wps/1.0.0"+xmlns:ows="http://www.opengis.net/ows/1.1"++xmlns:xlink="http://www.w3.org/1999/xlink"+xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"++xsi:schemaLocation="http://www.opengis.net/wps/1.0.0++http://schemas.opengis.net/wps/1.0.0/wpsExecute_request.xsd">++<ows:Identifier>org.n52.wps.server.r.timeSeriesGapFiller</ows:Identifier>++<wps:DataInputs>++++<wps:Input>++++++<ows:Identifier>url</ows:Identifier>++++++<wps:Data>++++++++<wps:LiteralData>'+url_user+'</wps:LiteralData>++++++</wps:Data>++++</wps:Input>++</wps:DataInputs>++<wps:ResponseForm>++++<wps:ResponseDocument+storeExecuteResponse="false">++++++<wps:Output+asReference="false">++++++++<ows:Identifier>output</ows:Identifier>++++++</wps:Output>++++</wps:ResponseDocument>++</wps:ResponseForm></wps:Execute>'
                #graphs the new time series
                #wps_request = urllib2.Request(url_wps,process_input)
                #wps_open = urllib2.urlopen(wps_request)
                #wps_read = wps_open.read()
                #graph_info =TimeSeriesConverter(wps_read)#prepares data for graphing
                test_run = run_wps(process_id,input,output)
                download_link = test_run[1]
                string_download = ''.join(download_link)
                upload_hs = string_download
                graph_info =TimeSeriesConverter(test_run[0])#prepares data for graphing
                number_ts.append({'name':graph_original['site_name']+" "+graph_original['data_type']+ ' Convertered','data':graph_info['for_highchart']})
                #legend.append(graph_original['site_name']+' Convertered')
            timeseries_plot = chartPara(graph_original,number_ts,graph_original['units'])#plots graph data

    if error_message!= None:
        error_bool = "True"
    else:
        error_bool = "False"
    text_input_options = TextInput(display_text='Enter URL of Water ML data and click "Add a Time Series"',
                                   name='url_name',
                                    )
    hydroshare_resource = TextInput(display_text='Enter Hydroshare Resouce ID',
                                   name='hydroshare_resource',
                                    )
    hydroshare_file = TextInput(display_text='Enter file name of Hydroshare Resource',
                                   name='hydroshare_file',
                                    )
    select_interval = SelectInput(display_text='Select a new time frame',
                            name='select_interval',
                            multiple=False,
                            options=[('Select a new interval', 'default'),('Daily', 'daily'),('Weekly','weekly'), ('Monthly', 'monthly'), ('Yearly','yearly')],
                            original=['Two'])
    select_stat = SelectInput(display_text='Select a statistics function',
                            name='select_stat',
                            multiple=False,
                            options=[('Select a statistics function', 'no_select'),('Mean', 'mean'), ('Median','median')],
                            original=['Two'])
    select_r_script = SelectInput(display_text='Select a R Script',
                            name='select_r_script',
                            multiple=False,
                            options=[("Select an R script", "Select an R script"),('Time Series Converter', 'Time Series Converter'), ('Gap Filler','Gap Filler')],
                            original=['Two'])
    hydroshare = Button(display_text ="Upload Hydroshare Resource",
                        name ='hydroshare',
                        submit = True)
    water_ml = Button(display_text ="Upload water ml url",
                        name ='water_ml',
                        submit = True)
    show_input1 = Button(display_text ="Manual Input",
                        name ='show_input1',
                        submit = True)
    add_ts = Button(display_text='Add a Time Series',
                       name='add_ts',
                       submit=True)
    clear_all_ts = Button(display_text='Clear all Time Series',
                       name='clear_all_ts',
                       submit=True)
    run = Button(display_text='Run Script',
                       name='run',
                       submit=True)
    download = Button(display_text='Download CSV',
                       name='download',
                       submit=True)
    graph = Button(display_text='Graph Oringal Time Series',
                       name='graph',
                       submit=True)
    select_r = Button(display_text='Select R Script',
                       name='select_r',
                       submit=True)
    upload_hs = Button(display_text='Upload data to HydroShare',
                       name='upload_hs',
                       submit=True)
    message_error =MessageBox(name = 'message_error',
                              title = 'Error',
                              message = error_message,
                              dismiss_button = 'Cancel',
                              affirmative_button = "OK",
                              width = 400,
                              affirmative_attributes = 'href=javascript:void(0);')
    sampleModal = MessageBox(name='sampleModal',
                         title='Message Box Title',
                         message='Congratulations! This is a message box.',
                         dismiss_button='Nevermind',
                         affirmative_button='Proceed',
                         width=400,
                         affirmative_attributes='href=javascript:void(0);')

    context = {
'timeseries_plot':timeseries_plot,
'text_input_options':text_input_options,
'name':name,
'select_interval': select_interval,
'select_stat':select_stat,
'select_r_script':select_r_script,
'show_time':show_time,
'no_url':no_url,
'output_converter':output_converter,
'add_ts':add_ts,
'run':run,
'clear_all_ts':clear_all_ts,
'graph':graph,
'legend':legend,
'select_r':select_r,
'string_download':string_download,
'download_bool':download_bool,
'Current_r': Current_r,
'hydroshare':hydroshare,
'show_hydroshare':show_hydroshare,
'hydroshare_file':hydroshare_file,
'hydroshare_resource':hydroshare_resource,
'water_ml':water_ml,
'show_waterml':show_waterml,
'upload_hs':upload_hs,
'message_error':message_error,
'error_bool':error_bool,
'error_message':error_message,
'sampleModal':sampleModal,
'show_input':show_input,
'show_input1':show_input,
'update_url':update_url
}


    return render(request, 'ts_converter/home.html', context)

def run_wps(process_id,input,output):

    #choose the first wps engine
    #my_engine = WebProcessingService('http://appsdev.hydroshare.org:8282/wps/WebProcessingService', verbose=False, skip_caps=True)
    my_engine = WebProcessingService('http://appsdev.hydroshare.org:8282/wps/WebProcessingService',verbose=False, skip_caps=True)
    my_engine.getcapabilities()
    #wps_engines = list_wps_service_engines()
    #my_engine = wps_engines[0]
    #choose the r.time-series-converter
    my_process = my_engine.describeprocess(process_id)

    my_inputs = my_process.dataInputs
    input_names = [] #getting list of input
    for input1 in my_inputs:
        input_names.append(input1)
    #executing the process..
    execution = my_engine.execute(process_id, input, output)
    request = execution.request
    #set store executeresponse to false
    request = request.replace('storeExecuteResponse="true"', 'storeExecuteResponse="false"')

    url_wps = 'http://appsdev.hydroshare.org:8282/wps/WebProcessingService'

    wps_request = urllib2.Request(url_wps,request)
    wps_open = urllib2.urlopen(wps_request)
    wps_read = wps_open.read()



    if 'href' in wps_read:
        tag = 'href="'
        location = wps_read.find(tag)

        new= wps_read[location+len(tag):len(wps_read)]
        tag2 = '"/>\n    </wps:Output>\n  </wps:ProcessOutputs>\n</wps:'
        location2 = new.find(tag2)
        final = new[0:location2]
        split = final.split()
        wps_request1 = urllib2.Request(split[0])

        wps_open1 = urllib2.urlopen(wps_request1)
        wps_read1 = wps_open1.read()

    #now we must use our own method to send the request1
    #we need to use the request
    #this code is for the normal wps which is not working right now
    # monitorExecution(execution)
    # output_data = execution.processOutputs
    # final_output_url = output_data[0].reference
    # final_data = read_final_data(final_output_url)

    #return [final_output_url, final_data]
    return [wps_read1, split]


def read_final_data(url):
    r = requests.get(url)
    data = r.text
    reader = csv.reader(data.splitlines(), delimiter='\t')
    rows = []
    for row in reader:
        rows.append(row)
    return rows

def View_R():
    display_r =[]
    session = SessionMaker1()
    script1 = session.query(rscript).all()
    session.close()
    for script in script1:
        display_r.append(script.rscript)
    if display_r[0] == "Time Series Converter":
        my_url = "http://appsdev.hydroshare.org:8282/wps/R/scripts/timeSeriesConverter.R"
    elif display_r[0] =="Gap Filler":
        my_url = 'http://appsdev.hydroshare.org:8282/wps/R/scripts/timeSeriesGapFiller.R'
    r = urllib2.urlopen(my_url)
    r_html = r.read()
    r_code = r_html

    return  {'r_code':r_code,'my_url':my_url}

def upload_to_hs(id,file):
    auth = HydroShareAuthBasic(username='mbayles2', password='lego2695')
    hs = HydroShare(auth=auth)
    fpath = '/path/to/somefile.txt'
    resource_id = hs.addResourceFile('id', file)


