# annotate.py
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

import file_utils as fu
import utils as u

indicesKnownGenes=[12, 1, 3] #12 for gene

def collapseGeneNames(row, indices, region, cnt):
    names = ['bin', 'name', 'chrom', 'transcriptStrand', 'txStart', 'txEnd', 
        'cdsStart', 'cdsEnd', 'exonCount', 'exonStarts', 'exonEnds', 'score',
        'name2', 'cdsStartStat', 'cdsEndStat', 'exonFrames']
    collapsed=[]
    for i in indices:
        mn = names[i]
        r = str(row[i])
        if(len(r) > 0 ):
            collapsed.append(mn + '=' + r.strip())
    collapsed.append(region)

    return  ';'.join(collapsed)


""""Collapces bigRefSegTable
"""
def collapseRefSeq(line):
    names = ['chr', 'start', 'end', 'haplotypeReference', 
        'haplotypeAlternate', 'name', 'name2', 'transcriptStrand', 
        'positionType', 'frame', 'mrnaCoord', 'codonCoord', 'spliceDist',
        'referenceCodon', 'referenceAA', 'variantCodon', 'variantAA',
        'changesAA', 'functionalClass','codingCoordStr','proteinCoordStr',
        'inCodingRegion', 'spliceInfo','uorfChange']
    fields = line.strip().split('\t')
    fcount = 0
    collapsed = []

    for f in fields:
        if (fcount > 4):
            if(len(str(f)) > 0 and str(f) !='0'):
                collapsed.append(str(names[fcount]).strip() + '=' + str(f).strip())
        fcount = fcount + 1

    return  ';'.join(collapsed)


def binarySearchUniqueAndSorted(arg0, key):
    low = 0;
    high = len(arg0) - 1
    mid = 0;
    obj = 0;

    while (low <= high):
        mid = (low + high) / 2
        obj = arg0[mid]

        if (obj < key):
            low = mid + 1;
        elif (obj > key):
            high = mid - 1;
        else:
            return mid;

    return -1 # NOT_FOUND


"""Cleans characters not accepted by MySQL
"""
def clean_mysql_chars(entry):
    entry = entry.replace("\"", "")
    entry = entry.replace("\'", "")
    return str(entry)


def getFormatSpecificIndices(format='vcf'):
    chr_ind = 0
    pos_ind = 1
    ref_ind = 3
    alt_ind = 4

    if (format != 'vcf'):
        ref_ind = 2
        alt_ind = 3

    return [chr_ind, pos_ind, ref_ind, alt_ind]


def getComplementary(nuc):
    compNuc = ''
    if (str(nuc) == 'A'):
        return 'T'
    elif (str(nuc) == 'T'):
        return 'A'
    elif (str(nuc) == 'G'):
        return 'C'
    elif (str(nuc) == 'C'):
        return 'G'
    else:
        return compNuc


""""Format must be pileup or vcf
    Types of variants in dbSNP135: DIV, SNV, MNV, MIXED
""" 
def getSnpsFromDbSnp(vcf, format='vcf', tmpextin='', tmpextout='.1',
    varclass='SNV', sep='\t'):
    
    outfile = vcf + tmpextout
    fh_out = open(outfile, "w")
    logcountfile = vcf + '.count.log'
    fh_log = open(logcountfile, 'w')
    var_count = 0

    inds = getFormatSpecificIndices(format=format)

    fh = open(vcf)
    conn = u.db_connect()
    cursor = conn.cursor()
    linenum = 1

    for line in fh:
        line = line.strip()
        if not line.startswith("#"):
            fields = line.split(sep)
            chr = fields[inds[0]].strip()
            if chr.startswith("chr"):
                chr = chr.replace('chr', '')

            pos = fields[inds[1]].strip()
            ref = clean_mysql_chars(fields[inds[2]]).strip()
            alt = clean_mysql_chars(fields[inds[3]]).strip()

            compRef = getComplementary(ref)
            compAlt = getComplementary(alt)

            sql = 'select * from dbSNP where CHR="' + str(chr) + \
                '" AND POS=' + str(pos) + ' AND ( REF="' + str(ref) + \
                '" OR REF ="' + str(compRef) + '" )  AND INFO = "' + \
                varclass + '" ;'
            cursor.execute(sql)
            rows = cursor.fetchall()

            fields[2] = '.'
            rsids = []
            mafs = []
            if (len(rows) > 0):
                for row in rows:
                    rsids.append(str(row[3]))
                    if (str(row[7]) != '.'):
                        mafs.append('GMAF=' + str(row[7]))

                maf_str=''
                if (len(mafs) > 0):
                    maf_str = ';' + ';'.join([str(x) for x in mafs])

                var_count = var_count + 1
                if (str(fields[7]) == '.'):
                    fields[7] = 'DB' + maf_str
                else:
                    fields[7] = fields[7] + ';DB;VC=' + varclass + maf_str

                fields[2] = str(';'.join(rsids))
                l = '\t'.join([str(x) for x in fields])
                fh_out.write(l + '\n')

            else:
                ## reset rsid to "." - in case there was annotation from old release of dbSNP
                fh_out.write('\t'.join([str(x) for x in fields]) + '\n')

            linenum = linenum + 1

        else:
            fh_out.write(line + '\n')

    ratioInDbSnp = (var_count / float(linenum)) * 100
    fh_log.write("## Please notice that all Isoforms were counted\n")
    fh_log.write("## Numbers may exceed number of variants in the annotated file\n")
    fh_log.write(f"Total: {str(linenum)}\n")
    fh_log.write(f"In dbSNP: {str(var_count)} ({str(ratioInDbSnp)}%)\n")
    fh_log.close()

    conn.close()
    fh.close()
    fh_out.close()


