#!/usr/bin/env python
# -*- coding: utf-8 -*-
## wkt_downloader.py
## A helpful tool to fetch data from website & generate mdx source file
##
## This program is a free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation, version 3 of the License.
##
## You can get a copy of GNU General Public License along this program
## But you can always get it from http://www.gnu.org/licenses/gpl.txt
##
## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
## GNU General Public License for more details.
import os
import re
import time
import urllib
import random
import string
import shutil
import fileinput
import requests
from os import path
from datetime import datetime
from multiprocessing import Pool
from multiprocessing import Manager
from collections import OrderedDict


MAX_PROCESS = 25
STEP = 8000
F_WORDLIST = 'wordlist.txt'
ORIGIN = 'https://en.wiktionary.org/wiki/'
_DEBUG_ = 1


def fullpath(file, suffix='', base_dir=''):
    if base_dir:
        return ''.join([os.getcwd(), path.sep, base_dir, file, suffix])
    else:
        return ''.join([os.getcwd(), path.sep, file, suffix])


def readdata(file, base_dir=''):
    fp = fullpath(file, base_dir=base_dir)
    if not path.exists(fp):
        print("%s was not found under the same dir of this tool." % file)
    else:
        fr = open(fp, 'rU')
        try:
            return fr.read()
        finally:
            fr.close()
    return None


def dump(data, file, mod='w'):
    fname = fullpath(file)
    fw = open(fname, mod)
    try:
        fw.write(data)
    finally:
        fw.close()


def removefile(file):
    if path.exists(file):
        os.remove(file)


def randomstr(digit):
    return ''.join(random.sample(string.ascii_letters, 1)+
        random.sample(string.ascii_letters+string.digits, digit-1))


def info(l, s='word'):
    return '%d %ss' % (l, s) if l>1 else '%d %s' % (l, s)


def fix_c(c):
    return c.replace('%', '%25').replace('/', '%2F').replace('&', '%26').replace('\'', '%27').replace('?', '%3F')


def getwordlist(file, base_dir='', tolower=False):
    words = readdata(file, base_dir)
    if words:
        wordlist = []
        p = re.compile(r'\s*\n\s*')
        words = p.sub('\n', words).strip()
        for word in words.split('\n'):
            try:
                w, u = word.split('\t')
                if tolower:
                    wordlist.append((w.strip().lower(), u.strip().lower()))
                else:
                    wordlist.append((w, u))
            except Exception, e:
                import traceback
                print traceback.print_exc()
                print word
        return wordlist
    print("%s: No such file or file content is empty." % file)
    return []


def getpage(link, BASE_URL=''):
    r = requests.get(''.join([BASE_URL, link]), timeout=10, allow_redirects=False)
    if r.status_code == 200:
        return r.content
    else:
        return None


class downloader:
#common logic
    def __init__(self, name):
        self.__session = None
        self.DIC_T = name

    @property
    def session(self):
        return self.__session

    def login(self, REF=''):
        HEADER = 'Mozilla/5.0 (Windows NT 5.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/37.0.2062.102 Safari/537.36'
        self.__session = requests.Session()
        self.__session.headers['User-Agent'] = HEADER
        self.__session.headers['Origin'] = ORIGIN
        self.__session.headers['Referer'] = REF

    def __mod(self, flag):
        return 'a' if flag else 'w'

    def __dumpwords(self, sdir, words, sfx='', finished=True):
        f = fullpath('rawhtml.txt', sfx, sdir)
        if len(words):
            mod = self.__mod(sfx)
            fw = open(f, mod)
            try:
                [fw.write('\n'.join([en[0], en[1], '</>\n'])) for en in words]
            finally:
                fw.close()
        elif not path.exists(f):
            fw = open(f, 'w')
            fw.write('\n')
            fw.close()
        if sfx and finished:
            removefile(fullpath('failed.txt', '', sdir))
            l = -len(sfx)
            cmd = '\1'
            nf = f[:l]
            if path.exists(nf):
                msg = "Found rawhtml.txt in the same dir, delete?(default=y/n)"
                cmd = 'y'#raw_input(msg)
            if cmd == 'n':
                return
            elif cmd != '\1':
                removefile(nf)
            os.rename(f, nf)

    def __fetchdata_and_make_mdx(self, arg, part, suffix=''):
        sdir, d_app, d_w = arg['dir'], OrderedDict(), OrderedDict(part)
        words, crefs, count, logs, failed = [], OrderedDict(), 1, [], []
        leni = len(part)
        while leni:
            for url, cur in part:
                if count % 100 == 0:
                    print ".",
                    if count % 1000 == 0:
                        print count,
                try:
                    page = getpage(self.makeurl(url))
                    if page:
                        if self.makeword(page, cur, words, logs, d_app):
                            crefs[cur] = url
                            count += 1
                    else:
                        failed.append((url, cur))
                except Exception, e:
                    import traceback
                    print traceback.print_exc()
                    print "%s failed, retry automatically later" % cur
                    failed.append((url, cur))
            lenr = len(failed)
            if lenr >= leni:
                break
            else:
                leni = lenr
                part, failed = failed, []
        print "%s browsed" % info(count-1),
        if crefs:
            mod = self.__mod(path.exists(fullpath('cref.txt', base_dir=sdir)))
            dump(''.join(['\n'.join(['\t'.join([k, v]) for k, v in crefs.iteritems()]), '\n']), ''.join([sdir, 'cref.txt']), mod)
        d_app2 = OrderedDict()
        for k in d_app.keys():
            if not k in d_w:
                d_app2[k] = d_app[k]
        if d_app2:
            mod = self.__mod(path.exists(fullpath('appd.txt', base_dir=sdir)))
            dump(''.join(['\n'.join(['\t'.join([k, v]) for k, v in d_app2.iteritems()]), '\n']), ''.join([sdir, 'appd.txt']), mod)
        if failed:
            dump(''.join(['\n'.join(['\t'.join([w, u]) for w, u in failed]), '\n']), ''.join([sdir, 'failed.txt']))
            self.__dumpwords(sdir, words, '.part', False)
        else:
            print ", 0 word failed"
            self.__dumpwords(sdir, words, suffix)
        if logs:
            mod = self.__mod(path.exists(fullpath('log.txt', base_dir=sdir)))
            dump('\n'.join(logs), ''.join([sdir, 'log.txt']), mod)
        return len(crefs), d_app2

    def start(self, arg):
        import socket
        socket.setdefaulttimeout(120)
        import sys
        reload(sys)
        sys.setdefaultencoding('utf-8')
        sdir = arg['dir']
        fp1 = fullpath('rawhtml.txt.part', base_dir=sdir)
        fp2 = fullpath('failed.txt', base_dir=sdir)
        fp3 = fullpath('rawhtml.txt', base_dir=sdir)
        if path.exists(fp1) and path.exists(fp2):
            print ("Continue last failed")
            failed = getwordlist('failed.txt', sdir)
            return self.__fetchdata_and_make_mdx(arg, failed, '.part')
        elif not path.exists(fp3):
            print ("New session started")
            return self.__fetchdata_and_make_mdx(arg, arg['alp'])

    def getcreflist(self, file, base_dir=''):
        words = readdata(file, base_dir)
        if words:
            p = re.compile(r'\s*\n\s*')
            words = p.sub('\n', words).strip()
            crefs = OrderedDict()
            for word in words.split('\n'):
                k, v = word.split('\t')
                crefs[k] = k
                crefs[v] = k
            return crefs
        print("%s: No such file or file content is empty." % file)
        return OrderedDict()

    def combinefiles(self, dir, args):
        times = 0
        for d in os.listdir(fullpath(dir)):
            if re.compile(r'^\d+$').search(d) and path.isdir(fullpath(''.join([dir, d, path.sep]))):
                times += 1
        dtp = ''.join([dir, 'data', path.sep])
        for imgdir in [fullpath(''.join([dir, 'v'])), fullpath(dtp),
        fullpath(''.join([dtp, 'p'])), fullpath(''.join([dtp, 'v']))]:
            if not path.exists(imgdir):
                os.mkdir(imgdir)
        print "combining files..."
        for fn in ['cref.txt', 'log.txt']:
            fw = open(fullpath(''.join([dir, fn])), 'w')
            for i in xrange(1, times+1):
                sdir = ''.join([dir, '%d'%i, path.sep])
                if path.exists(fullpath(fn, base_dir=sdir)):
                    fw.write('\n'.join([readdata(fn, sdir).strip(), '']))
            sdir = ''.join([dir, 'patch', path.sep])
            if path.exists(fullpath(fn, base_dir=sdir)):
                fw.write('\n'.join([readdata(fn, sdir).strip(), '']))
            fw.close()
        words, logs, buf = [], [], []
        self.set_repcls()
        self.localize, self.shrink, self.svg2png = args.local, '', args.svg2png
        if args.pngquant:
            exe = fullpath('pngquant.exe')
            if path.exists(exe):
                self.shrink = exe
        self.crefs = self.getcreflist('cref.txt', dir)
        self.clstbl, self.imgidx = OrderedDict(), OrderedDict()
        self.index, self.need_fix = Manager().dict(), OrderedDict()
        self.patch_keys, patch = self.load_patch(dir, words, logs)
        pool, params = Pool(2), []
        for i in xrange(1, times+1):
            params.append((self, ''.join([dir, '%d'%i, path.sep])))
        dics = pool.map(formatter, params)
        file = ''.join([dir, self.DIC_T, path.extsep, 'txt'])
        dump(''.join(patch), file)
        for i in xrange(1, times+1):
            sdir = ''.join([dir, '%d'%i, path.sep])
            text = readdata('formatted.txt', base_dir=sdir)
            if text:
                dump(text, file, 'a')
                os.remove(fullpath('formatted.txt', base_dir=sdir))
        if self.index:
            print "copying images at %s ..." % datetime.now()
            self.copy_images()
        for dic, word in dics:
            words.extend(word)
            self.imgidx.update(dic.imgidx)
            self.clstbl.update(dic.clstbl)
            if _DEBUG_:
                self.need_fix.update(dic.need_fix)
        print "%s totally" % info(len(words))
        dump('\n'.join(words), ''.join([dir, 'words.txt']))
        if logs:
            mod = self.__mod(path.exists(fullpath('log.txt', base_dir=dir)))
            dump('\n'.join(logs), ''.join([dir, 'log.txt']), mod)
        if self.imgidx:
            dump(''.join(['\n'.join(['\t'.join([k, v[0]]) for k, v in self.imgidx.iteritems()]), '\n']), ''.join([dir, 'image_index.txt']))
        if self.clstbl:
            del buf[:]
            for k, v in self.clstbl.iteritems():
                buf.append(k)
                for c, r in v.iteritems():
                    buf.append(''.join([' \'', c, '\': \'', r, '\',']))
            dump('\n'.join(buf), ''.join([dir, 'cls.txt']))
        if _DEBUG_:
            if self.need_fix:
                dump(''.join(['\n'.join(['\n'.join([k, v, '</>']) for k, v in self.need_fix.iteritems()]), '\n']), ''.join([dir, 'check_cls.txt']))
                dump(''.join(['\n'.join(['\t'.join([k.replace(' ', '_'), k]) for k, v in self.need_fix.iteritems()]), '\n']), ''.join([dir, 'wordlist.txt']))
            uk, ue = [{}, {}], [OrderedDict(), OrderedDict()]
            for k, v in self.imgidx.iteritems():
                for i in xrange(0, 2):
                    if v[i] in uk[i]:
                        ue[i][k] = v[i]
                        ue[i][uk[i][v[i]]] = v[i]
                    else:
                        uk[i][v[i]] = k
            print len(ue[0]), ',', len(ue[1])
            for i in xrange(0, 2):
                if ue[i]:
                    dump(''.join(['\n'.join(['\t'.join([v, k]) for k, v in ue[i].iteritems()]), '\n']), ''.join([dir, 'check_image', str(i), '.txt']))


