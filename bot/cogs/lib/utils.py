import discord
import json
from discord.ext import commands
import traceback
import sys
import os
import glob
import typing
import requests

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
    return v.lower() in ("yes", "true", "yup", "1", "t", "y")

def chunk_list(lst, size):
    # looping till length l
    for i in range(0, len(lst), size):
        yield lst[i:i + size]

def get_random_name():
    nouns = requests.get("https://random-word-form.herokuapp.com/random/noun?count=1").json()
    adjectives = requests.get("https://random-word-form.herokuapp.com/random/adjective?count=1").json()
    results = adjectives + nouns
    return " ".join(w.title() for w in results)
