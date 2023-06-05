#!/usr/bin/env python3

import requests, re, json, time, random, datetime
import asyncio
from proxybroker import Broker, ProxyPool
from proxybroker.errors import NoProxyError
from signal import SIGINT, SIGTERM
import argparse
from bs4 import BeautifulSoup
requests.packages.urllib3.disable_warnings()

base_url = 'https://poll.fm/'
poll_id = 12348499
answer_id = 55877168
useragents = []
proxies = []

def choose_useragent():
    k = random.randint(0, len(useragents)-1)
    return useragents[k]

def vote_once(proxy, form, value):
    print(f'Using proxy {proxy}')
    c = requests.Session()
    c.proxies={'https': f'{proxy.host}:{proxy.port}'}

    ua = choose_useragent()
    hdrs = {"Referer": base_url + str(form) + "/", "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8", "User-Agent": ua, "Upgrade-Insecure-Requests":"1", "Accept-Encoding": "gzip, deflate, sdch", "Accept-Language": "en-US,en;q=0.8"}
    url = base_url + str(form)

    try:
        print(f'request with proxies: {c.proxies}')
        resp = c.get(url, headers=hdrs, timeout=2)
        print(f'resp: {resp}')
    except requests.exceptions.ConnectTimeout:
        print('Timed out')
        c.close()
        return False

    # Contains variables
    data = re.search("data-vote=\"(.*?)\"",resp.text).group(1).replace('&quot;','"')
    data = json.loads(data)
    # print(f'data: {data}')
    pz = re.search("type='hidden' name='pz' value='(.*?)'",resp.text).group(1)
    # print(f'Found pz: {pz}')

    # Build the GET url to vote
    request = "https://poll.fm/vote?va=" + str(data['at']) + "&pt=0&r=0&p=" + str(form) + "&a=" + str(value) + "%2C&o=&t=" + str(data['t']) + "&token=" + str(data['n']) + "&pz=" + str(pz)
    print(f'Sending request: {request}')
    try:
        print(f'proxies: {c.proxies}')
        send = c.get(request, headers=hdrs, timeout=2)
    except requests.exceptions.ConnectTimeout:
        print('Timed out 2')
        c.close()
        return False
    
    c.close()

    if "revoted" in send.url:
        print('Counted as revote')
        return False
    else:
        return True

async def vote(proxies, form, value, times, wait_min = None, wait_max = None):
    print('proxy gathering done')
    for i in range(times):
        start = datetime.datetime.now()

        res = False
        try:
            print('await start')
            proxy = await proxies.get()
            print('await done')
            if proxy is not None:
                res = vote_once(proxy, form, value)
        except:
            time.sleep(random.randint(30, 60))

        if res:
            print(f"Voted {i+1}/{times} times!")
        else:
            print('Failed to vote')

        # Randomize timing if set
        if wait_min and wait_max:
            seconds = random.randint(wait_min, wait_max)
        else:
            seconds = 5

        end = datetime.datetime.now()
        seconds -= (end - start).total_seconds()
        if (seconds > 0):
            print(f'Sleeping for {seconds} seconds')
            time.sleep(seconds)


if __name__ == '__main__':

    with open('useragent.txt', 'r') as f:
        for line in f:
            useragents.append(line.rstrip('\n').rstrip('\r'))

    types = ['HTTPS']
    countries = ['US', 'CA', 'DE', 'FR', 'GB', 'MX']
    
    # Add signal handlers to cancel loop
    # loop.add_signal_handler(SIGINT, tasks.cancel)
    # loop.add_signal_handler(SIGTERM, tasks.cancel)

    # Run until cancelled
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
                if nvotes < 0 or nvotes > 10000000:
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
            if nvotes > 100:
                nvotes = 100
            print(f'Diff (x1.2) is {diff}, voting {nvotes} times')

            min = None
            max = None
            if our_votes < int(other_votes*1.05):
                # overdrive mode
                print('Engaging lightspeed')
                min = 2
                max = 4
            print('Starting tasks')

            proxies = asyncio.Queue()
            broker = Broker(proxies, verify_ssl=False)

            tasks = asyncio.gather(
                broker.find(types=types, countries=countries, limit=nvotes),
                vote(proxies, poll_id, answer_id, nvotes, min, max))
            loop = asyncio.get_event_loop()
            loop.run_until_complete(tasks)
    