def f_start((obj, arg)):
    return obj.start(arg)


def formatter((dic, sdir)):
    words, logs, fmtd = [], [], []
    file = ''.join([sdir, 'formatted.txt'])
    fmtd = dic.load_file(sdir, words, logs)
    if fmtd:
        dump(''.join(fmtd), file)
    print sdir
    return dic, words


def multiprocess_fetcher(dir, d_refs, wordlist, obj, base):
    times = int(len(wordlist)/STEP)
    pl = [wordlist[i*STEP: (i+1)*STEP] for i in xrange(0, times)]
    pl.append(wordlist[times*STEP:])
    times = len(pl)
    fdir = fullpath(dir)
    if not path.exists(fdir):
        os.mkdir(fdir)
    for i in xrange(1, times+1):
        subdir = ''.join([dir, '%d'%(base+i)])
        subpath = fullpath(subdir)
        if not path.exists(subpath):
            os.mkdir(subpath)
    imgdir = fullpath(''.join([dir, 'p']))
    if not path.exists(imgdir):
        os.mkdir(imgdir)
    pool, n = Pool(MAX_PROCESS), 1
    d_app = OrderedDict()
    while n:
        args = []
        for i in xrange(1, times+1):
            sdir = ''.join([dir, '%d'%(base+i), path.sep])
            file = fullpath(sdir, 'rawhtml.txt')
            if not(path.exists(file) and os.stat(file).st_size):
                param = {}
                param['alp'] = pl[i-1]
                param['dir'] = sdir
                args.append((obj, param))
        if len(args) > 0:
            vct = pool.map(f_start, args)#[f_start(args[0])]#for debug
            n = 0
            for count, dt in vct:
                n += count
                d_app.update(dt)
        else:
            break
    dt = OrderedDict()
    for k, v in d_app.iteritems():
        if not k in d_refs:
            dt[k] = v
    return times, dt.items()


