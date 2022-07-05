import logging
log_level = logging.INFO

authentication = False
login = {
    'GOOGLE_LOGIN_CLIENT_ID': 'XXX',
    'GOOGLE_LOGIN_CLIENT_SECRET': 'YYY'
}
group_auth = {
    'GROUPS': ['group@domain.org'],
    'SERVICE_ACCOUNT_FILE': '/path/to/service-account.json',
    'DOMAIN': 'domain.org',
    'DELEGATED_ACCOUNT': 'admin@domain.org'
}

phenos = '/Users/jkarjala/FinnGen/R9/Coding/data/analyzed_phenos.json'
variant_annotation = '/Users/jkarjala/FinnGen/R9/Coding/data/r9_imp_chip_anno.tsv.gz'
gwas_tiledb = '/Users/jkarjala/FinnGen/R9/Coding/data/r9_coding_tiledb'
top_table = '/Users/jkarjala/FinnGen/R9/Coding/data/R9_coding_variant_results_1e-5_signals.tsv'

cluster_plot_bucket = 'finngen-production-library-green'
cluster_plot_loc = 'finngen_R9/cluster_plots/raw/'
