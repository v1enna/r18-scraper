#!/usr/bin/env python

import requests
import io
import os
import sys
import argparse

from pathlib import Path
from html5print import HTMLBeautifier
from bs4 import BeautifulSoup
from table import parse_html

class Colors:
    HEADER = '\033[95m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

class Actress:
    def __init__(self, name, url):
        self.name = name
        self.url = url

    def get_name(self):
        return self.name

    def get_url(self):
        return self.url

class Studio:
    def __init__(self, name, url):
        self.name = name
        self.url = url

    def get_name(self):
        return self.name

    def get_url(self):
        return self.url

class Movie:
    def __init__(self, content_id, url):
        self.content_id = content_id
        self.movie_id = None
        self.title = None
        self.release_date = None
        self.studio = None
        self.url = url
        self.cast = None
        self.trailer = None

    def get_content_id(self):
        return self.content_id

    def get_movie_id(self):
        return self.movie_id

    def get_title(self):
        return self.title

    def get_release_date(self):
        return self.release_date

    def get_studio(self):
        return self.studio

    def get_url(self):
        return self.url

    def get_cast(self):
        return self.cast

    def get_trailer(self):
        return self.trailer

    def set_content_id(self, content_id):
        self.content_id = content_id

    def set_movie_id(self, movie_id):
        self.movie_id = movie_id

    def set_title(self, title):
        self.title = title

    def set_release_date(self, release_date):
        self.release_date = release_date

    def set_studio(self, studio):
        self.studio = studio

    def set_url(self, url):
        self.url = url

    def set_cast(self, cast):
        self.cast = cast

    def set_trailer(self, trailer):
        self.trailer = trailer

class Scraper:
    def __init__(self, html):
        self.html = html
        self.soup = BeautifulSoup(self.html, 'html.parser')

    def get_html(self):
        return self.html

    def parse_movie_id(self):
        return self.soup.find(string = "DVD ID:").find_next("dd").text.strip()

    def parse_title(self):
        return self.soup.find("cite", { "itemprop" : "name" }).text.strip()

    def parse_release_date(self):
        return self.soup.find(string = "Release Date:").find_next("dd").text.strip()

    def parse_studio(self):
        studio_name = self.soup.find(string = "Studio:").find_next("a").text.strip()
        studio_url = self.soup.find(string = "Studio:").find_next("a")["href"]
        return Studio(studio_name, studio_url)

    def parse_content_id(self):
        return self.soup.find(string = "Content ID:").find_next("dd").text.strip()

    def parse_cast(self):
        cast = []

        cast_raw = self.soup.find("div", { "itemprop" : "actors" }).findChildren("a")

        for actress in cast_raw:
            cast.append(Actress(actress.text.strip(), actress["href"]))

        return cast

    def parse_trailer_url(self):
        if(self.soup.find("video") is not None):
            return self.soup.find("video").find_next("source")["src"]
        else:
            return None
    
