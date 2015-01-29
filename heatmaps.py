"""
Usage:
    heatmaps.py [ --term_file=<file> --pickle_file=<file> ]
    heatmaps.py -h | --help
Options:
    -t --term_file=<file>       newline separate list of terms
    -p --pickle_file=<file>
"""
import os
import pickle
from collections import defaultdict

from IPython import embed  #FIXME name collisions sadness
import requests
import libxml2
import numpy as np
import pylab as plt
from docopt import docopt

args = docopt(__doc__, version='heatmaps .0001')


# NOTES: normalize by the first appearance of the term in the literature to attempt to control for historical entrenchment
# consider also normalizing by the total number of records per datasource??

#urls
url_oq_con_term = "http://nif-services.neuinfo.org/ontoquest/concepts/term/"  #used in get_term_id
url_oq_gp_term = "http://nif-services.neuinfo.org/ontoquest/getprop/term/"  # used to get the id for relationship
url_oq_rel = "http://nif-services.neuinfo.org/ontoquest/rel/all/%s?level=1&includeDerived=true&limit=0"  # %s is id
url_serv_summary = "http://nif-services.neuinfo.org/servicesv1/v1/summary.xml?q="

#xpaths
term_id_xpath = "//class[not(contains(id,'NEMO'))]/id/text()"  #FIXME ok for some reason the non-nemo id gives SHIT results
#term_id_xpath = "//class[contains(id,'NEMO')]/id/text()"  #FIXME NEVER MIND! that tree goes nowhere ;_;
rel_id_xpath =  "//class[not(contains(id,'%s'))]/id/text()"  # %s should be relationship here!
child_term_ids_object_xpath = "//relationship[object/@id='%s' and property/@id='%s']/subject/@id"  # %s id %s relationship
child_term_ids_subject_xpath = "//relationship[subject/@id='%s' and property/@id='%s']/object/@id"

#files
file_birnlex_796_rel = "~/Downloads/birnlex_796.xml"


def re_tree_der():
    """
        A rel/all dump with includeDerived=ture on brain flattens everything, the tree is still there, but we have to
        recreate it

        JUST KIDDING! not actually possible because they real did flatten it >_<
    """

    xmlDoc = libxml2.parseEntity(file_birnlex_796_rel)
    c = xmlDoc.xpathNewContext()
    child_term_ids_xpath = "//relationship[subject/@id='%s' and property/@id='%s']/subject/@id"%('birnlex_768',)  # %s id %s relationship
    c.xpathEval(child_term_ids_xpath)


class Summary:
    "the summary xml"


def get_xpath(doc, query):
    """ doc is a string that is an xml document
        query is a string that is a valid xpath query
        returns a list of nodes
    """
    try:
        node = libxml2.parseDoc(doc)
    except libxml2.parserError:  # derp 
        return []
    xpc = node.xpathNewContext()
    return xpc.xpathEval(query)

def run_xpath(url, *queries):
    #xmlDoc = libxml2.parseEntity(url)  #XXX this causes hangs due to no timeout
    #xmlDoc = libxml2.parseFile('/home/tom/Dropbox/neuroinformatics/force15_poster/summary.xml')
    #print("WARNING YOU ARE NOT GETTING REAL DATA")
    #"""
    try:
        resp = requests.get(url, timeout=20)  # sometimes we need a longer timeout :/  FIXME :/ stateful?
    except requests.exceptions.Timeout:
        return [None] * len(queries)
    try:
        xmlDoc = libxml2.parseDoc(resp.text)
    except libxml2.parserError:  # derp 
        return [None] * len(queries)
    #"""
    xpc = xmlDoc.xpathNewContext()
    out = []
    for query in queries:
        out.append(xpc.xpathEval(query))
    if len(queries) == 1:
        return out[0]
    return out

def get_rel_id(relationship):  #FIXME this is NOT consistently ordred! AND is_a and part_of behave VERY differently!
    """
        Used to get relationship ids so that xpath queries will actually work :/
    """
    query_url = url_oq_gp_term + relationship
    #response = requests.get(query_url)
    #ids = get_xpath(response.text, rel_id_xpath%relationship)

    ids = run_xpath(query_url, rel_id_xpath%relationship)
    print([t.content for t in ids])
    try:
        id_ = ids[0].content
    except IndexError:
        id_ = None
    return id_


def get_term_id(term):
    """ Return the id for a term or None if an error occures """
    query_url = url_oq_con_term + term.replace(" ", "%20")
    try:
        response = requests.get(query_url, timeout=20)
    except requests.exceptions.Timeout:
        return None
    ids = get_xpath(response.text, term_id_xpath)
    #ids = run_xpath(query_url, term_id_xpath)
    try:
        id_ = ids[0].content
    except IndexError:
        id_ = None
    return id_

