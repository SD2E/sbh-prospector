import argparse
import functools
import logging
import os
import sys

import pandas as pd

import synbiohub_adapter as sbha

SUBJECT_QUERY = """
    SELECT ?s WHERE {{
        VALUES (?p ?o) {{ ( <{}> <{}> ) }}
        ?s ?p ?o .
    }}
"""

SUBJECT_INFO_QUERY = """
    SELECT ?p ?o WHERE {{
        VALUES (?s) {{ ( <{}> ) }}
        ?s ?p ?o .
    }}
"""

SPO_QUERY = """
    SELECT ?s ?p ?o WHERE {{
        VALUES (?s ?p ?o) {{ ( <{}> <{}> <{}> ) }}
        ?s ?p ?o .
    }}
"""

O_QUERY = """
    SELECT ?o WHERE {{
        VALUES (?s ?p) {{ ( <{}> <{}> ) }}
        ?s ?p ?o .
    }}
"""

SO_QUERY = """
    SELECT ?s ?o WHERE {{
        VALUES (?p) {{ ( <{}> ) }}
        ?s ?p ?o .
    }}
"""

SP_QUERY = """
    SELECT ?s ?p WHERE {{
        VALUES (?o) {{ ( <{}> ) }}
        ?s ?p ?o .
    }}
"""

SBOL_ROOT = 'http://sbols.org/v2'
SBOL_TYPE_COMPONENT = SBOL_ROOT + '#Component'
SBOL_PRED_COMPONENT = SBOL_ROOT + '#component'
SBOL_DEFINITION = SBOL_ROOT + '#definition'
SBOL_MEMBER = SBOL_ROOT + '#member'
SBOL_FUNCTIONAL_COMPONENT = SBOL_ROOT + '#functionalComponent'
SBOL_MODULE = SBOL_ROOT + '#module'
SBOL_BUILT = SBOL_ROOT + '#built'
SBOL_ROLE = SBOL_ROOT + '#role'
SBOL_TYPE = SBOL_ROOT + '#type'

# CHEBI prefixes are used to identify reagents
CHEBI_PURL_PREFIX = 'http://purl.obolibrary.org/obo/CHEBI'
CHEBI_IDENTIFIERS_PREFIX = 'http://identifiers.org/chebi/CHEBI'

CHALLENGE_PROBLEMS = [
    sbha.SD2Constants.RULE_30_DESIGN_COLLECTION,
    sbha.SD2Constants.YEAST_GATES_DESIGN_COLLECTION,
    sbha.SD2Constants.RIBOSWITCHES_DESIGN_COLLECTION,
    sbha.SD2Constants.NOVEL_CHASSIS_DESIGN_COLLECTION
]

DC_TERMS_TITLE = 'http://purl.org/dc/terms/title'
RDF_TYPE = 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type'

# SD2-specific values
SD2E_STUB = 'http://sd2e.org#stub_object'


def subjects_for(sbh_query, pred, obj):
    sparql = SUBJECT_QUERY.format(pred, obj)
    logging.debug('Query is %s', sparql)
    result = sbh_query.fetch_SPARQL(None, sparql)
    result = sbh_query.format_query_result(result, ['s'])
    return result


def subject_info(sbh_query, subj):
    sparql = SUBJECT_INFO_QUERY.format(subj)
    logging.debug('Query is %s', sparql)
    result = sbh_query.fetch_SPARQL(None, sparql)
    # result = sbh_query.format_query_result(result, [])
    result = [(r['p'], r['o']) for r in sbh_query.format_query_result(result, ['p', 'o'])]
    return result


def o_query(sbh_query, subj, pred):
    sparql = O_QUERY.format(subj, pred)
    logging.debug('Query is %s', sparql)
    result = sbh_query.fetch_SPARQL(None, sparql)
    result = format_query_result(sbh_query, result)
    return result


# A wrapper with a better function name than "o_query"
def objects_for(sbh_query, subj, pred):
    return o_query(sbh_query, subj, pred)


def sp_query(sbh_query, obj):
    sparql = SP_QUERY.format(obj)
    logging.debug('Query is %s', sparql)
    result = sbh_query.fetch_SPARQL(None, sparql)
    result = format_query_result(sbh_query, result)
    return result