"""NOTE: all isoforms are collapsed in one record
    1. chrom_pos_equal_base
    2. chrom_pos_equal_nobase
    3. chrom_pos_unequal
"""
def getBigRefGene(vcf, format='vcf', tmpextin='.1', tmpextout='.2', sep='\t'):
    basefile = vcf
    vcf = basefile + tmpextin
    outfile = basefile + tmpextout
    fh_out = open(outfile, "w")
    inds = getFormatSpecificIndices(format=format)
    fh = open(vcf)

    conn = u.db_connect()
    cursor = conn.cursor()
    vcf_linenum = 1

    for line in fh:
        line = line.strip()
        if not line.startswith("#"):
            fields = line.split(sep)
            chr = fields[inds[0]].strip()
            if chr.startswith("chr"):
                chr = chr.replace('chr', '')

            pos = fields[inds[1]].strip()
            ref = clean_mysql_chars(fields[inds[2]]).strip()
            alt = clean_mysql_chars(fields[inds[3]]).strip()

            compRef = getComplementary(ref)
            compAlt = getComplementary(alt)

            sql1 = 'select * from chrom_pos_equal_base where CHR="' + \
                str(chr) + '" AND start = ' + str(pos) + \
                ' AND ((haplotypeReference="' + str(ref) + \
                '" AND haplotypeAlternate ="' + str(alt) + \
                '") OR (haplotypeReference="' + str(compRef) + \
                '" AND haplotypeAlternate ="' + str(compAlt) + '"));'

            sql2 = 'select * from chrom_pos_equal_nobase where CHR="' + \
                str(chr) + '" AND start = ' + str(pos) + ';'

            sql3 = 'select * from chrom_pos_unequal where CHR="' + \
                str(chr) + '" AND start <= ' + str(pos) + ' AND ' + \
                str(pos) + ' <= end ;'

            keep_going = True
            cursor.execute(sql1)
            rows = cursor.fetchall()

            if (len(rows) > 0):
                keep_going = False
                m = set([])
                for row in rows:
                    m.add(collapseRefSeq('\t'.join([str(x) for x in row[1:len(row)] ])))

                fields[7] = fields[7] + ';' + ';'.join(m)
                if (str(fields[7]).startswith(".;")):
                    fields[7] = str(fields[7]).replace('.;', '', 1)

                l = '\t'.join([str(x) for x in fields])
                fh_out.write(l + '\n')

            if (keep_going):
                cursor.execute(sql2)
                rows = cursor.fetchall()

                if (len(rows) > 0):
                    keep_going = False
                    m = set([])
                    for row in rows:
                        m.add(collapseRefSeq('\t'.join([str(x) for x in row[1:len(row)]])))

                    fields[7] = fields[7] + ';' + ';'.join(m)
                    if (str(fields[7]).startswith(".;")):
                        fields[7] = str(fields[7]).replace('.;', '', 1)
                    
                    l = '\t'.join([str(x) for x in fields])
                    fh_out.write(l + '\n')

            if (keep_going):
                cursor.execute(sql3)
                rows = cursor.fetchall()

                if (len(rows) > 0):
                    keep_going = False
                    m = set([])
                    for row in rows:
                        m.add(collapseRefSeq('\t'.join([str(x) for x in row[1:len(row)]])))

                    fields[7] = fields[7] + ';' + ';'.join(m)
                    if (str(fields[7]).startswith(".;")):
                        fields[7] = str(fields[7]).replace('.;', '', 1)

                    l = '\t'.join([str(x) for x in fields])
                    fh_out.write(l + '\n')

            if (keep_going):
                fh_out.write(line + '\n')

            vcf_linenum = vcf_linenum + 1

        else:
            fh_out.write(line + '\n')

    conn.close()
    fh.close()
    fh_out.close()


