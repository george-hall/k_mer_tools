#! /bin/bash -x

# Takes .fasta file  and desired output name as inputs and returns two reads, which simulate 100x coverage reads of length 100 in both forward and backward directions.
# Assumes that original .fasta reads are of length 250
# Call as script in directory containing .fasta file.
# Finally combines both reads into one file

# Eventually should make more universal (i.e. user can use different read lengths and coverages etc)

INPUT_FILE=$1
COVERAGE=$2
READ_LENGTH=$3
INSERT_SIZE=$4
NAME=$5

~zn1/src/process/screen/linux-64/simulation_reads-randam2 -rlength $READ_LENGTH -cover $COVERAGE -insert $INSERT_SIZE $INPUT_FILE "temp-simu-random.fastq"
~zn1/bin/ssaha_reads -file 22 "temp-simu-random.fastq_0000.fastq" $NAME-simu-random_1.fastq $NAME-simu-random_2.fastq
rm temp-simu-random.fastq_*.fastq

cat $NAME-simu-random_1.fastq $NAME-simu-random_2.fastq > $NAME-simu-random_both.fastq

echo "Finished simulating reads"