def so_query(sbh_query, pred):
    sparql = SO_QUERY.format(pred)
    logging.debug('Query is %s', sparql)
    result = sbh_query.fetch_SPARQL(None, sparql)
    result = format_query_result(sbh_query, result)
    return result


def title_for(sbh_query, subj):
    result = o_query(sbh_query, subj, DC_TERMS_TITLE)
    if result:
        return result[0]
    else:
        return ''


def has_type(sbh_query, subj, rdf_type):
    sparql = SPO_QUERY.format(subj, RDF_TYPE, rdf_type)
    logging.info('Querying %s for type %s', subj, rdf_type)
    logging.debug('Query is %s', sparql)
    result = sbh_query.fetch_SPARQL(None, sparql)
    result = [(r['s'], r['o']) for r in format_query_result(sbh_query, result)]
    return result


def find_subjects(sbh_query, results, pred):
    new_results = {}
    for obj in results:
        subjects = subjects_for(sbh_query, pred, obj)
        logging.info('Found %d %s for %s', len(subjects), pred, obj)
        if not subjects:
            # Didn't find anything. What are the possiblities?
            sp_list = sp_query(sbh_query, obj)
            preds = set([sp['p'] for sp in sp_list])
            logging.info('All predicates for %s: %r', obj, preds)
            # sys.exit(0)
        for s in subjects:
            if s in new_results:
                raise Exception('Two paths to {}'.format(s))
            new_results[s] = [(s, pred, obj)] + results[obj]
            # rdf_type = o_query(sbh_query, s, RDF_TYPE)
            # logging.info('%s has type %s', s, rdf_type)
    return new_results


def find_implementations(sbh_query, obj, media=None):
    """Given an object, return all the implementations that link to it by
    a SBOL #built predicate. Also include the dc/terms/title of the
    implementations.

    """
    query_template = """
        SELECT ?s ?title WHERE {{
            VALUES (?built_pred ?o ?title_pred) {{ ( <{}> <{}> <{}> ) }}
            ?s ?built_pred ?o .
            ?s ?title_pred ?title .
    """
    if media is not None:
        media_clause = """
            ?o <http://sbols.org/v2#module> ?mod .
            ?mod <http://sbols.org/v2#definition> <{0}> .
            <{0}> <http://sbols.org/v2#role> <http://purl.obolibrary.org/obo/NCIT_C85504> .
        """
        query_template += media_clause.format(media)
    query_template += "\n}}\n"
    sparql = query_template.format(SBOL_BUILT, obj, DC_TERMS_TITLE)
    logging.debug('Query is %s', sparql)
    result = sbh_query.fetch_SPARQL(None, sparql)
    return format_query_result(sbh_query, result)


