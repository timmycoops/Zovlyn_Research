#!/bin/bash

#Scrape the Latest ASX Company Directory using MPXA
./mpxa scrape asx-company-dir

#Create a unique set of Companys from the ASX Data that is updated to the Materials Sector - this file is then used for the Scraping function and other captures
csvgrep -c "GICs industry group" -m "Materials" '/home/coops/inbox/ASX Companies Directory.csv'  > /home/coops/Outputs/ASX_Materials.csv
awk -F, '{print $1}' '/home/coops/Outputs/ASX_Materials.csv' | cut -c1-3 | sort | uniq -u > /home/coops/Outputs/Company_List.csv

#These commands create take the Manual Cash Spreadsheet and update them to ensure no errors when viewing and create a latest_cash_balances sheet for use in any EV Calculation
awk -F, -v OFS=',' '{gsub(",", " "); print}' /home/coops/Outputs/Manual_Cash.csv | rg '(\w{3}.)(\d+)-(\d+)-(\d+)(.*.txt).(\d*)' -r '$1,$2-$3-$4,$2,$3,$4,$5,$6' | sed '1 i\ASX Code,Date,Year,Month,Day,Title,Cash Balance' > /home/coops/Outputs/All_Cash_Balances.csv
head -n 1 /home/coops/Outputs/All_Cash_Balances.csv > /home/coops/Outputs/Latest_Cash_Balances.csv && tail -n +2 /home/coops/Outputs/All_Cash_Balances.csv | sort -t, -k1,1 -k2,2r | awk -F, '!seen[$1]++' >> /home/coops/Outputs/Latest_Cash_Balances.csv



