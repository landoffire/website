#! /usr/bin/env python

import hashlib
import hmac
import os
import subprocess

from flask import Flask, render_template, request, Response

import config_bootstrap as config
from nav import Nav
from wiki import wiki_bp


app = Flask(__name__)

app.register_blueprint(wiki_bp, url_prefix='/wiki')


@app.template_filter('plural')
def plural(s, count=None):
    # Would be nice to use inflect here, but it has a bug with all-caps input.
    return s if count == 1 else s + 's'


def add_simple(*args, **kw):
    need_online = kw.pop('online', False)
    need_news = kw.pop('news', False)
    need_gallery = kw.pop('gallery', False)
    nav = Nav(*args, **kw)

    def func(ref=nav.ref, pages=nav.registry):
        kw = {'current': ref, 'pages': pages}
        if need_news:
            kw['news'] = news()
        if need_online:
            kw['online'] = online()
        if need_gallery:
            kw['gallery'] = gallery()

        return render_template(ref + '.html', **kw)

    app.add_url_rule(nav.url, nav.ref, func)


def online():
    if config.DEBUG:
        raw_players = ['KeeKee (GM)', 'Pihro (GM)      ', 'LOFBot   ', 'Pyndragon', 'Ozthokk']
    else:
        with open(config.ONLINE_LIST_PATH, 'rb') as fl:
            raw_players = fl.read().decode('utf-8').splitlines()[4:-2]

    count = len(raw_players)

    gms = []
    devs = []
    bots = []
    players = []

    for player in sorted(raw_players):
        player = player.rstrip()
        gm = False
        if player.endswith('(GM)'):
            gm = True
            player = player[:-4]
        player = player.rstrip()

        if player.startswith('LOFBot'):
            bots.append(player)
        elif player in ('Pihro', 'Pyndragon'):
            devs.append(player)
        elif gm:
            gms.append(player)
        else:
            players.append(player)

    return dict(count=count, gms=gms, players=players, bots=bots, devs=devs)


def news():
    with open('news.txt' if config.DEBUG else config.NEWS_PATH, 'rb') as fl:
        paragraphs = fl.read().decode('utf-8').split('\n\n')

    output = []
    lines_remaining = 25
    for p in paragraphs:
        if not p:
            continue
        if lines_remaining <= 0:
            break

        lines = [(L[2], L[4:]) for L in p.splitlines(True)]
        lines_remaining -= len(lines)

        ident = lines[0][0]
        if ident == config.F_LIST:
            parsed = ['list', lines[0][1], [L[1][2:] for L in lines[1:]]]
        elif ident == config.F_AUTHOR and lines[0][1].startswith('\u2014'):
            # Strip off leading em-dash and whitespace
            parsed = ['author', lines[0][1][1:].rstrip()]
        else:
            name = {config.F_NORMAL: 'normal', config.F_TITLE: 'title', config.F_AUTHOR: 'author'}.get(ident, 'normal')
            parsed = [name, '\n'.join(L[1] for L in lines)]

        output.append(parsed)

    return output


def gallery():
    if config.DEBUG:
        return ['LOF_banner_still_licensed_web_4.png', 'screenshot-2016.03.23-tulimshar.png']
    else:
        return [img for img in os.listdir(config.GALLERY_DIR) if os.path.isfile(os.path.join(config.GALLERY_DIR, img))]


@app.route('/gallery/<image>')
def gallery_closeup(image):
    return render_template('gallery.html', current='gallery', gallery=image, pages=Nav.registry)


@app.url_build_error_handlers.append
def check_for_nav_url(error, endpoint, values):
    if endpoint in Nav.reg_dict:
        return Nav.reg_dict[endpoint].url
    raise


add_simple('Home', 'index', '/')
#Nav('Forum', url=config.FORUM_URL, external=True)
Nav('Wiki', ref='wiki.wiki', url='/wiki')
add_simple('Gallery', online=False, news=False, gallery=True)
Nav('Discord', url=config.DISCORD_URL, external=True)
add_simple('Project')
add_simple('Team')
add_simple('Donate')


if __name__ == '__main__':
    app.run(debug=config.DEBUG, use_reloader=True)
