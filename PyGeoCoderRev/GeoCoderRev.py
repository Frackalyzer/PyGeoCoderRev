# -*- coding: utf-8 -*-

# ========================================================================
#
# Copyright � 2016 Khepry Quixote
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#     http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# ========================================================================

import argparse
import csv
import datetime
import io
import json
import os
import requests

from pprint import pprint
from time import time

import reverse_geocoder as rg

pgm_name = 'GeoCoderRev.py'
pgm_version = '1.0'

quotemode_choices = ['QUOTE_MINIMAL', 'QUOTE_NONE', 'QUOTE_ALL', 'QUOTE_NONNUMERIC']

def delimiter_xlator(delimiter_str):

    delimiter_val = ','
    
    if delimiter_str == '\\t':
        delimiter_val = '\t'
    
    return delimiter_val

def quotemode_xlator(quote_mode_str):

    quote_mode_val = csv.QUOTE_MINIMAL
    
    if quote_mode_str.upper() == 'QUOTE_MINIMAL':
        quote_mode_val = csv.QUOTE_MINIMAL
    elif quote_mode_str.upper() == 'QUOTE_ALL':
        quote_mode_val = csv.QUOTE_ALL
    elif quote_mode_str.upper() == 'QUOTE_NONE':
        quote_mode_val = csv.QUOTE_NONE
    elif quote_mode_str.upper() == 'QUOTE_NONNUMERIC':
        quote_mode_val = csv.QUOTE_NONNUMERIC
    
    return quote_mode_val

def get_datetime_value(value, pattern, null_value):
    
    value = value.strip()
    try:
        value = datetime.datetime.strptime(value, pattern)
    except ValueError:
        value = null_value
    return value

def get_float_value(value, null_value):
    
    value = value.strip()
    if value != '':
        try:
            rtn_value = float(value)
        except:
            rtn_value = null_value
    else:
        rtn_value = null_value
    return rtn_value

def get_int_value(value, null_value):
    
    value = value.strip()
    if value != '':
        try:
            rtn_value = int(value)
        except:
            rtn_value = null_value
    else:
        rtn_value = null_value
    return rtn_value

arg_parser = argparse.ArgumentParser(prog='%s' % pgm_name, description='Reverse geo-code an NCEDC-formatted earthquake CSV file.')

arg_parser.add_argument('--src-file-path', required=True, help='source file path')
arg_parser.add_argument('--src-delimiter', default=',', help='source file delimiter character')
arg_parser.add_argument('--src-quotechar', default='"', help='source file quote character')
arg_parser.add_argument('--src-quotemode', dest='src_quotemode_str', default='QUOTE_MINIMAL', choices=quotemode_choices, help='source file quoting mode (default: %s)' % 'QUOTE_MINIMAL')
arg_parser.add_argument('--src-date-ymd-separator', default='/', help='source date year, month, day separator (default: /)')

arg_parser.add_argument('--dtg-parse-pattern', default='%Y-%m-%d %H:%M:%S', help='Date-Time-Group Pattern (default: %Y-%m-%d %H:%M:%S)')

arg_parser.add_argument('--out-file-path', default=None, help='output file path (default: None, same path as source file)')
arg_parser.add_argument('--out-delimiter', default=',', help='output file delimiter character')
arg_parser.add_argument('--out-quotechar', default='"', help='output file quote character')
arg_parser.add_argument('--out-quotemode', dest='out_quotemode_str', default='QUOTE_MINIMAL', choices=quotemode_choices, help='output file quoting mode (default: %s)' % 'QUOTE_MINIMAL')
arg_parser.add_argument('--out-header-row', default='Y', choices=['Y','N'], help='output a header row to file (default: Y)')
arg_parser.add_argument('--out-db-null-value', default=None, help='output null value (default: NULL)')
arg_parser.add_argument('--out-es-null-value', default=None, help='output null value (default: NULL)')
arg_parser.add_argument('--out-elastic-search', default='N', choices=['Y','N'], help='output to ElasticSearch index (default: N)')

arg_parser.add_argument('--es-host-url', default='localhost', help='ElasticSearch host URL')
arg_parser.add_argument('--es-port-number', default='9200', help='ElasticSearch port number')
arg_parser.add_argument('--es-index-name', default='quakes', help='ElasticSearch index name')

arg_parser.add_argument('--out-file-name-folder', default=None, help='output file name folder (default: None')
arg_parser.add_argument('--out-file-name-prefix', default='NCEDC_earthquakes', help='output file name prefix (default: NCEDC_earthquakes')
arg_parser.add_argument('--out-file-name-suffix', default='_reverse_geocoded', help='output file name suffix (default: _reverse_geocoded)')
arg_parser.add_argument('--out-file-name-extension', default='.csv', help='output file name extension (default: .csv)')
arg_parser.add_argument('--out-date-ymd-separator', default='-', help='output date year, month, day separator (default: -)')

