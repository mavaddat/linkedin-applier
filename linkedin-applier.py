# linkedin-applier.py
#
# how this works
#  - there's 'browser' object that persists and gets passed around, content of
#  its browser.page_source changes as we make GET requests
#  - linkedin paginates job pages every 25 listings, the 25 listings don't
# appear immediately, they are lazy loaded, to get around this JS we scroll to
# bottom
#  - linkedin GET query: "&start=x*25" is what allows you to load x page,
# "&f_LF=f_AL" shows only "Easy Apply" listings

import keyring
import os
import time
import urllib
import random
from selenium import webdriver
from selenium.common import exceptions
from bs4 import BeautifulSoup

url_job_pages = (
    r'https://www.linkedin.com/jobs/search/'
    r'?f_E=2&geoId=90009553&keywords=software%20engineer&'
    r'location=Greater%20Vancouver%20Metropolitan%20Area'
    )
SCRAPE_RECOMMENDED_JOBS = True


def get_job_links(page):
    links = []
    for link in page.find_all('a'):
        url = link.get('href')
        if url and '/jobs/view/' in url:
            path = urllib.parse.urlparse(url).path   # extract path from url,
            # e.g. only '/jobs/view/942882320/'
            links.append(path)
    return links


def job_traverse_all_pages(browser, url, current_page=0):
    browser.get(url)
    js_scroll_to_bottom = '''
         var jobPane = document.querySelector(".jobs-search-results");
         jobPane.animate({scrollTop: jobPane.prop("scrollHeight")}, 1000);
         '''
    # linkedin won't show you up to 25 job listings right away due to
    # disgusting JS infested UI design
    browser.execute_script(js_scroll_to_bottom)
    time.sleep(1.0)
    page = BeautifulSoup(browser.page_source, features="html.parser")

    links = list(set(get_job_links(page)))
    # list(set(foo)) removes duplicates
    url_nextpage = url_job_pages + "&start=" + str(current_page * 25)
    # linkedin paginates its jobs every 25 listings
    current_page += 1
    time.sleep(random.uniform(0.2, 0.9))  # random sleep

    if len(links) < 25:  # if there's less than 25 job listings then we
        # assume there's no next page
        return links
    else:
        return links + job_traverse_all_pages(
            browser, url_nextpage, current_page)


def job_landing_page(browser):
    url_landing_page = 'https://www.linkedin.com/jobs/'  # among things
    # contains linkedin's recommended jobs
    job_list = []

    if SCRAPE_RECOMMENDED_JOBS:
        browser.get(url_landing_page)
        page = BeautifulSoup(browser.page_source, features="html.parser")
        job_list = get_job_links(page)  # initial population, from now on we
        # will concat '/jobs/view/*' urls to job_list list

    job_list += job_traverse_all_pages(browser, url_job_pages)

    return job_list


def get_button(browser, tag, button_name):
    elements_list = browser.find_elements_by_tag_name(tag)
    for x in elements_list:
        try:
            if str(x.text) == button_name:
                return x
        except exceptions.StaleElementReferenceException:
            pass


def job_bot(browser):
    job_list = job_landing_page(browser)
    count = 0

    for job in job_list:
        time.sleep(random.uniform(2.0, 5.0))
        browser.get("https://www.linkedin.com" + job)

        # apply for job
        easy_apply_button = get_button(browser, 'span', 'Easy Apply')
        if easy_apply_button is None:
            continue  # you might have already applied for this job,
            # hence apply button is missing
        easy_apply_button.click()
        time.sleep(0.5)
        submit_button = get_button(browser, 'button', 'Submit application')
        if submit_button is None:
            print("[-] Could not apply for " + job + " | " + browser.title)
            continue
        else:
            submit_button.click()
            count += 1
            print(
                "[+] Applied:  " + browser.title + "\n(" + str(count) + "/" +
                str(len(job_list)) + ") Applied/Queue)")

        time.sleep(5)


def main():
    '''
    Prior to execution, run the following on CLI:
        $ keyring.exe set system email
        Password for 'email' in 'system': *****************
        $ keyring.exe set system linkedin
        Password for 'email' in 'system': *****************
    '''
    email = keyring.get_password("system", "email")
    passwd = keyring.get_password("system", "linkedin")
    localappdata = os.environ.get('LOCALAPPDATA')
    webdriver_service = webdriver.chrome.service.Service(
        os.path.join(localappdata, 'operadriver_win64\\operadriver.exe'))
    webdriver_service.start()

    browser = webdriver.Remote(
        webdriver_service.service_url,
        webdriver.DesiredCapabilities.OPERA)
    browser.get("https://linkedin.com/uas/login")

    email_element = browser.find_element_by_id("username")
    email_element.send_keys(email)
    pass_element = browser.find_element_by_id("password")
    pass_element.send_keys(passwd)
    pass_element.submit()
    time.sleep(5)
    try:
        mfa_element = browser.find_element_by_id(
            "input__phone_verification_pin")
        mfa_element.send_keys(input("What is the LinkedIn verification code?"))
        mfa_element.submit()
    except exceptions.NoSuchElementException:
        pass
    os.system('cls')
    print("[+] Logged in")
    job_bot(browser)
    browser.close()


if __name__ == '__main__':
    main()