def val_term_id(term, reltionship):  # TODO FIXME this is actually a problem with the ontology ;_;
    """ get term id by validating that this particular term actually has the relationship listed """
    query_url = url_oq_con_term + term.replace(" ", "%20")
    response = requests.get(query_url)
    ids = get_xpath(response.text, term_id_xpath)

def get_child_term_ids(parent_id, level, relationship, child_relationship, exclude_parents=False):
    """ This was burried deep within the tree of kepler actors making it nearly
        impossible to find the actual data. Also, who though that using the
        equivalent of environment variables to pass global information down
        a giant tree of actors was a remotely good idea?

        NOTE: the terms are unordered, not entierly clear when we should try
        to order them

        this will concat all the way up, flattening the tree at that level
        yay dev tools level fail
    """
    #TODO: allow more dynamic traversal of the tree by stoping at nodes where
    #the reference count is zero for all children so we can show relative depth
    #esp. important for coverage of species


    #response = requests.get(url_oq_rel%parent_id)  #FIXME brain returns a truncated result ;_; that is what is breaking things!

    if child_relationship == "subject":
        xpath = child_term_ids_subject_xpath%(parent_id, relationship)
        xnames = "//relationship[subject/@id='%s' and property/@id='%s']/object"%(parent_id, relationship)
    else:
        xpath = child_term_ids_object_xpath%(parent_id, relationship)
        xnames = "//relationship[object/@id='%s' and property/@id='%s']/subject"%(parent_id, relationship)



    #id_list = [n.content for n in get_xpath(response.text, xpath)]  # FIXME not clear if this is returning what we want across all levels of the tree
    query_url = url_oq_rel%parent_id

    id_nodes, name_nodes = run_xpath(query_url, xpath, xnames)
    #id_list = [i.content for i in id_nodes]
    id_name_dict = {id_.content:n.content for id_, n in zip(id_nodes, name_nodes)}

    if level == 1:
        #print(id_list)
        print('level',level,'parent_id',parent_id,'ids',id_name_dict)
        #print([n.content for n in run_xpath(query_url, xnames)])  #FIXME MMMM HIT DAT SERVER

        return id_name_dict
        #return id_list
    else:
        child_dicts = []
        new_level = level - 1
        for id_ in id_name_dict.keys():
            new_dict = get_child_term_ids(id_, new_level, relationship, child_relationship, exclude_parents)  #funstuff here with changing the rels
            child_dicts.append(new_dict)
        if exclude_parents:
            id_name_dict = {}
        for dict_ in child_dicts:
            id_name_dict.update(dict_)
        print('level',level,'parent_id',parent_id,'ids',id_name_dict)
        return id_name_dict

def get_summary_counts(id_):
    if ' ' in id_:
        id_ = '"%s"'%id_  # fix to prevent AND expansion RE: this kills service
    print('getting summary for', id_)
    query_url = url_serv_summary + id_
    #nodes = run_xpath(query_url, '//results/result')
    nodes, name, lit = run_xpath(query_url, '//results/result', '//clauses/query', '//literatureSummary/@resultCount')
    if name:
        name = name[0].content
        print(name)
    if nodes:
        if nodes[0] == None:
            return [('error-0',id_,'ERROR', -100)], None
    else:
        return [('error-1',id_,'ERROR', -100)], None

    #name = run_xpath(query_url, '//clauses/query')[0].content  # FIXME please don't hit this twice ;_;


    nifIds = []
    dbs = []
    indexables = []
    counts = []

    for node in nodes:
        if node.prop('nifId') not in nifIds:  #TODO should we have a simple way to generalize schemas of attributes + content > columns?
            nifId = node.prop('nifId')
            db =  node.prop('db')
            indexable = node.prop('indexable')
            cs = node.xpathEval('./count')
            if len(cs) > 1:
                print(id_, name, [c.content for c in cs])
                raise IndexError('too many counts!')
            count = int(cs[0].content)

            nifIds.append(nifId)
            dbs.append(db)
            indexables.append(indexable)
            counts.append(count)
        else:
            print(node.prop('nifId'))

    #literature
    nifIds.append('nlx_82958')
    dbs.append('PubMed')  # this is a fiction, it comes from PMC too
    indexables.append('Literature')
    counts.append(int(lit[0].content))

    print(dbs)
    return [a for a in zip(nifIds, dbs, indexables, counts)], name



    #counts = get_xpath(response.text, term_id_xpath)


def get_term_count_data(term, level, relationship, child_relationship, exclude_parents=False, term_id=None):
    """
        for a given term go get all its children at a given level and get the
        counts for their instances across databases
    """
    if not term_id:
        term_id = get_term_id(term)  # FIXME this fails to work as expected given relationships
    child_data = {}
    if term_id == None:
        term_id = term
        #print('ERROR:',term,'could not find an id!')
        #return {}, {}
    #else:
    if level == 0:  # FIXME surely there is a more rational place to put this?
        id_name_dict = {term_id:term}
    else:
        id_name_dict = get_child_term_ids(term_id, level, relationship, child_relationship, exclude_parents=exclude_parents)  # TODO this is one place we could add the level info??
    for child_id in id_name_dict.keys():#[0:10]:
        data, term_name = get_summary_counts(child_id)
        print(data)
        child_data[child_id] = data
    return child_data, id_name_dict

