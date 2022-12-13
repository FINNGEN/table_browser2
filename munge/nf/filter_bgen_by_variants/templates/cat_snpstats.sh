grep -Ev "^#" *.snpstats | awk 'NR==1||!($0~"^alternate_ids")' > filtered.snpstats