class Handler():
    def __init__(self, id):
        self.request = None
        self.request_url = None
        self.parser = None

        start_message = Colors.HEADER + Colors.BOLD + "> Starting (id: " + id + ")" + Colors.HEADER + Colors.BOLD

        print(start_message)

        search_url = "https://www.r18.com/common/search/floor=movies/searchword=" + id + "/"
        search_request = requests.get(search_url, headers = { 'User-Agent' : 'Mozilla/5.0'})

        if search_request.ok and search_request.text.find('1 titles found') != -1:
            search_soup = BeautifulSoup(search_request.text, features = "html.parser")
            if (search_soup.find("li", { "data-tracking_id" : "dmmref" })) == None:
                print(Colors.FAIL + "> Script failure. Can't retrieve the movie page." + Colors.ENDC)
            self.request_url = search_soup.find("li", { "data-tracking_id" : "dmmref" }).findChildren("a")[0]["href"]
            print('> Request URL: ' + self.request_url)
        else:
            print(Colors.FAIL + "> Script failure. Can't retrieve the movie page." + Colors.ENDC)
            self.request_url = None

    def start(self):
        if self.request_url is None:
            print(Colors.FAIL + "> Request failed." + Colors.ENDC)
            return

        self.request = requests.get(self.request_url, headers = { 'User-Agent' : 'Mozilla/5.0' })

        if self.request.ok:
            print(Colors.OKCYAN + '> Connected successfully to R18.' + Colors.ENDC)

            self.parser = Scraper(self.request.text)

            print(Colors.WARNING + '> Scraping data... ' + Colors.ENDC)

            self.movie = Movie(self.parser.parse_content_id(), self.request_url)
            self.movie.set_movie_id(self.parser.parse_movie_id())
            self.movie.set_title(self.parser.parse_title())
            self.movie.set_studio(self.parser.parse_studio())
            self.movie.set_release_date(self.parser.parse_release_date())
            self.movie.set_cast(self.parser.parse_cast())

            print(Colors.OKCYAN + '> Data obtained. Proceding...' + Colors.ENDC)

            self.create_folders()
            self.download_assets()
            self.download_table(self.generate_table())

            print(Colors.OKGREEN + Colors.BOLD + '> Success!' + Colors.ENDC + Colors.ENDC)
            return (HTMLBeautifier.beautify(self.generate_table() + '<br>', 4))
        else:
            print(Colors.FAIL + "> Can't retrieve the movie page." + Colors.ENDC)
            self.start()

    def create_folders(self):
        print(Colors.WARNING + '> Creating folders...' + Colors.ENDC)

        Path('requests/' + self.movie.get_movie_id()).mkdir(exist_ok = True)      
        Path('requests/' + self.movie.get_movie_id() + "/assets/").mkdir(exist_ok = True)

    def download_assets(self):
        print(Colors.WARNING + '> Downloading assets...' +  Colors.ENDC)

        self.download_header()
        self.download_images()
        self.download_trailer()

    def download_header(self):
        header_download_url = 'https://pics.r18.com/digital/video/' + self.movie.get_content_id() + '/' + self.movie.get_content_id() + 'pl.jpg'
        header_download_path = requests.get(header_download_url, allow_redirects = True, headers = { 'User-Agent' : 'Mozilla/5.0' })

        print(Colors.WARNING + '> Downloading header from: ' + header_download_url + Colors.ENDC)

        header_save_path = 'requests/' + self.movie.get_movie_id() + '/assets/' + self.movie.get_movie_id() + '-JAV'

        if header_download_path.ok:
            if len(self.movie.get_cast()) == 1:
                header_save_path += "-"
                header_save_path += self.movie.get_cast()[0].name.replace(" ", "-")

            header_save_path += '-Header.jpg'

            print(Colors.OKCYAN + '> Header saved to: ' + header_save_path + Colors.ENDC)

            open(header_save_path, 'wb').write(header_download_path.content)
        else:
            print(Colors.FAIL + "> Can't download the header image." + Colors.ENDC)

    def download_images(self):
        failure = 0

        print(Colors.WARNING + '> Looking for images... ' + Colors.ENDC)

        for i in range(1, 6, 1):
            image_download_url = 'https://pics.r18.com/digital/video/' + self.movie.get_content_id()  + '/' + self.movie.get_content_id()  + 'jp-' + str(i) +'.jpg'
            image_download_path = requests.get(image_download_url, allow_redirects = False, headers = { 'User-Agent' : 'Mozilla/5.0' })
            
            image_save_path = 'requests/' + self.movie.get_movie_id() + '/assets/' + self.movie.get_movie_id() + '-JAV'

            if image_download_path.ok or len(image_download_path.history) != 0:
                if len(self.movie.get_cast()) == 1:
                    image_save_path += "-"
                    image_save_path += self.movie.get_cast()[0].name.replace(" ", "-")

                image_save_path += '-0' + str(i) + '.jpg'

                print(Colors.WARNING + '> Downloading image ' +  str(i) + ' from: ' + image_download_url + Colors.ENDC)

                open(image_save_path, 'wb').write(image_download_path.content)
            else:
                failure += 1

        if failure < 5:
            print(Colors.OKCYAN + '> Images saved to: requests/' + self.movie.get_content_id() + '/assets/' + Colors.ENDC)
        else:
            print(Colors.FAIL + "> Can't download any image. That's bad..." + Colors.ENDC)

    def download_trailer(self):
        trailer_download_url = self.parser.parse_trailer_url()

        print(Colors.WARNING + '> Looking for a trailer...' + Colors.ENDC)

        if trailer_download_url is not None:
            trailer_download_path = requests.get(trailer_download_url, allow_redirects = True, headers = { 'User-Agent' : 'Mozilla/5.0' })
            if trailer_download_path.ok:

                trailer_save_path = 'requests/' + self.movie.get_movie_id() + '/assets/'
                trailer_save_name = self.movie.get_movie_id() + '-JAV'

                if len(self.movie.get_cast()) == 1:
                    trailer_save_name += "-"
                    trailer_save_name += self.movie.get_cast()[0].name.replace(" ", "-")

                trailer_save_name += '.mp4'

                print(Colors.OKCYAN + '> MP4 trailer saved to: ' + trailer_save_path + trailer_save_name + Colors.ENDC)

                self.movie.set_trailer(trailer_save_name)

                open(trailer_save_path + trailer_save_name, 'wb').write(trailer_download_path.content)
            else:
                print(Colors.FAIL + "> Can't obtain any MP4 trailer (can't download the file)." + Colors.ENDC)
        else:
            print(Colors.FAIL + "> Can't obtain any MP4 trailer (can't find any source)." + Colors.ENDC)

    def generate_table(self):
        return parse_html(self.movie)

    def download_table(self, table):
        print(Colors.OKCYAN + "> Downloading HTML table in 'requests/" + self.movie.get_movie_id() + "/html.txt'" + Colors.ENDC)

        with io.open("requests/" + self.movie.get_movie_id() + "/html.txt", "w+", encoding = "utf-8") as f:
            f.write(table)

if len(sys.argv) == 1:
    print(Colors.BOLD + "Correct use: ./app.py <content/movie id>" + Colors.ENDC)  
else:
    Path("requests/").mkdir(exist_ok = True)
    result = ''
    for i in range(1, len(sys.argv)):
        print(Colors.OKGREEN + Colors.BOLD + '> Starting request ' + str(i) + '.' + Colors.ENDC + Colors.ENDC)
        result += Handler(sys.argv[i].strip()).start()
    print(Colors.OKGREEN + Colors.BOLD + "[!] Done. Results posted in '<source>/requests/'" + Colors.ENDC + Colors.ENDC)  
    with io.open("requests/result.txt", "w+", encoding = "utf-8") as f:
        f.write(result)
        