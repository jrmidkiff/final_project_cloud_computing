# file_utils.py
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

import os.path
import linecache
import csv
import os
import shutil
import sys

import itertools, operator

"""Execute command
"""
def execute(com, debug=False):
    if debug:
        print(com)
    os.system(com)


"""Linear search, returns first index
"""
def find_first_index(lst, elem):
    ind = 0
    for l in lst:
        if (str(elem).strip() == str(l).strip()):
            return ind
        ind = ind + 1

    return -1


"""Returns True or False 
"""
def isOnTheList(theList, theElement):
    theList = map(str, theList)
    return str(theElement) in theList


"""Removes NA
"""
def rmNA(intstr):
    if ((intstr == 'NA') or (intstr == 'NaN')):
        return 0
    else:
        return int(float(intstr))


"""Check whether 'str' contains ANY of the chars in 'set'
"""
def containsAny(str, set):
    return (1 in [c in str for c in set])


"""Check whether 'str' contains ALL of the chars in 'set'
"""
def containsAll(str, set):
    return (0 not in [c in str for c in set])


def contains(theString, theQueryValue):
  return (theString.find(theQueryValue) > -1)


def str2bool(v):
  return (v.lower() in ["y", "yes", "true", "t", "1"])


def isExist(filename):
    if (os.path.exists(filename) and os.path.isfile(filename)):
        return True
    else:
        return False


def fileSize(filename):
    return int(os.path.getsize(filename))


def delete(filename):
    if (os.path.exists(filename) and os.path.isfile(filename)):
        os.unlink(filename)


"""Makes directory if it does not exist
"""
def mkdirp(directory):
    if not os.path.isdir(directory):
        os.makedirs(directory)


"""Extracts column specified by column index
   Assumes that first row as a header
"""
def get_column(path, c=0, r=1, sep='\t'):
    try:
        reader = csv.reader(open(path, "r"), delimiter=sep)
        return [row[c] for row in reader] [r :]
    except IOError:
        print(f"list_rows: file '{path}' does not exist")
        return 'list_rows failed'


"""Load the file as a list of strings lines
"""
def loadFile(filename):
    fh = open(filename, "r")
    lines = []

    for line in fh:
        line = line.strip()
        lines.append(line)
    return lines


"""Loads CNV table
   By default first row (zero based) is a header and
   pound sign is a comment character
"""
def loadTable(filename, headerrow=0, commentchar='#'):
    fh = open(filename, "r")
    lines = []
    count = 0
    for line in fh:
        line = line.strip()
        if line.startswith(commentchar) == False and \
            len(line) > 0 and count > headerrow:
            lines.append(line)
        count = count + 1
    return lines


"""Extracts column specified by column index
   Assumes that first row as a header
"""
def get_int_column(path, c=0, r=1, sep='\t'):

    try:
        reader = csv.reader(open(path, "r"), delimiter=sep)
        return [int(row[c]) for row in reader] [r :]
    except IOError:
        print(f"list_rows: file '{path}' does not exist")
        return 'list_rows failed'


def read_one_int_col(filename):
    fh = open(filename, "r")
    values = []
    for line in fh:
        values.append(int(line.strip('\r\n')))
    return values


def read_one_float_col(filename):
    fh = open(filename, "r")
    values = []
    for line in fh:
        values.append(float(line.strip()))
    return values


def read_one_str_col(filename):
    fh = open(filename, "r")
    values = []
    for line in fh:
        line = line.strip()
        if (len(line) > 0):
            values.append(line.strip())
    return values


def get_index_of_col_or_row(lst, value):
    try:
        return lst.index(value)
    except:
        print(f"get_index_of_col_or_row: value not found '{value}'")
        return -1


def array2str(array, sep='\t'):
    strA = []
    for a in array:
        strA.append(str(a))
    return sep.join(strA)


def array2header(array, sep='\t'):
    strA = ["samples"]
    for a in array:
        strA.append('p' + str(a))
    return sep.join(strA)


def readindices(filename, sep='\t'):
    fh = open(filename, "r")
    values = []
    for line in fh:
        line = line.strip('\n')
        if (len(line) > 0):
            if (len(line.split(sep)) == 1):
                values.append(int(line))
            else:
                start = int(line.split(sep)[0])
                end = int(line.split(sep)[1])
                while (start <= end):
                    values.append(start)
                    start = start + 1

    return sorted(values)


""""Count number of lines in file, file is not loaded to memory
"""
def linecount(filename):
    fh = open(filename, "r")
    linenum = 0
    for line in fh:
        linenum = linenum + 1
    return linenum


"""Saves list of rows and columns in a text file
"""
def save2txt(read_data, txtfile, compress=False, debug=True):
    try:
        f = open(txtfile, 'w')
        tmp = array2str(array=read_data, sep='\n')
        f.write(tmp)
        if compress:
            os.system('gzip ' + str (txtfile) )
        if debug:
            print ("Written " + str(txtfile) )
    except IOError:
        print(f"save2txt: can not write to file '{file}'")
        return 'save_list_of_str failed'
    finally:
        f.close()

### EOF