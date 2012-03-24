#!/usr/bin/env python
# Developed with pyton 2.7
# Copyright 2012 Logan Ding <logan.ding@gmail.com>. All Rights Reserved.
#
#---------------------------------------------                             
#    Coursera.org Downloader <Version 1.1>   
#          by Logan Ding                                      
#---------------------------------------------
#
# Dependent on 'mechanize'. Use 'easy_install mechanize' first if 'mechanize' not installed.
# Be sure to change the email and the password in main() to yours first before running.
#
# Run as: 'python coursera_downloader.py' will download to CWD.
# Run as: 'python coursera_downloader.py <dir>' will download to path <dir>.
#
# Only support single thread to download right now.
# Add courses by yourself. Not all tested. You can feed back.
# Download videos, subtitles, PDF and PPT(X) slides.
# Has problem to resolve subtitles for 'modelthinking'. Ignored...now.

import cookielib, re, sys, os
try:
    import mechanize
except ImportError, e:
    print e
    print 'You must install "mechanize" first. Can use "easy_install": easy_install mechanize'
    sys.exit(1)

def split_string(source,splitlist):
    if source == '':
        return [source]
    result = []
    tmp = ''
    for c in source:
        if c not in splitlist:
            tmp += c
        else:
            if tmp != '':
                result.append(tmp)
            tmp = ''
    if tmp != '':
        result.append(tmp)
    return result      

def resolve_name_with_hex(name):
    r = re.finditer(r'%\w\w', name)
    for m in r:
        c = m.group()[1:].decode('hex') 
        c = c if c not in '\/:*?"<>|' else '_'
        name = re.sub(m.group(), c, name)
    return name

def resolve_name_with_illegal_char(name):
    return re.sub(r'[\\/:*?"<>|]', ' -', name)

def initialize_browser(course, email, password):
    #Use mechanize to handle cookie
    print
    print 'Initialize browsering session...'
    br = mechanize.Browser()
    cj = cookielib.LWPCookieJar()
    br.set_cookiejar(cj)
    br.set_handle_equiv(True)
    #br.set_handle_gzip(True)
    br.set_handle_redirect(True)
    br.set_handle_referer(True)
    br.set_handle_robots(False)
    br.set_handle_refresh(mechanize._http.HTTPRefreshProcessor(), max_time = 0)
    auth_url = 'https://www.coursera.org/****/auth/auth_redirector?type=login&subtype=normal&email'.replace('****', course)
    br.open(auth_url)

    br.select_form(nr = 0)
    br.form['email'] =  email
    br.form['password'] = password
    br.submit()
    print 'It takes seconds to login and resolve resources to download...\n'

    #Check if email + password submitted correctly
    if 'https://www.coursera.org/****/auth/login_receiver?data='.replace('****', course) not in br.geturl():
        print 'Failed to login, exit...'
        sys.exit(1)

    video_lectures = 'https://www.coursera.org/****/lecture/index'.replace('****', course)
    br.open(video_lectures)
    return br

def resolve_resources(br, path, course):
    title       = []
    pdf         = []
    pptx        = []
    link_txt    = []
    link_srt    = []
    link_video  = []

    for l in br.links():
        m_title = re.search(r'text=[\'\"](.+)[\'\"], tag=\'a\', .+\'class\', \'lecture-link\'', str(l))
        m_pdf = re.search(r'https*:[\S]+/([\S]+\.pdf)', str(l))
        m_pptx = re.search(r'https*:[\S]+/([\S]+\.pptx*)', str(l))
        m_txt = re.search(r'url=\'(https:[\S]+subtitles\?[\S]+=txt)', str(l))
        m_srt = re.search(r'url=\'(https:[\S]+subtitles\?[\S]+=srt)', str(l))
        m_video = re.search(r'https:[\S]+download.mp4[\S]+\'', str(l))

        if m_title:
            title.append(resolve_name_with_illegal_char(m_title.group(1).strip()))
        if m_pdf:
            pdf.append([resolve_name_with_hex(m_pdf.group(1)), m_pdf.group()])
        if m_pptx:
            pptx.append([resolve_name_with_hex(m_pptx.group(1)), m_pptx.group()])
        if m_txt:
            link_txt.append(m_txt.group(1))
        if m_srt:
            link_srt.append(m_srt.group(1))
        if m_video:
            link_video.append(m_video.group().rstrip("'"))

    if len(title) == len(link_video):
        video = zip([t+'.mp4' for t in title], link_video)
    else:
        print 'Video names resolving error. Ignore videos...'
        video = []
    # Here is a buggy way to handle different numbers of videos and subtitles for 'modelthinking' and 'saas'.
    # To completely solve the problem, need to change the links resolve and match method completely.
    # Will fix this if have time. Right now, this inelegant way can handle 'saas' only.
    if len(title) == len(link_srt):
        srt = zip([t+'.srt' for t in title], link_srt)
    elif course == 'saas':
        srt = zip([t+'.srt' for t in title[len(title)-len(link_srt) : ]], link_srt)
    else:
        print 'Can NOT match video names with subtitiles. Ignore...'
        srt = []

    if len(title) == len(link_txt):
        txt = zip([t+'.txt' for t in title], link_txt)
    elif course == 'saas':
        txt = zip([t+'.txt' for t in title[len(title)-len(link_txt) : ]], link_txt)
    else:
        print 'Can NOT match video names with subtitiles. Ignore...'
        txt = []
    return video, srt, txt, pdf, pptx
    
