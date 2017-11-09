from __future__ import print_function
import sys
import xlrd

# Column indices
ORDER = 0
PARENT = 1
CHILDA = 2
CHILDB = 3
LARGER = 4
ASYMMETRIC = 5

ROW_OFFSET = 1
LARGE_LABEL = 'L'
SMALL_LABEL = 'S'
ASYM_LABEL = 'A'
SAME_LABEL = 'Z'

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
    graph.draw('diff-tree.png')
    print(graph)

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
                        #sg.graph_attr['rank'] = 'same'
                        sg.add_edge(s, n, style='invisible', arrowhead='none')


if __name__ == '__main__':
    if len(sys.argv) > 1:
        xls_file = sys.argv[1]
    else:
        print( "Please, provide an xls or "
                "xlsx file as the first argument", file=sys.stderr)
        sys.exit(-1)

    sheet_name = None
    if len(sys.argv) > 2:
        sheet_name = sys.argv[2]

    wb = xlrd.open_workbook(xls_file)
    if sheet_name is not None:
        sheet = wb.sheet_by_name(sheet_name)
    else:
        sheet = wb.get_sheet(1)
    lol(sheet)
