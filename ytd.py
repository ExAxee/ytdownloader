#!/usr/bin/python3
# coding=utf-8
from urllib.parse import unquote
import requests
import json
import sys
import re
import logging
import argparse
import os

#TODO: testing, adding the download and convert (from mp4 to mp3) function + playlist loop + channel monitoring

#log levels dict with logging counterpart as values
logLevels = {
    "info": logging.INFO,
    "debug": logging.DEBUG,
    "warn": logging.WARN,
    "error": logging.ERROR,
}

class RequestFailError(Exception):
    """failed request"""

def remove_spec(data):
    """
    removes special characters from a string
    """
    if isinstance(data, str):
        return data.encode("ascii", "ignore").decode("ascii")
    elif isinstance(data, list):
        return [d.encode("ascii", "ignore").decode("ascii") for d in data]

def extract_id(link):
    """
    extracts the video id from a link
    """
    if len(link) == 11: #len of video IDs are 11 characters
        logging.debug(f"found a 11 character string, could be video id: {link}")
        return link
    else:
        matches = re.search(
            r'^(http|https)://(www.youtube.com/watch\?v=|youtu.be/)(?P<id>[a-zA-Z0-9\-_]+)((&.*)|$)',
            link
        )

        #check if regex matching is succesfull, if so there might be a video ID, otherwise error
        try:
            logging.debug(f"regex video ID extracting returned: {matches.group('id')}")
            return matches.group("id")
        except AttributeError:
            logging.error(f"'{link}' is not an extended or contracted youtube link or a 11 characters video ID")
            raise ValueError(f"'{link}' is not an extended or contracted youtube link or a 11 characters video ID")

def query(id):
    """
    query youtube api for video info
    """
    logging.debug(f"queried youtube server for id {id}")
    #query the api for video informations
    return requests.get("https://www.youtube.com/get_video_info?&video_id="+id)

def process_data(raw_data):
    """
    converts a string containing variables to a python dict
    """
    global args
    #remove special characters from the query and decompile the URL (with the urllib.parse.unquote())
    raw_data = remove_spec(unquote(str(raw_data.content.decode("ascii")))).split("&")

    data = {}
    #decode data and translate to python dict
    for single in raw_data:
        eqIndex = single.find("=")
        try:
            data[f'{single[:eqIndex]}'] = json.loads(single[eqIndex+1:])
        except json.decoder.JSONDecodeError:
            data[f'{single[:eqIndex]}'] = single[eqIndex+1:]

    #check if the API sent a fail response
    if data["status"] == "fail":
        logging.error(f"request got 'fail' status")
        raise RequestFailError("request got 'fail' status")

    #dumps set to be dumped on log file
    if not args.dumps:
        if not args.no_python:
            logging.debug(f"PYTHON DATA PROCESS DUMP: {str(data)}")
        if not args.no_json:
            logging.debug(f"JSON DATA PROCESS DUMP: {json.dumps(data)}")

    #dumps set to be dumped on separated file
    else:
        with open(args.dumps, "a") as dumpFile:
            if not args.no_python:
                dumpFile.write(f"PYTHON DATA PROCESS DUMP: {str(data)}"+"\n")
            if not args.no_json:
                dumpFile.write(f"JSON DATA PROCESS DUMP: {json.dumps(data)}"+"\n")

    return data

def filter_data(data):
    """
    removes useless data
    """
    global args

    output = {}
    #save only useful data
    output["streamingData"] = data["player_response"]["streamingData"]
    output["videoDetails"] = data["player_response"]["videoDetails"]

    #dumps set to be dumped on log file
    if not args.dumps:
        if not args.no_python:
            logging.debug(f"PYTHON DATA FILTERING DUMP: {str(output)}")
        if not args.no_json:
            logging.debug(f"JSON DATA FILTERING DUMP: {json.dumps(output)}")

    #dumps set to be dumped on separated file
    else:
        with open(args.dumps, "a") as dumpFile:
            if not args.no_python:
                dumpFile.write(f"PYTHON DATA FILTERING DUMP: {str(output)}"+"\n")
            if not args.no_json:
                dumpFile.write(f"JSON DATA FILTERING DUMP: {json.dumps(output)}"+"\n")

    return output

def display(data, tab=4):
    """
    displays a json formatted
    """
    return json.dumps(data, indent=tab)

def main(args, link):
    if args.debug:
        global logLevels

        #wipe out the dumps file if no_overwrite is FALSE
        if args.dumps:
            if not args.no_overwrite:
                with open(args.dumps, "wt") as file:
                    file.write("")

        #retrieve and check that the log level is correct
        try:
            selectedLevel = logLevels[args.log_level]
        except KeyError:
            raise ValueError(f"invalid log level value: {args.log_level}")

        #start the logger
        logging.basicConfig(
            filename = args.debug_file,
            filemode = "w",
            level = selectedLevel,
            format = '%(asctime)s %(levelname)s: %(message)s',
            datefmt = '%d-%m-%Y %I:%M:%S %p'
        )

    #get the video info
    data = filter_data(process_data(query(extract_id(link))))

if __name__ == "__main__":
    #defining command line options
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "cmd",
        type = str,
        help = "the command to execute on the link"
    )
    parser.add_argument(
        "link",
        type = str,
        help = "the link of the video"
    )
    parser.add_argument(
        "-p", "--no-python",
        dest = "no_python",
        action = "store_true",
        help = "disable python dump"
    )
    parser.add_argument(
        "-j", "--no-json",
        dest = "no_json",
        action = "store_true",
        help = "disable json dump"
    )
    parser.add_argument(
        "-f", "--file",
        dest = "debug_file",
        default = f"{os.path.abspath(__file__).replace('.py', '')}_debug.txt",
        metavar = "FILE",
        action = "store",
        help = "debug FILE, note that if '-d' isn't present this argument will be ignored"
    )
    parser.add_argument(
        "-d", "--debug",
        dest = "debug",
        action = "store_true",
        help = "writes debug on specified FILE if specified, else it will print the debug data on default FILE"
    )
    parser.add_argument(
        "-l", "--log-level",
        dest = "log_level",
        action = "store",
        default = "debug",
        choices = ["info", "debug", "warn", "error"],
        help = "sets the log level, default 'debug', note that if '-d' isn't present this argument will be ignored",
    )
    parser.add_argument(
        "-s", "--separate-dumps",
        dest = "dumps",
        metavar = "DUMPS FILE",
        action = "store",
        help = "separates the json and python dump from the log and outputs it in the DUMPS FILE, this option can be used only with '-d' otherwise will be ignored"
    )
    parser.add_argument(
        "-n", "--no-overwrite",
        dest = "no_overwrite",
        action = "store_true",
        help = "do not overwrite the dump file, append output instead, this option can be used only with '-s' otherwise will be ignored"
    )

    args = parser.parse_args()

    #display program options for debug purposes
    if args.debug:
        print(args)
    main(args, args.link)
