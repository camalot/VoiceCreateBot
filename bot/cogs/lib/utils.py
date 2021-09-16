import discord
import json
from discord.ext import commands
import traceback
import sys
import os
import glob
import typing
import requests
import random
import re
import datetime

def dict_get(dictionary, key, default_value = None):
    if key in dictionary.keys():
        return dictionary[key] or default_value
    else:
        return default_value

def get_scalar_result(conn, sql, default_value = None, *args):
    cursor = conn.cursor()
    try:
        cursor.execute(sql, args)
        return cursor.fetchone()[0]
    except Exception as ex:
        print(ex)
        traceback.print_exc()
        return default_value

def str2bool(v):
    return v.lower() in ("yes", "true", "yup", "1", "t", "y", "on")

def chunk_list(lst, size):
    # looping till length l
    for i in range(0, len(lst), size):
        yield lst[i:i + size]

def get_random_name(noun_count = 1, adjective_count = 1):
    try:
        adjectives = load_from_gist("adjectives", adjective_count)
        nouns = load_from_gist("nouns", noun_count)
        results = adjectives + nouns
        return " ".join(w.title() for w in results)
    except Exception as ex:
        print(ex)
        traceback.print_exc()
        try:
            nouns = requests.get(f"https://random-word-form.herokuapp.com/random/noun?count={str(noun_count)}").json()
            adjectives = requests.get(f"https://random-word-form.herokuapp.com/random/adjective?count={str(adjective_count)}").json()
            results = adjectives + nouns
            print("FROM random-word-form")
            return " ".join(w.title() for w in results)
        except Exception as ex:
            print(ex)
            traceback.print_exc()
            try:
                print("FROM random-word-api")
                results = requests.get(f"https://random-word-api.herokuapp.com/word?number={str(noun_count + adjective_count)}&swear=0").json()
                return " ".join(w.title() for w in results)
            except Exception as ex:
                print(ex)
                traceback.print_exc()
                return "New Voice Channel"

def to_timestamp(date):
    return (date - datetime.datetime(1970,1,1)).total_seconds()
def get_timestamp():
    return to_timestamp(datetime.datetime.now())

def load_from_gist(type, count):
    types = [ "adjectives", "nouns", "verbs" ]
    if type not in types:
        type = "nouns"
    if count <= 0:
        count = 1
    elif count > 10:
        count = 10
    data = requests.get(f"https://gist.githubusercontent.com/camalot/8d2af3796ac86083e873995eab98190d/raw/b39de3a6ba03205380caf5d58e0cae8a869ac36d/{type}.js").text
    data = re.sub(r"(var\s(adjectives|nouns|verbs)\s=\s)|;$","", data)
    jdata = json.loads(data)
    return random.sample(jdata, count)

def get_args_dict(func, args, kwargs):
    args_names = func.__code__.co_varnames[:func.__code__.co_argcount]
    return {**dict(zip(args_names, args)), **kwargs}

def str_replace(input_string: str, *args, **kwargs):
    xargs = get_args_dict(str_replace, args, kwargs)
    result = input_string
    for a in xargs:
        result = result.replace(f"{{{a}}}", kwargs[a])
    return result