class wkt_downloader(downloader):
#wiktionary downloader
    def __init__(self):
        downloader.__init__(self, 'WKT')
        self.__base_url = ORIGIN
        self.__re_d = {re.I: {}, 0: {}}

    def makeurl(self, cur):
        return ''.join([self.__base_url, cur])

    def __rex(self, ptn, mode=0):
        if ptn in self.__re_d[mode]:
            pass
        else:
            self.__re_d[mode][ptn] = re.compile(ptn, mode) if mode else re.compile(ptn)
        return self.__re_d[mode][ptn]

    def __repcls(self, m):
        tag = m.group(1)
        cls = m.group(3)
        if tag in self.__trs_tbl and cls in self.__trs_tbl[tag]:
            return ''.join([tag, m.group(2), self.__trs_tbl[tag][cls]])
        else:
            return m.group(0)

    def cleansp(self, html):
        p = self.__rex(r'\s{2,}')
        html = p.sub(' ', html)
        p = self.__rex(r'\s*<br/?>\s*')
        html = p.sub('<br>', html)
        p = self.__rex(r'(\s*<br>\s*)*(<(?:/?(?:div|p|ul|ol|li|hr)[^>]*|br)>)(\s*<br>\s*)*', re.I)
        html = p.sub(r'\2', html)
        p = self.__rex(r'(\s*<br>\s*)*(<(?:/?(?:div|p)[^>]*|br)>)(\s*<br>\s*)*', re.I)
        html = p.sub(r'\2', html)
        p = self.__rex(r'(?:\s|&#160;)*(<(?:/?(?:div|p|ul|ol|li|table|tr)[^>]*|br)>)(?:\s|&#160;)*', re.I)
        html = p.sub(r'\1', html)
        p = self.__rex(r'(?<=[^,])\s+(?=[,;\?]|\.(?:[^\d\.]|$))')
        html = p.sub(r'', html)
        return html

    def __preformat(self, page):
        page = page.replace('\xC2\xA0', ' ')
        p = self.__rex(r'[\n\r]+(\s+[\n\r]+)?')
        page = p.sub(' ', page)
        n = 1
        while n:
            p = self.__rex(r'\t+|&(?:nb|en|em|thin)sp;|\s{2,}')
            page, n = p.subn(r' ', page)
        p = self.__rex(r'(</?)strong(?=[^>]*>)')
        page = p.sub(r'\1b', page)
        return page

    def __fix_nm(self, url, nm):
        p = self.__rex('commons/thumb/(\w+/\w+/)', re.I)
        m = p.search(url)
        if m:
            nm = ''.join([m.group(1).replace('/', '_'), nm])
        if len(nm) > 150:
            nm = nm[:150].replace('%', '')
        return nm

    def __fix_ext(self, ext):
        pos = ext.rfind('?')
        if pos > 0:
            ext = ext[:pos]
        return ext

    def __dl_img(self, p, div, dest, header=''):
        for url, file in p.findall(div):
            name, ext = path.splitext(file)
            name, ext = self.__fix_nm(url, name), self.__fix_ext(ext)
            file = ''.join([self.DIC_T, path.sep, dest, path.sep, name, ext])
            if not path.exists(fullpath(file)):
                fc = 0
                while fc < 20:
                    try:
                        img = getpage(url, header)
                        dump(img, file, 'wb')
                        break
                    except Exception, e:
                        fc += 1
                if fc == 20:
                    raise AssertionError("Can't download %s" % url)

    def __get_img(self, p, worddef):
        q = self.__rex(r'<img\b[^<>]*src="(//[^<>"]+?/([^<>"/]+))"', re.I)
        for div in p.findall(worddef):
            self.__dl_img(q, div, 'p', 'https:')

    def makeword(self, page, word, words, logs, d_app):
        exist = False
        page = self.__preformat(page)
        p = self.__rex(r'<h1 id="firstHeading"[^<>]*>.+?</h1>', re.I)
        m1 = p.search(page)
        p = self.__rex(r'<h2>\s*<span class="mw-headline" id="English">.+?</h2>\s*(.+?)\s*(?=<h2\b|<noscript)', re.I)
        m2 = p.search(page)
        if not m2:
            p = self.__rex(r'<h2>\s*<span class="mw-headline" id="Translingual">.+?</h2>\s*(.+?)\s*(?=<h2\b|<noscript)', re.I)
            m2 = p.search(page)
        if m1 and m2:
            worddef = ''.join([m1.group(0), m2.group(1)])
            p = self.__rex(r'<img\b[^<>]*src="(https?://[^<>"]+?/svg/([^<>"/]+))"', re.I)
            self.__dl_img(p, worddef, 'v')
            p = self.__rex(r'<div class="(?:thumb (?:tright|tnone|tleft|tmulti tright)|floatright|tright)"[^<>]*>(.+?)\s*(?=<h\d|$)', re.I)
            self.__get_img(p, worddef)
            p = self.__rex(r'(<table (?:class="(?:floatright|toc|metadata mbox-small)"|align="right").+?)\s*(?=<h\d|$)', re.I)
            self.__get_img(p, worddef)
            p = self.__rex(r'(?<=<ul class="gallery mw-gallery-traditional")(.+?)(?=</ul>)', re.I)
            self.__get_img(p, worddef)
            words.append([word, worddef])
            exist = True
        else:
            logs.append("I01:\t'%s' is not found in En-Wiktionary" % word)
        return exist

    def load_file(self, sdir, words, logs, is_patch=False):
        file, buf = fullpath('rawhtml.txt', base_dir=sdir), []
        if not path.exists(file):
            print "%s does not exist" % file
            return []
        lns = []
        for ln in fileinput.input(file):
            ln = ln.strip()
            if ln == '</>':
                if is_patch or not lns[0] in self.patch_keys:
                    buf.append(self.format(lns[0], lns[1], logs))
                    words.append(lns[0])
                del lns[:]
            elif ln:
                lns.append(ln)
        return buf

    def load_patch(self, dir, words, logs):
        sdir = ''.join([dir, 'patch', path.sep])
        buf, keys = self.load_file(sdir, words, logs, True), OrderedDict()
        for w in words:
            keys[w] = None
        if path.exists(fullpath(sdir)):
            dump(''.join(['\n'.join(['\t'.join([k, urllib.quote(k.replace(' ', '_'))]) for k, v in keys.iteritems()]), '\n']), ''.join([sdir, 'cref.txt']))
        return keys, buf

    def set_repcls(self):
        self.__trs_tbl = {'div': {'thumbinner': 'ymp', 'tright': 'ggs',
        'floatleft': 'nwh', 'floatright': 'ouf', 'disambig-see-also': 'szh',
        'thumbcaption': 'b9i', 'center': 'pdi', 'thumb tleft': 'eky',
        'tsingle': 'fjk', 'thumbimage': 'npg', 'CategoryTreeChildren': 'bu9',
        'NavFrame': 'exc', 'NavHead': 'bss', 'poem': 'dje', 'CategoryTreeItem': 'bzr',
        'citation-whole': 'azl', 'mediaContainer': 'a0p', 'CategoryTreeSection': 'c5f',
        'disambig-see-also-2': 'xds', 'derivedterms CategoryTreeTag': 'zyn',
        'noresize': 'lbf', 'gallerytext': 'qfk', 'thumb': 'dep', 'floatnone': 'u49',
        'haudio': 'nnp', 'wiktQuote': 'hcr', 'description': 'b23', 'fn': 'pnf',
        'vsSwitcher vsToggleCategory-pronunciations': 'ei1', 'vsShow': 'mjw',
        'vsHide': 'aty', 'templatequotecite': 'z58'},
        'h1': {'firstHeading': 'bxr'}, 'blockquote': {'templatequote': 'hte'},
        'span': {'IPA': 'm8r', 'AHD enPR': 'gbf', 'Latn': 'nyr', 'defdate': 'oxq',
        'mw-headline': 'tsr', 'tr mention-tr': 'saf', 'see-cites': 'b0f', 'Latf': 'w8x',
        'mention-gloss': 'vw0', 'etylcleanup': 'mcq', 'use-with-mention': 'bk3',
        'reference-text': 'r8l', 'mw-cite-backlink': 'vev', 'plainlinks': 'rsb',
        'cited-source': 'ceq', 'cited-passage': 'q0e', 'Latinx': 'qyc', 'gender': 'fmr',
        'etyl': 'wmb', 'ib-content': 'ta8', 'biota': 'nia', 'gloss-content': 'axy',
        'mention-gloss-paren': 'eil', 'Jpan': 'geb', 'Hani': 'fzx', 'Brai': 'ck1',
        'Arab': 'msy', 'mention': 'ysy', 'Cyrl': 'c5o', 'ug-Arab': 'byq', 'None': 'jin',
        'Kore': 'vd4', 'Grek': 'v1n', 'Hebr': 'qf0', 'Xsux': 'bq4', 'fa-Arab': 'pmt',
        'Thai': 'dnh', 'Deva': 'fpg', 'Armn': 'rmw', 'Telu': 'sdn', 'Zsym': 'ulm',
        'ur-Arab': 'xx2', 'pa-Arab': 'xoy', 'Mymr': 'xrc', 'Khmr': 'btv', 'Glag': 'd4k',
        'Laoo': 'ylv', 'Cyrs': 'e9b', 'Runr': 'mnm', 'Orkh': 'a5j', 'kk-Arab': 'ols',
        'Hang': 'qf2', 'Phnx': 'uec', 'ps-Arab': 'kqo', 'Syrc': 'xcs', 'Tibt': 'm5l',
        'Sinh': 'ucx', 'Talu': 'rlb', 'ku-Arab': 'g1h', 'tpos': 'tey', 'Mong': 'xa6',
        'Geor': 'qev', 'Gujr': 'znk', 'Beng': 'xay', 'Guru': 'gzh', 'Orya': 'a3c',
        'Hant': 'r8d', 'Hans': 'sok', 'Copt': 'wz3', 'jump-links-section': 'kyg',
        'book': 'dpj', 'Goth': 'hv4', 'wiktQuote': 'wd3', 'termcleanup': 'jm4',
        'polytonic': 'wcw', 'neverexpand': 'qth', 'deprecated-label': 'ojo',
        'CategoryTreeBullet': 'hty', 'CategoryTreeToggle': 'yj2', 'tr': 'b4c',
        'CategoryTreeNotice': 'cw0', 'mw-formatted-date': 'efe',
        'jump-target': 'r5i', 'jump-links': 'e0u', 'jump-target-section': 'hte',
        'PDFlink noprint': 'rxl', 'serial-and': 'kug'},
        'sup': {'reference': 'mxf'}, 'audio': {'kskin': 'gj1'},
        'ol': {'references': 'tvu'}, 'li': {'senseid': 'yis', 'gallerybox': 'bif'},
        'table': {'floatright': 'wop', 'wikitable': 'fai', 'related terms': 'yox',
        'mw-hiero-table': 'tyr', 'wikitable mw-collapsible mw-collapsed': 'x5o',
        'inflection-table vsSwitcher vsToggleCategory-inflection': 'ptm', 'toc': 'qfm',
        'inflection-table': 'grh', 'prettytable inflection-table': 'o3c',
        'toccolours': 'd3p', 'wikitable inflection-table': 'pfp'},
        'tr': {'vsShow': 'yaf', 'vsHide': 'nxn'}, 'th': {'vsToggleElement': 'xx5'},
        'td': {'mbox-image': 'b1r', 'mbox-text': 'nru', 'hiddenStructure': 'if6'},
        'ul': {'gallery mw-gallery-traditional': 'zrb'}, 'small': {'ce-date': 'v1i'},
        'b': {'Latn': 'nyr', 'None': 'bvh', 'Latn headword': 'aqj', 'Grek': 'mgs',
        'Jpan': 'zav', 'selflink': 'i8c'},
        'i': {'Latinx mention': 'yvo', 'Deva mention': 'med', 'Latn mention': 'wpt',
        'polytonic mention': 'dvu', 'Hebr mention': 'ykw', 'Latinx mention': 'kaa',
        'Arab mention': 'c3a', 'fa-Arab mention': 'zrn', 'Phli mention': 'e8m',
        'Xpeo mention': 'xzn', 'Cyrl mention': 'wvm', 'None mention': 'jti',
        'Runr mention': 'tsm', 'Geor mention': 'ie6', 'Syrc mention': 'e4h',
        'Ethi mention': 'fba', 'ota-Arab mention': 'con', 'Armn mention': 'zfd',
        'Goth mention': 'fu7', 'Jpan mention': 'ai4', 'Tibt mention': 'bhs',
        'Mymr mention': 'oof', 'Thai mention': 'uuw', 'Grek mention': 'zqd',
        'ur-Arab mention': 'l2n', 'Xsux mention': 'dxa', 'Copt mention': 'wl4',
        'Ital mention': 'tfn', 'Sinh mention': 'dnr', 'nv-Latn mention': 'eqz',
        'ps-Arab mention': 'gyl', 'Cans mention': 'b1e', 'Taml mention': 'pie',
        'Avst mention': 'tex', 'Hani mention': 'ekp', 'Kana mention': 'cx4',
        'Mlym mention': 'bof', 'Phnx mention': 'hjf', 'Armi mention': 'd20',
        'Tfng mention': 'ven', 'Mong mention': 'ayu', 'Telu mention': 'qd2',
        'Beng mention': 'dgx', 'Egyp mention': 'blo', 'Zsym mention': 'wc2',
        'Prti mention': 'qr0', 'Linb mention': 'kz2', 'Thaa mention': 'fgf',
        'Laoo mention': 'typ', 'Knda mention': 'ctm', 'Cyrs mention': 'jtc',
        'Kore mention': 'rb2', 'Gujr mention': 'md1', 'Java mention': 'uci',
        'Orkh mention': 'a2c', 'Guru mention': 'ubw', 'Orya mention': 'eif',
        'sd-Arab mention': 'oit', 'Hant mention': 'nrk', 'Hans mention': 'kzh',
        'Khmr mention': 'qvk', 'Zmth mention': 'zcu', 'Cher mention': 'tgt',
        'Mani mention': 'b1w', 'Glag mention': 'pbs', 'Hang mention': 'lef',
        'Ugar mention': 'odu', 'ug-Arab mention': 'duu', 'Ogam mention': 'kss',
        'Sund mention': 'udq', 'Egyd mention': 'l7h', 'Olck mention': 'znx',
        'ku-Arab mention': 'qyp', 'pa-Arab mention': 'ats', 'Brai mention': 'dda',
        'pjt-Latn mention': 'y7d'}}

    def __an(self, at, f):
        p = self.__rex(r'<td class="unicode audiolink">([^<>]+)</td>', re.I)
        m = p.search(at)
        id = 'uk'
        if m:
            if self.__rex(r'\bUS\b', re.I).search(m.group(1)):
                id = 'us'
        return ''.join([' <img src="', id, '.png" onclick="kyw.a(this,', '\'', f, '\')" class="avj">'])

    def __hd_no(self, m):
        self.__no += 1
        return ''.join([m.group(1), m.group(2), '<sup> ', str(self.__no), '</sup>', m.group(3)])

    def __rm_sas(self, m):
        p = self.__rex(r'<div class="disambig-see-also">.+?</div>', re.I)
        sas = p.sub(r'', m.group(1))
        p = self.__rex(r'^\s*(<(li|[ud]l)>.+?</\2>)', re.I)
        sas = p.sub(self.__cov_p, sas)
        return sas

    def __rm_p(self, pg):
        txt = self.__rex(r'</?[^<>]+>|&#160;').sub(r'', pg)
        if self.__rex(r'^[^<>]{,50}?\son\sWik\w+(\sCommons)?\.?\s*$', re.I).search(txt):
            return ''
        return pg

    def __cov_p(self, m):
        p = self.__rex(r'<([ud]l)>(.+?)</\1>', re.I)
        px = p.sub(r'\2', m.group(1))
        p = self.__rex(r'<(li|dd)>(.+?)</\1>', re.I)
        px = p.sub(r'<p>\2</p>', px)
        return self.__rm_p(px)

    def __cut_thm(self, p, pt):
        thms = p.findall(pt)
        pt = p.sub(r'', pt)
        return ''.join(thms), pt

    def __fix_tmb(self, m, before=False):
        div = r'<div class="(?:thumb tleft|thumbinner|floatright|tright|toc)"[^<>]*>.+?</div>'
        tbl = r'<table class="(?:floatright|toc|xkn|wikitable)[^<>]*>.+?</table>'
        p = self.__rex(''.join([r'(', div, r'|', tbl, r')\s*(?=</?(?:[odu]l|li|dd|p>)|(?:</div>\s*)?(?:<h\d|$))']), re.I)
        thms, blk = self.__cut_thm(p, m.group(0))
        if before:
            return ''.join([''.join(thms), blk])
        else:
            return ''.join([blk, ''.join(thms)])

    def __rm_psd(self, m):
        if m.group(1).find('</div>') < 0:
            return ''
        return m.group(0)

    def __fmt_quot(self, m):
        qt = m.group(1)
        p = self.__rex(r'<li>(.+?)</li>', re.I)
        qt = p.sub(r'<div class="iqz">\1</div>', qt)
        p = self.__rex(r'<dl>(.+?)</dl>', re.I)
        qt = p.sub(r'\1', qt)
        return ''.join(['<div class="ypu">', qt, '</div>'])

    def __a2em(self, reg):
        p = self.__rex(r'<a href="/wiki/Appendix:[^<>]+>([^<>]*)</a>', re.I)
        reg = p.sub(r'<em class="qsp">\1</em>', reg)
        p = self.__rex(r'<a\b[^<>]+>([^<>]*)</a>', re.I)
        reg = p.sub(r'<em class="rkl">\1</em>', reg)
        return reg

    def __fmt_lk(self, m):
        ref, anc = m.group(3), m.group(4)
        if (not anc or self.__rex(r'^#English\b', re.I).search(anc)) and ref in self.crefs:
            ref = self.crefs[ref]
            return ''.join([m.group(1), m.group(2), 'entry://', fix_c(ref), '">', m.group(5), m.group(6)])
        else:
            return m.group(5)

    def __fmt_infl(self, m):
        infl = m.group(0)
        p = self.__rex(r'(<i\b[^<>]*>.+?</i>)', re.I)
        infl = p.sub(lambda n: self.__a2em(n.group(1)), infl)
        infl = self.__del_links(infl, True, True)
        p = self.__rex(r'(<a )[^<>]*(href=")/wiki/([^<>"]+?)((?:#[^<>"]+)?)"[^<>]*>(.+?)(</a>)', re.I)
        infl = p.sub(self.__fmt_lk, infl)
        p = self.__rex(r'(?<=<b)(>[^<>]+)(</b>)([\!\?]?)', re.I)
        infl = p.sub(r' class="nyr"\1\3\2', infl)
        return infl

    def __fixreg(self, m):
        reg = self.__a2em(m.group(2))
        p = self.__rex(r'<span class="ib-content">\s*([^<>\s]+)</span>\s*$', re.I)
        reg = p.sub(r'<em class="bst">\1</em>', reg)
        p = self.__rex(r'<span class="ib-content">\s*([^<>\s]+\s[^<>\s]+)</span>\s*$', re.I)
        reg = p.sub(r'<em class="bst">\1</em>', reg)
        p = self.__rex(r'(?<=<span class="ib-content">)\s*([^<>,\s]+)(?=,)', re.I)
        reg = p.sub(r'<em class="bst">\1</em>', reg)
        p = self.__rex(r'<span class="ib-content">(.+?)</span>\s*$', re.I)
        reg = p.sub(r'\1', reg)
        reg = self.__rex(r'\)\s*\(').sub(r', ', reg)
        return ''.join([m.group(1), '<span class="igj">', reg, '</span>'])

    def __fmt_reg(self, m):
        li = m.group(1)
        p = self.__rex(r'(^|<li>(?:\s*<div class="thumbinner"[^<>]*>.+?</div>)?|<dd class="lxr">)\s*\((.+?</span>\s*)\)')
        return p.sub(self.__fixreg, li)

    def __add_q_btn(self, m):
        li = m.group(1)
        if li.find('<div class="ypu">') > -1:
            p = self.__rex(r'(<dl|<div class="ypu">)', re.I)
            n = p.search(li)
            if n:
                li = ''.join([li[:n.start()], ' <img src="q.png" onclick="kyw.q(this)" class="gph">', li[n.start():]])
        return li

    def __fmt_swt(self, m):
        swt = self.__fix_links(m.group(1), False)
        if self.__rex(r'^show', re.I).search(swt):
            p = self.__rex(r'(?=</li>)', re.I)
            swt = p.sub(r' <img src="q.png" onclick="kyw.w(this)" class="gph">', swt)
        return swt

    def __rm_img(self, m):
        src = m.group(1)
        if self.__rex(r'^/static/images|-logo\.(svg\.)?png$', re.I).search(src):
            return ''
        return m.group(0)

    def __get_img2(self, text):
        p = self.__rex(r'<img\b[^<>]*src="\s*([^<>"]+)\s*"[^<>]*>', re.I)
        text = p.sub(self.__rm_img, text)
        p = self.__rex(r'<img\b[^<>]*src="(//[^<>"]+?/([^<>"/]+))"', re.I)
        self.__dl_img(p, text, 'p', 'https:')
        p = self.__rex(r'<img\b[^<>]*src="(/w/extensions/[^<>"]+?/([^<>"/]+))"', re.I)
        self.__dl_img(p, text, 'p', ORIGIN[:-6])
        return text

    def __fmt_def(self, m):
        lbl, df = m.group(1), m.group(2)
        p = self.__rex(r'(</h\d>(?:\s*<p\b[^<>]*>.+?</p>)?)\s*<ul>(.+?)</ul>', re.I)
        df = p.sub(r'\1<ol>\2</ol>', df)
        df = self.__rex(r'(?<=<ol)(?=>)', re.I).sub(r' class="p3i"', df, 1)
        df = self.__get_img2(df)
        p = self.__rex(r'(?<=<ol)(?=>)', re.I)
        df = p.sub(r' class="sxw"', df)
        p = self.__rex(r'<ul>(.+?)</ul>', re.I)
        df = p.sub(self.__fmt_quot, df)
        p = self.__rex(r'(?<=<li>)\s*(.+?)(?=</li>)', re.I)
        q = self.__rex(r'(?<=<dd)(>\s*(?:\(.+?\))?\s*)<i>(.+?)(?=</dd>)', re.I)
        df = p.sub(lambda n: q.sub(r' class="lxr"\1\2', n.group(1)), df)
        df = p.sub(self.__fmt_reg, df)
        df = p.sub(self.__add_q_btn, df)
        p = self.__rex(r'(?<=<dd)(.+?)(?=</dd>)', re.I)
        q = self.__rex(r'</?i\b[^<>]*>')
        df = p.sub(lambda n: q.sub(r'', n.group(1)).replace('\xE2\x80\x83', '<br>'), df)
        df = self.__fix_links(df, False)
        p = self.__rex(r'(?<=<span )style="white-space:nowrap;?"(?=>)', re.I)
        df = p.sub(r'class="wpq"', df)
        p = self.__rex(r'<i>([^<>]+)</i>(?=\s*<ol)', re.I)
        df = p.sub(r'\1', df)
        return ''.join([lbl, df])

    def __fmt_pron(self, pr):
        pr = self.__fix_links(pr, True, True)
        p = self.__rex(r'<div class="NavHead"[^<>]*>.*?</div>', re.I)
        pr = p.sub(r'', pr)
        p = self.__rex(r'<div class="NavContent"[^<>]*>\s*(<table.+?</table>)([^<>]*?)\s*</div>', re.I)
        pr = p.sub(self.__fmt_nav, pr)
        p = self.__rex(r'<div class="NavFrame"[^<>]*>(.*?)</div>\s*$', re.I)
        pr = p.sub(r'\1', pr)
        return ''.join(['<div class="axr">', pr, '</div>'])

    def __fmt_altn(self, alt):
        alt = self.__fix_links(alt, True, True)
        return ''.join(['<div class="fvr">', alt, '</div>'])

    def __fmt_cp(self, m):
        p = self.__rex(r'<img [^<>]*src="[^<>]*?(?:/static/images|-logo\.(svg\.)?png)[^<>]*>', re.I)
        cp = p.sub(r'', m.group(1))
        p = self.__rex(r'<a\b[^<>]*>\s*</a>', re.I)
        cp = p.sub(r'', cp)
        return ''.join(['<p class="gdi">', cp, '</p>'])

    def __fmt_sa(self, blk):
        p = self.__rex(r'(?<=\()\s*<span class="ib-content">(.+?)</span>\s*(?=\))', re.I)
        blk = p.sub(r'\1', blk)
        p = self.__rex(r'(?<=\(<span class=")qualifier-content(?=">.+?</span>\))', re.I)
        blk = p.sub(r'rrq', blk)
        return blk

    def __rm_ttt(self, tbl):
        if not self.__rex(r'class="inflection-table|<th\b', re.I).search(tbl):
            p = self.__rex(r'</?(?:td|tr|table)[^<>]*>', re.I)
            tbl = p.sub(r'', tbl)
        return tbl

    def __fmt_nav(self, m):
        note = m.group(2).strip()
        p = self.__rex(r'<div\b[^<>]*>(.+?)</div>', re.I)
        note = p.sub(r'\1', note)
        note = ''.join(['<div class="xxe">', self.__rex(r'^\s*<p\b[^<>]*>(.+?)</p>\s*$').sub(r'\1', note), '</div>']) if note else ''
        tbl = self.__rm_ttt(m.group(1))
        return ''.join([tbl, note])

    def __fmt_blk(self, m):
        lbl, blk = m.group(1), m.group(3)
        lbl = self.__rex(r'\s+\d+').sub(r'', lbl)
        lbl = self.__rex(r'(?<=<h\d)(?=>)').sub(r' class="t9d"', lbl)
        blk = self.__get_img2(blk)
        p = self.__rex(r'(?<=<div )style="[^<>"]*overflow:auto[^<>"]*">\s*(?=<table\b)', re.I)
        blk = p.sub(r'class="qvg">', blk)
        p = self.__rex(r'<table [^<>]*border="0" width="100%"[^<>]*>\s*<tr>\s*<td\b[^<>]*>\s*(<table.+?</(?:p|div|table)>)\s*</td>\s*</tr>\s*</table>', re.I)
        blk = p.sub(r'\1', blk)
        p = self.__rex(r'<div class="NavHead"[^<>]*>\s*(?:Derived terms|alternat[^<>]+)\s*</div>', re.I)
        blk = p.sub(r'', blk)
        if blk.count('<div class="NavHead"')==1 and not self.__rex(r'Alternat').search(lbl):
            p = self.__rex(r'<div class="NavHead"[^<>]*>.*?</div>', re.I)
            blk = p.sub(r'', blk)
        p = self.__rex(r'<div class="NavContent"[^<>]*>\s*(<table.+?</table>)\s*([^<>]*?|<(div|p)\b[^<>]*>.+?</\3>)\s*</div>', re.I)
        p2 = self.__rex(r'<td\b[^<>]*>\s*<ul\b', re.I)
        if lbl.find('Etymology') > -1:
            cls = 'eol'
        elif self.__rex(r'(?: links|See also)', re.I).search(lbl):
            cls = 'msm'
            if not p.search(blk):
                blk = self.__rm_ttt(blk)
        elif self.__rex(r'Quotations?', re.I).search(lbl):
            cls = 'ld7'
        elif self.__rex(r'References?', re.I).search(lbl):
            cls = 'rok'
        elif self.__rex(r'(?: term|Anagram|Synonym|Antonym|Hyponym|Hypernym)s?', re.I).search(lbl):
            cls = 'cyo'
            blk = self.__fmt_sa(blk)
            if p.search(blk):
                cls = 'bft'
            elif p2.search(blk):
                cls = 'bft'
                blk = self.__rm_ttt(blk)
        else:
            cls = 'bkm'
        blk = p.sub(self.__fmt_nav, blk)
        rmw = True if cls in ['eol', 'cyo', 'bft'] else False
        blk = self.__fix_links(blk, rmw)
        blk = self.__rex(r'</?ul[^<>]*>', re.I).sub(r'', blk)
        return ''.join([lbl, '<img src="c.png" onclick="kyw.s(this)" class="ywp">',
        m.group(2), '<div class="', cls, '">', blk, '</div>'])

    def __fmt_htb(self, txt):
        txt = self.__get_img2(txt)
        txt = self.__fix_links(txt, False)
        return txt

    def __fmt_hp(self, m):
        txt = self.__fmt_htb(m.group(2))
        return ''.join([m.group(1), ' class="hv7"', txt])

    def __fmt_wk_tbl(self, m):
        tbd = m.group(1)
        p = self.__rex(r'(<table[^<>]*?style="[^<>]*?)width\s*:\s*\w+;?', re.I)
        tbd = self.__rex(r'style="\s*"', re.I).sub('', p.sub(r'\1', tbd))
        tbd = self.__get_img2(tbd)
        tbd = self.__fix_links(tbd, False)
        p = self.__rex(r'(<div [^<>]*style="[^<>]*?)width:\s*\d{3,}px;?(?=[^<>]*>)', re.I)
        tbd = p.sub(r'\1', tbd)
        p = self.__rex(r'(<span style="background-color:[^<>]+>)\s*(?=</span>)', re.I)
        tbd = p.sub(r'\1&nbsp;&nbsp;&nbsp;', tbd)
        return tbd

    def __rm_tbl(self, m):
        tbl = m.group(0)
        if tbl.count('</tr>')==1 and tbl.count('</td>')==1 and self.__rex(r'Wik\w+-logo\.', re.I).search(tbl):
            tbl = ''
        return tbl

    def __rm_tbl2(self, m):
        tbl = m.group(0)
        if self.__rex(r'This entry (?:needs|is part of)', re.I).search(tbl):
            tbl = ''
        return tbl

    def __rm_tbl3(self, m):
        tbl = m.group(0)
        if self.__rex(r'Requests for cleanup', re.I).search(tbl):
            tbl = ''
        return tbl

    def __del_links(self, line, rmw=True, rmg=False):
        p = self.__rex(r'<a [^<>]*href="ftp://[^<>]+>(.+?)</a>', re.I)
        line = p.sub(r'\1', line)
        p = self.__rex(r'<a [^<>]*href="(?:NEWS|urn):[^<>]+"[^<>]*>(.+?)</a>', re.I)
        line = p.sub(r'\1', line)
        if rmw:
            p = self.__rex(r'<a [^<>]*href="https://en\.wikipedia\.org[^<>]+>(.+?)</a>', re.I)
            line = p.sub(r'\1', line)
        if rmg:
            p = self.__rex(r'<a [^<>]*href="(?:https?://|//www\.)[^<>"]+"[^<>]*>(.+?)</a>', re.I)
            line = p.sub(r'\1', line)
        else:
            p = self.__rex(r'(?<=<a )[^<>]*(href="(?:https?://|//www\.)[^<>"]+")[^<>]*(?=>)', re.I)
            line = p.sub(r'\1 class="zwb" target="_new"', line)
        return line

    def __fix_af(self, m):
        a = m.group(3)
        cls = 'bra' if self.__rex(r'^\s*<img', re.I).search(a) else 'e5g'
        return ''.join([m.group(1), ORIGIN, m.group(2), r'class="', cls, '" target="_new">', a])

    def __fix_lk(self, m):
        ref, anc = m.group(2), m.group(3)
        if (not anc or self.__rex(r'^#English\b', re.I).search(anc)) and ref in self.crefs:
            ref = self.crefs[ref]
            return ''.join([m.group(1), 'entry://', fix_c(ref), '"'])
        else:
            return ''.join([m.group(1), ORIGIN, ref, anc, '" class="jjw" target="_new"'])

    def __fix_links(self, line, rmw=True, rmg=False):
        p = self.__rex(r'(?<=<a )[^<>]*(href=")(?=//dx\.doi\.org|//species\.wikimedia\.org|//en\.wik\w+\.org)', re.I)
        line = p.sub(r'\1http:', line)
        line = self.__del_links(line, rmw, rmg)
        p = self.__rex(r'(?<=<a )[^<>]*(href=")(?=//)', re.I)
        line = p.sub(r'\1https:', line)
        p = self.__rex(r'(?<=<a )[^<>]*(href=")/wiki/([^<>]+?:[^<>"]+")[^<>]*>(.+?</a>)', re.I)
        line = p.sub(self.__fix_af, line)
        p = self.__rex(r'(?<=<a )[^<>]*(href=")/wiki/([^<>"]+?)((?:#[^<>"]+)?)"[^<>]*(?=>)', re.I)
        line = p.sub(self.__fix_lk, line)
        return line

    def __setval(self, nm, name, no, of):
        d = self.index[nm]
        d[name] = []
        l = d[name]
        l.append(no)
        l.append(of)
        d[name] = l
        return d

    def __shk_nm(self, src, filename, ext, dest):
        name = self.__fix_nm(src, filename)
        of = fullpath(''.join([self.DIC_T, path.sep, dest, path.sep, name, '' if ext=='.svg' else ext]))
        if not path.exists(of):
            print self.key, ":", of, "not found"
        nm = urllib.unquote(name)
        pos = nm.find('-')
        if pos > 0:
            nm = nm[pos:].strip('-_')
        p = self.__rex(r'[\s\'\(\)\[\],]+')
        nm = self.__rex(r'[_\-]{2,}').sub('-', p.sub('-', nm))
        n = self.__rex(r'[a-zA-Z0-9_-]{2,18}').search(nm)
        if n:
            nm = n.group(0).strip('_-')
        else:
            nm = p.sub('-', self.key)
        nm = ''.join([dest, path.sep, nm, ext])
        if nm in self.index:
            if not name in self.index[nm]:
                self.index[nm] = self.__setval(nm, name, len(self.index[nm])+1, of)
            idx = self.index[nm][name][0]
            if idx > 1:
                nm, ext = path.splitext(nm)
                nm = ''.join([nm, str(idx), '_', ext])
        else:
            self.index[nm] = {}
            self.index[nm] = self.__setval(nm, name, 1, of)
        self.imgidx[src.rstrip('"')] = (nm, ''.join([name, ext]))
        return nm.replace(path.sep, '/')

    def copy_images(self):
        for nm, d in self.index.items():
            for name, l in d.iteritems():
                file, ext = path.splitext(nm)
                idx = l[0]
                if idx > 1:
                    file = ''.join([file, str(idx), '_'])
                nf = fullpath(''.join([self.DIC_T, path.sep, 'data', path.sep, file, ext]))
                if not path.exists(nf) or len(d)>1:
                    shutil.copyfile(l[1], nf)
                    if self.shrink and ext.lower()=='.png':
                        os.system(''.join([self.shrink, ' -f --ext .png --quality 70-80 --speed=3 "', nf, '" "', nf, '"']))

    def __fmt_img(self, m):
        lb, src, st = m.group(1), m.group(2), m.group(3)
        p = self.__rex(r'(?<=[\s"])(?:width|height|style)="[^<>"]+"', re.I)
        st = ' '.join(p.findall(''.join([lb, st])))
        if self.localize:
            p = self.__rex(r'[^<>]+/([^<>/]+?)(\.\w{3,4})["\?].*', re.I)
            src = p.sub(lambda n: self.__shk_nm(src, n.group(1), n.group(2), 'p'), src)
        elif src.startswith('//'):
            src = ''.join(['https:', src])
        else:
            src = ''.join([ORIGIN[:-6], src])
        return ''.join(['src="', src, '" ', st])

    def __zom_svg(self, m, zoom):
        lb, sf = m.group(1), m.group(2)
        f = round(float(sf)*zoom, 2)
        return ''.join([lb, str(f)])

    def __fmt_svg(self, m):
        st = ''
        if self.localize:
            ext = '.png' if self.svg2png else '.svg'
            src, zoom = self.__shk_nm(m.group(3), m.group(3), ext, 'v'), 1.2
        else:
            src, zoom = m.group(2), 1
        p = self.__rex(r'(?<=[\s"])(style="[^<>"]+")', re.I)
        n = p.search(''.join([m.group(1), m.group(4)]))
        if n:
            p = self.__rex(r'((?:width|height)\s*:)\s*(\.?\d+(?:\.\d*)?)(?=[^\d\.])', re.I)
            st = p.sub(lambda o: self.__zom_svg(o, zoom), n.group(1))
        return ''.join(['src="', src, '" ', st])

    def __fmt_lbl(self, m):
        lbl = m.group(2)
        p = self.__rex(r'(?<=[\s"])(?:title|xml:lang|lang)\s*=\s*"[^<>"]*"', re.I)
        return ''.join([m.group(1), p.sub(r'', lbl).rstrip()])

    def format(self, key, line, logs):
        self.key = key
        line = line.replace('\xE2\x80\x8E', '')
        p = self.__rex(r'<!--[^<>]+?-->|</?hr\s*/?>')
        line = p.sub('', line)
        p = self.__rex(r'<h\d>\s*<span class="mw-headline" id="Translations(?:_\d+)?">Translations</span>.+?(?=<h\d\b|$)', re.I)
        line = p.sub(r'', line)
        p = self.__rex(r'<div [^<>]*id="Translations.+?(?=<h\d\b|$)', re.I)
        line = p.sub(r'', line)
        p = self.__rex(r'<div class="pseudo NavFrame">\s*<div class="NavHead"[^<>]*>(.+?)</div>\s*</div>', re.I)
        line = p.sub(self.__rm_psd, line)
        p = self.__rex(r'<sup title="translation[^<>]*?">.+?</sup>', re.I)
        line = p.sub(r'', line)
        p = self.__rex(r'<div class="NavFrame" style="background:#FFB90F">\s*<div class="NavHead"[^<>]*>.+?</div>\s*<div class="NavContent"[^<>]*>.+?</div>\s*</div>', re.I)
        line = p.sub(r'', line)
        p = self.__rex(r'<div class="(?:noprint|sister-(?:wiki\w+|project|species)|was-wotd floatright).+?</div>\s*(?=<h\d|<p|<table|<[odu]l|<li|<div class="(?:thumb|floatright|tright|toc)|$)', re.I)
        line = p.sub(r'', line)
        p = self.__rex(r'<tr>\s*<th[^<>]*>\s*<a\b[^<>]+>Picture dictionary</a>\s*</th>\s*</tr>', re.I)
        line = p.sub(r'', line)
        p = self.__rex(r'<a\b[^<>]+>\s*<img alt="About this image"[^<>]*>\s*</a>', re.I)
        line = p.sub(r'', line)
        p = self.__rex(r'<table style="[^<>]*float:\s*right;[^<>]*">.+?</table>', re.I)
        line = p.sub(self.__rm_tbl, line)
        p = self.__rex(r'(?<=<div )[^<>]*class="PopUpMediaTransform"[^<>]*?((?:style="[^<>"]+")?)[^<>]+>(.+?)(?=</div>)', re.I)
        line = p.sub(r'class="d0j" \1>\2', line)
        p = self.__rex(r'<span class="mw-editsection">.+?(?=</h\d>)', re.I)
        line = p.sub(r'', line)
        p = self.__rex(r'<small class="editlink">.+?</small>|<sub class="preloadtext">.+?</sub>', re.I)
        line = p.sub(r'', line)
        p = self.__rex(r'<sup class="(?:plainlinks|attentionseeking)"[^<>]*>\s*\[.+?\]\s*</sup>', re.I)
        line = p.sub(r'', line)
        p = self.__rex(r'(,\s*)?<span style="color:\s*#777777;?">\(.+?\)\s*</span>,?', re.I)
        line = p.sub(r'', line)
        p = self.__rex(r'<span class="CategoryTreeEmptyBullet">[^<>]*</span>', re.I)
        line = p.sub(r'', line)
        p = self.__rex(r'<span class="previewonly">[^<>]*</span>', re.I)
        line = p.sub(r'', line)
        p = self.__rex(r'<span class="interProject">(?:\s*<a\b[^<>]+>.*?</a>)?\s*</span>', re.I)
        line = p.sub(r'', line)
        p = self.__rex(r'(?<=</h1>)(.+?)(?=<h3>)', re.I)
        line = p.sub(self.__rm_sas, line)
        p = self.__rex(r'<table style="[^<>]*margin:\s*auto[^<>]*">.+?</table>', re.I)
        line = p.sub(self.__rm_tbl2, line)
        p = self.__rex('<table[^<>]*>.+?</table>', re.I)
        line = p.sub(self.__rm_tbl3, line)
        p = self.__rex('<span class="mwe-math-mathml-inline[^<>]+>.+?</span>', re.I)
        line = p.sub(r'', line)
        p = self.__rex(r'<math xmlns=.+?</math>', re.I)
        line = p.sub(r'', line)
        p = self.__rex(r'<dl>\s*<dd>\s*(<table\b[^<>]*>.+?</table>)\s*</dd>\s*</dl>', re.I)
        line = p.sub(r'\1', line)
        p = self.__rex(r'<table class="mw-hiero-table mw-hiero-outer"[^<>]*>\s*<tr>\s*<td>\s*(.+?)\s*</td>\s*</tr>\s*</table>', re.I)
        line = p.sub(r'\1', line)
        p = self.__rex(r'<span\b[^<>]*>\s*(<img\b[^<>]+>)\s*</span>', re.I)
        line = p.sub(r'\1', line)
        p = self.__rex(r'<div class="checksense">.+?</div>', re.I)
        line = p.sub(r'', line)
        p = self.__rex(r'(?<=<div class="vsShow")\s*style="display:none"(?=>)', re.I)
        line = p.sub(r'', line)
        p = self.__rex(r'<span class="metadata audiolinkinfo">.+?</span>', re.I)
        line = p.sub(r'', line)
        p = self.__rex(r'(?<=<table class=")metadata mbox-small"[^<>]*(?=>)', re.I)
        line = p.sub(r'xkn"', line)
        p = self.__rex(r'<td colspan="2" class="mbox-text".+?</td>', re.I)
        line = p.sub(r'', line)
        n = 1
        while n:
            p = self.__rex(r'<(dd|dl|li|ul|p)[^<>]*>\s*</\1>', re.I)
            line, n = p.subn(r' ', line)
        p = self.__rex(r'<a [^<>]*href="/w/index\.php\?title=[^<>]+>(.+?)</a>', re.I)
        line = p.sub(r'\1', line)
        p = self.__rex(r'<li class="mw-empty-elt">\s*</li>', re.I)
        line = p.sub(r'', line)
        ph = self.__rex(r'(<h1 id="firstHeading"[^<>]*>)(.+?)(</h1>)', re.I)
        line = ph.sub(r'\1<span class="gec">\2</span>\3', line)
        hd = ph.search(line).group(0)
        p = self.__rex(r'(<h\d>\s*<span class="mw-headline" id="Etymology(?:_\w+)?">)', re.I)
        m, n, self.__no = p.search(line), 0, 0
        if m:
            pt1, pt2 = line[:m.end()], line[m.end():]
            pt2, n = p.subn(''.join([hd, r'\1']), pt2)
            line = ''.join([pt1, pt2])
        if n:
            line = ph.sub(self.__hd_no, line)
        p = self.__rex(r'<h([2-9])>\s*<span [^<>]+>[^<>]+</span>\s*</h\1>\s*(?=<h\d)', re.I)
        line = p.sub(r'', line)
        p = self.__rex(r'<div class="thumbcaption"[^<>]*>\s*<div class="magnify">\s*<a [^<>]+>\s*</a>\s*</div>(.+?)\s*</div>', re.I)
        line = p.sub(self.__fmt_cp, line)
        p = self.__rex(r'<div class="thumb tmulti tright">\s*(<div.+?</div>)\s*</div>\s*(?=<h\d|<p|<[odu]l|<table|<div class="(?:thumb|floatright|tright|toc)|$)', re.I)
        q = self.__rex(r'<div class="thumbcaption"[^<>]*>\s*(.+?)\s*</div>', re.I)
        line = p.sub(lambda m: q.sub(r'<p class="gdi">\1</p>', m.group(1)), line)
        p = self.__rex(r'<div class="thumb (?:tright|tnone)">\s*(<div.+?</div>)\s*</div>', re.I)
        q = self.__rex(r'<div class="thumbcaption"[^<>]*>\s*(<p>.+?</p>)\s*</div>', re.I)
        line = p.sub(lambda m: q.sub(r'\1', m.group(1)), line)
        p = self.__rex(r'(<a\b[^<>]+>)\s*<span class="play-btn-large">.+?</span>\s*(?=</a>)', re.I)
        line = p.sub(r'\1<img src="pl.png" class="k76">', line)
        p = self.__rex(r'<span class="ib-brac"><span class="qualifier-brac">([\(\)\[\]])</span></span>', re.I)
        line = p.sub(r'\1', line)
        p, n = self.__rex(r'<span class="(?:ib-(?:brac|comma|colon)|q-hellip-b|q-hellip-sp|(?:qualifier|serial)-comma|sense-qualifier-colon|gloss-brac)">([\(\)\[\],:])</span>', re.I), 1
        while n:
            line, n = p.subn(r'\1', line)
        p = self.__rex('<span class="mention-gloss-double-quote">([^<>]+)</span>', re.I)
        line = p.sub(r'\1', line)
        line = line.replace('<sup>(<a href="/wiki/Appendix:English_pronunciation" title="Appendix:English pronunciation">key</a>)</sup>', '')
        p = self.__rex(r'<a href="/wiki/Wiktionary:International_Phonetic_Alphabet"[^<>]*>(IPA|enPR)</a>', re.I)
        line = p.sub(r'\1', line)
        p = self.__rex(r'<a href="/wiki/Appendix:English_pronunciation"[^<>]*>(IPA|enPR)</a>', re.I)
        line = p.sub(r'\1', line)
        p = self.__rex(r'(?<=<span class=")IPA\b[^<>]+>', re.I)
        line = p.sub(r'm8r">', line)
        p = self.__rex(r'(?<=<span )title="X-SAMPA[^<>]*><tt class="SAMPA">([^<>]+)</tt>(?=</span>)', re.I)
        line = p.sub(r'class="m8r">\1', line)
        ens = line.split('</h1>')
        p = self.__rex(r'<table class="audiotable".+?</table>\s*,?', re.I)
        q = self.__rex(r'<source [^<>]*src="([^<>"]+)\.ogg"', re.I)
        r = self.__rex(r'^//upload\.wikimedia\.org/wikipedia/commons/', re.I)
        pc = self.__rex(r'(?=<h\d)', re.I)
        pm = self.__rex(r'^(.+?)(?=<h\d>\s*<span class="mw-headline" id="(?!Pronunciation|Alternat|Etymology))', re.I)
        pn = self.__rex(r'<div style="background-color:\s*#f0f0f0;">\s*<p>(.+?)</p>\s*</div>', re.I)
        pp = self.__rex(r'(<h\d>\s*<span class="mw-headline" id="Pronunciation.+?)(?=<h\d\b)', re.I)
        ps = self.__rex(r'(<h\d>\s*<span class="mw-headline" id="Alternat.+?)(?=<h\d\b)', re.I)
        pt = self.__rex(r'<table\b', re.I)
        pu = self.__rex(r'</?ul[^<>]*>', re.I)
        for i in xrange(0, len(ens)):
            abf = []
            for at in p.findall(ens[i]):
                m = q.search(at)
                if m:
                    f, n = r.subn('', m.group(1))
                    if not n:
                        raise AssertionError(''.join([key, '\t', m.group(1)]))
                    abf.append(self.__an(at, f))
            if abf:
                ens[i-1] = ''.join([ens[i-1], ''.join(abf)])
            m = pp.search(ens[i])
            if m:
                ens[i] = pp.sub(r'', ens[i])
                ens[i] = pc.sub(self.__fmt_pron(pu.sub('', m.group(1))), ens[i], 1)
            ens[i] = pm.sub(lambda m: self.__fix_tmb(m, True), ens[i])
            m = pn.search(ens[i])
            ens[i] = pn.sub(r'', ens[i])
            if m:
                ens[i] = ''.join(['<div class="waq">', self.__fix_links(m.group(1), False), '</div>', ens[i]])
            m = ps.search(ens[i])
            if m and not pt.search(m.group(1)):
                ens[i] = ps.sub(r'', ens[i])
                ens[i-1] = ''.join([ens[i-1], self.__fmt_altn(pu.sub('', m.group(1)))])
                pa = self.__rex(r'<h(\d)>\s*<span class="mw-headline" id="Alternat[^<>]+">[^<>]+</span>\s*</h\1>', re.I)
                ens[i-1] = pa.sub(r'', ens[i-1])
        line = p.sub(r'', '</h1>'.join(ens))
        p = self.__rex(r'(<([du]l)>.+?</\2>)', re.I)
        line = p.sub(self.__fix_tmb, line)
        p = self.__rex(r'<h(\d)>\s*<span class="mw-headline" id="Pronunciation(?:[^<>]+)?">[^<>]+</span>\s*</h\1>', re.I)
        line = p.sub(r'', line)
        p = self.__rex(r'(<h\d>\s*<span class="mw-headline" id="Etymology[^<>]+>[^<>]+</span>)\s*(</h\d>)(.+?)(?=<h\d\b)', re.I)
        line = p.sub(self.__fmt_blk, line)
        p = self.__rex(r'(?<=<p)(>\s*)(?:<b class="\w+ headword"[^<>]*>.+?</b>)', re.I)
        line = p.sub(r' class="aak"\1', line)
        p = self.__rex(r'(?<=<span class=")mw-headline("[^<>]+>[^<>]+)(</span>)(\s*</h\d>)(\s*<p class="aak">.*?</p>)', re.I)
        line = p.sub(r'vbz\1 \2\4\3', line)
        p = self.__rex(r'<p class="aak">\s*</p>', re.I)
        line = p.sub(r'', line)
        p = self.__rex(r'(?<=<p class="aak">)(.+?)(?=</p>)', re.I)
        line = p.sub(self.__fmt_infl, line)
        p = self.__rex(r'(<h\d>\s*<span class=")mw-headline(?=" id="(?:ad[jv]|(proper_)?noun|verb|pronoun|prep|conjunction|interj|Symbol|Numeral|Initialism|Abbreviation))', re.I)
        line = p.sub(r'\1vbz', line)
        p = self.__rex(r'(<h\d>\s*<span class="vbz"[^<>]*>[^<>]+</span>\s*</h\d>\s*<p>.*?</p>)', re.I)
        line = p.sub(self.__fmt_infl, line)
        p = self.__rex(r'(<h\d>\s*<span class="mw-headline"[^<>]+>[^<>]+</span>)\s*(</h\d>)(.+?)(?=<h\d\b|$)', re.I)
        line = p.sub(self.__fmt_blk, line)
        for id in ['Etymology', 'Alternat']:
            p = self.__rex(''.join([r'(<h\d[^<>]*>\s*<span class="mw-headline" id="', id, '.+?)(<h[3-9]>.+?)(?=<h\d class="t9d">|<h1|$)']), re.I)
            line = p.sub(r'\2\1', line)
        p = self.__rex(r'(?<=\(<span class=")ib-content(">)<span class="qualifier-content">(.+?)</span>(?=</span>\))', re.I)
        line = p.sub(r'mwx\1\2', line)
        p = self.__rex(r'(<h\d>\s*<span class="vbz"[^<>]*>[^<>]+</span>)(.+?)\s*(?=<h\d|$)', re.I)
        line = p.sub(self.__fmt_def, line)
        p = self.__rex(r'(<table [^<>]*class="wikitable"[^<>]*>.+?)(?=</table>)', re.I)
        line = p.sub(self.__fmt_wk_tbl, line)
        p = self.__rex(r'(<\w+\b)([^<>]+)(?=>)', re.I)
        line = p.sub(self.__fmt_lbl, line)
        p = self.__rex(r'(<table (?:class="(?:floatright|toc|xkn)"|align="right").+?)(?=</table>\s*(?:<h\d|<p|<[odu]l|<li|<div class=))', re.I)
        line = p.sub(lambda m: self.__fix_links(m.group(1), False), line)
        p = self.__rex(r'(<div class="(?:thumbinner|tright|floatright)".+?)(?=<h\d\b|<table class="floatright"|<p class="aak">|<ol)', re.I)
        line = p.sub(lambda m: self.__fix_links(m.group(1), False), line)
        p = self.__rex(r'(?<=<ul class="gallery mw-gallery-traditional")(.+?)(?=</ul>)', re.I)
        line = p.sub(lambda m: self.__fix_links(m.group(1), False), line)
        p = self.__rex(r'(?<=<div class="vs)((?:Hide|Show)">.+?)(?=</div>)', re.I)
        line = p.sub(self.__fmt_swt, line)
        p = self.__rex(r'(?<=h1)(.+?)(?=<h\d>)', re.I)
        q = self.__rex(r'<(p|[du]l)>.+?</\1>', re.I)
        line = p.sub(lambda m: q.sub(lambda n: self.__rm_p(n.group(0)), m.group(1)), line)
        p = self.__rex(r'(?<=</h1>)\s*(<p)(>.+?</p>)', re.I)
        line = p.sub(self.__fmt_hp, line)
        p = self.__rex(r'(?<=</h1>)\s*(<table style=.+?</table>)', re.I)
        line = p.sub(lambda m: self.__fmt_htb(m.group(1)), line)
        p = self.__rex(r'(?<=<img )([^<>]*)src="((?://|/w/extensions/)[^<>"]+?")([^<>]*)(?=>)', re.I)
        line = p.sub(lambda m: self.__fmt_img(m), line)
        p = self.__rex(r'(?<=<img )([^<>]*)src="(https?://[^<>"]+?/svg/([^<>"/]+))"([^<>]*)(?=>)', re.I)
        line = p.sub(lambda m: self.__fmt_svg(m), line)
        p = self.__rex(r'(<source [^<>]*src=")(?=//)', re.I)
        line = p.sub(r'\1https:', line)
        line = self.__rex(r'(?=<h1)').sub(''.join([r'<a href="', ORIGIN, urllib.quote(key.replace(' ', '_')),
        r'#English"target="_new"><img src="x.png" class="qkx"></a>']), line, 1)
        p = self.__rex(r'(?<=<span class=")form-of\b[^<>]*?(?=">)', re.I)
        line = p.sub(r'apd', line)
        p = self.__rex(r'<span class="ib-content"><span class="qualifier-content">([^<>]+)</span></span>', re.I)
        line = p.sub(r'\1', line)
        line = self.__rex(r'(</?)h[4-9]\b').sub(r'\1h3', line)
        p = self.__rex(r'<span[^<>]*>(\s*|&#160;|&nbsp;)</span>', re.I)
        line = p.sub(r' ', line)
        p = self.__rex(r'<a\b[^<>]+>(\s*)</a>', re.I)
        line = p.sub(r'\1', line)
        p = self.__rex(r'(<i\b[^<>]*>\s*)(\()(.+?)(\))(\s*</i>)', re.I)
        line = p.sub(r'\2\1\3\5\4', line)
        line = self.__rex(r'(\s+)(\))').sub(r'\2\1', line)
        line = self.__rex(r'(\()(\s+)').sub(r'\2\1', line)
        p = self.__rex(r'(<span\b[^<>]*>)([^<>]+)(?=</span>)', re.I)
        line = p.sub(lambda m: ''.join([m.group(1), m.group(2).replace('\xE2\x80\xA7', '<span class="ifh"></span>')]), line)
        p = self.__rex(r'(?<=<)(span|div|h1|ol|ul|li|b|table|th|tr|td|sup|i|audio|small|blockquote)(\b[^<>]*class=")([^<>"]+)(?=")', re.I)
        line = p.sub(self.__repcls, line)
        p = self.__rex(r'(<table [^<>]*?class="ptm"[^<>]*>.+?)(?=</table>)', re.I)
        q = self.__rex(r'(?=</th>\s*</tr>)', re.I)
        line = p.sub(lambda m: q.sub(' <img src="c.png" onclick="kyw.t(this)" class="qsj">', m.group(1), 1), line)
        line = self.cleansp(line)
        n = 1
        while n:
            line, n = self.__rex(r'<(div|li|[du]l|p|dd)\b[^<>]*>\s*</\1>|<td style="border-style:none"></td>', re.I).subn(r'', line)
        js = '<script type="text/javascript"src="wk.js"></script>' if line.find('onclick=')>-1 else ''
        line = ''.join(['<link rel="stylesheet"href="', self.DIC_T, '.css"type="text/css"><div class="wic">', line, js, '</div>'])
        if _DEBUG_:
            p = self.__rex(r'<(\w+)\b[^<>]*class="([^<>"]{4,})"')
            for tag, cls in p.findall(line):
                if tag in self.clstbl:
                    if not cls in self.clstbl[tag]:
                        self.clstbl[tag][cls] = randomstr(3).lower()
                else:
                    self.clstbl[tag] = OrderedDict()
                    self.clstbl[tag][cls] = randomstr(3).lower()
            if p.search(line) or self.__rex(r'<a href="/|Wi\w+-logo\.', re.I).search(line):
                self.need_fix[key] = line
        return '\n'.join([key, line, '</>\n'])


