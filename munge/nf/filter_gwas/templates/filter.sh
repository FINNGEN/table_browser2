mkdir filtered
python3 - !{variants} !{sumstat} <<EOF | bgzip > filtered/!{sumstat}
import sys
import gzip

variants = {}
with gzip.open(sys.argv[1], 'rt') as f:
    for line in f:
        variants[line.strip().replace('X', '23').replace('Y', '24').replace('MT', '25').replace('M', '25')] = True

with gzip.open(sys.argv[2], 'rt') as f:
    line = f.readline().strip()
    print(line)
    for line in f:
        line = line.strip()
        s = line.split('\t')
        chr = s[0].replace('chr', '').replace('X', '23').replace('Y', '24').replace('MT', '25').replace('M', '25')
        id = chr + ':' + s[1] + ':' + s[2] + ':' + s[3]
        if id in variants:
            print(line)
EOF

qqplot.R --file filtered/!{sumstat} --chrcol "#chrom" --bp_col "pos" --pval_col "pval" --loglog_pval 10 > qq_out 2> qq_err
tabix -s1 -b2 -e2 filtered/!{sumstat}