def find_construct_experiments(sbh_query, construct, media=None):
    definers = subjects_for(sbh_query, SBOL_DEFINITION, construct)

    results = {}
    for d in definers:
        results[d] = [(d, SBOL_DEFINITION, construct)]

    logging.info('Found %d definers', len(definers))
    # for d in definers:
    #     logging.info('Definer: %s', d)
    #     for p, o in subject_info(sbh_query, d):
    #         logging.info('%s:   %s', p, o)
    #     logging.info('--------------------------------------------------')

    logging.info('Keeping definers of type component')
    definers = [d for d in definers if has_type(sbh_query, d, SBOL_TYPE_COMPONENT)]
    logging.info('%d definers are components', len(definers))
    # for d in definers:
    #     logging.info('component definer: %s', d)

    members = []
    for d in definers:
        new_members = subjects_for(sbh_query, SBOL_PRED_COMPONENT, d)
        for m in new_members:
            results[m] = [(m, SBOL_PRED_COMPONENT, d)] + results[d]
            members.append(m)
    logging.info('Found %d possible members', len(members))
    for m in members:
        logging.info('Possible member: %s', m)

    # We're really looking for implementations via the `built` relationship, not challenge problem.

    new_results = {}
    for m in members:
        design_defs = subjects_for(sbh_query, SBOL_DEFINITION, m)
        for dd in design_defs:
            if dd in new_results:
                raise Exception('Two paths to {}'.format(dd))
            new_results[dd] = [(dd, SBOL_DEFINITION, m)] + results[m]
    results = new_results

    new_results = {}
    for dd in results:
        circuit_designs = subjects_for(sbh_query, SBOL_FUNCTIONAL_COMPONENT, dd)
        logging.info('Found %d circuit designs for %s', len(circuit_designs), m)
        for cd in circuit_designs:
            if cd in new_results:
                raise Exception('Two paths to {}'.format(cd))
            new_results[cd] = [(cd, SBOL_FUNCTIONAL_COMPONENT, dd)] + results[dd]
            rdf_type = o_query(sbh_query, cd, RDF_TYPE)
            logging.info('%s has type %s', cd, rdf_type)
    results = new_results

    results = find_subjects(sbh_query, results, SBOL_DEFINITION)
    results = find_subjects(sbh_query, results, SBOL_MODULE)

    # Now find implementations of the modules found above
    new_results = {}
    df_rows = []
    for obj in results:
        impls = find_implementations(sbh_query, obj, media)
        for impl in impls:
            subj = impl['s']
            new_results[subj] = results[obj] + [(subj, SBOL_BUILT, obj)]
            df_rows.append(dict(uri=subj, title=impl['title']))

    data_frame = pd.DataFrame(df_rows)
    logging.info('Done')
    return data_frame


def find_grna(sbh_query):
    sparql = """
      SELECT ?s ?title WHERE {
        ?s <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <http://sbols.org/v2#ComponentDefinition> .
        ?s <http://purl.org/dc/terms/title> ?title .
      }
    """
    result = sbh_query.fetch_SPARQL(None, sparql)
    result = [(r['s'], r['title']) for r in format_query_result(sbh_query, result)]
    return result


def format_query_result(sbh_query, result, bindings=None):
    if bindings is None:
        bindings = result['head']['vars']
    formatted_result = sbh_query.format_query_result(result, bindings)
    # Could translate to an object here to access via r.gene instead of r['gene']
    return formatted_result


# cache size 256 is an arbitrary choice
@functools.lru_cache(maxsize=256)
def parent_module_definitions(sbh_query, uri):
    """Find all the module definitions that contain this element. This
    function does not recursively find grandparents, etc. It only goes
    one level up via either a module or functionaComponent predicate.
    """
    # First, gather module definitions found via an intervening "Module" node
    modules = subjects_for(sbh_query, SBOL_DEFINITION, uri)
    module_defs = [subjects_for(sbh_query, SBOL_MODULE, m) for m in modules]
    result = set(md for md_list in module_defs for md in md_list)
    # Second, gather module definitions found via an intervening "Functional Component" node
    functional_components = subjects_for(sbh_query, SBOL_DEFINITION, uri)
    module_defs = [subjects_for(sbh_query, SBOL_FUNCTIONAL_COMPONENT, fc) for fc in functional_components]
    result.update(set(md for md_list in module_defs for md in md_list))
    return result


# cache size 256 is an arbitrary choice
@functools.lru_cache(maxsize=256)
def root_module_definitions(sbh_query, uri):
    """Perform a breadth first search up the module definition hierarchy
    looking for module definitions which have no parent module.
    """
    ancestors = list(parent_module_definitions(sbh_query, uri))
    roots = []
    # print(ancestors)
    while ancestors:
        parent = ancestors.pop(0)
        # print('Parent: {}'.format(parent))
        parents = parent_module_definitions(sbh_query, parent)
        # print('Found {} ancestors'.format(len(parents)))
        if not parents:
            roots.append(parent)
        ancestors.extend(parents)
    return roots


# cache size 256 is an arbitrary choice
@functools.lru_cache(maxsize=256)
def child_module_definitions(sbh_query, uri):
    """Find all children that are module definitions
    """
    # Gather module definitions found via an intervening "Module" node
    modules = objects_for(sbh_query, uri, SBOL_MODULE)
    module_defs = [objects_for(sbh_query, m, SBOL_DEFINITION) for m in modules]
    result = set(md for md_list in module_defs for md in md_list)
    return result


