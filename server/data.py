import threading
import timeit
import json
import tiledb as td
import numpy as np
import pandas as pd
import logging as lg
import gzip
from collections import defaultdict as dd

from exceptions import NotFoundException
from variant import Variant

lg.basicConfig(format='%(levelname)s %(asctime)s - %(message)s',
               datefmt='%Y-%m-%d %H:%M:%S', level=lg.DEBUG)


class Datafetch(object):

    def _init_anno(self):
        lg.info('loading up variant annotations from %s',
                self.conf['variant_annotation'])
        self.gene2region = {}
        self.index2anno = {}
        self.variant2index = {}
        with gzip.open(self.conf['variant_annotation'], 'rt') as f:
            h = {h: i for i, h in enumerate(f.readline().strip().split('\t'))}
            for line in f:
                line = line.strip().split('\t')
                gene = line[h['gene_most_severe']]
                index = int(line[h['#index']])
                if gene not in self.gene2region:
                    self.gene2region[gene] = (float('inf'), float('-inf'))
                self.gene2region[gene] = (min(self.gene2region[gene][0], index), max(
                    self.gene2region[gene][1], index))
                self.index2anno[index] = {k: self._format_value(
                    k, line[h[k]]) for k in h}
                self.variant2index[str(Variant(line[h['variant']]))] = index
        lg.info('annotations read for %d variants',
                len(self.variant2index))
        lg.info('gene-to-region mapping read for %d genes',
                len(self.gene2region))

    def _init_tiledb(self):
        self.tiledb = dd(lambda: td.open(self.conf['gwas_tiledb'], 'r'))

    def _init_phenos(self):
        self.pheno_list = json.load(open(self.conf['phenos'], 'rt'))
        self.pheno_dict = {pheno['code']: pheno for pheno in self.pheno_list}
        # TODO would be nice to require that phenos in phenolist are in db
        # and log out phenos that are in db but not in phenolist
        # but unique_dim_values errors out
        # https://github.com/TileDB-Inc/TileDB-Py/issues/441
        # phenos_in_db = [p.decode("utf-8")
        #                 for p in self.tiledb[threading.get_ident()].unique_dim_values('pheno')]
        # # log out phenos that are in db but not in phenolist
        # for p in phenos_in_db:
        #     if p not in self.pheno_dict:
        #         lg.info('phenotype %s is in the database %s and not in the phenotype list %s - this phenotype will not be shown',
        #                 p, self.conf['gwas_tiledb'], self.conf['phenos'])
        #         continue
        # # error out on phenos that are in phenolist but not in db
        # n_phenos_not_in_db = 0
        # for p in self.pheno_dict:
        #     if p not in phenos_in_db:
        #         continue
        #         lg.error('''phenotype %s is in the phenotype list %s and not
        #         in the database %s - please remove it from the phenotype list
        #         or add it to the database''',
        #                  p, self.conf['phenos'], self.conf['gwas_tiledb'])
        #         n_phenos_not_in_db = n_phenos_not_in_db + 1
        # if n_phenos_not_in_db > 0:
        #     raise(DataException(
        #         'data for phenotype(s) in the phenotype list does not exist in the database'))

    def _init_top_results(self):
        lg.info('loading up top results from %s',
                self.conf['top_table'])
        top_list = pd.read_csv(self.conf['top_table'], sep='\t')[
            ['pheno',
             'variant',
             'mlogp_add',
             'mlogp_rec',
             'mlogp_chip',
             'beta_add',
             'beta_rec',
             'beta_chip',
             'possible_explaining_signals']
             ].fillna('NA').to_dict(orient='records')
        indices = {}
        for res in top_list:
            indices[self.variant2index[res['variant']]] = True
            for key in res:
                if key == 'pheno':
                    if res[key] not in self.pheno_dict:
                        lg.info(
                            '%s is in top table but not in phenolist, using pheno code as pheno name')
                        res[key] = {'code': res[key], 'name': res[key]}
                    else:
                        res[key] = self.pheno_dict[res[key]]
                elif res[key] == 'NA':
                    res[key] = None
                elif key.startswith('mlogp_') or key.startswith('beta_'):
                    if np.isnan(res[key]):
                        res[key] = None
                    else:
                        res[key] = float(res[key])
        self._set_top_flags(top_list)
        anno = {self.index2anno[i]['variant']: self.index2anno[i] for i in indices}
        self.top_results = {
            'results': top_list,
            'anno': anno
        }
        lg.info('loaded top results for %d variants', len(top_list))

    def __init__(self, conf):
        self.conf = conf
        self._init_anno()
        self._init_tiledb()
        self._init_phenos()
        self._init_top_results()

    def _format_value(self, name, value):
        name = name.lower()
        if value is None or value == 'NA':
            return 'NA'
        if name == 'variant':
            return str(Variant(value))
        if name.startswith('time'):
            return round(float(value), 4)
        elif name.startswith('ac') or name.startswith('an') or name.startswith('pos'):
            return int(float(value))
        elif name.startswith('beta') or name.startswith('sebeta'):
            return round(float(value), 3)
        # use 4 instead of 3 decimals for mlogp so that
        # the actual p-value can be shown accurately to 2 significant digits
        elif name.startswith('mlogp') or name.startswith('info'):
            return round(float(value), 4)
        # 7 is fine for AF so can still represent today's GWAS scale data
        # with 2 digits scientific
        elif name.startswith('af'):
            return round(float(value), 7)
        return value

    def get_variant_range(self, variant: Variant):
        try:
            index = self.variant2index[str(variant)]
            return (index, index)
        except KeyError:
            raise NotFoundException('variant not found')

    def get_gene_range(self, gene: str):
        try:
            return self.gene2region[gene.upper()]
        except KeyError:
            raise NotFoundException('gene not found')

    def _set_top_flags(self, results):
        # figure out top variant for each pheno
        # and top pheno for each variant
        pheno2top = dd(lambda: ('variant', 0))
        var2top = dd(lambda: ('pheno', 0))
        for res in results:
            code = res['pheno']['code']
            variant = res['variant']
            p_add = res['mlogp_add']
            p_chip = res['mlogp_chip']
            if p_add is not None and p_add > pheno2top[code][1]:
                pheno2top[code] = (variant, p_add)
            if p_chip is not None and p_chip > pheno2top[code][1]:
                pheno2top[code] = (variant, p_chip)
            if p_add is not None and p_add > var2top[variant][1]:
                var2top[variant] = (code, p_add)
            if p_chip is not None and p_chip > var2top[variant][1]:
                var2top[variant] = (code, p_chip)
        for res in results:
            if res['variant'] == pheno2top[res['pheno']['code']][0]:
                res['is_top_variant'] = True
            if res['pheno']['code'] == var2top[res['variant']][0]:
                res['is_top_pheno'] = True

    # TODO this is slow
    # should we do the dict-to-list conversion client side or speed it up here
    def get_results(self, index_range: tuple, gene=None):
        start_time = timeit.default_timer()
        results = self.tiledb[threading.get_ident(
        )][index_range[0]:index_range[1]+1]
        time_db = timeit.default_timer() - start_time
        # convert results from {a: [1,2], b: [3,4]} to [{a: 1, b: 3}, {a: 2, b: 4}]
        start_time = timeit.default_timer()
        results_munged = []
        indices = {}
        for i in range(len(results['variant_index'])):
            res = {}
            keep = True
            for key in results:
                if key == 'pheno':
                    pheno_str = results[key][i].decode("utf-8")
                    if pheno_str in self.pheno_dict:
                        val = self.pheno_dict[pheno_str]
                    else:
                        keep = False
                        break
                # NaN is not valid json, replace with null
                elif np.isnan(results[key][i]):
                    val = None
                else:
                    # some time is saved here not truncating decimals
                    # but more data are sent to the client
                    # val = self._format_value(key, float(results[key][i]))
                    val = float(results[key][i])
                res[key] = val
            if not keep:
                continue
            # save some time here by not creating Variants
            res['variant'] = self.index2anno[res['variant_index']
                                             ]['variant'].replace(':', '-')
            indices[res['variant_index']] = True
            del res['variant_index']
            results_munged.append(res)
        time_munge = timeit.default_timer() - start_time
        start_time = timeit.default_timer()
        self._set_top_flags(results_munged)
        anno = {self.index2anno[i]['variant']: self.index2anno[i] for i in indices}
        # if a gene was given, filter to variants whose most severe
        # consequence is for that gene
        if gene is not None:
            anno = {k: v for k, v in anno.items(
            ) if v['gene_most_severe'].upper() == gene.upper()}
            results_munged = [
                res for res in results_munged if res['variant'] in anno]
        time_rest = timeit.default_timer() - start_time
        return {
            'results': results_munged,
            'anno': anno,
            'time': {
                'db': self._format_value('time', time_db),
                'munge': self._format_value('time', time_munge),
                'rest': self._format_value('time', time_rest),
            }
        }
