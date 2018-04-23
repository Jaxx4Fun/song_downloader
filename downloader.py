import re
import time
import os
import requests
import argparse
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException

from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains


from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class MusicDownloader(object):
    AVAILABLE_SITE = ['kugou', 'qq','kuwo']
    # AVAILABLE_SITE = ['qq']
    URL_REGEX = re.compile(r'https?://\w+.([\w\d]+).com')
    DEFAULT_SONG_NAME = "千千阙歌"
    PLAY_TAB_TAG = ['试听', '播放', '正在','单曲']
    STORAGE_PATH = './downloads'

    def __init__(self, *args, **kwargs):
        self.browser = webdriver.Chrome()
        self.wait = WebDriverWait(self.browser,10)
        self.url = kwargs.get('url')
        self.song_name = kwargs.get('name', MusicDownloader.DEFAULT_SONG_NAME)
        if not os.path.exists(MusicDownloader.STORAGE_PATH):
            os.makedirs(MusicDownloader.STORAGE_PATH)
    def search(self, **kwargs):
        '''
        百度搜索歌曲
        '''
        self.browser.get('https://www.baidu.com')
        self.song_name = kwargs.get('name') or self.song_name
        kw_input = self.browser.find_element_by_css_selector("#kw")
        kw_input.send_keys(self.song_name)
        search_btn = self.browser.find_element_by_css_selector("#su")
        search_btn.click()
        i = 1
        # # 调试用，因为每次返回的web不是同一个，有些会出现bug
        # flag = input()
        # while not flag:
        #     self.browser.refresh()
        #     flag = input()

        # time.sleep(0.5)
        # tabs = self.browser.find_elements_by_xpath('//ul[@class="c-tabs-nav-more"]/li[@music-data]')
        tabs = self.wait.until(EC.presence_of_all_elements_located((By.XPATH,('//ul[@class="c-tabs-nav-more"]/li[@music-data]'))))
        for source in tabs:
            self.site_name = source.get_attribute('music-data').split('.')[1]
            if self.site_name in MusicDownloader.AVAILABLE_SITE:
                if i>1:
                    source.click()
                break
            i += 1
        if i > len(tabs):
            raise Exception("Not supported" % self.song_name)
        # 表格的情况
        try:
            div = self.wait.until(EC.presence_of_element_located((By.XPATH,'//div[contains(@class,"c-tabs-content")][{}]'.format(i))))
        except NoSuchElementException as e:
            song = self.browser.find_element_by_xpath(
                '//a[contains(text(),"在线试听")]')
        try:
            song = div.find_element_by_xpath(
                'table[@class="c-table op-musicsongs-songs"]/tbody/tr[2]/td[4]/a')
        except NoSuchElementException:
            song = div.find_element_by_xpath('//a[contains(text(),"在线试听")]')
        song.click()

    def switch_play_tab(self):
        '''
        切换chrome的标签页
        '''
        if self.site_name == 'qq':
            time.sleep(3)
        for window in self.browser.window_handles[::-1]:
            self.browser.switch_to_window(window)
            title = self.browser.title
            for tag in MusicDownloader.PLAY_TAB_TAG:
                if tag in title:
                    url = self.browser.current_url
                    m = MusicDownloader.URL_REGEX.match(url)
                    if m:
                        self.site_name = m.group(1)
                    return

    def extract_page(self, page_url=None):
        """
        从页面中提取url
        """
        if page_url:
            self.browser.get(page_url)

        if 'kugou' == self.site_name:
            # 等待js加载
            time.sleep(0.5)
            audio = self.browser.find_element_by_css_selector('audio#myAudio')
            singer = ','.join(map(lambda elem: elem.text,self.browser.find_elements_by_xpath('//p[contains(@class,singerName)]/a')[1:]))
            self.song_name = '%s - %s' %(self.browser.find_element_by_xpath(
                '//span[@id="songName"]').text,singer)
            self.url = audio.get_attribute('src')
        elif 'qq' == self.site_name:
            time.sleep(1)
            print(self.browser.current_url)
            try:
                self.song_name = '%s - %s' % (self.browser.find_element_by_xpath(
                    '//*[@id="sim_song_info"]/a[1]').text, self.browser.find_element_by_xpath('//*[@id="sim_song_info"]/a[2]').text)
            except NoSuchElementException:
                pass
            self.url = self.browser.find_element_by_xpath(
                '//*[@id="h5audio_media"]').get_attribute('src')
        elif 'kuwo' == self.site_name:
            song_id = 'Music_'+self.browser.current_url.split('?')[0].split('/')[-1]
            self.url = 'http://antiserver.kuwo.cn/anti.s?format=aac|mp3&rid='+song_id+'&type=convert_url&response=res'
            self.song_name = ' - '.join(self.browser.title.split('-')[:2])

        else:
            raise Exception("Site not supported")
    def download(self, audio_url=None):
        """
        根据页面解析的url下载音频
        """
        self.url = audio_url or self.url
        rsp = requests.get(self.url)
        if 200 == rsp.status_code:
            path = os.path.join(MusicDownloader.STORAGE_PATH,self.song_name+'.mp3')
            with open(path, 'wb') as f:
                f.write(rsp.content)
    def run(self,name='爱的供养'):
        try:
            self.search(name=name)
        except Exception as e:
            print(e)
            return
        self.switch_play_tab()
        self.extract_page()
        self.download()
    def close(self):
        self.browser.quit()



if __name__ == '__main__':
    '''
    测试
    '''
    parser = argparse.ArgumentParser()
    parser.add_argument('-n','--name',help='Input the song name you want to search')
    parser.add_argument('-f','--file',help='Specify the path of song list')
    parser.add_argument('-l','--link',help='Specify the link of the song')
    args = parser.parse_args()
    md = MusicDownloader()
    if args.file:
        with open(args.file.strip()) as f:
            for name in f.readlines():
                md.run(name)
    elif args.name:
        md.run(args.name)
    elif args.link:
        md.extract_page(page_url=args.link)
        md.download()
    md.close()
