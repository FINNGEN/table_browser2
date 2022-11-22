#!/usr/bin/env python3

import tiledb as td
import numpy as np
import logging as lg
import sys
import gzip
import os
import multiprocessing

lg.basicConfig(format='%(levelname)s %(asctime)s - %(message)s',
               datefmt='%Y-%m-%d %H:%M:%S', level=lg.DEBUG)


class ImportException(Exception):
    pass


def get_variant_index(filename, limit=None):
    lg.info('loading variant index from %s', filename)
    vi = {}
    f = gzip.open(filename, 'rt') if filename.endswith(
        '.gz') else open(filename, 'rt')
    h = {h.lower(): i for i, h in enumerate(
        f.readline().strip().split('\t'))}
    i = 0
    for line in f:
        s = line.strip().split('\t')
        vi[s[h['variant']]] = i
        i = i+1
    f.close()
    lg.info('variant index loaded, %d variants', len(vi))
    return vi


def create_array(array_name, data_fields, num_variants, rewrite=False):
    if td.object_type(array_name) == "array":
        if not rewrite:
            lg.info('array already exists: %s', array_name)
            return
        else:
            td.remove(array_name)
            lg.info('removed existing array: %s', array_name)
    lg.info('creating array: %s', array_name)
    dom = td.Domain(td.Dim(name="variant_index", domain=(0, num_variants-1), tile=100, dtype=np.int32),
                    td.Dim(name="pheno", domain=(None, None), tile=None, dtype=np.bytes_))
    schema = td.ArraySchema(domain=dom,
                            sparse=True,
                            attrs=[td.Attr(name=name, dtype=np.float32,
                                           filters=td.FilterList([td.ZstdFilter()])) for name in data_fields])
    td.SparseArray.create(array_name, schema)
    lg.info('array created: %s', array_name)


def shove_stats_to_tiledb(args):
    filename, data_fields, variant_index, pheno, array_name = args
    lg.info('reading summary stats from %s', filename)
    dims = [[], []]
    dats = [[] for foo in data_fields]
    with gzip.open(filename, 'rt') as f:
        h = {h.lower(): i for i, h in enumerate(
            f.readline().strip().split('\t'))}
        for line in f:
            s = line.strip().split('\t')
            v = s[h['#chrom']].replace(
                'X', '23') + ':' + s[h['pos']] + ':' + s[h['ref']] + ':' + s[h['alt']]
            try:
                index = variant_index[v]
            except KeyError:
                raise ImportException(
                    'variant {} in {} is not in given annotation file'.format(v, filename))
            dims[0].append(index)
            dims[1].append(pheno)
            for j, field in enumerate(data_fields):
                dats[j].append(float(s[h[field]]) if field in h and s[h[field]]
                               != 'NA' else np.nan)
    lg.info('read %d variants from %s, shoving to tiledb',
            len(dats[0]), filename)
    with td.SparseArray(array_name, mode='w') as A:
        A[dims[0], dims[1]] = {field: np.array(
            dats[i]) for i, field in enumerate(data_fields)}
    lg.info('shoved %s to tiledb', dims[1][0])


if __name__ == '__main__':
    array_name = sys.argv[1]
    data_fields = sys.argv[3].split(',')
    variant_index = get_variant_index(sys.argv[4])
    create_array(array_name, data_fields, len(variant_index), False)
    pool = multiprocessing.Pool(multiprocessing.cpu_count())
    lg.info('shoving data to tiledb with %d cores',
            multiprocessing.cpu_count())
    sumstats = [line.strip() for line in open(sys.argv[2], 'rt').readlines()]
    phenos = [os.path.splitext(os.path.basename(sumstat))[0]
              for sumstat in sumstats]
    args = [(sumstat, data_fields, variant_index, phenos[i], array_name)
            for i, sumstat in enumerate(sumstats)]
    try:
        pool.map(shove_stats_to_tiledb, args)
    except ImportException as e:
        lg.error(e)
        quit()
    lg.info('sumstats shoved to tiledb, consolidating the array')
    td.consolidate(array_name)
    td.vacuum(array_name)
    lg.info('done')