arg_parser.add_argument('--max-rows', type=int, default=0, help='maximum rows to process, 0 means unlimited')
arg_parser.add_argument('--flush-rows', type=int, default=1000, help='flush rows interval')

arg_parser.add_argument('--version', action='version', version='version=%s %s' % (pgm_name, pgm_version))

args = arg_parser.parse_args()

args.out_header_row = args.out_header_row.upper();

if args.out_file_path is None:
    if args.out_file_name_folder is None:
        args.out_file_name_folder = os.path.dirname(args.src_file_path)
    args.out_file_path = os.path.join(args.out_file_name_folder, args.out_file_name_prefix + args.out_file_name_suffix + args.out_file_name_extension)
    
args.src_quotemode_enm = quotemode_xlator(args.src_quotemode_str)
args.out_quotemode_enm = quotemode_xlator(args.out_quotemode_str)

args.src_delimiter = delimiter_xlator(args.src_delimiter)
args.out_delimiter = delimiter_xlator(args.out_delimiter)

args.max_rows = abs(args.max_rows)
args.flush_rows = abs(args.flush_rows)

if args.src_file_path.startswith('~'):
    args.src_file_path = os.path.expanduser(args.src_file_path)
args.src_file_path = os.path.abspath(args.src_file_path)

if args.out_file_path.startswith('~'):
    args.out_file_path = os.path.expanduser(args.out_file_path)
args.out_file_path = os.path.abspath(args.out_file_path)
    
print ('Reverse-geocoding source NCEDC earthquakes file: "%s"' % args.src_file_path)
print ('Outputting to the target NCEDC earthquakes file: "%s"' % args.out_file_path)
print ('')

print('Command line args:')
pprint (vars(args))
print('')

es_actions = []

if args.out_elastic_search == 'Y':
    from elasticsearch import Elasticsearch, helpers

# beginning time hack
bgn_time = time()

# initialize
# row counters
row_count = 0
out_count = 0

