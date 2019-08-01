import sys
import logging

import synbiohub_adapter as sbha
import sbh_explorer as sbhe

"""Find all the strains contained in all the members of the yeast
gates challenge problem.
"""

# Enter the sd2e SynBioHub password
SBH_USER = 'sd2e'
SBH_PASSWORD = 'INSERT_PASSWORD'

# Authenticate to SynBioHub
sbh_query = sbha.SynBioHubQuery(sbha.SD2Constants.SD2_SERVER)
sbh_query.login(SBH_USER, SBH_PASSWORD)

# First get all the members of the yeast gates challenge problem
yg_members = sbhe.objects_for(sbh_query,
                              sbha.SD2Constants.YEAST_GATES_DESIGN_COLLECTION,
                              sbhe.SBOL_MEMBER)
print('Found {} yeast gate challenge problem members'.format(len(yg_members)))

# Iterate through the members, finding contained strains
all_strains = []
print('Looking for strains...', end='', flush=True)
yg_count = 0
for yg in yg_members:
    # print(yg)
    strains = sbhe.find_contained_strains(sbh_query, yg)
    all_strains.extend(strains)
    yg_count += 1
    if yg_count % 10 == 0:
        print('.', end='', flush=True)
print()
print('Found {} strains'.format(len(all_strains)))

# I don't know if strains can be used in more than one, but in case
# they can, let's use a set to remove duplicates.
unique_strains = set(all_strains)
print('Found {} unique strains'.format(len(unique_strains)))

# Print out all the unique strains we found
print('Strains:')
for strain in sorted(unique_strains):
    print('\t', strain)
