#! /bin/bash -x

HASH_LOCATION=$1
REFERENCE=$2

/software/hpag/bin/smalt-0.7.4 index -k 17 -s 17 $HASH_LOCATION $REFERENCE
