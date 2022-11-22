mkdir -p filtered

qctool -g !{bgen} -incl-rsids <(zcat !{annotation} | cut -f1 | sed 's/^23:/X:/' | sed 's/:/_/g' | awk '{print "chr"$0}') -og filtered/!{bgen.baseName}.filtered.bgen

qctool -g filtered/!{bgen.baseName}.filtered.bgen -threshold 0.9 -snp-stats -osnp !{bgen.baseName}.snpstats -force
