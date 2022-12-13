import os
import sys
import json
import tiledb as td
import pandas as pd

# tiledb = td.open(sys.argv[1], 'r')
# phenos_in_db = [p.decode("utf-8") for p in tiledb.nonempty_domain()[1]]
phenos_in_db = [os.path.splitext(os.path.basename(line.strip()))[
                                 0] for line in open(sys.argv[1], 'r').readlines()]
pheno_dict = {p['NAME']: p for p in pd.read_csv(
    sys.argv[2], sep='\t').to_dict(orient='records')}
phenolist = [{'code': p, 'name': pheno_dict[p]['LONGNAME']}
             for p in phenos_in_db if p in pheno_dict]
json.dump(phenolist, open('data/analyzed_phenos.json', 'w'))