"""Get information about location in gene structures
"""
def getGenes(vcf, format='vcf', table='refGene', promoter_offset=500, 
    tmpextin='.2', tmpextout='.3', sep='\t'):
    
    basefile = vcf
    vcf = basefile + tmpextin
    outfile = basefile + tmpextout
    fh_out = open(outfile, "w")

    logcountfile = basefile + '.count.log'
    fh_log = open(logcountfile, 'a')

    interGenic_count = 0
    cds_count = 0
    utr3_count = 0
    utr5_count = 0
    intronic_count = 0
    non_coding_intronic_count = 0
    exonic_count = 0
    non_coding_exonic_count = 0
    promoter_count = 0

    inds = getFormatSpecificIndices(format=format)
    fh = open(vcf)
    conn = u.db_connect()
    cursor = conn.cursor()
    linenum = 1

    for line in fh:
        line = line.strip()
        if not line.startswith("#"):
            fields = line.split(sep)
            chr = fields[inds[0]].strip()

            if not chr.startswith("chr"):
                chr = "chr" + chr

            pos = fields[inds[1]].strip()
            ref = clean_mysql_chars(fields[inds[2]]).strip()
            alt = clean_mysql_chars(fields[inds[3]]).strip()
            info_field = clean_mysql_chars(fields[7]).strip()
            this_gene_name = str(u.parse_field(info_field, 'name', ';', '='))

            sql = 'select * from ' + table + ' where chrom="' + str(chr) + \
                '" AND (txStart - ' + str(promoter_offset) +') <= ' + \
                str(pos) + ' AND ' + str(pos) + ' <= (txEnd + ' + \
                str(promoter_offset) +');'

            cursor.execute(sql)
            rows = cursor.fetchall()
            info = []

            if (len(rows) > 0):
                cnt = 1
                for row in rows:
                    #count location
                    positionType = str(u.parse_field(info_field, 
                        'positionType', ';', '='))
                    
                    if (positionType == 'intron'):
                        intronic_count = intronic_count + 1
                    elif (positionType == 'non_coding_intron'):
                        non_coding_intronic_count = non_coding_intronic_count + 1
                    elif (positionType == 'CDS'):
                        cds_count = cds_count + 1
                    elif (positionType == 'non_coding_exon'):
                        non_coding_exonic_count = non_coding_exonic_count + 1
                    elif (positionType == 'utr5'):
                        utr5_count = utr5_count + 1
                    elif (positionType == 'utr3'):
                        utr3_count = utr3_count + 1

                    txtStart = int(row[4])
                    txtEnd = int(row[5])
                    cdsStart = int(row[6])
                    cdsEnd = int(row[7])
                    exonCount = int(row[8])
                    exonStarts =str(row[9].decode("utf-8"))
                    exonEnds = str(row[10].decode("utf-8"))
                    geneSymbol = str(row[12])
                    strand = str(row[3])

                    promoter_plus = txtStart - int(promoter_offset)
                    promoter_minus = txtEnd + int(promoter_offset)
                    region = ""
                    pos = int(pos)
                    exons = []
                    exonsSt = exonStarts.split(',')
                    exonsEn = exonEnds.split(',')

                    if (cdsStart == cdsEnd):
                        for e in range(0, exonCount):
                            if (u.isBetween(pos, int(exonsSt[e]), int(exonsEn[e]))):
                                exnum = e + 1
                                if (strand == '-'):
                                    exnum = exonCount - e
                                exons.append("non_coding_exon=" + "ex" + \
                                    str(exnum) + '/' + str(exonCount))
                        if (len(exons) > 0):
                            region = ";".join(exons)
                    elif (u.isBetween(pos, cdsStart, cdsEnd)):
                        for e in range(0, exonCount):
                            if u.isBetween(pos, int(exonsSt[e]), int(exonsEn[e])):
                                exnum = e + 1
                                if (strand == '-'):
                                    exnum = exonCount - e
                                exons.append("exon=" +  "ex" + \
                                    str(exnum) + '/' + str(exonCount))
                                exonic_count = exonic_count + 1
                        if (len(exons) > 0):
                            region = ";".join(exons)

                    elif (u.isBetween(pos, promoter_plus, txtStart) and 
                        (strand == "+")):
                        sql = 'select chrom, chromStart, chromEnd, name from ' + \
                            'cpgIslandExt where chrom="' + str(chr) + \
                            '" AND (chromStart <= ' + str(pos) + \
                            ' AND ' + str(pos) + ' <= chromEnd);'
                        cursor.execute(sql)
                        rows = cursor.fetchone()

                        if (rows is not None):
                            region = 'putativePromoterRegion=' + \
                                "".join(str(rows[3]).split())
                            promoter_count = promoter_count + 1

                    elif (u.isBetween(pos, txtEnd, promoter_minus) and (strand == "-")):
                        sql = 'select chrom, chromStart, chromEnd, name from ' + \
                            'cpgIslandExt where chrom="' + str(chr) + \
                            '" AND (chromStart <= ' + str(pos) + \
                            ' AND ' + str(pos) + ' <= chromEnd);'
                        cursor.execute(sql)

                        rows = cursor.fetchone()
                        if (rows is not None):
                            region = 'putativePromoterRegion=' +  \
                                "".join(str(rows[3]).split())
                            promoter_count = promoter_count + 1

                    else:
                        region = ''

                    if (region != ''):
                        info.append(collapseGeneNames(row=row, 
                            indices=indicesKnownGenes, region=region, cnt=cnt))

                    cnt = cnt + 1

                str_info = ";".join(info)
                fields[7] = fields[7] + ';' + str_info
                fh_out.write('\t'.join(fields) + '\n')

            else:
                fields[7] = fields[7] + ";positionType=interGenic"
                fh_out.write('\t'.join(fields) + '\n')
                interGenic_count = interGenic_count + 1

            linenum = linenum + 1

        else:
            fh_out.write(line + '\n')

    print("Variants located:")
    fh_log.write("Variants located:\n")

    print(f"In interGenic {str(interGenic_count)}")
    fh_log.write(f"In interGenic {str(interGenic_count)}\n")

    print(f"In CDS {str(cds_count)}")
    fh_log.write(f"In CDS {str(cds_count)}\n")

    print(f"In \'3 UTR {str(utr3_count)}")
    fh_log.write(f"In \'3 UTR {str(utr3_count)}\n")

    print(f"In \'5 UTR {str(utr5_count)}")
    fh_log.write(f"In \'5 UTR {str(utr5_count)}\n")

    print(f"In Intronic {str(intronic_count)}")
    fh_log.write(f"In Intronic {str(intronic_count)}\n")

    print(f"In Non_coding_intronic {str(non_coding_intronic_count)}")
    fh_log.write(f"In Non_coding_intronic {str(non_coding_intronic_count)}\n")

    print(f"In Exonic {str(exonic_count)}")
    fh_log.write(f"In Exonic {str(exonic_count)}\n")

    print(f"In Non_coding_exonic {str(non_coding_exonic_count)}")
    fh_log.write(f"In Non_coding_exonic {str(non_coding_exonic_count)}\n")

    print(f"In Putative Promoter Region {str(promoter_count)}")
    fh_log.write(f"In Putative Promoter Region {str(promoter_count)}\n")

    fh_out.close()
    fh_log.close()
    fh.close()
    conn.close()