def downloader(video, srt, txt, pdf, pptx, br, path):
    # Only single download thread supported right now.
    print
    print 'Videos can be downloaded:'
    v = choose_download(video)
    print 'srt subtitles can be downloaded:'
    s = choose_download(srt)
    print 'txt subtitles can be downloaded:'
    t = choose_download(txt)
    print 'PDF slides can be downloaded:'
    f = choose_download(pdf)
    print 'PPT slides can be downloaded:'
    x = choose_download(pptx)

    # Combine all to be downloaded together for multiple downloading threads later
    all = v + s + t + f + x 
    for r in all:
        filename = os.path.join(path, r[0])
        print 'Downloading', r[0]
        br.retrieve(r[1], filename)

def choose_course(course):
    for key in sorted(course.keys()):
        print key, ':', course[key]
    choice = raw_input('Please choose course by number: ')
    while choice not in course.keys():
        choice = raw_input('Invalid choice, input again or Enter to quit: ')
        if choice == '':
            sys.exit(1)
    return course[choice]

def parse_choice(input):
    if input == '':
        return input
    input = split_string(input, ' ,')
    # This split can handle your input as: 1,3,4-5 or 1 3 4-5 or 1, 3, 4-5. Besides, range input support 4-5 or 4:5 
    choice = []
    for e in input:
        if e.isdigit():
            if e not in choice:
                choice.append(int(e))
        else:
            s = split_string(e, ':-')
            if len(s) != 2 or not s[0].isdigit() or not s[1].isdigit():
                print 'Ignore invalid input %s' %e
            else:
                for num in range(int(s[0]), int(s[1])+1):
                    if num not in choice:
                        choice.append(num)
    return sorted(choice)           

def choose_download(resource):
    for i in range(len(resource)):
        print '['+repr(i).rjust(2)+']:', resource[i][0]
    print 'Enter your choice, such as: 1, 3, 5-9. Or just Enter to skip.'
    choice = raw_input('>')
    choice = parse_choice(choice)
    print 'To be downloaded:', choice
    print
    download = []
    for i in choice:
        if i in range(len(resource)):
            download.append(resource[i])
    return download

def download_path():
    if len(sys.argv) > 1:
        if not os.path.exists(sys.argv[1]):
            try:
                os.mkdir(sys.argv[1])
            except Exception, error:
                print error
                sys.exit(1)
        return os.path.abspath(sys.argv[1])
    else:
        return os.path.abspath('.')

def main():
    print '----------------------------------'
    print '-    Coursera.org Downloader     -'
    print '-         by Logan Ding          -'
    print '----------------------------------'
    print
    # Add courses by yourself. Not all tested. You can feed back.
    course = { '1' : 'modelthinking',
               '2' : 'gametheory',  
               '3' : 'crypto',
               '4' : 'saas',
               '5' : 'pgm', 
               '6' : 'algo'}

    # Your Coursera.org email and password needed here to download videos. 
    email = 'youremail'
    password = 'password'

    if email == 'youremail':
        print 'You must change the email and the password to yours in main() first.'
        sys.exit(1)

    path  = download_path()
    print 'All files will be downloaded to:', path
    print
    course = choose_course(course)
    br = initialize_browser(course, email, password)
    vidoe, srt, txt, pdf, pptx = resolve_resources(br, path, course)
    downloader(vidoe, srt, txt, pdf, pptx, br, path)

if __name__ == '__main__':
    main()
