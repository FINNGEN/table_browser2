nextflow.enable.dsl=2

process filter_bgen {

    memory 2.GB
    disk 100.GB

    input:
      path annotation
      path bgen
    output:
      path "filtered/${bgen.baseName}.filtered.bgen", emit: out
      path "${bgen.baseName}.snpstats", emit: snpstats
    shell:
      template 'filter_bgen_by_variants.sh'
}

process gather {

    memory 2.GB
    disk 100.GB
    publishDir "$params.outdir"

    input:
      path('*')
    output:
      path 'filtered.bgen'
    shell:
      template 'cat_bgen.sh'
}

process gather_snpstats {

    memory 2.GB
    disk 100.GB
    publishDir "$params.outdir"

    input:
      path('*')
    output:
      path 'filtered.snpstats'
    shell:
      template 'cat_snpstats.sh'
}

workflow {
    filter_bgen(channel.value(file(params.annotation)), channel.fromPath(params.files))
    gather(filter_bgen.out.out | collect)
    gather_snpstats(filter_bgen.out.snpstats | collect)
}