"""Method used in INDELS, where bigRefGeneTable is not applicable
"""
def getExonsEtAl(vcf, format='vcf', table='refGene', promoter_offset=500, 
    tmpextin='.2', tmpextout='.3', sep='\t'):

    basefile = vcf
    vcf = basefile + tmpextin
    outfile = basefile + tmpextout
    fh_out = open(outfile, "w")

    logcountfile = basefile + '.count.log'
    fh_log = open(logcountfile, 'a')

    interGenic_count = 0
    cds_count = 0
    utr3_count = 0
    utr5_count = 0
    intronic_count = 0
    non_coding_intronic_count = 0
    exonic_count = 0
    non_coding_exonic_count = 0
    promoter_count = 0

    inds = getFormatSpecificIndices(format=format)
    fh = open(vcf)
    conn = u.db_connect()
    cursor = conn.cursor()
    linenum = 1

    for line in fh:
        line = line.strip()
        if not line.startswith("#"):
            fields = line.split(sep)
            chr = fields[inds[0]].strip()
            
            if not chr.startswith("chr"):
                chr = "chr" + chr
            
            pos = fields[inds[1]].strip()
            ref = clean_mysql_chars(fields[inds[2]]).strip()
            alt = clean_mysql_chars(fields[inds[3]]).strip()
            info_field = clean_mysql_chars(fields[7]).strip()
            this_gene_name = str(u.parse_field(info_field, 'name', ';', '='))

            sql = 'select * from ' + table + ' where chrom="' + str(chr) + \
                '"   AND (txStart - ' + str(promoter_offset) + ') <= ' + \
                str(pos) + ' AND ' + str(pos) + ' <= (txEnd + ' + \
                str(promoter_offset) +');'
            cursor.execute(sql)
            rows = cursor.fetchall()
            info = []
            if (len(rows) > 0):
                cnt = 1
                for row in rows:
                    txtStart = int(row[4])
                    txtEnd = int(row[5])
                    cdsStart = int(row[6])
                    cdsEnd = int(row[7])
                    exonCount = int(row[8])
                    exonStarts =str(row[9].decode('utf-8'))
                    exonEnds = str(row[10].decode('utf-8'))
                    geneSymbol = str(row[12])
                    strand = str(row[3])

                    promoter_plus = txtStart - int(promoter_offset)
                    promoter_minus = txtEnd + int(promoter_offset)
                    region = ""
                    pos = int(pos)
                    exons = []
                    exonsSt = exonStarts.split(',')
                    exonsEn = exonEnds.split(',')

                    if (cdsStart == cdsEnd):
                        for e in range(0, exonCount):
                            if (u.isBetween(pos, int(exonsSt[e]), int(exonsEn[e]))):
                                exnum = e + 1
                                if (strand == '-'):
                                    exnum =  exonCount - e
                                exons.append("non_coding_exon=" + "ex" + \
                                    str(exnum) + '/' + str(exonCount))
                                non_coding_exonic_count = non_coding_exonic_count + 1
                        if (len(exons) > 0):
                            region='positionType=non_coding_exon;' + ";".join(exons)
                        else:
                            non_coding_intronic_count = non_coding_intronic_count + 1
                            region = 'positionType=non_coding_intron'

                    elif (u.isBetween(pos, cdsStart, cdsEnd) and (cdsStart < cdsEnd)):
                        cds_count = cds_count + 1
                        for e in range(0, exonCount):
                            if (u.isBetween(pos, int(exonsSt[e]), int(exonsEn[e]))):
                                exnum = e + 1
                                if (strand == '-'):
                                    exnum =  exonCount - e
                                exons.append("exon=" + "ex" + \
                                    str(exnum) + '/' + str(exonCount))
                                exonic_count=exonic_count+1
                        if (len(exons) > 0):
                            region = 'positionType=CDS;' + ";".join(exons)
                        else:
                            intronic_count = intronic_count + 1
                            region = 'positionType=CDS;' + 'intron'

                    elif (u.isBetween(pos, txtStart, cdsStart) and \
                        (cdsStart < cdsEnd) and (strand == "+")):
                        utr5_count = utr5_count + 1
                        region = 'positionType=utr5'

                    elif (u.isBetween(pos, cdsEnd, txtEnd) and \
                        (cdsStart < cdsEnd) (strand == "+")):
                        utr3_count = utr3_count + 1
                        region = 'positionType=utr3'

                    elif (u.isBetween(pos, cdsEnd, txtEnd) and 
                        (cdsStart < cdsEnd) (strand == "-")):
                        utr5_count = utr5_count + 1
                        region = 'positionType=utr5'

                    elif (u.isBetween(pos, txtStart, cdsStart) and \
                        (cdsStart < cdsEnd) and (strand == "-")):
                        utr3_count = utr3_count + 1
                        region = 'positionType=utr3'

                    elif (u.isBetween(pos, promoter_plus, txtStart) and \
                        (strand == "+")):
                        sql = 'select chrom, chromStart, chromEnd, name ' + \
                            'from cpgIslandExt where chrom="' + str(chr) +  \
                            '" AND (chromStart <= ' + str(pos) + ' AND ' + \
                            str(pos) + ' <= chromEnd);'
                        cursor.execute(sql)
                        rows = cursor.fetchone()

                        if (rows is not None):
                            region = 'putativePromoterRegion=' + \
                                "".join(str(rows[3]).split())
                            promoter_count = promoter_count + 1

                    elif (u.isBetween(pos, txtEnd, promoter_minus) and \
                        (strand == "-")):
                        sql = 'select chrom, chromStart, chromEnd, name ' + \
                            'from cpgIslandExt where chrom="' + str(chr) + \
                            '" AND (chromStart <= ' + str(pos) + ' AND ' + \
                            str(pos) + ' <= chromEnd);'
                        cursor.execute(sql)
                        rows = cursor.fetchone()

                        if (rows is not None):
                            region = 'putativePromoterRegion=' + \
                            "".join(str(rows[3]).split())
                            promoter_count = promoter_count + 1

                    else:
                        region = ''

                    if (region != ''):
                        info.append(collapseGeneNames(
                            row=row, indices=indicesKnownGenes, 
                            region=region, cnt=cnt))

                    cnt = cnt + 1

                str_info = ";".join(info)
                fields[7] = fields[7] + ';' + str_info
                fh_out.write('\t'.join(fields) + '\n')

            else:
                fields[7] = fields[7] + ";positionType=interGenic"
                fh_out.write('\t'.join(fields) + '\n')
                interGenic_count = interGenic_count + 1

            linenum = linenum + 1

        else:
            fh_out.write(line + '\n')

    print("Variants located:")
    fh_log.write("Variants located:\n")

    print(f"In interGenic {str(interGenic_count)}")
    fh_log.write(f"In interGenic {str(interGenic_count)}\n")

    print(f"In CDS {str(cds_count)}")
    fh_log.write(f"In CDS {str(cds_count)}\n")

    print(f"In \'3 UTR {str(utr3_count)}")
    fh_log.write(f"In \'3 UTR {str(utr3_count)}\n")

    print(f"In \'5 UTR {str(utr5_count)}")
    fh_log.write(f"In \'5 UTR {str(utr5_count)}\n")

    print(f"In Intronic {str(intronic_count)}")
    fh_log.write(f"In Intronic "+str(intronic_count) +'\n')

    print(f"In Non_coding_intronic {str(non_coding_intronic_count)}")
    fh_log.write(f"In Non_coding_intronic {str(non_coding_intronic_count)}\n")

    print(f"In Exonic {str(exonic_count)}")
    fh_log.write(f"In Exonic {str(exonic_count)}\n")

    print(f"In Non_coding_exonic {str(non_coding_exonic_count)}")
    fh_log.write(f"In Non_coding_exonic {str(non_coding_exonic_count)}\n")

    print(f"In Putative Promoter Region {str(promoter_count)}")
    fh_log.write(f"In Putative Promoter Region {str(promoter_count)}\n")

    fh_out.close()
    fh_log.close()
    fh.close()
    conn.close()


