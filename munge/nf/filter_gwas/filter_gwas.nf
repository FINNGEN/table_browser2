nextflow.enable.dsl=2

process filter_stats {

    memory 6.GB
    disk 100.GB
    publishDir "$params.outdir"

    input:
      path variants
      path sumstat
    output:
      path 'filtered/*.gz'
      path 'filtered/*.gz.tbi'
      path 'filtered/*.png'
    shell:
      template 'filter.sh'
}

workflow {
    filter_stats(channel.value(file(params.variants)), channel.fromPath(params.files))
}
