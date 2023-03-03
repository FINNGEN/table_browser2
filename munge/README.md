## Data preparation for table_browser2

For the browser, we need two kinds of data:

1. Coding variant annotations
2. Summary stats of additive analysis, possibly also of recessive and chip analyses

Locally run scripts used in this README are under [scripts](scripts) and workflows are under [nf](nf).

### Coding variant annotations

We need a variant annotation file for coding variants, imputed and chip combined. The annotation file is read in-memory in table_browser2.

The annotation file is required for importing summary stats to tiledb because it contains the variant index column which is used as a tiledb dimension.

To create the annotation file, we need 1) chip coding variant annotations 2) imputed coding variant annotations. See [finngen-analysis-overview chip data preparation](https://github.com/FINNGEN/finngen-analysis-overview/tree/master/chip) for creation of 1). For 2), to filter imputed annotation file to coding INFO > 0.6 variants, do something like:

```
zcat R10_annotated_variants_v2.gz | \
awk '
BEGIN{OFS="\t";
a["transcript_ablation"]=1
a["splice_donor_variant"]=1
a["stop_gained"]=1
a["splice_acceptor_variant"]=1
a["frameshift_variant"]=1
a["stop_lost"]=1
a["start_lost"]=1
a["inframe_insertion"]=1
a["inframe_deletion"]=1
a["missense_variant"]=1
a["protein_altering_variant"]=1
}
NR==1{for(i=1;i<=NF;i++) h[$i]=i; print $0}
NR >1 && $h["most_severe"] in a && $h["INFO"] > 0.6
' | bgzip -@2 > r10_imp_fullanno_coding_INFO0.6.gz
```

While still at it, merge imputed and chip annotation files - this is needed for web import later:

```
import pandas as pd
imp = pd.read_csv('r10_imp_fullanno_coding_INFO0.6.gz', sep='\t')
chip = pd.read_csv('r10_chip_anno_coding.gz', sep='\t')
chip.columns = [c + '_chip' if c != '#variant' else c for c in chip.columns]
anno = imp.merge(chip, how='outer', on='#variant')
# replace fields with chip anno when no imputed anno
anno.loc[pd.isnull(anno['gene_most_severe']), 'gene_most_severe'] = anno.loc[pd.isnull(anno['gene_most_severe']), 'gene_most_severe_chip']
anno.loc[pd.isnull(anno['most_severe']), 'most_severe'] = anno.loc[pd.isnull(anno['most_severe']), 'most_severe_chip']
anno.loc[pd.isnull(anno['chr']), 'chr'] = anno.loc[pd.isnull(anno['chr']), 'chr_chip']
anno.loc[pd.isnull(anno['pos']), 'pos'] = anno.loc[pd.isnull(anno['pos']), 'pos_chip']
anno.loc[pd.isnull(anno['ref']), 'ref'] = anno.loc[pd.isnull(anno['ref']), 'ref_chip']
anno.loc[pd.isnull(anno['alt']), 'alt'] = anno.loc[pd.isnull(anno['alt']), 'alt_chip']
anno.loc[pd.isnull(anno['rsid']), 'rsid'] = anno.loc[pd.isnull(anno['rsid']), 'rsid_chip']
anno.loc[pd.isnull(anno['AF']), 'AF'] = anno.loc[pd.isnull(anno['AF']), 'AF_chip']
anno.loc[pd.isnull(anno['GENOME_enrichment_nfee']), 'GENOME_enrichment_nfee'] = anno.loc[pd.isnull(anno['GENOME_enrichment_nfee']), 'GENOME_enrichment_nfee_chip']
anno.loc[pd.isnull(anno['EXOME_enrichment_nfsee']), 'EXOME_enrichment_nfsee'] = anno.loc[pd.isnull(anno['EXOME_enrichment_nfsee']), 'EXOME_enrichment_nfsee_chip']
# get enrichment from genomes when no exome enrichment
anno['enrichment'] = anno['EXOME_enrichment_nfsee']
anno.loc[pd.isnull(anno['enrichment']), 'enrichment'] = anno.loc[pd.isnull(anno['enrichment']), 'GENOME_enrichment_nfee']
# compute hom AC by affy/legacy
cols = [c for c in anno.columns if c.startswith('AC_Hom_') and not c.startswith('AC_Hom_Axiom') and not c == 'AC_Hom_chip']
anno['AC_Hom_legacy'] = anno[cols].sum(axis=1)
cols = [c for c in anno.columns if c.startswith('AC_Hom_Axiom')]
anno['AC_Hom_affy'] = anno[cols].sum(axis=1)
anno.sort_values(['chr', 'pos'], inplace=True, ignore_index=True)
anno.rename(columns={'#variant': 'variant'}, inplace=True)
anno = anno.astype({'chr': int, 'pos': int})
anno.to_csv('r10_imp_chip_anno.tsv', sep='\t', na_rep='NA', index_label='#index', columns=['variant', 'chr', 'pos', 'ref', 'alt', 'INFO', 'AF', 'AC_Het', 'AC_Hom', 'AF_chip', 'AC_Het_chip', 'AC_Hom_chip', 'AC_Hom_legacy', 'AC_Hom_affy', 'most_severe', 'gene_most_severe', 'rsid', 'enrichment'])
```

tabix:

```
bgzip r10_imp_chip_anno.tsv && tabix -s 3 -b 4 -e 4 r10_imp_chip_anno.tsv.gz
```

### Professor level variant annotations

The annotation file created above is the one used by the application. Here we add some things to help with homozygote deficiency analysis.

Create a bgen file of coding variants and compute snpstats with a GP threshold of 0.9 to get high-probability homozygotes as per imputation with [this Nextflow worklow](nf/filter_bgen_by_variants/filter_bgen_by_variants.nf). See tower VM config files for accessToken and SMTP password configurations.

Munge out extra headers (we could fix the workflow up front preferably):

```
gsutil cp gs://r10-data/bgen/filtered.snpstats .
awk 'BEGIN{FS=":"}{print $2}' filtered.snpstats | awk 'NR==1||!($0~"^alter")' > R10_coding_variants.snpstats_gp0.9
```

Then join that to annotation and calculate extra stats:

```
import pandas as pd
import scipy.stats
anno = pd.read_csv('r10_imp_chip_anno.tsv.gz', sep='\t')
ss = pd.read_csv('R10_coding_variants.snpstats_gp0.9', sep='\t')
ss.columns = [c + '_gp0.9' for c in ss.columns]
anno['cpra'] = 'chr' + anno['chr'].replace(23, 'X').astype(str) + '_' + anno['pos'].astype(str) + '_' + anno['ref'] + '_' + anno['alt']
proflevel = anno.merge(ss, how='left', left_on='cpra', right_on='alternate_ids_gp0.9')
proflevel['n_samples'] = proflevel['AA_gp0.9'] + proflevel['AB_gp0.9'] + proflevel['BB_gp0.9'] + proflevel['NULL_gp0.9']
proflevel['OBS_Hom'] = proflevel['AC_Hom']/2
proflevel['OBS_Hom_affy'] = proflevel['AC_Hom_affy']/2
proflevel['OBS_Hom_legacy'] = proflevel['AC_Hom_legacy']/2
proflevel['OBS_Hom_chip'] = proflevel['AC_Hom_chip']/2
proflevel['EXP_Hom'] = proflevel['AF']*proflevel['AF']*proflevel['n_samples']
proflevel['OBS/EXP'] = proflevel['OBS_Hom']/proflevel['EXP_Hom']
proflevel['poisson'] = scipy.stats.poisson.cdf(proflevel['OBS_Hom'], proflevel['EXP_Hom'])
proflevel = proflevel.astype({'chr': int, 'pos': int})
# remove HLA and APOE
proflevel = proflevel[~((proflevel['chr'] == 6) & (proflevel['pos'] > 23000000) & (proflevel['pos'] < 38000000)) & ~((proflevel['chr'] == 19) & (proflevel['pos'] > 43000000) & (proflevel['pos'] < 46000000))]
proflevel = proflevel[proflevel['EXP_Hom']>4]
proflevel.sort_values('poisson', inplace=True, ignore_index=True)
proflevel.to_csv('r10_imp_chip_anno_proflevel.tsv', sep='\t', na_rep='NA', index=False, columns=[
'variant',
'chr',
'pos',
'ref',
'alt',
'rsid',
'most_severe',
'gene_most_severe',
'INFO',
'enrichment',
'AF_chip',
'AF',
'AC_Het_chip',
'AC_Het',
'OBS_Hom_chip',
'OBS_Hom',
'OBS_Hom_affy',
'OBS_Hom_legacy',
'EXP_Hom',
'OBS/EXP',
'poisson',
'HW_exact_p_value_gp0.9',
'alleleB_frequency_gp0.9',
'AA_gp0.9',
'AB_gp0.9',
'BB_gp0.9',
'NULL_gp0.9'])
```

Ad hoc addition of column of how many batches went into imputation

```
cut -f1 r10_imp_chip_anno_proflevel.tsv | tail -n+2 > proflevel_vars
awk 'NR==FNR{a[$1]=1} NR>FNR&&(FNR==1||($1 in a))' proflevel_vars <(zcat R10_annotated_variants_v2.gz) | bgzip > proflevel_vars_anno.gz
zcat proflevel_vars_anno.gz | awk 'BEGIN{OFS="\t"}NR==1{for(i=1;i<=NF;i++) if($i~"^CHIP_Axiom") use[i]=1; print "variant","n_chip"} NR>1{n=0; for(i in use) if($i==1) n++; print $1,n}' > proflevel_vars_nchip

import pandas
d = pandas.read_csv("r10_imp_chip_anno_proflevel.tsv", sep="\t")
n = pandas.read_csv("proflevel_vars_nchip", sep="\t")
d.merge(n, how="left", on="variant").to_csv("r10_imp_chip_anno_proflevel_nchip.tsv", sep="\t", index=False)
```

### Import coding variant results to db

We put coding variant results of imputed additive, imputed recessive and chip additive analyses to tiledb. tiledb is then used to serve data for a web interface.

First let's filter the sumstats of additive scans to coding variants only using [this Nextflow workflow](nf/filter_gwas/filter_only_gwas.nf). Use tower VM `/mnt/disks/tower/nextflow/env.sh` to set the needed environment variables. Then run: `nextflow run filter_only_gwas.nf -c nextflow.config -profile gls -resume`

Then get coding variant summary stats for the three analysis types:

```
mkdir -p data/add data/rec data/chip
gsutil -mq cp gs://r10-data/regenie/release/summary_stats_coding_INFO_06/filtered/*.gz data/add/
gsutil -mq cp gs://r10-data/regenie/release/recessive/*.gz data/rec/
gsutil -mq cp gs://r10-data/chip/regenie/summary_stats/*.gz data/chip/
```

Get list of analyzed phenos in any of the three analyses:

```
ls -1 data/add/*.gz data/rec/*.gz data/chip/*.gz | xargs -I {} basename {} .gz | sort -u > analyzed_phenos
```

Create a config file like:

```
$ cat coding_config.json
{
  "join_columns": ["#chrom", "pos", "ref", "alt"],
  "sumstats": [
    {
      "sumstat_type": "add",
      "sumstat_loc": "data/add"
    },
    {
      "sumstat_type": "rec",
      "sumstat_loc": "data/rec"
    },
    {
      "sumstat_type": "chip",
      "sumstat_loc": "data/chip"
    }
  ]
}
```

For each phenotype, merge the three analyses (this takes a while, maybe joinsort.sh would be better;):

```
python3 join_sumstats.py analyzed_phenos coding_config.json
```

This wrote merged pheno files to `merged/`.

Then shove sumstats to tiledb:

```
ls -1 merged/*.gz > analyzed_merged_sumstats
python3 tiledb_import_sparse.py r10_coding_tiledb analyzed_merged_sumstats mlogp_add,beta_add,sebeta_add,af_alt_cases_add,af_alt_controls_add,mlogp_rec,beta_rec,sebeta_rec,mlogp_chip,beta_chip,sebeta_chip data/r10_imp_chip_anno.tsv.gz
```

Get endpoint definition file and create `phenos.json` for web table

```
gsutil cp gs://finngen-production-library-red/finngen_R10/phenotype_1.0/documentation/finngen_R10_endpoint_definitions_1.0.txt .
cat analyzed_merged_sumstats | xargs -I {} basename {} .gz > analyzed_merged_phenos
python3 create_phenolist.py analyzed_merged_phenos finngen_R10_endpoint_core_noncore_1.0.tsv
```

Phenotypes not in the `finngen_R10_endpoint_core_noncore_1.0.tsv` definition file (e.g. _IRN quants) will need to be manually added to `phenos.json`

### Create one file with all p < 1e-5 associations

OK this was done in a hurry.. unfortunately in the above join_sumstats.py the resulting merged files will have different columns depending on what data was available for each phenotype. This could be fixed up front so it would be trivial to combine the files. Anyway, filter merged sumstats with a p-value threshold:

```
for file in merged/*.gz; do echo $file; gunzip -c $file | awk -v name_file=`basename $file .gz` 'BEGIN{OFS="\t"} NR==1{for(i=1;i<=NF;i++) { if($i=="#chrom") $i="chrom"; h[$i]=i }; print "pheno",$0} NR>1 && (("pval_add" in h && $h["pval_add"]<1e-5) || ("pval_rec" in h && $h["pval_rec"]<1e-5) || ("pval_chip" in h && $h["pval_chip"]<1e-5)) {print name_file,$0}' > $file.sig.tsv; done
```

Then concat the filtered sumstats to one - this will set missing columns to nan:

```
import pandas as pd
import glob
dfs = [pd.read_csv(file, sep='\t') for file in glob.glob('merged/*.sig.tsv')]
df = pd.concat(dfs, axis=0, ignore_index=True)
df['variant'] = df['chrom'].astype(str).replace('23', 'X') + '-' + df['pos'].astype(str) + '-' + df['ref'] + '-' + df['alt']
# remove HLA/APOE
df = df[~((df['chrom'] == 6) & (df['pos'] > 23000000) & (df['pos'] < 38000000)) & ~((df['chrom'] == 19) & (df['pos'] > 43000000) & (df['pos'] < 46000000))]
# remove extra quant runs, might as well remove the files up front
df = df[~((df['pheno'] == 'WEIGHT') | (df['pheno'] == 'HEIGHT') | (df['pheno'] == 'BMI'))]
df.to_csv('R10_coding_variant_results_1e-5.tsv', na_rep='NA', sep='\t', index=False)
```

Join data on more significant associations from compared_joined.tsv:

```
d = pd.read_csv('R10_coding_variant_results_1e-5.tsv', sep='\t')
a = pd.read_csv('compared_joined.tsv', sep='\t')[['pheno', 'variant', 'strongest_association', 'strongest_hit', 'possible_explaining_signals', 'signal_connection_type']]
a['variant'] = a['variant'].str.replace(':','-')
a['variant'] = a['variant'].str.replace('^23','X')
j = d.merge(a, on=['variant', 'pheno'])
j.to_csv('R10_coding_variant_results_1e-5_signals.tsv', index=False, sep='\t', na_rep="NA")
```

`R10_coding_variant_results_1e-5_signals.tsv` is then used in table_browser2 config.py
