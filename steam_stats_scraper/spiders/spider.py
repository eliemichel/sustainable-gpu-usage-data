# This file describes how the Steam stats pages should be scraped


from datetime import datetime as dt
import scrapy
import re

class SteamStatsSpider(scrapy.Spider):
    name = 'steam_stats'

    def start_requests(self):
        yield scrapy.Request('https://store.steampowered.com/hwsurvey/videocard/')

    def parse(self, response):
        print("##################### START PARSE #####################")

        # TABLE HEADERS
        # The table labels correspond to the name of each table on the page, and will be used as keys in the dictionary values_by_table_name
        table_labels = []
        # months_labels = []
        # print("TABLE HEADERS")
        for table_header_div in response.xpath('//div[@class="substats_col_left col_header"]'):
            table_label = table_header_div.xpath('./text()').get()
            table_labels.append(table_label)
        
        # The months correspond to column headers, with each row containing one value per month
        # I commented this bit because months are also stored in the first row of each table
        # print("MONTHS HEADERS")
        # for month_header_div in response.xpath('//div[@class="substats_col_month col_header"]'):
        #     month_label = month_header_div.xpath('./text()').get()
        #     if month_label not in months_labels:
        #         months_labels.append(month_label)

        # print(table_labels, months_labels)
        
        # TABLE VALUES
        values_by_table_name = {}
        curr_table_label = None
        for row_or_header in response.xpath('//div[@id="sub_stats"]/div[re:test(@class, "(substats_row)|(substats_col_left col_header)|(substats_col_left)|(substats_col_month)|(stats_hr_white)")]'):

            # Header column div: contains the name of the table (eg: "ALL VIDEO CARDS")
            if "substats_col_left col_header" in row_or_header.xpath('./@class').get():
                # initialize table values for this label
                curr_table_label = row_or_header.xpath('./text()').get()
                values_by_table_name[curr_table_label] = []

            # Row of values: in more recent pages, values are grouped by row under a "substats_row" div
            elif "substats_row" in row_or_header.xpath('./@class').get():
                # we're dealing with a table row
                # match all columns
                row_div = row_or_header
                row_values = []
                # 
                for col_div in row_div.xpath('div[re:test(@class, "substats_col_(left)|(month$)|(month_last_pct)")]'):
                    # Try extracting text
                    col_text = col_div.xpath('./text()').get()
                    if col_text is None:
                        col_text = col_div.xpath('.//span/text()').get()
                    if col_text is None:
                        col_text = col_div.xpath('.//strong/text()').get()

                    if col_text is not None:
                        row_values.append(col_text)
                
                # Store the row in the current table
                if curr_table_label is not None:
                    values_by_table_name[curr_table_label].append(row_values)

            # Ignore this column (contains the percentage change between months)
            elif "substats_col_month_last_chg" in row_or_header.xpath('./@class').get():
                # ignore
                continue
            # Column containing a value: in older pages, values are listed directly in column divs
            # the trick is to always add values to the latest row, and create rows whenever we encounter a line break (next elif)
            elif "substats_col_left" in row_or_header.xpath('./@class').get() or "substats_col_month" in row_or_header.xpath('./@class').get() :
                # we're dealing with a value column
                # Try extracting text
                col_text = row_or_header.xpath('./text()').get()
                if col_text is None:
                    col_text = row_or_header.xpath('.//span/text()').get()
                if col_text is None:
                    col_text = row_or_header.xpath('.//strong/text()').get()

                # Store the text
                if curr_table_label is not None and col_text is not None:
                    if len(values_by_table_name[curr_table_label]) == 0:
                        # start first row of that table
                        values_by_table_name[curr_table_label].append([])
                    # always add the value to the current row (last one of the table)
                    values_by_table_name[curr_table_label][-1].append(col_text)

            # Line break: in older pages, indicates that we change row
            elif "stats_hr_white" in row_or_header.xpath('./@class').get():
                # line break between rows (old versions of the site)
                # => start new row
                values_by_table_name[curr_table_label].append([])


        # print(values_by_table_name)

        timestamp = response.meta['wayback_machine_time'].timestamp()
        time = dt.fromtimestamp(timestamp).strftime('%d/%m/%y')
        print(f"date = {time}")
        return {
            'url': response.meta['wayback_machine_url'],
            'timestamp': int(timestamp),
            'table_labels': table_labels,
            # 'months_labels': months_labels,
            'values': values_by_table_name
        }


        print("##################### END PARSE #####################")
