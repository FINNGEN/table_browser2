version 1.0

workflow filter_only_gwas {

    input {
        File sumstatfiles
        File variants
        String docker

        Array[File] sumstats = read_lines(sumstatfiles)
    }

    scatter (sumstat in sumstats) {

        call filter {
            input:
                sumstat = sumstat,
                variants = variants,
                docker = docker
        }

    }

    output {
        Array[File] filtered_sumstat = filter.filtered_sumstat
    }

}


task filter {

    input {
        File sumstat
        File variants
        String docker

        String base = basename(sumstat)

        Int disk_size = ceil(size(sumstat, "G") + size(variants, "G")) + 5
    }

    command <<<

        set -euxo pipefail

        python3 - ~{variants} ~{sumstat} <<EOF | bgzip > ~{base}.filtered.gz
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

    >>>

    output {
        File filtered_sumstat = base + ".filtered.gz"
    }

    runtime {
        docker: "~{docker}"
        cpu: 1
        memory: "2 GB"
        disks: "local-disk ~{disk_size} HDD"
        zones: "europe-west1-b europe-west1-c europe-west1-d"
        preemptible: 2
        noAddress: true
    }
}