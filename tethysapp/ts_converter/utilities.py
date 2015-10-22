import os
#from tethys_apps.base.persistent_store import get_persistent_store_engine as gpse
import urllib2
from lxml import etree
from datetime import datetime
from datetime import timedelta
from dateutil import parser
import csv
from collections import OrderedDict
import re
from django.http import HttpResponse
import zipfile
import StringIO
import requests
from tethys_sdk.gizmos import TimeSeries
import xml.etree.ElementTree as ET

import time



def get_version(root):
    wml_version = None
    for element in root.iter():
        if '{http://www.opengis.net/waterml/2.0}Collection' in element.tag:
            wml_version = '2.0'
            break
        if '{http://www.cuahsi.org/waterML/1.1/}timeSeriesResponse' \
        or '{http://www.cuahsi.org/waterML/1.0/}timeSeriesResponse' in element.tag:
            wml_version = '1'
            break
    return wml_version

#drew 20150401 convert date string into datetime obj
def time_str_to_datetime(t):
    try:
        t_datetime=parser.parse(t)
        return t_datetime
    except ValueError:
        print "time_str_to_datetime error: "+ t
        raise Exception("time_str_to_datetime error: "+ t)
        return datetime.now()


#drew 20150401 convert datetime obj into decimal second (epoch second)
def time_to_int(t):
    try:
        d=parser.parse(t)
        t_sec_str=d.strftime('%s')
        return int(t_sec_str)
    except ValueError:
        print ("time_to_int error: "+ t)
        raise Exception('time_to_int error: ' + t)



def parse_1_0_and_1_1(root):

    try:
        if 'timeSeriesResponse' in root.tag or 'timeSeries' in root.tag or "soap:Envelope":

            # lists to store the time-series data
            for_graph = []
            for_highchart = []
            my_times = []
            my_values = []

            t0 = time.time()

            # metadata items
            units, site_name, variable_name = None, None, None
            unit_is_set = False

            # iterate through xml document and read all values
            for element in root.iter():
                brack_lock = -1
                if '}' in element.tag:
                    brack_lock = element.tag.index('}')  #The namespace in the tag is enclosed in {}.
                    tag = element.tag[brack_lock+1:]     #Takes only actual tag, no namespace

                if 'value' == tag:
                    my_times.append(element.attrib['dateTime'])
                    my_values.append(element.text)
                else:
                    if 'unitName' == tag:  # in the xml there is a unit for the value, then for time. just take the first
                        if not unit_is_set:
                            units = element.text
                            unit_is_set = True

                    if 'noDataValue' == tag:
                        nodata = element.text
                    if 'siteName' == tag:
                        site_name = element.text
                    if 'variableName' == tag:
                        variable_name = element.text

            print "root.iter time: " + str(time.time() - t0)

            t0 = time.time()

            for i in range(0, len(my_times)):
                t= datetime.strptime(my_times[i], '%Y-%m-%dT%H:%M:%S')

                #check to see if there are null values in the time series
                if my_values[i] == nodata:
                    for_highchart.append([t, None])
                else:
                    for_highchart.append([t, float(my_values[i])])

            smallest_time = for_highchart[0][0]
            largest_time = for_highchart[len(for_highchart) - 1][0]

            print "convert time time: " + str(time.time() - t0)

            #print request.get_host()

            #dates = []
            #data = []
            #item = []
            #for k, v in values.items():
            #    dates = values.keys()
            #    data = values.values()
            #for i in range(0,len(dates)):
            #    time_str = dates[i]
            #    values_str = data[i]
            #    t= datetime.strptime(time_str, '%Y-%m-%dT%H:%M:%S')
            #    if values_str == nodata: #check to see if there are null values in the time series
            #        value_float = None
            #    else:
            #        value_float = float(values_str)
            #    #item.append([t,value_float])
            #    for_highchart.append([t,value_float])

            #smallest_time = list(values.keys())[0]
            #largest_time =  list(values.keys())[0]
            #for t in list(values.keys()):
            #    if t < smallest_time:
            #        smallest_time = t
            #    if t>largest_time:
            #        largest_time = t

            return {
                    'site_name': site_name,
                    'start_date': str(smallest_time),
                    'end_date':str(largest_time),
                    'variable_name': variable_name,
                    'units': units,
                    'for_graph': for_graph,
                    'wml_version': '1',
		            'for_highchart':for_highchart}
        else:
            return "Parsing error: The waterml document doesn't appear to be a WaterML 1.0/1.1 time series"
    except Exception, e:
        print e
        return "Parsing error: The Data in the Url, or in the request, was not correctly formatted for water ml 1."

# Prepare for Chart Parameters
def chartPara(ts_original,for_highcharts):

    title_text= ts_original ['site_name']+" "+ ts_original['start_date'] +" - "+ts_original['end_date']
    x_title_text = "Time Period"
    y_title_text = ts_original['units']
    # Timeseries plot example

    timeseries_plot = TimeSeries(
    height='500px',
    width='500px',
    engine='highcharts',
    title= ts_original ['site_name']+" "+ts_original['start_date']+" - "+ts_original['end_date'],
    y_axis_title='Snow depth',
    y_axis_units='m',
    show_legend = False,
    legend={
            'layout': 'horizontal',
            'align': 'left',
            'verticalAlign': 'middle',
            'borderWidth': 0
    },
    series= for_highcharts

)
    return timeseries_plot