# cache size 256 is an arbitrary choice
@functools.lru_cache(maxsize=256)
def child_component_definitions(sbh_query, uri):
    """Find all children that are component definitions.
    """
    # Gather component definitions found via an intervening "FunctionalComponent" node
    # uri --functionalComponent--> FunctionComponent --definition--> ComponentDefinition
    fcs = objects_for(sbh_query, uri, SBOL_FUNCTIONAL_COMPONENT)
    comp_defs = [objects_for(sbh_query, fc, SBOL_DEFINITION) for fc in fcs]
    result = set(cd for cd_list in comp_defs for cd in cd_list)

    # Gather component definitions found via an intervening "component" node
    # uri --component--> Component --definition--> ComponentDefinition
    comps = objects_for(sbh_query, uri, SBOL_PRED_COMPONENT)
    defs = [objects_for(sbh_query, comp, SBOL_DEFINITION) for comp in comps]
    result.update(d for d_list in defs for d in d_list)
    return result


def triple_exists(sbh_query, subj, pred, obj):
    """Determine if the given triple exists. Returns a bool."""
    sparql = SPO_QUERY.format(subj, pred, obj)
    logging.info('Querying for %s %s %s', subj, pred, obj)
    logging.debug('Query is %s', sparql)
    result = sbh_query.fetch_SPARQL(None, sparql)
    result = format_query_result(sbh_query, result)
    return bool(result)


# cache size 256 is an arbitrary choice
@functools.lru_cache(maxsize=256)
def is_strain(sbh_query, module_uri):
    """Determines if the given module contains the given strain."""
    # Just this module, not a recursive search
    # Strains are ModuleDefinitions that have a role ('http://sbols.org/v2#role’)
    # of 'http://purl.obolibrary.org/obo/NCIT_C14419’.
    return triple_exists(sbh_query, module_uri, SBOL_ROLE, 'http://purl.obolibrary.org/obo/NCIT_C14419')

# Backward compatibity
# TODO: remove any callers of module_is_strain
module_is_strain = is_strain

# cache size 256 is an arbitrary choice
@functools.lru_cache(maxsize=256)
def is_reagent(sbh_query, uri):
    types = objects_for(sbh_query, uri, SBOL_TYPE)
    for typ in types:
        if typ.startswith(CHEBI_PURL_PREFIX) or typ.startswith(CHEBI_IDENTIFIERS_PREFIX):
            return True
    return False


# cache size 256 is an arbitrary choice
@functools.lru_cache(maxsize=256)
def is_stub(sbh_query, uri):
    """Determines if the given URI is marked as a stub in SynBioHub.
    Returns True if it is marked as a stub, False otherwise.
    """
    stub_values = sbhe.objects_for(sbh_query, uri, SD2E_STUB)
    # TODO: Is it the very presence of the STUB attribute that denotes
    # a stub? Or does the value somehow denote it? The string 'true'
    # is one example.
    return 'true' in stub_values


# Don't cache here, cache in the next layer out, like `find_contained_reagents`
def find_contained_items(sbh_query, uri, predicate):
    found = []
    uris = [uri]
    while uris:
        item = uris.pop(0)
        if predicate(sbh_query, item):
            found.append(item)
        uris.extend(child_module_definitions(sbh_query, item))
        uris.extend(child_component_definitions(sbh_query, item))
    return found


# Syntactic sugar. Find contained items that match the `is_reagent`
# predicate.
#
# cache size 256 is an arbitrary choice
@functools.lru_cache(maxsize=256)
def find_contained_reagents(sbh_query, uri):
    """Walk down the hierarchy of ModuleDefinitions and
    ComponentDefinitions finding items that match the `is_reagent`
    predicate.

    """
    return find_contained_items(sbh_query, uri, is_reagent)