"""Overlap with tfbsConsSites
"""
def addOverlapWithTfbsConsSites(vcf, format='vcf', table='tfbsConsSites', 
    tmpextin='.2', tmpextout='.3', sep='\t'):

    allowed_chrom=['1','2','3','4','5','6','7','8','9','10','11','12','13',
        '14','15','16','17','18','19','20','21','22','X','Y']

    basefile = vcf
    vcf = basefile + tmpextin
    outfile = basefile + tmpextout

    fh_out = open(outfile, "w")
    fh = open(vcf)

    logcountfile = basefile + '.count.log'
    fh_log = open(logcountfile, 'a')
    var_count = 0
    line_count = 0

    inds = getFormatSpecificIndices(format=format)
    conn = u.db_connect()
    cursor = conn.cursor()

    linenum = 1
    for line in fh:
        line = line.strip()
        ## not comments
        if (line.startswith("##")):
            fh_out.write(line + '\n')

        #header line
        elif (line.startswith('#CHROM') or line.startswith('CHROM')):
            fh_out.write(line + '\n')

        else:
            fields = line.split(sep)
            chr = fields[inds[0]].strip()
            # For some reason this table has no "chr" preceeding number
            if not chr.startswith("chr"):
                chr = "chr" + chr

            pos=fields[inds[1]].strip()
            isOverlap = False
            chrIndex=chr.replace('chr', '')

            if (chrIndex in allowed_chrom):
                isOverlap = False
                sql = 'select chrom, chromStart, chromEnd, name ' + \
                    'from tfbsConsSites' + chrIndex + \
                    ' where  chromStart <= ' + str(pos) + ' AND ' + \
                    str(pos) + ' <= chromEnd;'
                cursor.execute(sql)
                rows = cursor.fetchall()
                records = []

                if (len(rows) > 0):
                    records_count = 1
                    line_count = line_count + 1

                    for row in rows:
                        var_count = var_count + 1
                        t = str(row[3]) + '.' + str(row[0]) + '.' + \
                            str(row[1]) + '.' + str(row[2])
                        t = t.strip()
                        records.append('tfbsRegion' + '=' + t)
                        records_count = records_count + 1

                    if str(fields[7]).endswith(';'):
                        fields[7] = fields[7] + ';'.join(records)
                    else:
                        fields[7] = fields[7] + ';' + ';'.join(records)

                    fh_out.write('\t'.join(fields) + '\n')

                else: # chrom is not on the list
                    fh_out.write(line + '\n')

            else: # chrom is not on the list
                fh_out.write(line + '\n')

        linenum = linenum + 1

    fh_log.write(f"In {str(table)}: {str(var_count)} in " + \
        f"{str(line_count)} variants\n")
    fh_log.close()

    conn.close()
    fh.close()
    fh_out.close()