def parse_2_0(root):

    try:
        if 'Collection' in root.tag:
            ts = etree.tostring(root)
            keys = []
            vals = []
            for_graph = []
            for_highchart=[]
            units, site_name, variable_name, latitude, longitude, method = None, None, None, None, None, None
            name_is_set = False
            variable_name = root[1].text
            for element in root.iter():
                if 'MeasurementTVP' in element.tag:
                        for e in element:
                            if 'time' in e.tag:
                                keys.append(e.text)
                            if 'value' in e.tag:
                                vals.append(e.text)
                if 'uom' in element.tag:
                    units = element.text
                if 'MonitoringPoint' in element.tag:
                    for e in element.iter():
                        if 'name' in e.tag and not name_is_set:
                            site_name = e.text
                            name_is_set = True
                        if 'pos' in e.tag:
                            lat_long = e.text
                            lat_long = lat_long.split(' ')
                            latitude = lat_long[0]
                            longitude = lat_long[1]
                if 'observedProperty' in element.tag:
                    for a in element.attrib:
                        if 'title' in a:
                            variable_name = element.attrib[a]
                if 'ObservationProcess' in element.tag:
                    for e in element.iter():
                        if 'processType' in e.tag:
                            for a in e.attrib:
                                if 'title' in a:
                                    method=e.attrib[a]
                if 'noDataValue'in element.tag:
                    for e in element.iter():
                        nodata = e.text

            for i in range(0,len(keys)):
                time_str=keys[i]
                time_obj=time_str_to_datetime(time_str)
                if vals[i] == nodata:
                    val_obj = None
                else:
                    val_obj=float(vals[i])
                item=[time_obj,val_obj]
                for_highchart.append(item)
            values = dict(zip(keys, vals))

            for k, v in values.items():
                t = time_to_int(k)
                for_graph.append({'x': t, 'y': float(v)})
            smallest_time = list(values.keys())[0]
            largest_time = list(values.keys())[0]
            for t in list(values.keys()):
                if t < smallest_time:
                    smallest_time = t
                if t> largest_time:
                    largest_time = t
	    test = "testingkkkk"	   
            return {'time_series': ts,
                    'site_name': site_name,
                    'start_date': smallest_time,
                    'end_date':largest_time,
                    'variable_name': variable_name,
                    'units': units,
                    'values': values,
                    'for_graph': for_graph,
                    'wml_version': '2.0',
                    'latitude': latitude,
                    'longitude': longitude,
                    'for_highchart':for_highchart,
		    'test':test
                    }
        else:
            print "Parsing error: The waterml document doesn't appear to be a WaterML 2.0 time series"
            return "Parsing error: The waterml document doesn't appear to be a WaterML 2.0 time series"
    except:
        print "Parsing error: The Data in the Url, or in the request, was not correctly formatted."
        return "Parsing error: The Data in the Url, or in the request, was not correctly formatted."


def TimeSeriesConverter(string_data):
    data = None
    counter = None
    #xml_string = str(xml_data)
    #root = etree.fromstring(xml_string)
    #converted_file = xml_data

    #using strings
    # if '<wps:ComplexData encoding="UTF-8" mimeType="text/plain">' in xml_string:
    #     tag = '<wps:ComplexData encoding="UTF-8" mimeType="text/plain">'
    #     location = xml_string.find(tag)
    #     new= xml_string[location+len(tag):len(xml_string)]
    #     tag2 = '<'
    #     location2 = new.find(tag2)
    #     final = new[0:location2]
    #     split = final.split()
    #     data= []
    for_highchart =[]
    split = string_data.split()

    time = split[::2]
    value = split[1::2]
    item = []

    for i in range(0,len(time)):
            time_str = time[i]
            value_str = value[i]
            if value_str == "NA": #check to see if there are null values in the time series
                 value_float = None
            else:
                value_float = float(value_str)

            time_int = datetime.strptime(time_str, '%Y-%m-%d')
            for_highchart.append([time_int,value_float])
    return {
                'for_highchart':for_highchart,
           }


def Original_Checker(html):
    root = etree.XML(html)
    wml_version = get_version(root)
    if wml_version == '1':
        return parse_1_0_and_1_1(root)
    elif wml_version == '2.0':
        return parse_2_0(root)


def file_unzipper(url_cuashi):
    #this function is for unzipping files
    ts =[]
    site_name =None
    smallest_time=None
    largest_time=None
    variable_name=None
    units=None
    values=None
    for_graph=None
    latitude=None
    longitude=None
    for_highchart=None

    r = requests.get(url_cuashi)
    z = zipfile.ZipFile(StringIO.StringIO(r.content))

    file_list = z.namelist()
    for  file in file_list:
        joe = z.read(file)

    return file_list



def csv_reader(file):
    #this was designed to read the cuashi data which is in csv format, however, this likely change to waterml format
    for_highchart=[]
    z_object = file.open("nwisuv-salt_creek_at_nephi,_ut-gage_height,_feet.csv")
    csv_cuashi = csv.reader(z_object)

    for row in csv_cuashi:
        #row   associate time_obj and val_obj with row values
        time_obj = row[0]
        val_obj = row[3]
        item=[time_obj,val_obj]
        for_highchart.append(item)

    return for_highchart