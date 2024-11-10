#!/usr/bin/env python3
"""
Educationa; sha-1 brute force attack
Usage: python shacrack.py <SHA-1 hash value>
"""
import datetime
import itertools
import hashlib
import multiprocessing
import sys


def generate_combinations(wordlen):
    '''sha-1 brute force attack with multicpu'''
    for combination in itertools.product('abcdefghijklmnopqrstuvwxyz', repeat=wordlen):
        bruteinput=''.join(combination)
        s = hashlib.sha1()
        s.update(bruteinput.encode("utf-8"))
        h = s.hexdigest()
        if h==shain:
            end_time = datetime.datetime.now()
            print("SHA-1 input:",bruteinput,"\nTime for breaking: ", end_time - start_time)
            sys.exit(0)

#def worker(num):
    # Perform CPU-intensive task here
#    result = ...
#    return result

if len(sys.argv) != 2:
    print("Usage: python shacrack.py <SHA-1 hash value>")
    sys.exit(1)

shain = sys.argv[1]
num_cores = multiprocessing.cpu_count()
#pool = multiprocessing.Pool()
start_time = datetime.datetime.now()
for words in range(1,16):
    generate_combinations(words)
#results = pool.map(worker, range(num_cores))