def getlinks(ap, dict):
    p = re.compile(r'<div id="mw-pages">(.+?)<noscript>', re.I)
    q = re.compile(r'<li>(.+?)</li>', re.I)
    r = re.compile(r'<a href="/wiki/([^\?&<>"]+?)(?:#[^<>"]+)?\s*"[^>]*>\s*(.+?)\s*</a>', re.I)
    div = p.search(ap).group(1)
    for li in q.findall(div):
        m = r.search(li)
        if m:
            word = m.group(2).replace('&amp;', '&').replace('&#039;', '\'').replace('&quot;', '"').strip()
            dict[m.group(1).strip()] = word
    s = re.compile(r'<a href="(/w/index\.php\?title=Category:English_lemmas[^<>"]+?)(?:%0A[^<>]+?)?"[^>]*>next page</a>', re.I)
    m = s.search(ap)
    if m:
        url = m.group(1).replace('&amp;', '&')
        print url
        fc = 0
        while fc < 20:
            try:
                ap = getpage(url, 'https://en.wiktionary.org')
                return getlinks(re.compile(r'[\n\r]+').sub(r'', ap), dict)
            except Exception, e:
                time.sleep(10)
                fc += 1
        if fc == 20:
            return url
    return ''


def makewordlist(file):
    fp = fullpath(file)
    if path.exists(fp):
        dt = OrderedDict(getwordlist(file))
    else:
        print "Get word list: start at %s" % datetime.now()
        ptl = path.exists(fullpath(''.join([file, '.part'])))
        if ptl and path.exists(fullpath('failedurl.txt')):
            url, file = readdata('failedurl.txt'), ''.join([file, '.part'])
            dt = OrderedDict(getwordlist(file))
            print len(dt)
            fp = fullpath(file)
        else:
            url, dt = '/wiki/Category:English_lemmas', OrderedDict()
        page = getpage(url, 'https://en.wiktionary.org')
        page = re.compile(r'[\n\r]+').sub(r'', page)
        failed = getlinks(page, dt)
        dump(''.join(['\n'.join(['\t'.join([k, v]) for k, v in dt.iteritems()]), '\n']), file)
        if failed:
            dump(failed, 'failedurl.txt')
            if not ptl:
                os.rename(fp, ''.join([fp, '.part']))
            dt = OrderedDict()
        elif ptl:
            os.rename(fp, fp[:-5])
            removefile(fullpath('failedurl.txt'))
        print "\nGet word list: finished at %s" % datetime.now()
    print "%s totally" % info(len(dt))
    return dt


