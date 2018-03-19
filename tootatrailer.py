#!/usr/bin/env python

import sqlite3
import requests
import feedparser
import os
import sys
import time
import schedule
from bs4 import BeautifulSoup
from mastodon import Mastodon
from io import BytesIO

# get our dir.
bot_dir = os.path.dirname(os.path.realpath(__file__))


def get_post_title(entry):
    if 'tags' in entry.keys():
        return entry['title']
    else:
        pass


def get_post_link(entry):
    if 'tags' in entry.keys():
        return entry['link']
    else:
        pass


def get_post_img(entry):
    if 'tags' in entry.keys():
        _content = entry['content'][0]['value']
        _soup = BeautifulSoup(_content, 'html.parser')

        return _soup.find('img')['src']
    else:
        pass


def init_db(dbfile):
    conn = sqlite3.connect(dbfile)
    sql_cmd = """
    CREATE TABLE IF NOT EXISTS bringatrailer (
    id integer PRIMARY KEY,
    title text,
    image text,
    link text
    )
    """

    c = conn.cursor()
    c.execute(sql_cmd)
    conn.close()


def update_db(dbfile, title, image, link):
    conn = sqlite3.connect(dbfile)
    c = conn.cursor()
    query = """
    INSERT INTO bringatrailer (
    title, image, link
    ) VALUES (
    '{}', '{}', '{}'
    )
    """.format(title, image, link)

    c.execute(query)
    conn.commit()
    conn.close()


def query_latest_db(dbfile):
    """
    Get the entry most recently added to our db.

    :rtype: str
    """

    conn = sqlite3.connect(dbfile)
    c = conn.cursor()
    query = """
    SELECT * FROM bringatrailer ORDER BY id DESC LIMIT 1
    """
    
    c.execute(query)
    return c.fetchall()[0]
    conn.close()


def entry_exist_bool(dbfile, link):
    """
    Check if the latest entry from the feed already exists in our database.
    If so, discard it.

    :rtype: bool
    """

    conn = sqlite3.connect(dbfile)
    c = conn.cursor()
    query = """
    SELECT link FROM bringatrailer WHERE link='{}'
    """.format(link)
    c.execute(query)
    result = c.fetchall()
    if not result:
        return False
    else:
        return True


def val_db(dbfile):
    """
    Debug contents of DB.

    :rtype: None
    """

    conn = sqlite3.connect(dbfile)
    c = conn.cursor()
    c.execute('SELECT * FROM bringatrailer ORDER BY id')
    for elem in c.fetchall():
        print(elem)
    conn.close()


def prune_db(dbfile):
    """
    delete DB grift.

    :rtype: None
    """

    conn = sqlite3.connect(dbfile)
    c = conn.cursor()
    c.execute('DELETE FROM bringatrailer WHERE image = "None"')
    conn.commit()
    conn.close()


def fetch_image(img_url):
    """
    Get raw bytes for image at img_url.

    :rtype: _io.BytesIO
    """

    r = requests.get(img_url)
    return BytesIO(r.content)


def mastodon_client(client_id, client_secret, access_token, base_url):
    return Mastodon(client_id, client_secret, access_token, base_url)


def main():
    client_id, client_secret, access_token = sys.argv[1:]

    d = feedparser.parse('https://bringatrailer.com/feed/')
    latest_entry = d.entries[0]

    auction_db = os.path.join(bot_dir, 'auction_db.sqlite')

    if not auction_db:
        init_db(auction_db)

    title = get_post_title(latest_entry)
    link = get_post_link(latest_entry)
    image = get_post_img(latest_entry)

    if None in (title, link, image):
        print('latest entry is not auction')
    elif entry_exist_bool(auction_db, link):
        print('latest entry already in our db')
    else:
        update_db(auction_db, title, image, link)

        prune_db(auction_db)
        val_db(auction_db)

        (auction_title, img_url, auction_link) = query_latest_db(auction_db
                                                                 )[1:]
        print(img_url)

        api = mastodon_client(client_id,
                              client_secret,
                              access_token,
                              'https://fasterwhen.red')

        img_data = fetch_image(img_url)

        img_media = api.media_post(img_data, "image/jpeg")

        print(img_media)

        response = api.status_post(
                status="Beep Boop! New Auction posted on BAT!\n{}\n{}"
                .format(auction_title, auction_link),
                media_ids=[img_media['id']])

        print(response)


if __name__ == '__main__':
    #schedule.every().hour.do(main)

    #while True:
    #    schedule.run_pending()
    #    time.sleep(1)

    main()