problem_ids = ['birnlex_1700', 'birnlex_1571', 'birnlex_1570','birnlex_1577',
               'birnlex_1576','birnlex_1575','birnlex_1574','birnlex_1170',
               'birnlex_1581','birnlex_1583','birnlex_1586',
              ]  # report these, some seem to be redirects in neurolex and a number w/ PONS_brain_region
                 # or regional part of the brain
                 # fairley certain that the stuff that succeeds is cached and that I broke the service


# converting terms and data sources (and eventually anything) into a reliably indexed matrix
# as long as we know the mapping from the ids to the reference table the order actually doesnt matter
# in fact it may make life easier if we can just add new sources on to the end (eh)
# the ids will be used to generate a REFERENCE matrix where ids are mapped to natural numbers 0-n
# various orderings of the ids will be mapped to permutations of the original index
# eg aijth term from the reference matrix will be placed in the bxyth position when a new ordering
# maps i->x and j->y
# aij i->rows j->columns as per convention, we will make the term ids the rows and the source (etc) ids the columns
# this works nicely with the fact that each row has only a subset of the sources
# WE NEED to have the FULL list of terms 
# consideration: the list of terms probably changes more quickly than the list of sources, another argument for keeping
# terms as rows since we will have to iterate over all terms when we index a new source anyway
# XXX DERP just keep the bloody thing in dict form and use the orderings from there
# all we need to know is how many total data sources there are and what index we want to use for each of them (ie we need to fill in the zeros)
# XXX may still want this becasue if we want to reorder on data sources it is going to be a pain if we can't use slicing

full_list_of_datasource_nifids = []  # this is useful if we don't know the number of terms and haven't made a matrix, just a set of lists
map_of_datasource_nifids = {} # better to use a dict to map id -> index  XXX validate uniqueness

def get_source_entity_nifids():
    summary = get_summary_counts('*')
    ids = ['nlx_82958']
    names = ['PubMed']
    #counts = []
    for id_, name, idx, count in summary[0]:
        if id_ not in ids:
            ids.append(id_)
            if name == 'Integrated':
                name = name + ' ' + idx
            names.append(name)
            #counts.append(count)
            #to_sort.append((id_, name, count))

    #TODO sorting here doesnt help and didn't really reveal much of interest
    #order = np.argsort(counts)
    #ids = list(np.array(ids)[order])
    #names = list(np.array(names)[order])
    return ids, names

def make_collapse_map(ids, names):
    """ use the data on source entities and collapse redundant entries """

    collapse = defaultdict(list)

    for id_, name in zip(ids, names):
        collapse[name].append(id_)

    unames = list(collapse.keys())
    unames.sort()  # this masks any prior sorting
    ids_list = []
    for n in unames:
        ids_list.append(tuple(collapse[n]))

    return ids_list, unames

    

def construct_columns(data_dict, term_id_list, datasource_nifid_list, collapse_map=None):
    """
        Given two lists of ids, the first list will be rows the 2nd will be comluns
        The values first list should match the keys in the data dict

        The orderings of both indexes are stored in term_id_list and datasource_nifid_list
        and those can be used to reorder the matrix, or maybe we just call this function again.
    """
    n_cols = len(datasource_nifid_list)

    #make a lookup dict to map nifids to indexes for faster updates
    nid_map = {nid:i for i, nid in enumerate(datasource_nifid_list)}

    rows_to_vstack = []
    for term_id in term_id_list:
        data_list = data_dict[term_id]
        row = np.zeros((n_cols))
        for nifId, _, _, count in data_list:
            if count >= 0:  #ignore errors
                row[nid_map[nifId]] = count
        rows_to_vstack.append(row)

    data_matrix = np.vstack(rows_to_vstack)
    print(data_matrix)
    # a collapse map should be a list of tuples of nifids from the same source
    # it MUST also have an acompanying name mapping (used to generate the list)
    if collapse_map:  # if we dont want the full split on source id
        cols_to_hstack = []
        for id_tup in collapse_map:
            col_tup = [nid_map[id_] for id_ in id_tup]  #get the cols for that id
            new_col = np.sum(data_matrix[:,col_tup], axis=1)
            cols_to_hstack.append(np.vstack(new_col))
        data_matrix = np.hstack(cols_to_hstack)
    return data_matrix

