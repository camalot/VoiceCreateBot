import discord
import json
from discord.ext import commands
import traceback
import sys
import os
import glob
import typing

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
