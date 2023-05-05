#!/usr/bin/env python3

import requests, re, json, time, random
import argparse
requests.packages.urllib3.disable_warnings()

base_url = 'https://polldaddy.com/poll/'
poll_id = 12224023
answer_id = 55428209
useragents = []
proxies = []


def choose_useragent():
    k = random.randint(0, len(useragents)-1)
    return useragents[k]

def choose_proxy():
    k = random.randint(0, len(proxies)-1)
    return {"http": proxies[k]}

def vote_once(form, value):
    c = requests.Session()
    ua = choose_useragent()
    px = choose_proxy()
    print(f'{ua=}')
    print(f'{px=}')
    hdrs = {"Referer": base_url + str(form) + "/", "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8", "User-Agent": ua, "Upgrade-Insecure-Requests":"1", "Accept-Encoding": "gzip, deflate, sdch", "Accept-Language": "en-US,en;q=0.8"}

    url = base_url + str(form) + "/"
    resp = c.get(url, headers=hdrs, verify=False, proxies=px)

    # Contains variables
    data = re.search("data-vote=\"(.*?)\"",resp.text).group(1).replace('&quot;','"')
    data = json.loads(data)
    print(f'data: {data}')
    pz = re.search("type='hidden' name='pz' value='(.*?)'",resp.text).group(1)
    print(f'Found pz: {pz}')

    # Build the GET url to vote
    request = "https://poll.fm/vote?va=" + str(data['at']) + "&pt=0&r=0&p=" + str(form) + "&a=" + str(value) + "%2C&o=&t=" + str(data['t']) + "&token=" + str(data['n']) + "&pz=" + str(pz)
    print(f'Sending request: {request}')
    send = c.get(request, headers=hdrs, verify=False, proxies=px)

    print(send.url)

def vote(form, value, times, wait_min = None, wait_max = None):
    global redirect
    # For each voting attempt
    i = 1
    while i < times+1:
        b = vote_once(form, value)
        # If successful, print that out, else try waiting for 60 seconds (rate limiting)
        if not b:
            # Randomize timing if set
            if wait_min and wait_max:
                seconds = random.randint(wait_min, wait_max)
            else:
                seconds = 3

            print("\nVoted (time number " + str(i) + ")!\n")
            time.sleep(seconds)
        else:
            i-=1
            time.sleep(60)
        i += 1

if __name__ == '__main__':

    with open('useragent.txt', 'r') as f:
        for line in f:
            useragents.append(line.rstrip('\n').rstrip('\r'))
    with open('proxy.txt', 'r') as f:
        for line in f:
            proxies.append(line.rstrip('\n').rstrip('\r'))

    parser = argparse.ArgumentParser()
    parser.add_argument('-n', help='number of times to vote', type=int, required=True)

    args = parser.parse_args()
    vote(poll_id, answer_id, args.n, None, None)