def discretize(data_matrix):
    bins = [0,1,10,100]
    vals = [None,1,2,3]

    #for l in bins[:-1]:
        #for u in bins[1:]:
            #f_m = (data_matrix > l) * (data_matrix <= u)
            #data_matrix[f_m]

    for lower, upper, val in zip(bins[:-1],bins[1:], vals[:-1]):
        data_matrix[ (data_matrix >= lower) * (data_matrix < upper) ] = val

    data_matrix[data_matrix >= bins[-1]] = vals[-1]

    return data_matrix

def compute_diversity(matrix):
    """ our measure of how well something is understood """
    # FIXME we clearly need to control for how 'generic' the term is, eg 'brain' could easily be the best understood
    # this is not what we want, the most frequently used across fields is not very useful since it may mean that we
    # well, no, that is wrong because we DO understand the brain pretty damned well at the level of pointing to it as
    # an organ, that is a VERY different metric from how well we understand all of its parts (which is another metric)
    total_data_sources = float(matrix.shape[1])  # yay py2 >_<
    sources_per_term = np.sum(matrix > 0, axis=1) / total_data_sources
    print(sources_per_term)
    return sources_per_term

def display_grid(mats, rns, titles, col_names, figname, hspace=0):
    aspect = .3
    ratio = float(mats[0].shape[1] + 1) / float(sum([m.shape[0] for m in mats]) + 1)  # cols / rows
    gcols = 2
    grows = len(mats)

    base = 22
    dpi = 600
    width_ratios = 98,2
    size = (base, base / ratio * aspect)  #FIXME >_<
    term_fsize = 2

    fig = plt.figure(figsize=size, dpi=dpi)
    gs = plt.matplotlib.gridspec.GridSpec(grows, gcols, hspace=hspace, wspace=0, height_ratios = [m.shape[0] for m in mats], width_ratios=width_ratios)
    axes = []
    for r in range(grows):
        matrix = mats[r]
        row_names = rns[r]
        if axes:
            ax1 = fig.add_subplot(gs[r,0], sharex=axes[0][0])
        else:
            ax1 = fig.add_subplot(gs[r,0])
        ax2 = fig.add_subplot(gs[r,1], sharey=ax1)

     
        #axis 1
        img = ax1.imshow(matrix, interpolation='nearest', cmap=plt.cm.get_cmap('Greens'), aspect='auto', vmin=0, vmax=3)

        #axes
        ax1.xaxis.set_ticks([i for i in range(len(col_names))])
        ax1.xaxis.set_ticklabels(col_names)
        ax1.xaxis.set_ticks_position('top')
        [l.set_rotation(90) for l in ax1.xaxis.get_majorticklabels()]  #alternate is to use plt.setp but why do that?
        [l.set_fontsize(int(base * .25)) for l in ax1.xaxis.get_ticklabels()]
        if axes:
            #plt.setp(ax1.get_xticklabels(), visible=False)
            ax1.xaxis.set_tick_params(label1On=False,label2On=False)
        print('axis label', titles[r])
        ax1.xaxis.set_label_text(titles[r])
        ax1.xaxis.set_label_position('bottom')
        #if titles[r]:
            #embed()

        ax1.yaxis.set_ticks([i for i in range(len(row_names))])
        ax1.yaxis.set_ticklabels(row_names)
        ax1.yaxis.set_ticks_position('left')
        [l.set_fontsize(term_fsize) for l in ax1.yaxis.get_ticklabels()]

        ax1.tick_params(direction='in', length=0, width=0)

        #axis 2
        div = compute_diversity(matrix)  # FIXME this is called twice :/
        ll, ul = ax1.get_ylim()
        width = (ul - ll) / matrix.shape[0]
        other = np.arange(ll, ul, width)[::-1]  # for whatever reason backwards, probably imshow idiocy
        ax2.barh(other, div, width, edgecolor='None')  #FIXME for some reason horizonal breaks things?
        ax2.yaxis.set_ticks_position('right')
        [l.set_fontsize(term_fsize) for l in ax2.yaxis.get_ticklabels()]
        ax2.set_xlim(0,1)
        ax2.tick_params(direction='in', length=0, width=0)
        ax2.xaxis.set_ticks([0,.5,1])
        ax2.xaxis.set_ticklabels(['0','.5','1'])
        [l.set_fontsize(int(base * .25)) for l in ax2.xaxis.get_ticklabels()]

        axes.append((ax1, ax2))

    title = figname 
    fig.savefig('/tmp/%s.png'%title, bbox_inches='tight', pad_inches=.1, dpi=dpi)