# if the source file exists
if os.path.exists(args.src_file_path):

    if args.out_elastic_search == 'Y':
        # make sure ES is up and running
        res = requests.get('http://' + args.es_host_url + ':' + args.es_port_number)
        pprint(res.content)
        #connect to the ElasticSearch cluster
        es = Elasticsearch([{'host': args.es_host_url, 'port': args.es_port_number}])
        #delete the quakes index
        es.indices.delete(index=args.es_index_name, ignore=[400,404])

    # open the target file for writing
    with io.open(args.out_file_path, 'w', newline='') as out_file:

        # open the source file for reading
        with io.open(args.src_file_path, 'r', newline='') as src_file:

            # open a CSV file dictionary reader object
            csv_reader = csv.DictReader(src_file, delimiter=args.src_delimiter, quotechar=args.src_quotechar, quoting=args.src_quotemode_enm)

            # obtain the field names from
            # the first line of the source file
            fieldnames = csv_reader.fieldnames
            # append the reverse geo-coding
            # result fields to field names list
            fieldnames[fieldnames.index('DateTime')] = 'Event_DTG'
            fieldnames.append('Event_Year')
            fieldnames.append('Event_Month')
            fieldnames.append('Event_Day')
            fieldnames.append('Event_Hour')
            fieldnames.append('Event_Min')
            fieldnames.append('Event_Sec')
            fieldnames.append('cc')
            fieldnames.append('admin1')
            fieldnames.append('admin2')
            fieldnames.append('name')

            # instantiate the CSV dictionary writer object with the modified field names list
            csv_writer = csv.DictWriter(out_file, delimiter=args.out_delimiter, quotechar=args.out_quotechar, quoting=args.out_quotemode_enm, fieldnames=fieldnames)

            # output the header row
            if args.out_header_row == 'Y':
                csv_writer.writeheader()
            
            # beginning time hack
            bgn_time = time()

            # reader row-by-row
            for row in csv_reader:

                row_count += 1
                
                # tweak column to null
                # if it's not a valid date-time stamp
                row['Event_DTG'] = row['Event_DTG'][:-3].replace(args.src_date_ymd_separator, args.out_date_ymd_separator)
                event_dtg = get_datetime_value(row['Event_DTG'], args.dtg_parse_pattern, args.out_db_null_value)

                # only output rows with valid DTGs
                if event_dtg != args.out_db_null_value:
                    # remove last 3 characters (.00)
                    # so that the timestamp will be more
                    # suitable for importation into databases
                    row['Event_Year'] = event_dtg.year
                    row['Event_Month'] = event_dtg.month
                    row['Event_Day'] = event_dtg.day
                    row['Event_Hour'] = event_dtg.hour
                    row['Event_Min'] = event_dtg.minute
                    row['Event_Sec'] = event_dtg.second
                    
                    # tweak columns to NULL
                    # if they're not numeric
                    row['Depth'] = get_float_value(row['Depth'], args.out_db_null_value);
                    row['Magnitude'] = get_float_value(row['Magnitude'], args.out_db_null_value);
                    row['NbStations'] = get_int_value(row['NbStations'], args.out_db_null_value);
                    row['Gap'] = get_float_value(row['Gap'], args.out_db_null_value);
                    row['Distance'] = get_float_value(row['Distance'], args.out_db_null_value);
                    
                    # remove DateTime column
                    row.pop('DateTime', None)
    
                    # convert string lat/lon
                    # to floating-point values
                    latitude = float(row['Latitude'])
                    longitude = float(row['Longitude'])
                    
                    row['Latitude'] = get_float_value(row['Latitude'], args.out_db_null_value)
                    row['Longitude'] = get_float_value(row['Longitude'], args.out_db_null_value)
    
                    # instantiate coordinates tuple
                    coordinates = (latitude, longitude)
    
                    # search for the coordinates
                    # returning the cc, admin1, admin2, and name values
                    # using a mode 1 (single-threaded) search
                    results = rg.search(coordinates, mode=1) # default mode = 2
    
                    # if results obtained
                    if results is not None:
                        # result-by-result
                        for result in results:
                            # map result values
                            # to the row values
                            row['cc'] = result['cc']
                            row['admin1'] = result['admin1']
                            row['admin2'] = result['admin2']
                            row['name'] = result['name']
                            # output a row
                            if args.out_header_row == 'Y' or row_count > 1:
                                csv_writer.writerow(row)
                                out_count += 1
                                if args.out_elastic_search == 'Y':
                                    # es.index(index=args.es_index_name, doc_type='quake', id=out_count, body=body)
                                    action = {'_index': args.es_index_name, '_type': 'quake', '_id': out_count, '_source': json.dumps(row)}
                                    es_actions.append(action)
                    else:
                        # map empty values
                        # to the row values
                        row['cc'] = ''
                        row['admin1'] = ''
                        row['admin2'] = ''
                        row['name'] = ''
                        # output a row
                        if args.out_header_row == 'Y' or row_count > 1:
                            csv_writer.writerow(row)
                            out_count += 1
                            if args.out_elastic_search == 'Y':
                                # es.index(index=args.es_index_name, doc_type='quake', id=out_count, body=body)
                                action = {'_index': args.es_index_name, '_type': 'quake', '_id': out_count, '_source': json.dumps(row)}
                                es_actions.append(**row)

                # if row count equals or exceeds max rows
                if args.max_rows > 0 and row_count >= args.max_rows:
                    # break out of reading loop
                    break

                # if row count is modulus
                # of the flush count value
                if row_count % args.flush_rows == 0:

                    # flush accumulated
                    # rows to target file
                    out_file.flush()
                    
                    if args.out_elastic_search == 'Y' and len(es_actions) > 0:
                        helpers.bulk(es, es_actions)
                        es_actions.clear()

                    # ending time hack
                    end_time = time()
                    # compute records/second
                    seconds = end_time - bgn_time
                    if seconds > 0:
                        rcds_per_second = row_count / seconds
                    else:
                        rcds_per_second = 0
                    # output progress message
                    message = "Processed: {:,} rows in {:,.0f} seconds @ {:,.0f} records/second".format(row_count, seconds, rcds_per_second)
                    print(message)
                    
else:
    
    print ('NCEDC-formatted Earthquake file not found: "%s"' % args.src_file_path)
    
if args.out_elastic_search == 'Y' and len(es_actions) > 0:
    helpers.bulk(es, es_actions)
    es_actions.clear()

# ending time hack
end_time = time()
# compute records/second
seconds = end_time - bgn_time
if seconds > 0:
    rcds_per_second = row_count / seconds
else:
    rcds_per_second = row_count
# output end-of-processing messages
message = "Processed: {:,} rows in {:,.0f} seconds @ {:,.0f} records/second".format(row_count, seconds, rcds_per_second)
print(message)
print('Output file path: "%s"' % args.out_file_path)
print("Processing finished, {:,} rows output!".format(out_count))