"""Overlap with GadAll table
"""
def addOverlapWithGadAll(vcf, format='vcf', table='gadAll', tmpextin='', 
    tmpextout='.1', sep='\t'):
    
    basefile = vcf
    vcf = basefile + tmpextin
    outfile = basefile + tmpextout

    fh_out = open(outfile, "w")
    fh = open(vcf)

    logcountfile = basefile+'.count.log'
    fh_log = open(logcountfile, 'a')
    var_count = 0
    line_count = 0

    inds = getFormatSpecificIndices(format=format)
    conn = u.db_connect()
    cursor = conn.cursor()
    linenum = 1

    for line in fh:
        line = line.strip()
        ## not comments
        if not line.startswith("##"):
            #header line
            if (line.startswith('CHROM') or line.startswith('#CHROM')):
                fh_out.write(line + '\n')
            else:
                fields = line.split(sep)
                chr = fields[inds[0]].strip()
                # For some reason this table has no "chr" preceeding number
                if chr.startswith("chr"):
                    chr = str(chr).replace("chr", "")

                pos = fields[inds[1]].strip()
                isOverlap = False

                sql = 'select * from ' + table + ' where chromosome="' + \
                    str(chr) + '" AND (chromStart <= ' + str(pos) + \
                    ' AND ' + str(pos) + ' <= chromEnd);'
                cursor.execute(sql)
                rows = cursor.fetchall()
                records = []

                if (len(rows) > 0):
                    records_count = 1
                    line_count = line_count + 1
                    r_tmp = []
                    for row in rows:
                        var_count = var_count + 1
                        if not fu.isOnTheList(r_tmp, str(row[3])):
                            r_tmp.append(str(row[3]) )
                            records.append(str(table) + '=' + str(row[3]))
                            records_count = records_count + 1
                    if str(fields[7]).endswith(';'):
                        fields[7] = fields[7] + ';'.join(records)
                    else:
                        fields[7] = fields[7] + ';' + ';'.join(records)
                    fh_out.write('\t '.join(fields) + '\n')
                else:
                    fh_out.write(line + '\n')

            linenum = linenum + 1
        else:
            fh_out.write(line + '\n')

    fh_log.write(f"In {str(table)}: {str(var_count)} in " + \
        f"{str(line_count)} variants\n")
    fh_log.close()

    conn.close()
    fh.close()
    fh_out.close()


""" Overlap with gwasCatalog table """
def addOverlapWithGwasCatalog(vcf, format='vcf', table='gwasCatalog', \
    tmpextin='', tmpextout='.1', sep='\t'):
    
    basefile = vcf
    vcf = basefile + tmpextin
    outfile = basefile + tmpextout

    fh_out = open(outfile, "w")
    fh = open(vcf)

    logcountfile = basefile+'.count.log'
    fh_log = open(logcountfile, 'a')
    var_count = 0
    line_count = 0

    inds = getFormatSpecificIndices(format=format)
    conn = u.db_connect()
    cursor = conn.cursor()
    linenum = 1

    for line in fh:
        line = line.strip()
        ## not comments
        if not line.startswith("##"):
            #header line
            if (line.startswith('CHROM') or line.startswith('#CHROM')):
                fh_out.write(line + '\n')
            else:
                fields = line.split(sep)
                chr = fields[inds[0]].strip()
                if not chr.startswith("chr"):
                    chr = "chr" + chr
                
                pos = fields[inds[1]].strip()
                isOverlap = False

                sql = 'select * from ' + table + ' where chrom="' + \
                    str(chr) + '" AND chromEnd = ' + str(pos) + ';'
                cursor.execute(sql)
                rows = cursor.fetchall()
                records = []

                if (len(rows) > 0):
                    line_count = line_count + 1
                    records_count = 1
                    for row in rows:
                        var_count = var_count + 1
                        records.append(str(table) + '=' + str('pubMedID') + \
                            '=' + str(row[5]) + ',trait=' + str(row[10]))
                        records_count = records_count + 1
                    if str(fields[7]).endswith(';'):
                        fields[7] = fields[7] + ';'.join(records)
                    else:
                        fields[7] = fields[7] + ';' + ';'.join(records)
                    fh_out.write('\t'.join(fields) + '\n')
                else:
                    fh_out.write(line + '\n')

            linenum = linenum + 1
        else:
            fh_out.write(line + '\n')

    fh_log.write(f"In {str(table)}: {str(var_count)} in " + \
        f"{str(line_count)} variants\n")
    fh_log.close()

    conn.close()
    fh.close()
    fh_out.close()


"""Overlap with HUGO Gene Nomenclature Committee (HGNC) table
"""
def addOverlapWitHUGOGeneNomenclature(vcf, format='vcf', table='hugo', 
    tmpextin='', tmpextout='.1', sep='\t'):
    
    basefile = vcf
    vcf = basefile + tmpextin
    outfile = basefile + tmpextout

    fh_out = open(outfile, "w")
    fh = open(vcf)

    logcountfile = basefile + '.count.log'
    fh_log = open(logcountfile, 'a')
    var_count = 0
    line_count = 0

    inds = getFormatSpecificIndices(format=format)
    conn = u.db_connect()
    cursor = conn.cursor()
    linenum = 1

    for line in fh:
        line = line.strip()
        ## not comments
        if not line.startswith("##"):
            #header line
            if (line.startswith('CHROM') or line.startswith('#CHROM')):
                fh_out.write(line + '\n')
            else:
                fields = line.split(sep)
                chr = fields[inds[0]].strip()
                if not chr.startswith("chr"):
                    chr = "chr" + chr

                pos=fields[inds[1]].strip()
                isOverlap = False

                sql = 'select * from ' + table + ' where chrom="' + \
                    str(chr) + '" AND (chromStart <= ' + str(pos) + \
                    ' AND ' + str(pos) + ' <= chromEnd);'
                cursor.execute(sql)
                rows = cursor.fetchall()
                records = []

                if (len(rows) > 0):
                    line_count = line_count + 1
                    records_count = 1
                    r_tmp = []
                    for row in rows:
                        var_count = var_count + 1
                        t = str(str(row[5]) + ',' + str(row[6])).strip()
                        if not fu.isOnTheList(r_tmp, t):
                            r_tmp.append(t)
                            records.append('HGNC_GeneAnnotation' + '=' + t)
                        records_count = records_count + 1

                    records_str = ','.join(records).replace(';', ',')

                    if str(fields[7]).endswith(';'):
                        fields[7] = fields[7] +records_str
                    else:
                        fields[7] = fields[7] + ';' + records_str
                    fh_out.write('\t'.join(fields) + '\n')
                else:
                    fh_out.write(line + '\n')

            linenum = linenum + 1
        else:
            fh_out.write(line + '\n')

    fh_log.write(f"In {str(table)}: {str(var_count)} in " + \
        f"{str(line_count)} variants\n")
    fh_log.close()

    conn.close()
    fh.close()
    fh_out.close()