def display_heatmap(matrix, row_names, col_names, title):
    #blanks = np.zeros_like(matrix[0])
    #matrix = np.vstack((blanks, matrix, blanks))
    #row_names = [''] + row_names + ['']
    aspect = .3
    #mm = float(max(matrix.shape)) #python2 a shit
    ratio = float(matrix.shape[1] + 1) / float(matrix.shape[0] + 1)  # cols / rows
    print('ratio', ratio)
    base = 22  #width
    dpi = 600
    width_ratios = 98, 2
    #width_ratios = 100, 0
    #size = (matrix.shape[1] / mm * base * (1/aspect), matrix.shape[0] / mm * base + 1)  #FIXME deal with the font vs figsize :/
    #size = (base + sum(width_ratios)/width_ratios[0], base / ratio * aspect)  #FIXME >_<
    size = (base, base / ratio * aspect)  #FIXME >_<
    print(size)
    term_fsize = 2
    #fig, (ax1, ax2) = plt.subplots(1, 2, figsize=size, dpi=dpi, sharey=True, gridspec_kw=gskw)  # FIXME for some reason using gridspec breaks imshow and tight_layout a;dslkfja;dslkjf
    fig = plt.figure(figsize=size, dpi=dpi)
    gs = plt.matplotlib.gridspec.GridSpec(1, 2, wspace=0, width_ratios=width_ratios)
    ax1 = fig.add_subplot(gs[0])
    ax2 = fig.add_subplot(gs[1], sharey=ax1)
                      

    #axis 1
    img = ax1.imshow(matrix, interpolation='nearest', cmap=plt.cm.get_cmap('Greens'), aspect='auto',vmin=0,vmax=3)#, aspect=aspect, extent=(0,matrix.shape[1]+1,0,matrix.shape[0]+1))#, vmin=0, vmax=np.max(matrix))  #FIXME x axis spacing :/  #FIXME consider pcolormesh?

    #axes
    ax1.xaxis.set_ticks([i for i in range(len(col_names))])
    ax1.xaxis.set_ticklabels(col_names)
    ax1.xaxis.set_ticks_position('top')
    [l.set_rotation(90) for l in ax1.xaxis.get_majorticklabels()]  #alternate is to use plt.setp but why do that?
    [l.set_fontsize(int(base * .25)) for l in ax1.xaxis.get_ticklabels()]

    ax1.yaxis.set_ticks([i for i in range(len(row_names))])
    ax1.yaxis.set_ticklabels(row_names)
    ax1.yaxis.set_ticks_position('left')
    #[l.set_fontsize(int(base / ratio * aspect * .75)+1) for l in ax1.yaxis.get_ticklabels()]
    [l.set_fontsize(term_fsize) for l in ax1.yaxis.get_ticklabels()]
    #ax1.set_xlim(-4,matrix.shape[1]*(10/3)+4)
    #ax1.set_xlim(-10,matrix.shape[1]+10)

    ax1.tick_params(direction='in', length=0, width=0)

    #axis 2
    div = compute_diversity(matrix)  # FIXME this is called twice :/
    #width = 1
    #other = [i - .5 for i in range(len(div))]  # FIXME ICK
    ll, ul = ax1.get_ylim()
    width = (ul - ll) / matrix.shape[0]
    #other = np.arange(ll, ul, width)
    other = np.arange(ll, ul, width)[::-1]  # for whatever reason backwards, probably imshow idiocy
    #other = np.linspace(ul, ll, len(div))  #using imshow makes everything backward :/
    #try:
        #width = other[1] - other[0]
    #except IndexError:
        #other = ll
        #width = ul - ll
                        
    #ax2.plot(div, other)
    print(other, div)
    #ax2 = plt.subplot(122, sharey=ax1)
    ax2.barh(other, div, width, edgecolor='None')  #FIXME for some reason horizonal breaks things?
    #ax2.yaxis.set_ticks([i for i in range(len(row_names))])
    #ax2.yaxis.set_ticklabels(row_names)
    ax2.yaxis.set_ticks_position('right')
    #[l.set_fontsize(int(base / ratio * aspect * .75)+1) for l in ax2.yaxis.get_ticklabels()]
    [l.set_fontsize(term_fsize) for l in ax2.yaxis.get_ticklabels()]
    ax2.set_xlim(0,1)
    ax2.tick_params(direction='in', length=0, width=0)
    ax2.xaxis.set_ticks([0,.5,1])
    ax2.xaxis.set_ticklabels(['0','.5','1'])
    [l.set_fontsize(int(base * .25)) for l in ax2.xaxis.get_ticklabels()]
    #ax2.xaxis.set_label('Div score.')  # XXX
    #ax2.set_sharey(ax1)

    fig.suptitle(title, x=.5, y=0, fontsize=base*.25, verticalalignment='bottom')  # FIXME stupidly broken >_<
    #ax1.xaxis.set_label(title) #XXX

    fig.savefig('/tmp/%s.png'%title, bbox_inches='tight', pad_inches=.1, dpi=dpi)
    #fig.show()
    return fig

def run_levels(term, level, relationship, child_relationship, term_id=None):
    level_dict = {}
    while level >= 0:
        data, idn_dict = get_term_count_data(term, level, relationship, child_relationship, exclude_parents=True, term_id=term_id)
        if idn_dict:
            level_dict[level] = data, idn_dict

        level -= 1

    return level_dict

