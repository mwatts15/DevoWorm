from __future__ import print_function
from functools import partial
import csv
import pygraphviz as pgv
import sys
import xlrd

# Column indices
ORDER = 0
PARENT = 1
CHILDA = 2
CHILDB = 3
LARGER = 4
ASYMMETRIC = 5

NIKIL_INDICES = {
    'cell':0,
    'parent':1,
    'lineage_name':2,
    'birth':3,
    'death':4,
    'type':5,
    'description':6
}

NIKIL_ROW_OFFSET = 1

ROW_OFFSET = 1
LARGE_LABEL = 'L'
SMALL_LABEL = 'S'
ASYM_LABEL = 'A'
SAME_LABEL = 'Z'

LABEL_COLOR_MAP = {LARGE_LABEL : 'red',
                   SMALL_LABEL : 'cadetblue1',
                   ASYM_LABEL  : 'gray',
                   SAME_LABEL  : 'green'}
LABEL_WEIGHT_MAP = {LARGE_LABEL : 10,
                    SMALL_LABEL : 5}

REJECTS = set([406, 290])



existing_idents = set()


def idgen(x):
    z = '|'.join(str(y) for y in x)
    s = hash(z)
    if s == 3163574879612140193:
        print(z)
    if s in existing_idents:
        print("Possible identity hash collision with "
                        "data='{}' and hash={}".format(z, s), file=sys.stderr)
        s += 1
    existing_idents.add(s)
    return s


def g(sheet, row, idx):
    return sheet.cell_value(row + ROW_OFFSET, idx)


def p(ident, s, t):
    print("{},{},{}".format(ident, s, t))


def pi(s, t, label):
    p(idgen((s, t)), s, t)


def c(i, l):
    print("{},{}".format(i, l))


def helper(sheet, row_num, f):
    larger = g(sheet, row_num, LARGER)
    is_asymmetric = (g(sheet, row_num, ASYMMETRIC) == 1)
    a = g(sheet, row_num, CHILDA)
    b = g(sheet, row_num, CHILDB)

    if larger != 'X' and not is_asymmetric:
        if len(a) == 0 or len(b) == 0:
            raise Exception(
                "One or both child cells are empty"
                " for a symmetrical division on row {}."
                " Values are {}".format(
                    row_num + ROW_OFFSET + 1,
                    (a, b, larger, is_asymmetric)))
        alabel = LARGE_LABEL if larger == 'A' else SMALL_LABEL
        blabel = LARGE_LABEL if larger == 'B' else SMALL_LABEL
        if alabel == LARGE_LABEL or b == SMALL_LABEL:
            f(a, alabel)
            f(b, blabel)
        else:
            f(b, blabel)
            f(a, alabel)
    elif is_asymmetric:
        if len(a) > 0 and len(b) == 0:
            f(a, ASYM_LABEL)
        elif len(b) > 0 and len(a) == 0:
            f(b, ASYM_LABEL)
        elif len(a) > 0 and len(b) > 0:
            raise Exception(
                "Asymmetrical division has 2 children on row {}".format(
                    row_num +
                    ROW_OFFSET +
                    1))
    elif len(a) > 0 and len(b) > 0:
        f(a, SAME_LABEL)
        f(b, SAME_LABEL)


def lol(sheet):
    graph = pgv.AGraph(directed=True)
    for row_num in range(0, sheet.nrows - ROW_OFFSET):
        if g(sheet, row_num, ORDER) in REJECTS:
            continue
        parent = g(sheet, row_num, PARENT)
        sg = graph.add_subgraph()
        def pgvedge(t, ident):
            if t.startswith('AB'):
                pop = sg
            else:
                pop = graph
            pop.add_node(t,
                    style='filled',
                    fillcolor=LABEL_COLOR_MAP[ident],
                    weight=LABEL_WEIGHT_MAP.get(ident, 0),
                    largesmall=ident)
            pop.add_edge(parent, t, largesmall=ident)
        f = pgvedge
        helper(sheet, row_num, f)
    add_sibling_edges(graph)
    graph.layout('dot')
    return graph

def add_sibling_edges(graph):
    ns = graph.nodes()
    for n in ns:
        if n.attr['largesmall'] == SMALL_LABEL:
            parents = graph.predecessors(n)
            for p in parents:
                siblings = graph.successors(p)
                for s in siblings:
                    if s.attr['largesmall'] == LARGE_LABEL:
                        sg = graph.subgraph((n, s), n+":"+s, rank='same')
                        sg.add_edge(s, n, style='invisible', arrowhead='none')

def add_timing(graph, timings):
    reader = csv.reader(timings, delimiter='\t')
    for i in range(NIKIL_ROW_OFFSET):
        next(reader)
    for row in reader:
        name = row[NIKIL_INDICES['lineage_name']]
        birth = row[NIKIL_INDICES['birth']]
        death = row[NIKIL_INDICES['death']]
        try:
            n = graph.get_node(name)
        except:
            continue
        n.attr['birth_time'] = birth
        n.attr['death_time'] = death

if __name__ == '__main__':
    from argparse import ArgumentParser
    parser = ArgumentParser()
    parser.add_argument("lineage", help="an xlsx or xls file with relative "
            "size of cells. Formatted like "
            "(division_order,parent,daughterA,daughterB,larger[A or B],"
            "asymmetric_division[1=>yes,0=>no], ...)")
    parser.add_argument("sheet", help="the name of the sheet to use for "
            "lineage and relative size data.", nargs="?")
    parser.add_argument("-t", "--timing", dest="timings_file",
                      help="The CSV file for timings of birth and/or death"
                      " of cells. Formatted like "
                      "(cell,parent,lineage_name,birth,death, ...)")
    args = parser.parse_args()
    xls_file = args.lineage
    sheet_name = args.sheet

    wb = xlrd.open_workbook(xls_file)
    if sheet_name is not None:
        sheet = wb.sheet_by_name(sheet_name)
    else:
        sheet = wb.sheet_by_index(0)

    graph = lol(sheet)
    if args.timings_file is not None:
        timings = open(args.timings_file, mode='r')
        add_timing(graph, timings)
    graph.draw('diff-tree.png')
    print(graph)