def is_complete(dir, ext='.part'):
    if path.exists(dir):
        for root, dirs, files in os.walk(dir):
            for file in files:
                if file.endswith(ext):
                    return False
        return True
    return False


if __name__=="__main__":
    import sys
    reload(sys)
    sys.setdefaultencoding('utf-8')
    import argparse
    argpsr = argparse.ArgumentParser()
    argpsr.add_argument("diff", nargs="?", help="[p] To download missing words \n[f] format only")
    argpsr.add_argument("file", nargs="?", help="[file name] To specify additional wordlist when diff is [p]")
    argpsr.add_argument("-l", "--local", help="To localize image files", action="store_true")
    argpsr.add_argument("-q", "--pngquant", help="To shrink *.png files", action="store_true")
    argpsr.add_argument("-v", "--svg2png", help="To replace *.svg with *.png", action="store_true")
    args = argpsr.parse_args()
    print "Start at %s" % datetime.now()
    wkt_dl = wkt_downloader()
    dir = ''.join([wkt_dl.DIC_T, path.sep])
    if args.diff == 'f':
        if is_complete(fullpath(dir)):
            wkt_dl.combinefiles(dir, args)
        else:
            print "Word-downloading is not completed."
    else:
        wkt_dl.login()
        if wkt_dl.session:
            d_all, base = makewordlist(F_WORDLIST), 0
            if args.diff=='p':
                print "Start to download missing words..."
                wordlist = []
                d_p = OrderedDict(getwordlist(args.file)) if args.file and path.exists(fullpath(args.file)) else OrderedDict()
                for d in os.listdir(fullpath(dir)):
                    if re.compile(r'^\d+$').search(d) and path.isdir(fullpath(''.join([dir, d, path.sep]))):
                        base += 1
                for k, v in d_p.iteritems():
                    if k in d_all:
                        del d_p[k]
                    else:
                        wordlist.append((k, v))
                d_all.update(d_p)
            else:
                wordlist, d_p = d_all.items(), OrderedDict()
            if wordlist:
                multiprocess_fetcher(dir, d_all, wordlist, wkt_dl, base)
                if is_complete(fullpath(dir)):
                    wkt_dl.combinefiles(dir, args)
            print "Done!"
        else:
            print "ERROR: Login failed."
    print "Finished at %s" % datetime.now()