def display_div(div, names, levels, term, nterms=300):
    if nterms == None:
        nterms = len(div)
    order = np.argsort(div)
    div = np.array(div)[order][-nterms:]
    row_names = np.array(names)[order][-nterms:]
    levels = np.array(levels)[order][-nterms:]
    colors = {
        0:'b',
        1:'g',
        2:'r',
        3:'c',
        4:'y',
        5:'m',
        6:'gray',
    }

    #ll, ul = ax1.get_ylim()
    #width = (ul - ll) / matrix.shape[0]
    #other = np.arange(ll, ul, width)[::-1]  # for whatever reason backwards, probably imshow idiocy
    base = 5  #width
    height = nterms // 10 + 2
    dpi = 600
    #fakefig = plt.figure()
    fig = plt.figure(figsize=(5,height),dpi=dpi)
    ax2 = fig.add_subplot(111)
    #fig, ax2 = plt.subplots(figsize=(5,20),dpi=dpi)
    width = 1
    term_fsize = 9.5
    other = np.arange(len(div)) - .5
    hands = []
    labs = []
    for l, c in colors.items():
        subset = levels == l
        if subset.any():
            lab = 'lvl %s, n = %s'%(l,len(div[subset]))
            h = ax2.barh(other[subset], div[subset], width, color=c, edgecolor='None', label=lab)  #FIXME for some reason horizonal breaks things?
            hands.append(h)
            labs.append(lab)

    ax2.yaxis.set_ticks_position('right')
    [l.set_fontsize(term_fsize) for l in ax2.yaxis.get_ticklabels()]
    ax2.set_xlim(0,1)
    ax2.tick_params(direction='in', length=0, width=0)
    ax2.xaxis.set_ticks([0,.5,1])
    ax2.xaxis.set_ticklabels(['0','.5','1'])
    #ax2.xaxis.set_ticks_position('top')
    #[l.set_fontsize(int(base * .25)) for l in ax2.xaxis.get_ticklabels()]
    [l.set_fontsize(10) for l in ax2.xaxis.get_ticklabels()]
    
    ax2.yaxis.set_ticks([i for i in range(len(row_names))])
    ax2.yaxis.set_ticklabels(row_names)
    ax2.yaxis.set_ticks_position('left')
    ax2.set_ylim(-.5, len(div)-.5)
    [l.set_fontsize(term_fsize) for l in ax2.yaxis.get_ticklabels()]
    ax2.legend(loc='lower right',fontsize='small', frameon=False, borderpad=None)
    #fig.legend(hands, labs, loc=4)
    #plt.legend()
    fig.tight_layout()

    plt.title(term.capitalize()+' frequencies. Top %s terms.'%nterms,loc='right')

    fig.savefig('/tmp/%s_div.png'%term, bbox_inches='tight', pad_inches=.1, dpi=dpi)


###
#   Acqusition
###

class BaseDatagetter:
    """
        Datagetter classes should implement all the methods needed to do 3 things
        1) retrieve the raw data and put it in structured form
        2) sort the raw data
        3) collapse the raw data
        This class will actually RETRIEVE the data and save it so that it can be opperated on later 
        Often we will actually BUILD the collapse map or sort using only the raw data and thus
        we will not need the functionality provided here.
        NOTE: This class shall deal with REMOTE resources that CHANGE
        NOTE: This class is what we will use to map DIVERSELY formatted data
        into our common internal format, so make it good.
        NOTE: one problem to consider is that this is going to assume that the "datum" indexed
        is a scalar, but surely we can do better and make it work as long as the datatype is consistent
        across all indecies (eg a bitmap, or a time series, or anything set of things that all produce valid
        output from an arbitrary function f or set of functions)

        NOTE: if you don't need an index and are just going to use 0...n then you probably can just use dg.get()
    """
    def __init__(self):
        self.indicies = []
        self.get()

    def get_indecies(self):
        """ n should be number of the index. If not given auto? grrrr
            or rather, this method should get ALL the indexes
            This could read in from a text file or from the internet.
            We reccomend defining the different functions as class methods
            and then calling them from here.
        """
        raise NotImplemented
        # RULE the objects returned by the function that queries index_one
        # should themselves contain denormalized references named by objects in index_two
        index = ['hello','i','am','a','valid','index']  # TODO uniqueness??
        self.indicies.append(index)

    def get_collapse_map(self):
        """ If you are going to sum the quantitative values across fields and there
            is an external source for mapping those fields
        """
        raise NotImplemented

    def get_sort_map(self):
        raise NotImplemented
        
    def get(self):
        """ Replace this method to define how to retrieve the data"""
        raise NotImplemented

    def _make_metadata(self):
        """ Store standard metadata such as date and time """
        pass

    def store(self):
        """ Store the retrieved results somehwere for now, we pickle
            Consider also sqlite or postgress
        """
        raise NotImplemented

