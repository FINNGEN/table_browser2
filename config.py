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

phenos = '/opt/table_data_r10/analyzed_phenos.json'
variant_annotation = '/opt/table_data_r10/r10_imp_chip_anno.tsv.gz'
gwas_tiledb = '/opt/table_data_r10/r10_coding_tiledb'
top_table = '/opt/table_data_r10/R10_coding_variant_results_1e-5_signals.tsv'

cluster_plot_bucket = 'finngen-production-library-green'
cluster_plot_loc = 'finngen_R10/cluster_plots/raw/'
