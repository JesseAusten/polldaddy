#!/usr/bin/env python3

import requests, re, json, time, random
import argparse
from bs4 import BeautifulSoup
requests.packages.urllib3.disable_warnings()

base_url = 'https://poll.fm/'
poll_id = 12224023
answer_id = 55428209
useragents = []
proxies = []


def choose_useragent():
    k = random.randint(0, len(useragents)-1)
    return useragents[k]

def choose_proxy():
    k = random.randint(0, len(proxies)-1)
    return {"http:", proxies[k]}

def vote_once(form, value):
    c = requests.Session()
    ua = choose_useragent()
    px = choose_proxy()
    c.proxies=px
    # print(f'{ua=}')
    # print(f'{px=}')
    hdrs = {"Referer": base_url + str(form) + "/", "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8", "User-Agent": ua, "Upgrade-Insecure-Requests":"1", "Accept-Encoding": "gzip, deflate, sdch", "Accept-Language": "en-US,en;q=0.8"}

    url = base_url + str(form)
    try:
        resp = c.get(url, headers=hdrs, timeout=5)
    except requests.exceptions.ConnectTimeout:
        print('Timed out')
        return False

    # Contains variables
    data = re.search("data-vote=\"(.*?)\"",resp.text).group(1).replace('&quot;','"')
    data = json.loads(data)
    # print(f'data: {data}')
    pz = re.search("type='hidden' name='pz' value='(.*?)'",resp.text).group(1)
    # print(f'Found pz: {pz}')

    # Build the GET url to vote
    request = "https://poll.fm/vote?va=" + str(data['at']) + "&pt=0&r=0&p=" + str(form) + "&a=" + str(value) + "%2C&o=&t=" + str(data['t']) + "&token=" + str(data['n']) + "&pz=" + str(pz)
    # print(f'Sending request: {request}')
    try:
        send = c.get(request, headers=hdrs, verify=False, timeout=5)
    except requests.exceptions.ConnectTimeout:
        print('Timed out 2')
        return False

    if "revoted" in send.url:
        print('Counted as revote')
        return False
    else:
        return True

def vote(form, value, times, wait_min = None, wait_max = None):
    for i in range(times):
        try:
            while vote_once(form, value) is False:
                time.sleep(random.randint(30, 60))
        except:
            time.sleep(random.randint(30, 60))

        print(f"Voted {i+1}/{times} times!")

        # Randomize timing if set
        if wait_min and wait_max:
            seconds = random.randint(wait_min, wait_max)
        else:
            seconds = 3
        time.sleep(seconds)

if __name__ == '__main__':

    with open('useragent.txt', 'r') as f:
        for line in f:
            useragents.append(line.rstrip('\n').rstrip('\r'))
    with open('proxy.txt', 'r') as f:
        for line in f:
            proxies.append(line.rstrip('\n').rstrip('\r'))

    parser = argparse.ArgumentParser()
    parser.add_argument('-n', help='number of times to vote, only used if not monitoring votes', type=int, required=False)
    parser.add_argument('--min', help='min seconds to wait between votes', type=int, required=False)
    parser.add_argument('--max', help='max seconds to wait between votes', type=int, required=False)

    args = parser.parse_args()

    if args.n:
        vote(poll_id, answer_id, args.n, args.min, args.max)
        exit(0)

    last_diff = 0
    while True:
        other_votes = -1
        our_votes = -1

        resp = requests.get(f'https://poll.fm/{poll_id}/results')
        html = BeautifulSoup(resp.text, features='lxml')
        results = html.body.find_all('label', attrs={'class':'pds-feedback-label'})

        for result in results:
            nvotes = -1
            nvotes_str = result.find('span', attrs={'class':'pds-feedback-votes'}).string
            nvotes_lst = re.findall("([0-9,]*) votes", nvotes_str)
            if len(nvotes_lst) > 0:
                nvotes = int(nvotes_lst[0].replace(',', ''))
                if nvotes < 0 or nvotes > 100000:
                    nvotes = -1
            if '(9)' in result.find('span', attrs={'class':'pds-answer-text'}).string:
                if nvotes > 0:
                    our_votes = nvotes
            else:
                if nvotes > 0:
                    other_votes = nvotes

        print(f"{other_votes=}")
        print(f"{our_votes=}")

        if our_votes < int(other_votes*1.2):
            diff = int(other_votes*1.2) - our_votes
            nvotes = random.randint(diff, diff+int(other_votes*0.1))
            print(f'Diff (x1.2) is {diff}, voting {nvotes} times')

            min = args.min
            max = args.max
            if our_votes < int(other_votes*1.05):
                # overdrive mode
                print('Engaging lightspeed')
                min = 2
                max = 4
            vote(poll_id, answer_id, nvotes, min, max)


        time.sleep(10 + random.randint(0, 20))