class XMLDatagetter(BaseDatagetter):
    def __init__(self, timeout=8):
        self.timeout = timeout 
    def get_xml(self, url):
        try:
            self.resp = requests.get(url, timeout=self.timeout)  # sometimes we need a longer timeout :/  FIXME :/ stateful?
        except requests.exceptions.Timeout:
            #TODO
            pass
        try:
            self.xmlDoc = libxml2.parseDoc(resp.text)
        except libxml2.parserError:  # derp 
            #TODO
            pass

    def run_xpath(self, query):
        self

class NIFSummary(BaseDatagetter):
    def __init__(self):
        pass
    def get(self):  #XXX I HAVE NO IDEA WHAT
        pass

def disp_levels(level_dict, resource_ids, resource_names):  # TODO consider idn dict here?
    term = list(level_dict[0][1].values())[0]   # FIXME mmmm magic numbers
    for level, (data, idn_dict) in level_dict.items():
        row_ids = list(data.keys())
        collapse_map, unames = make_collapse_map(resource_ids, resource_names)
        matrix = construct_columns(data, row_ids, resource_ids, collapse_map)
        div = compute_diversity(matrix)
        order = np.argsort(div)#[::-1]  # start high # nope, trees better
        discre = discretize(matrix[order])
        row_names = []
        for i in order:
        #for rid in row_ids:
            rid = row_ids[i]
            name = idn_dict[rid]
            row_names.append(name)

        #out = compute_diversity(matrix)
        #display_heatmap(discre, row_names, resource_names, '%s level %s'%(term, level))
        display_heatmap(discre, row_names, unames, '%s level %s'%(term, level))

def acquire_data(save_loc='/tmp/'):
    terms = 'hindbrain', 'midbrain', 'forebrain'
    term_ids = 'birnlex_942', None, None
    for term, term_id in zip(terms, term_ids):
        levels = run_levels(term, 7, 'has_proper_part', 'subject', term_id=term_id)  # TODO need to fix level 1 of this w/ the parts of the superior coliculus >_<
        with open(save_loc+term+'.pickle','wb') as f:
            pickle.dump(levels, f)

def acquire_nt_data(save_loc='/tmp/'):
    terms = 'neurotransmitter',
    term_ids = None, 
    for term, term_id in zip(terms, term_ids):
        levels = run_levels(term, 0, 'subClassOf', 'object', term_id=term_id)  # TODO need to fix level 1 of this w/ the parts of the superior coliculus >_<
        with open(save_loc+term+'.pickle','wb') as f:
            pickle.dump(levels, f)
    return levels

def acquire_doa_data(save_loc='/tmp/'):
    terms = 'drug of abuse',
    term_ids = None, 
    for term, term_id in zip(terms, term_ids):
        levels = run_levels(term, 2, 'subClassOf', 'object', term_id=term_id)  # TODO need to fix level 1 of this w/ the parts of the superior coliculus >_<
        with open(save_loc+term+'.pickle','wb') as f:
            pickle.dump(levels, f)
    return levels

def acquire_dis_data(save_loc='/tmp/'):
    terms = 'nervous system disease',
    term_ids = None, 
    for term, term_id in zip(terms, term_ids):
        levels = run_levels(term, 5, 'subClassOf', 'object', term_id=term_id)  # TODO need to fix level 1 of this w/ the parts of the superior coliculus >_<
        with open(save_loc+term+'.pickle','wb') as f:
            pickle.dump(levels, f)
    return levels

def acquire_type_data(save_loc='/tmp/'):
    terms = 'neuron',
    term_ids = None, 
    for term, term_id in zip(terms, term_ids):
        levels = run_levels(term, 5, 'subClassOf', 'object', term_id=term_id)  # TODO need to fix level 1 of this w/ the parts of the superior coliculus >_<
        with open(save_loc+term+'.pickle','wb') as f:
            pickle.dump(levels, f)
    return levels

def get_term_file_counts(term_file, name, save_loc='/tmp/'):
    """ given a list of terms return the counts for each """
    with open(term_file) as f:
        lines = f.readlines()
    terms = [line.rstrip('\n').rstrip('\r') for line in lines]

    datas = {}
    idns = {}
    for term in terms:
        print(term)
        data, idn_dict = get_term_count_data(term, 0, 'subClassOf', 'subject', exclude_parents=True)  # FIXME if level == 0 IGNORE ALL THE THINGS
        datas.update(data)
        idns.update(idn_dict)

    level_dict = {0:(datas, idns)}


    with open(save_loc+name+'.pickle','wb') as f:
        pickle.dump(level_dict, f)

    return level_dict


