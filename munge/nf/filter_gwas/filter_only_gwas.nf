nextflow.enable.dsl=2

process filter_stats {

    memory 2.GB
    disk 100.GB
    publishDir "$params.outdir"

    input:
      path variants
      path sumstat
    output:
      path 'filtered/*.gz'
    shell:
      template 'filter_only.sh'
}

workflow {
    filter_stats(channel.value(file(params.variants)), channel.fromPath(params.files))
}
