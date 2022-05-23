# pileup2vcf.py
#
# Original code by: Vlad Makarov, Chris Yoon
# Original copyright (c) 2011, The Mount Sinai School of Medicine
# Available under BSD licence
#
# Modified code copyright (C) 2011-2019 Vas Vasiliadis
# University of Chicago
#
##
__author__ = 'Vas Vasiliadis <vas@uchicago.edu>'

import os
import datetime
import file_utils as fu

HETERO = {'M':'AC', 'R':'AG', 'W':'AT', 'S':'CG', 'Y':'CT', 'K':'GT'}
ACCEPTED_CHR = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13", 
                "14", "15", "16", "17", "18", "19", "20","21","22", "X", "Y", "MT"]
#http://www.broadinstitute.org/gsa/wiki/index.php/Understanding_the_Unified_Genotyper's_VCF_files

def count_alt(depth, bases):
    bases = bases.upper()
    lst = list(bases)
    ast = 0
    match_sum = 0

    for l in lst:
        l = str(l)

        if ((str(l) == '.') or (str(l) == ',')):
            match_sum = match_sum + 1
        elif (l == '*'):
            ast = ast + 1

    return (int(depth) - (match_sum + ast))


def vcfheader(pileup):
    """ Generates VCF header """
    pileup = os.path.basename(pileup)
    pileup = os.path.splitext(pileup)[0]
    now = datetime.datetime.now()
    curdate = str(now.year) + '-' + str(now.month) + '-' + str(now.day)
    lines = []
    lines.append("##fileformat=VCFv4.0")
    lines.append(f"##fileDate={curdate}")
    lines.append( "##reference=1000Genomes-NCBI37")
    lines.append('##INFO=<ID=DB,Number=0,Type=Flag,Description="dbSNP membership, build 132">')
    lines.append('##FILTER=<ID=q30,Description="Quality below 30">')
    lines.append('##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">')
    lines.append('##FORMAT=<ID=GQ,Number=1,Type=Integer,Description="Genotype Quality">')
    lines.append('##FORMAT=<ID=DP,Number=1,Type=Integer,Description="Read Depth">')
    lines.append('##FORMAT=<ID=AD,Number=1,Type=Integer,Description="Read Depth of Alternative Allele">')
    lines.append('#CHROM'+'\t'+'POS'+'\t'+'ID'+'\t'+'REF'+'\t'+'ALT'+'\t'+'QUAL'+'\t'+'FILTER'+'\t'+'INFO'+'\t'+'FORMAT' + '\t'+ pileup)
    return '\n'.join(lines)


def hetero2homo(ref, alt):
    """ Converts heterozygous symbols from Samtools pileup to A, G, T, C """
    if not fu.isOnTheList(HETERO.keys(), alt):
        return alt
    else:
        alt_x = HETERO[alt]
        if (str(ref) == str(alt_x)[0]):
            return str(alt_x)[1]
        else:
            return str(alt_x)[0]


def varpileup_line2vcf_line(pileupfields):
    """ Converts Variant Pileup format to VCF format """

    t = '\t'
    chr = str(pileupfields[0])
    pos = str(pileupfields[1])
    ref = str(pileupfields[2])
    alt = str(pileupfields[3])
    consqual = str(pileupfields[4])
    snpqual = str(pileupfields[5])
    mapqual = str(pileupfields[6])
    depth = str(pileupfields[7])
    alt_count = str(count_alt(depth, pileupfields[8]))

    GT = '1/1'
    if fu.isOnTheList(HETERO.keys(), alt):
        GT = '0/1'
        alt = hetero2homo(ref,alt)

    return chr + t + pos + t + '.' + t + ref + t + alt + t + mapqual + \
        t + 'PASS' + t + '.' + t + 'GT:GQ:DP:AD' + t + GT + ':' + \
        consqual + ':' + depth + ':' + alt_count


def filter_pileup(pileup, outfile=None, chr_col=0, 
    ref_col=2, alt_col=3, sep='\t'):
    
    fh = open(pileup, "r")
    if (outfile is None):
        outfile = pileup + '.vcf'

    fu.delete(outfile)
    fh_out = open(outfile, "w")
    fh_out.write(vcfheader(pileup) + '\n')


    for line in fh:
        line = line.strip()
        fields = line.split(sep)

        chr = str(fields[chr_col])
        ref = str(fields[ref_col])
        alt = str(fields[alt_col])

        if ((alt != ref) and \
            (fu.find_first_index(ACCEPTED_CHR, chr.strip()) > -1)):
            fh_out.write(varpileup_line2vcf_line(fields[0:9]) + '\n' )


"""Removes lines where ALT==REF and chromosomes other than 1 - 22, X, Y and MT
"""
def filter_vcf(pileup, outfile=None,  chr_col=0, ref_col=3, 
    alt_col=4, sep='\t'):

    fh = open(pileup, "r")
    if (outfile is None):
        outfile = pileup + '.filt'

    fu.delete(outfile)
    fh_out = open(outfile, "w")


    for line in fh:
        line = line.strip()
        if line.startswith('#'):
            fh_out.write(str(line)+'\n')
        else:
            fields = line.split(sep)
            if (len(fields) >= 8):
                chr = str(fields[chr_col])
                ref = str(fields[ref_col])
                alt = str(fields[alt_col])

                if ((alt != ref) and \
                    (fu.find_first_index(ACCEPTED_CHR, chr.strip()) > -1)):
                    fh_out.write(str(line) + '\n')

### EOF