def graph_data(paths):
    """ given a requisitely formatted dict in a pickle graph it """
    nifids, nif_names = get_source_entity_nifids()
    #terms = 'hindbrain', 'midbrain', 'forebrain', 'neurotransmitter', 'drug of abuse', 'species'
    #terms = 'neurotransmitter', 
    #terms = 'drug of abuse',
    #terms = 'species', #'neurotransmitter', 'drug of abuse'
    #terms = 'nervous system disease',
    #terms = 'auditory',
    #for term in terms:
    for path in paths:
        #with open(load_loc+term+'.pickle','rb') as f:
        with open(path,'rb') as f:
            levels = pickle.load(f)
        disp_levels(levels, nifids, nif_names)

def graph_partonomy(paths, titles=None, flatten=False, figname='test'):
    resource_ids, resource_names = get_source_entity_nifids()
    mats = []
    rns = []
    #for term in terms:
    for path in paths:
        #with open(load_loc+term+'.pickle','rb') as f:
        with open(path,'rb') as f:
            level_dict = pickle.load(f)
        term = list(level_dict[0][1].values())[0]   # FIXME mmmm magic numbers

        if flatten:
            if len(level_dict.keys()) > 1:  # 0 -> already flat
                flat = {0:({},{})}
                for level, (data, idn_dict) in level_dict.items():
                    flat[0][0].update(data)
                    flat[0][1].update(idn_dict)
                level_dict = flat
            levels = [0]
        else:
            levels = list(level_dict.keys())
            levels.sort()  #gurantee order

        comp_div = []
        comp_names = []
        comp_levels = []
        for level in levels:
            data, idn_dict = level_dict[level]
            row_ids = list(data.keys())
            collapse_map, unames = make_collapse_map(resource_ids, resource_names)
            matrix = construct_columns(data, row_ids, resource_ids, collapse_map)
            div = compute_diversity(matrix)
            order = np.argsort(div)#[::-1]  # start high #NOPE trees better than ice
            discre = discretize(matrix[order])
            row_names = []
            for i in order:
            #for rid in row_ids:
                rid = row_ids[i]
                name = idn_dict[rid]
                row_names.append(name)
            mats.append(discre)
            rns.append(row_names)

            comp_div.extend(div)
            comp_names.extend([idn_dict[rid] for rid in row_ids])
            comp_levels.extend([level] * len(div))


        display_div(comp_div, comp_names, comp_levels, term)
    if titles == None:
        #titles = [None]*(len(mats) - 1) + ['Brain partonomy']
        #titles = [None]*(len(mats) - 1) + ['Diseases']
        #titles = [None]*(len(mats) - 1) + ['Neuron types']
        titles = [None]*len(mats)
        hspace = 0
    else:
        hspace = .1
    #embed()
    #display_grid(mats, rns, titles, unames, figname, hspace=hspace)

def make_legend():
    fig = figure()
    ax1 = fig.add_subplot()
    ax2 = fig.add_subplot()
    matrix = [None, 1, 2, 3]
    img = ax1.imshow(matrix, interpolation='nearest', cmap=plt.cm.get_cmap('Greens'), aspect='auto', vmin=0, vmax=3)
    ax1.barh(0,1,.5,'')

def main():
    if args['--term_file']:
        path = args['--term_file']
        dirname = os.path.dirname(path)
        filename = os.path.basename(path)
        out = get_term_file_counts(args['--term_file'], filename, dirname)
        embed()
    if args['--pickle_file']:
        path = args['--pickle_file']
        graph_partonomy((path,))
        graph_data((path,))


    #run_auditory_terms()
    #aud_terms = 'auditory',
    #graph_partonomy(terms=aud_terms, figname='Auditory Terms')

    #graph_data() # FIXME

    #acquire_data()
    #out = acquire_nt_data()
    #out = get_term_file_counts('/tmp/neurotransmitters','neurotransmitter')   # FIXME NOTE: one thing to consider is how to deal to references to certain molecules which are NOT about its context as a neurotransmitter... THAT could be tricky
    #out= acquire_doa_data()
    #embed()

    #out = get_term_file_counts('/tmp/blast_names','species')  #TODO clean up names

    #out = acquire_dis_data()
    #graph_data()

    #out = acquire_type_data()


    #"""
    #neu_terms = 'neuron',
    #graph_partonomy(terms=neu_terms, figname='Neuron Types')

    #dis_terms = 'nervous system disease',
    #graph_partonomy(terms=dis_terms, figname='diseases')

    #brain_terms = 'hindbrain', 'midbrain', 'forebrain',
    #graph_partonomy(terms=brain_terms, figname='partonomy')

    #other_terms = 'species', #'neurotransmitter', 'drug of abuse'
    #other_titles = 'Species', #'Neurotransmitters', 'Drugs of abuse'
    #graph_partonomy(terms=other_terms,flatten=True,titles=other_titles, figname='others')  # species 227
    #"""


if __name__ == "__main__":
    main()
