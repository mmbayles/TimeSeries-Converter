# wps.des: timeSeriesConverter2, title = Convert time series to weekly, 
# abstract = Convert time series to new time frame; 
# wps.in: url, string;
# wps.in: interval, string;
# wps.in: stat, string;
# wps.out: output, text;
library(WaterML)
library(xts)
library(lubridate)
#water ml 2 test
#server <- 'http://worldwater.byu.edu/app/index.php/byu_test_justin/services/cuahsi_1_1.asmx/GetValues?location=byu_test_justin:B-Lw&variable=byu_test_justin:WATER&startDate=&endDate='
#url <-'http://hydrodata.info/chmi-h/cuahsi_1_1.asmx/GetValuesObject?location!CHMI-H:140~variable!CHMI-H:TEPLOTA~startDate!2015-07-01~endDate!2015-07-10~authToken!'
#TEST
#server <- 'http://hydrodata.info/chmi-h/cuahsi_1_1.asmx/GetValuesObject?location=CHMI-H:140&variable=CHMI-H:TEPLOTA&startDate=2015-07-01&endDate=2015-07-10&authToken='
#server <- 'http://worldwater.byu.edu/app/index.php/byu_test_justin/services/cuahsi_1_1.asmx/GetValuesObject?location=byu_test_justin:B-Lw&variable=byu_test_justin:WATER&startDate=&endDate='

#url <- 'http://hydrodata.info/chmi-h/cuahsi_1_1.asmx/GetValuesObject?location=CHMI-H:140&variable=CHMI-H:TEPLOTA&startDate=2015-07-01&endDate=2015-07-10&authToken='
#NA values
#server <-'http://hydrodata.info/chmi-d/cuahsi_1_1.asmx/GetValuesObject?location=CHMI-D:171&variable=CHMI-D:PRUTOK&startDate=2014-07-01&endDate=2015-07-30&authToken='
stat <- 'mean'
interval <- "weekly"
#url <- 'http://worldwater.byu.edu/app/index.php/byu_test_justin/services/cuahsi_1_1.asmx/GetValues?location=byu_test_justin:B-Lw&variable=byu_test_justin:WATER&startDate=&endDate='
#url <- "http://localhost:8000/apps/ts-converter/temp_waterml/cuahsi/cuahsi-wdc-2015-11-10-75637385.xml/"
#server <- gsub("!", "=", url)
#server <- gsub("~", "&", server)
#values <- GetValues(server)

#check for any errors
# attribute <- attributes(values)
# download_status <- attribute$download.status
# parse_status <- attribute$parse.status
# #get time series object
# n = nrow(values)

#if n is 0 then some error happened
# if (n == 0){
#   output <- "error"
#   status <- c(download_status, parse_status)
#   write.zoo(status, output)
# } else {
  
#url = '[[datetime.datetime(1990, 9, 1, 2, 0), 66.5983870967742], [datetime.datetime(1990, 9, 2, 5, 0), 75.3446666666667], [datetime.datetime(1990, 9, 3, 7, 0), 90.1029032258064]]'
  url2 = gsub("datetime.datetime", "", url)
  url2 = gsub("\\(", "", url2)
  url2 = gsub("\\)", "", url2)
  library(RJSONIO)
  test = fromJSON(url2, simplify=TRUE)
  counter = 1
  for(i in test)
  {
    if (counter ==1)
    {
      year =toString(i[1])
      month =toString(i[2])
      day =toString(i[3])
      hour= toString(i[4])
      minute=toString(i[5])
      time = paste(year,month,day,hour,minute, sep= ' ')
      date = c(time)
      value = i[6]

    }
    else
    {
      year =toString(i[1])
      month =toString(i[2])
      day =toString(i[3])
      hour= toString(i[4])
      minute=toString(i[5])
      time = paste(year,month,day,hour,minute, sep= ' ')
      date = c(date,time)
      value  = c(value,i[6])
    
    }
    counter = counter +1
  }
  date1 = as.POSIXct(date, format ="%Y %m %d %H %M")
  df = data.frame(times=date1, values=value)
  ts <- xts(df$values, order.by = df$times)
  
  if (interval == "daily"){
    ts_daily <-apply.daily(ts,stat)
    date<- as.Date(as.POSIXlt(time(ts_daily)))
    value <- as.double(ts_daily)
    daily_data <- data.frame(date,value)
    final_ts <- xts(daily_data$value, order.by = date)
    
  }
  if (interval == "weekly")
  {
    ts_weekly <- apply.weekly(ts,stat)
    date<- as.Date(as.POSIXlt(time(ts_weekly)))
    value <- as.double(ts_weekly)
    weekly_data <- data.frame(date,value)
    final_ts <- xts(weekly_data$value, order.by = date)
  }
  #convert to monthly
  if (interval == "monthly")
  {
    ts_monthly<- apply.monthly(ts, stat)
    #Converting the time so it displays as the first day of the month and trimming time of day off
    date<- as.Date(as.yearmon(time(ts_monthly)))
    value <- as.double(ts_monthly)
    monthly_data <- data.frame(date,value)
    final_ts <- xts(monthly_data$value, order.by = date)
  }
  if (interval == "yearly")
  {
    ts_yearly <- apply.yearly(ts,stat)
    date<- as.Date(as.POSIXlt(time(ts_yearly)))
    value <- as.double(ts_yearly)
    yearly_data <- data.frame(date,value)
    final_ts <- xts(yearly_data$value, order.by = date)
  }
  
  #plot(ts_weekly)
  #plot(ts)
  #plot(ts_monthly)
  #plot(ts_daily)
  #plot(final_ts)
  #rm(list=ls())
  #write the output
  output <- "Weekly Values"
  write.zoo(final_ts,output)
#}