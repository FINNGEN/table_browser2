#!/usr/bin/env python3

import json
import pandas as pd
import logging as lg
import os
import sys
import multiprocessing

lg.basicConfig(format='%(levelname)s %(asctime)s - %(message)s',
               datefmt='%Y-%m-%d %H:%M:%S', level=lg.DEBUG)


def merge(args):
    pheno = args[0]
    config = args[1]
    lg.info('processing pheno %s', pheno)
    fname = config['sumstats'][0]['sumstat_loc'] + '/' + pheno + '.gz'
    # the first sumstat type in the config must exist
    if not os.path.isfile(fname):
        lg.warning('sumstat not found, omitting phenotype: %s', fname)
        return
    d = pd.read_csv(fname, sep='\t')
    # add a suffix to column names
    # because column names are the same across different sumstat types
    d.columns = [c + '_' + config['sumstats'][0]['sumstat_type']
                 if c not in config['join_columns'] else c for c in d.columns]
    # join other sumstat types to the first one if they exist
    n_files = 1
    for i in range(1, len(config['sumstats'])):
        fname = config['sumstats'][i]['sumstat_loc'] + '/' + pheno + '.gz'
        if not os.path.isfile(fname):
            continue
        d2 = pd.read_csv(fname, sep='\t')
        d2.columns = [c + '_' + config['sumstats'][i]['sumstat_type']
                      if c not in config['join_columns'] else c for c in d2.columns]
        d = d.merge(d2, how='outer', on=config['join_columns'])
        n_files = n_files + 1
    d.to_csv('merged/' + pheno + '.gz',
             na_rep='NA', index=False, sep='\t')
    lg.info('%d file(s) merged to merged/' + pheno + '.gz', n_files)


if __name__ == '__main__':
    phenos = [line.strip() for line in open(sys.argv[1], 'rt').readlines()]
    config = json.load(open(sys.argv[2], 'rt'))
    os.makedirs('merged', exist_ok=True)
    pool = multiprocessing.Pool(multiprocessing.cpu_count())
    lg.info('merging phenos with %d cores', multiprocessing.cpu_count())
    args = [(pheno, config) for pheno in phenos]
    pool.map(merge, args)