"""Overlap with segdup regions genomicSuperDups
"""
def addOverlapWithGenomicSuperDups(vcf, format='vcf', 
    table='genomicSuperDups', tmpextin='', tmpextout='.1', sep='\t'):
    
    basefile = vcf
    vcf = basefile + tmpextin
    outfile = basefile + tmpextout

    fh_out = open(outfile, "w")
    fh = open(vcf)

    logcountfile = basefile + '.count.log'
    fh_log = open(logcountfile, 'a')
    var_count = 0
    line_count = 0

    inds = getFormatSpecificIndices(format=format)
    conn = u.db_connect()
    cursor = conn.cursor()
    linenum = 1

    for line in fh:
        line = line.strip()
        ## not comments
        if not line.startswith("##"):
            #header line
            if (line.startswith('CHROM') or line.startswith('#CHROM')):
                fh_out.write(line + '\n')
            else:
                fields = line.split(sep)
                chr = fields[inds[0]].strip()
                if not chr.startswith("chr"):
                    chr = "chr" + chr

                pos = fields[inds[1]].strip()
                isOverlap = False
                otherChrom = ''
                otherStart = ''
                otherEnd = ''
                l = str(isOverlap)

                sql = 'select * from ' + table + ' where chrom="'+ str(chr) + \
                    '" AND (chromStart <= ' + str(pos) + \
                    ' AND ' + str(pos) + ' <= chromEnd);'
                cursor.execute(sql)
                rows = cursor.fetchone()

                if rows is not None:
                    line_count = line_count + 1
                    var_count = var_count + 1
                    isOverlap = True
                    otherChrom = rows[7]
                    otherStart = rows[8]
                    otherEnd = rows[9]
                    fields[7] = fields[7] + ';' + str(table) + '=' + \
                        str(isOverlap) + ';' + 'otherChrom=' + \
                        str(otherChrom) + ';otherStart=' + \
                        str(otherStart) + ';otherEnd=' + str(otherEnd)

                fh_out.write('\t'.join(fields) + '\n')

            linenum = linenum + 1
        else:
            fh_out.write(line + '\n')

    fh_log.write(f"In {str(table)}: {str(var_count)} in " + \
        f"{str(line_count)} variants\n")
    fh_log.close()

    conn.close()
    fh.close()
    fh_out.close()


"""Searches Genes Databases and returns Genes/Cytobands 
   with which SNP or INDEL overlaps
"""
def addOverlapWithRefGene(vcf, format='vcf', table='refGene', 
    tmpextin='', tmpextout='.1', sep='\t'):
    
    basefile = vcf
    vcf = basefile + tmpextin
    outfile = basefile + tmpextout
    fh_out = open(outfile, "w")
    fh = open(vcf)

    logcountfile = basefile + '.count.log'
    fh_log = open(logcountfile, 'a')
    var_count = 0
    line_count = 0
    colindex = 1
    colindex2 = 12
    name = 'name'
    name2 = 'name2'
    startName = 'txStart'
    endName = 'txEnd'

    inds = getFormatSpecificIndices(format=format)
    conn = u.db_connect()
    cursor = conn.cursor()
    linenum = 1

    for line in fh:
        line = line.strip()
        ## not comments
        if not line.startswith("##"):
            #header line
            if (line.startswith('CHROM') or line.startswith('#CHROM')):
                fh_out.write(line + '\n')
            else:
                fields = line.split(sep)
                chr = fields[inds[0]].strip()
                if not chr.startswith("chr"):
                    chr = "chr" + chr

                pos = fields[inds[1]].strip()
                isOverlap = False
                
                sql = 'select * from ' + table + ' where chrom="' + \
                    str(chr) + '" AND (' + startName + ' <= ' + str(pos) + \
                    ' AND ' + str(pos) + ' <= ' + endName +');'
                overlapsWith = []
                cursor.execute(sql)
                rows = cursor.fetchall()

                if (len(rows) > 0):
                    line_count = line_count + 1
                    for row in rows:
                        var_count = var_count + 1
                        overlapsWith.append(name2 + '=' + \
                            str(row[colindex2]) + ';' + name + '=' + \
                            str(row[colindex]))

                    genes = ';'.join([str(x) for x in overlapsWith])
                    if str(fields[7]).endswith(";"):
                        fields[7] = fields[7] + str(genes)
                    else:
                        fields[7] = fields[7] + ';' + str(genes)
                fh_out.write('\t'.join(fields) + '\n')

            linenum = linenum + 1
        else:
            fh_out.write(line + '\n')

    fh_log.write(f"In {str(table)}: {str(var_count)} in " + \
        f"{str(line_count)} variants\n")
    fh_log.close()

    conn.close()
    fh.close()
    fh_out.close()


