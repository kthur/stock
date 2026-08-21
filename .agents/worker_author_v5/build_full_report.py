# Full report builder
import os

def get_sec1_2():
    with open(r'd:\Finance\code\stock\.agents\worker_author_v5\part1.py', 'r', encoding='utf-8') as f:
        loc1 = {}
        exec(f.read(), loc1)
        s1 = loc1['part1_text']
    with open(r'd:\Finance\code\stock\.agents\worker_author_v5\part2.py', 'r', encoding='utf-8') as f:
        loc2 = {}
        exec(f.read(), loc2)
        s2 = loc2['part2_text']
    return s1 + '\n\n' + s2

