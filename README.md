HGVS variant name parsing and generation
========================================

The Human Genome Variation Society (HGVS) promotes the discovery and
sharing of genetic variation in the human population.  As part of facilitating
variant sharing, the society has produced a series of recommendations for
how to name and refer to variants within research publications and clinical
settings.  A compilation of these recommendations is available on their
[website](http://www.hgvs.org/mutnomen/recs.html).

This library provides a simple Python API for parsing, formatting, and
normalizing HGVS names.  Surprisingly, there are many non-trivial steps
necessary in handling HGVS names and therefore there is a need for well tested
libraries that encapsulate these steps.

## HGVS name example

In most next-generation sequencing applications, variants are first
discovered and described in terms of their genomic coordinates such as
chromosome 7, position 117,199,563 with reference allele `G` and
alternative allele `T`.  According to the HGVS standard, we can
describe this variant as `NC_000007.13:g.117199563G>T`.  The first
part of the name is a RefSeq ID `NC_000007.13` for chromosome 7
version 13.  The `g.` denotes that this is a variant described in
genomic (i.e. chromosomal) coordinates.  Lastly, the chromosomal position,
reference allele, and alternative allele are indicated.  For simple
single nucleotide changes the `>` character is used.

More commonly, a variant will be described using a cDNA or protein
style HGVS name.  In the example above, the variant in cDNA style is
named `NM_000492.3:c.1438G>T`.  Here again, the first part of the name
refers to a RefSeq sequence, this time mRNA transcript `NM_000492`
version `3`.  Optionally, the gene name can also be given as
`NM_000492.3(CFTR)`.  The `c.` indicates that this is a cDNA name, and
the coordinate indicates that this mutation occurs at position 1438
along the coding portion of the spliced transcript (i.e. position 1 is
the first base of `ATG` translation start codon).  Briefly, the
protein style of the variant name is `NP_000483.3:p.Gly480Cys` which
indicates the change in amino-acid coordinates (`480`) along an
amino-acid sequence (`NP_000483.3`) and gives the reference and
alternative amino-acid alleles (`Gly` and `Cys`, respectively).

The standard also specifies custom name formats for many mutation
categories such as insertions (`NM_000492.3:c.1438_1439insA`),
deletions (`NM_000492.3:c.1438_1440delGGT`),
duplications (`NM_000492.3:c.1438_1440dupGGT`), and several
other more complex genomic rearrangements.

While many of these names appear to be simple to parse or generate,
there are many corner cases, especially with cDNA HGVS names.  For
example, variants before the start codon should have negative cDNA
coordinates (`NM_000492.3:c.-4G>C`), and variants after the stop codon
also have their own format (`NM_000492.3:c.*33C>T`).  Variants within
introns are indicated by the closest exonic base with an additional
genomic offset such as `NM_000492.3:4243-20A>G` (the variant is 20
bases in the 5' direction of the cDNA coordinate 4243).  Lastly, all
coordinates and alleles are specified on the strand of the
transcript.  This library properly handles all logic necessary to
convert genomic coordinates to and from HGVS cDNA coordinates.

Another important consideration of any library that handles HGVS names
is variant normalization.  The HGVS standard aims to provide "uniform
and unequivocal" description of variants.  Namely, two people
discovering a variant should be able to arrive at the same name for
it.  Such a property is very useful for checking whether a variant has
been seen before and connecting all known relevant information.  For
SNPs, this property is fairly easy to achieve.  However, for
insertions and deletions (indels) near repetitive regions, many indels
are equivalent (e.g. it doesn't matter which `AT` in a run of
`ATATATAT` was deleted). The VCF file format has chosen to uniquely
specify such indels by using the most left-aligned genomic coordinate.
Therefore, compliant variant callers that output VCF will have applied
this normalization.  The HGVS standard also specifies a normalization
for such indels. However, it states that indels should use the most 3'
position in a transcript.  For genes on the positive strand, this is
the opposite direction specified by VCF.  This library properly
implements both kinds of variant normalization and allows easy
conversion between HGVS and VCF style variants.  It also handles
many other cases of normalization (e.g. the HGVS standard recommends
indicating an insertion with the `dup` notation instead of `ins`
if it can be represented as a tandem duplication).

## Example usage

Below is a minimal example of parsing and formatting HGVS names.  In
addition to the name itself, two other pieces of information are
needed: the genome sequence (needed for normalization), and the
transcript model or a callback for fetching the transcript model
(needed for transcript coordinate calculations).  This library makes
as few assumptions as possible about how this external data is stored.
In this example, the genome sequence is read using the `pyfaidx` library
and transcripts are read from a RefSeqGenes flat-file using methods
provided by `hgvs`.

```python
import pyhgvs as hgvs
import hgvs.utils as hgvs_utils
from pyfaidx import Fasta

# Read genome sequence using pyfaidx.
genome = Fasta('hg19.fa')

# Read RefSeq transcripts into a python dict.
with open('hgvs/data/genes.refGene') as infile:
    transcripts = hgvs_utils.read_transcripts(infile)

# Provide a callback for fetching a transcript by its name.
def get_transcript(name):
    return transcripts.get(name)

# Parse the HGVS name into genomic coordinates and alleles.
chrom, offset, ref, alt = hgvs.parse_hgvs_name(
    'NM_000352.3:c.215A>G', genome, get_transcript=get_transcript)
# Returns variant in VCF style: ('chr11', 17496508, 'T', 'C')
# Notice that since the transcript is on the negative strand, the alleles
# are reverse complemented during conversion.

# Format an HGVS name.
chrom, offset, ref, alt = ('chr11', 17496508, 'T', 'C')
transcript = get_transcript('NM_000352.3')
hgvs_name = hgvs.format_hgvs_name(
    chrom, offset, ref, alt, genome, transcript)
# Returns 'NM_000352.3(ABCC8):c.215A>G'
```

The `hgvs` library can also perform just the parsing step and provide
a parse tree of the HGVS name.

```python
import pyhgvs as hgvs

hgvs_name = hgvs.HGVSName('NM_000352.3:c.215-10A>G')

# fields of the HGVS name are available as attributes:
#
# hgvs_name.transcript = 'NM_000352.3'
# hgvs_name.kind = 'c'
# hgvs_name.mutation_type = '>'
# hgvs_name.cdna_start = hgvs.CDNACoord(215, -10)
# hgvs_name.cdna_end = hgvs.CDNACoord(215, -10)
# hgvs_name.ref_allele = 'A'
# hgvs_name.alt_allele = 'G'
```

## Install

This library can be installed using the `setup.py` file as follows:

```sh
python setup.py install
```

## Tests

Test cases can be run by running

```sh
python setup.py nosetests
```

## Requirements

This library requires at least Python 2.6, but otherwise has no
external dependencies.

The library does assume that genome sequence is available through a `pyfaidx`
compatible `Fasta` object. For an example of writing a wrapper for
a different genome sequence back-end, see
[hgvs.tests.genome.MockGenome](pyhgvs/tests/genome.py).

# Docker Image

The docker image is `schnknc/hgvs` and is available here [https://hub.docker.com/r/schnknc/hgvs](https://hub.docker.com/r/schnknc/hgvs)

- Pull latest master build
```
docker pull schnknc/hgvs:master
```
- Pull a build of a specific github SHA
```
docker pull schnknc/hgvs:sha-b7d3ad5
```

```shell
./download_refGene.sh -hg38
docker build . -t hgvs
docker run -p 8002:8002 hgvs
or
docker compose up
```
# API

### Parameters
|Parameter|Description  |
|--|--|
| normalise | If True, Normalise allele according to VCF standard  |
| ignore_version | If True, Ignore version from input transcript/gene |
| indels_start_with_same_base | If True, When normalising, don't strip common prefix from indels |

## Translate Endpoint

### Valid Requests examples

#### Example 1
* Single variant

**Request**
```shell
## Request
curl -X "POST" "http://127.0.0.1:9001/translate" \
     -H 'Content-Type: application/json; charset=utf-8' \
     -d $'{
  "indels_start_with_same_base": true,
  "ignore_version": true,
  "input": "NM_001034853.2:c.778+1del",
  "normalise": true
}'
```

**Response**
```json
{
  "response": {
    "input": "NM_001034853.2:c.778+1del",
    "chr": "X",
    "pos": 38310613,
    "ref": "AC",
    "alt": "A",
    "message": null
  }
}
```

#### Example 2
* Single indel variant

**Request**
```shell
curl -X "POST" "http://127.0.0.1:9001/translate" \
     -H 'Content-Type: application/json; charset=utf-8' \
     -d $'{
  "indels_start_with_same_base": true,
  "ignore_version": true,
  "input": "NM_173495.3:c.1835_1839delinsGAA",
  "normalise": true
}'
```

**Response**
```
{
  "response": {
    "input": "NM_173495.3:c.1835_1839delinsGAA",
    "chr": "X",
    "pos": 23393352,
    "ref": "ATGTTG",
    "alt": "AGAA",
    "message": null
  }
}
```
#### Example 3
* Single indel variant
* If indels start with same base, ignore first base in output

**Request**
```shell
curl -X "POST" "http://127.0.0.1:9001/translate" \
     -H 'Content-Type: application/json; charset=utf-8' \
     -d $'{
  "indels_start_with_same_base": false,
  "ignore_version": true,
  "input": "NM_173495.3:c.1835_1839delinsGAA",
  "normalise": true
}'
```

**Response**
```
{
  "response": {
    "input": "NM_173495.3:c.1835_1839delinsGAA",
    "chr": "X",
    "pos": 23393353,
    "ref": "TGTTG",
    "alt": "GAA",
    "message": null
  }
}
```


### Invalid Requests examples

#### Example1
**Request**
```shell
curl -X "POST" "http://127.0.0.1:9001/translate" \
     -H 'Content-Type: application/json; charset=utf-8' \
     -d $'{
  "indels_start_with_same_base": true,
  "ignore_version": false,
  "input": "xyz",
  "normalise": false
}'
```

**Response**
```json
{
  "detail": {
    "error": {
      "summary": "Invalid HGVS Name:'xyz'",
      "details": null
    }
  }
}
```

## Bulk Translate Endpoint

### Valid Requests examples

**Request**
```shell
curl -X "POST" "http://127.0.0.1:9001/translate_bulk" \
     -H 'Content-Type: application/json; charset=utf-8' \
     -d $'{
  "indels_start_with_same_base": false,
  "ignore_version": false,
  "input": [
    "NM_031407.7:c.1237T>C",
    "NM_031407.7:c.2538T>A"
  ],
  "normalise": false
}'
```

**Response**
```json
{
  "response": [
    {
      "input": "NM_031407.7:c.1237T>C",
      "chr": "X",
      "pos": 53628498,
      "ref": "A",
      "alt": "G",
      "message": null
    },
    {
      "input": "NM_031407.7:c.2538T>A",
      "chr": "X",
      "pos": 53604793,
      "ref": "A",
      "alt": "T",
      "message": null
    }
  ]
}
```

### Invalid Requests examples

**Request**
```shell
curl -X "POST" "http://127.0.0.1:9001/translate_bulk" \
     -H 'Content-Type: application/json; charset=utf-8' \
     -d $'{
  "indels_start_with_same_base": false,
  "ignore_version": false,
  "input": [
    "XYZ",
    "NM_031407.7:c.2538T>A"
  ],
  "normalise": false
}'

```

**Response**
```json
{
  "response": [
    {
      "input": "XYZ",
      "chr": null,
      "pos": null,
      "ref": null,
      "alt": null,
      "message": "Invalid HGVS Name:'XYZ'"
    },
    {
      "input": "NM_031407.7:c.2538T>A",
      "chr": "X",
      "pos": 53604793,
      "ref": "A",
      "alt": "T",
      "message": null
    }
  ]
}
```