"""Method to find overlap with Cytoband table
"""
def addOverlapWithCytoband(vcf, format='vcf', table='cytoBand', 
    tmpextin='', tmpextout='.1', sep='\t'):
    
    basefile = vcf
    vcf = basefile + tmpextin
    outfile = basefile + tmpextout
    fh_out = open(outfile, "w")
    fh = open(vcf)

    logcountfile = basefile + '.count.log'
    fh_log = open(logcountfile, 'a')
    var_count = 0
    line_count = 0
    colindex = 12
    startName = 'txStart'
    endName = 'txEnd'

    if (table == 'cytoBand'):
        colindex = 3
        startName = 'chromStart'
        endName = 'chromEnd'

    inds = getFormatSpecificIndices(format=format)
    conn = u.db_connect()
    cursor = conn.cursor()
    linenum = 1

    for line in fh:
        line = line.strip()
        ## not comments
        if not line.startswith("##"):
            #header line
            if (line.startswith('CHROM') or line.startswith('#CHROM')):
                fh_out.write(line + '\n')
            else:
                fields = line.split(sep)
                chr = fields[inds[0]].strip()
                if not chr.startswith("chr"):
                    chr = "chr" + chr

                pos = fields[inds[1]].strip()
                isOverlap = False
                
                sql = 'select * from ' + table + ' where chrom="' + \
                    str(chr) + '" AND (' + startName + ' <= ' + str(pos) + \
                    ' AND ' + str(pos) + ' <= ' + endName + ');'
                overlapsWith = []
                cursor.execute(sql)
                rows = cursor.fetchall()

                if (len(rows) > 0):
                    line_count = line_count + 1
                    for row in rows:
                        var_count = var_count + 1
                        overlapsWith.append(str(row[colindex]))
                    overlapsWith = u.dedup(overlapsWith)
                    cytoband = ';'.join([str(x) for x in overlapsWith])

                    if str(fields[7]).endswith(";"):
                        fields[7] = fields[7] + str(table) + '=' + str(cytoband)
                    else:
                        fields[7] = fields[7] + ';' + str(table) + '=' + str(cytoband)
                fh_out.write('\t'.join(fields) + '\n')

            linenum = linenum + 1
        else:
            fh_out.write(line + '\n')

    fh_log.write(f"In {str(table)}: {str(var_count)} in " + \
        f"{str(line_count)} variants\n")
    fh_log.close()

    conn.close()
    fh.close()
    fh_out.close()


"""Method to find overlap with CNV tables
"""
def addOverlapWithCnvDatabase(vcf, format='vcf', table='dgv_Cnv', 
    tmpextin='', tmpextout='.1', sep='\t'):
    
    basefile = vcf
    vcf = basefile + tmpextin
    outfile = basefile + tmpextout

    fh_out = open(outfile, "w")
    fh = open(vcf)

    logcountfile = basefile + '.count.log'
    fh_log = open(logcountfile, 'a')
    var_count = 0
    line_count = 0

    inds = getFormatSpecificIndices(format=format)
    conn = u.db_connect()
    cursor = conn.cursor()
    linenum = 1

    for line in fh:
        line = line.strip()
        ## not comments
        if not line.startswith("##"):
            #header line
            if (line.startswith('CHROM') or line.startswith('#CHROM')):
                fh_out.write(line + '\n')
            else:
                fields = line.split(sep)
                chr = fields[inds[0]].strip()
                if not chr.startswith("chr"):
                    chr = "chr" + chr

                pos = fields[inds[1]].strip()
                isOverlap = False
                sql = 'select * from ' + table + ' where chrom="' + \
                    str(chr) + '" AND (chromStart <= ' + str(pos) + \
                    ' AND ' + str(pos) + ' <= chromEnd);'
                cursor.execute(sql)
                rows = cursor.fetchone()

                if rows is not None:
                    line_count = line_count + 1
                    var_count = var_count + 1
                    isOverlap = True
                    if str(fields[7]).endswith(";"):
                        fields[7] = fields[7] + str(table) + '=' + \
                        str(isOverlap)
                    else:
                        fields[7] = fields[7] + ';' + str(table) + \
                        '='+str(isOverlap)
                fh_out.write('\t'.join(fields) + '\n')

            linenum = linenum + 1
        else:
            fh_out.write(line + '\n')

    fh_log.write(f"In {str(table)}: {str(var_count)} in " + \
        f"{str(line_count)} variants\n")
    fh_log.close()

    conn.close()
    fh.close()
    fh_out.close()


"""Method to find overlap with targetScanS tables
"""
def addOverlapWithMiRNA(vcf, format='vcf', table='targetScanS', 
    tmpextin='', tmpextout='.1', sep='\t'):
    
    basefile = vcf
    vcf = basefile + tmpextin
    outfile = basefile + tmpextout

    fh_out = open(outfile, "w")
    fh = open(vcf)

    logcountfile = basefile + '.count.log'
    fh_log = open(logcountfile, 'a')
    var_count = 0
    line_count = 0

    inds = getFormatSpecificIndices(format=format)
    conn = u.db_connect()
    cursor = conn.cursor()
    linenum = 1

    for line in fh:
        line = line.strip()
        ## not comments
        if not line.startswith("##"):
            #header line
            if (line.startswith('CHROM') or line.startswith('#CHROM')):
                fh_out.write(line + '\n')
            else:
                fields = line.split(sep)
                chr = fields[inds[0]].strip()
                if not chr.startswith("chr"):
                    chr = "chr" + chr

                pos = fields[inds[1]].strip()
                sql = 'select * from ' + table + ' where chrom="' + \
                    str(chr) + '" AND (chromStart <= ' + str(pos) + \
                    ' AND ' + str(pos) + ' <= chromEnd);'
                cursor.execute(sql)
                rows = cursor.fetchone()

                if rows is not None:
                    line_count = line_count + 1
                    var_count = var_count + 1
                    t = str(rows[4]) + ',' +  str(rows[1]) + '_' + \
                        str(rows[2]) + '_' + str(rows[3])
                    t = 'miRNAsites=' + t.strip()
                    if str(fields[7]).endswith(";"):
                        fields[7] = fields[7] + t
                    else:
                        fields[7] = fields[7] + ';' + t
                fh_out.write('\t'.join(fields) + '\n')

            linenum = linenum + 1
        else:
            fh_out.write(line + '\n')

    fh_log.write(f"In miRNAsites: {str(var_count)} in " + \
        f"{str(line_count)} variants\n")
    fh_log.close()

    conn.close()
    fh.close()
    fh_out.close()

### EOF