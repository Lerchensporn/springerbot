#!env python2
# springerlink download script
# this script is released into the public domain

import sys
import argparse
import PyPDF2
import tempfile
from PyPDF2.generic import NameObject, createStringObject

import urllib
if sys.version_info < (3,0):
    from urllib import *
    from urllib2 import *
else:
    from urllib.request import *
    from urllib.error import HTTPError

def str_to_filename(string):
    mapping = [ ('\xc3\xbc', 'ue'), ('\xc3\xb6', 'oe'), ('\xc3\xa4', 'ae'), ('\xc3\u0178', 'ss')]
    for item in mapping:
        string.replace(item[0], item[1])
    for i in range(len(string)):
        if ord(string[i]) > 255:
            string[i] = '_'
    return string

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('doi', help='DOI of the book (the two numbers of the url)')
    parser.add_argument('--proxy', help='SOCKS proxy')
    parser.add_argument('--bibtex', action='store_true', help='only print bibtex entry')
    parser.add_argument('--output', help='output file name')
    parser.add_argument('--filename', help='default file name', choices=['isbn', 'title'])
    args = parser.parse_args()

    if args.proxy:
        try:
            import socks
        except ImportError:
            print('For proxy support download https://raw.github.com/Anorov/PySocks/master/socks.py')
            exit()

        import socket

        split = args.proxy.rsplit(':')
        if split[0] == 'localhost':
            split[0] = '127.0.0.1'
        if len(split) != 2:
            print('Invalid proxy parameter. It must be like "host:port".')
        socks.setdefaultproxy(socks.PROXY_TYPE_SOCKS5, split[0], int(split[1]))
        socket.socket = socks.socksocket

    link = 'http://link.springer.com/book/' + str(args.doi) + '/page/1'
#    print('Link: ' + link)
    try:
        html = str(urlopen(link).read())
    except:
        print('Page not found')
        return

    meta = get_meta(html)
    if args.bibtex:
        print_bibtex(meta)
        return

    filename = meta['isbn']
    if args.output:
        filename = output
    elif args.filename == 'title':
        filename = str_to_filename(meta['title'] + '. ' + meta['subtitle'])

    if (filename.find('.pdf') == -1):
        filename += '.pdf'

    print(meta['author'] + ': ' + meta['title'] + '. ' + meta['subtitle'] + '.')

    if html.find('<a class="access-link webtrekk-track"') != -1:
        print('Error: No download permission from this network.')
        exit()

    tmp = tempfile.mkdtemp()
    oldcwd = os.getcwd()
    os.chdir(tmp)
    chapters = download_chapters('http://link.springer.com/', args.doi, html)

    print('Writing %s' % filename)
    write_pdf(oldcwd + '/' + filename, chapters, meta)

    for chapter in chapters:
        os.remove(tmp + '/' + chapter[0])
    os.rmdir(tmp)

def download_chapters(base, doi, string):
    isbn = doi.rsplit('/')[1]
    chapname = ''

    def save_pdf(remote, path):
        total = int(remote.info().getheader('content-length'));
        downbytes = 0.0
        oldpercent = 0
        fp = open(str(path), 'wb')
        blocksize = 1024;
        while True:
            block = remote.read(blocksize)
            if not block:
                print('')
                break;
            downbytes += len(block)
            percent = int(downbytes / total * 100.)
            if percent > oldpercent:
                sys.stdout.write('\x1b[s:: ' + chapname + ' (' + str(percent).rjust(3) + ' %)\x1b[u')
                sys.stdout.flush()
                oldpercent = percent
            fp.write(block)
        fp.close()

    def filesize(key):
        find_between(string, key + '')

    chapters = list()
    chapname = 'front matter'
    try:
        key = '/content/pdf/bfm:' + str(isbn) + '/1'
        remote = urlopen(base + key)
        if remote.getcode() == 404:
            raise Exception
        save_pdf(remote, 'front-matter')
        chapters.append([ 'front-matter', None ])
    except:
        print('No front matter found')
        exit()

    chapname = 'back matter'
    try:
        key = '/content/pdf/bbm:' + str(isbn) + '/1'
        remote = urlopen(base + key)
        if remote.getcode() == 404:
            raise Exception
        save_pdf(remote, 'back-matter')
    except:
        print('No back matter found')
        exit()

    i = 1
    while True:
        try:
            key = str(doi) + '_' + str(i)
            remote = urlopen(base + '/content/pdf/' + key)
            if remote.getcode() == 404 or remote.info().getheader('content-type') != 'application/pdf':
                raise Exception
            title = find_between(string, '<a href="/chapter/' + key + '">', '</a>')
            chapters.append([ str(i), str(title) ])
            chapname = title
            save_pdf(remote, i)
            i += 1
        except:
            break

    chapters.append([ 'back-matter', None ])
    return chapters

def uni(string):
    return string.decode('utf-8')

def write_pdf(filename, chapters, meta):
    output = PyPDF2.PdfFileWriter()
    info = output._info.getObject()
    info.update({
        NameObject('/Title') : createStringObject(uni(meta['title'])),
        NameObject('/Author') : createStringObject(uni(meta['author'])),
        NameObject('/Creator') : createStringObject('springer.py')
    })

    page = 0
    for chapter in chapters:
        inp = PyPDF2.PdfFileReader(open(chapter[0], 'rb'))
        for i in range(inp.getNumPages()):
            output.addPage(inp.getPage(i))
        if chapter[1] != None:
            output.addBookmark(uni(chapter[1]), page)
        page += inp.getNumPages()

    fp = file(filename, 'wb')
    output.write(fp)
    fp.close()

def get_meta(string):
    meta = { }
    meta['doi'] = get_dd_content(string, 'abstract-about-book-online-doi')
    meta['isbn'] = get_dd_content(string, 'abstract-about-book-online-isbn')
    meta['year'] = get_dd_content(string, 'abstract-about-book-chapter-copyright-year')
    meta['title'] = get_dd_content(string, 'abstract-about-title')
    meta['subtitle'] = get_dd_content(string, 'abstract-about-book-subtitle')
    meta['doi'] = get_dd_content(string, 'abstract-about-book-chapter-doi')
    meta['publisher'] = get_dd_content(string, 'abstract-about-publisher')

    author = find_between(string, '<ul class="authors">', '</ul>')
    start = author.find('<li class="show-all-hide-authors">')
    author = re.sub('<.*?>', '', author[0:start])
    meta['author'] = author.strip()

    return meta

def find_between(hay, n1, n2):
    start = hay.find(n1)
    end = hay.find(n2, start)
    if start == -1 or end == -1:
        return ''
    return hay[start + len(n1):end]

def get_dd_content(string, attr):
    return find_between(string, '<dd id="' + attr + '">', '</dd>')

def print_meta(meta):
    print(meta['author'] + ': ' + meta['title'] + '. ' + meta['subtitle'] + '. ' + meta['publisher'] + ', ' + meta['year'] + '.')

def print_bibtex(meta):
    print('@book{<ref>,')
    fields = [ 'author', 'title', 'subtitle', 'publisher', 'year', 'isbn', 'doi' ]
    for item in fields:
        line = '    ' + item + ' = {' + meta[item] + '}'
        if item != fields[-1]:
            line += ','
        print(line)
    print('}')


if __name__ == '__main__':
    main()