# This should leverage `find_contained_items` now that it exists.
#
# An optimization could be to have find_contained_items only search
# the module definitions to make the search for strains faster.
#
# cache size 256 is an arbitrary choice
@functools.lru_cache(maxsize=256)
def find_contained_strains(sbh_query, uri):
    strains = []
    modules = [uri]
    while modules:
        module = modules.pop(0)
        # print('Module: {}'.format(module))
        if module_is_strain(sbh_query, module):
            strains.append(module)
        # print('Modules: {}'.format(modules))
        children = child_module_definitions(sbh_query, module)
        # print('children: {}'.format(children))
        # print('Module {} has {} children'.format(module, len(children)))
        modules.extend(children)
    # print('Strains: {}'.format(strains))
    return strains


def parse_args(args):
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--debug', action='store_true',
                        help="(default: %(default)s)")
    parser.add_argument('--staging', action='store_true',
                        help="(default: %(default)s)")
    parser.add_argument('-u', '--user', default='sd2e',
                        help="(default: %(default)s)")
    args = parser.parse_args(args)
    return args


def init_logging(debug=False):
    msgFormat = '%(asctime)s %(levelname)s %(message)s'
    dateFormat = '%m/%d/%Y %H:%M:%S'
    level = logging.INFO
    if debug:
        level = logging.DEBUG
    logging.basicConfig(format=msgFormat, datefmt=dateFormat, level=level)


def main(argv=None):
    args = parse_args(argv)

    # Init logging
    init_logging(args.debug)

    # Get SynBioHub password
    sbh_password = os.getenv('SBH_PASSWORD')
    if sbh_password is None:
        raise Exception('Environment does not contain SBH_PASSWORD')

    if args.staging:
        sbh_query = sbha.SynBioHubQuery(sbha.SD2Constants.SD2_STAGING_SERVER,
                                        spoofed_url=sbha.SD2Constants.SD2_SERVER)
    else:
        sbh_query = sbha.SynBioHubQuery(sbha.SD2Constants.SD2_SERVER)
    logging.info('Authenticating to {}'.format(sbh_query._server))
    sbh_query.login(args.user, sbh_password)
    logging.info('Authentication complete')

    # --------------------------------------------------

    # for s, title in find_grna(sbh_query):
    #     if 'gRNA Gene' in title:
    #         logging.info('%s     %s', s, title)
    # return

    # --------------------------------------------------

    # coll = 'https://hub.sd2e.org/user/sd2e/design/yeast_gates_plasmids/1'
    # coll_members = format_query_result(sbh_query, sbh_query.query_collection_members([coll]))
    # for m in sorted(coll_members):
    #     logging.info('yeast_gates_plasmid: %s', m)

    # --------------------------------------------------

    # Tell me about this thing...

    # subj = 'https://hub.sd2e.org/user/sd2e/design/anno_120009203/1'
    # for p, o in subject_info(sbh_query, subj):
    #     logging.info('%s    %s    %s', subj, p, o)
    # return

    # --------------------------------------------------

    # things = so_query(sbh_query, SBOL_FUNCTIONAL_COMPONENT)
    # for thing in things:
    #     logging.info('%s     ---->     %s', thing['s'], thing['o'])
    # sys.exit(0)

    # definers = subjects_for(sbh_query, SBOL_DEFINITION, 'https://hub.sd2e.org/user/sd2e/design/anno_120009203/1')
    gene = R10_GRNA_GENE
    gene = R3_GRNA_GENE

    data_frame = find_construct_experiments(sbh_query, gene)
    logging.info('Found %d experiments', data_frame.size)

    sys.exit(0)

    for x in results:
        logging.info('%s', x)
        title = title_for(sbh_query, x)
        logging.info('\ttitle: %s', title)
        # for triple in results[x]:
        #     logging.info('\t%r', triple)
        logging.info('--------------------------------------------------')

    sys.exit(0)

    cp_members = {}
    for cp in CHALLENGE_PROBLEMS:
        cp_members[cp] = format_query_result(sbh_query, sbh_query.query_collection_members([cp]))

    for cp in cp_members:
        actual_members = set(members).intersection(set(cp_members[cp]))
        for m in actual_members:
            logging.info('Component of %s (%s)', m, cp)
            titles = title_for(sbh_query, m)
            for title in titles:
                logging.info('%s title: %s', m, title)
            logging.info('Chain: %r', [(cp, SBOL_MEMBER, m)] + results[m])


if __name__ == "__main__":
    main()
