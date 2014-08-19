import os
import redis
from flask import Flask, g, url_for, redirect, request, session, \
    jsonify, render_template
from requests_oauthlib import OAuth2Session
from flask.ext.appconfig import HerokuConfig
from cachecontrol import CacheControl
from cachecontrol.caches import RedisCache
import requests.exceptions
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("app")
logger.setLevel(logging.INFO)

app = Flask(__name__)
HerokuConfig(app)

base_url = 'https://api.github.com/'
request_token_url = 'https://github.com/login/oauth/request_token'
access_token_url = 'https://github.com/login/oauth/access_token'
authorization_base_url = 'https://github.com/login/oauth/authorize'
consumer_key = os.environ['GITHUB_OAUTH_KEY']
consumer_secret = os.environ['GITHUB_OAUTH_SECRET']

redis = redis.from_url(os.getenv('REDISTOGO_URL', 'redis://localhost:6379'))


def new_session(state=None, token=None):
    sess = getattr(g, 'session', None)
    if not sess:
        if 'github_token' in session and not token:
            token = session['github_token']

        sess = g.session = CacheControl(OAuth2Session(
            consumer_key,
            state=state,
            token=token), RedisCache(redis))
    return sess


def github_get(url, partial=True):
    github = new_session()
    if partial:
        url = base_url+url
    logger.info("Get url: %s" % (url))
    r = github.get(url)
    r.raise_for_status()
    return r.json()


def fetch_users_repos():
    raw_repos = {"your-repos": github_get('user/repos')}
    orgs = github_get('user/orgs')
    for org in orgs:
        org_repos = github_get(org['repos_url'], partial=False)
        raw_repos[org['login']] = org_repos
    for orgname, repos in raw_repos.items():
        for repo in repos:
            try:
                repo['subscription'] = github_get(
                    repo['subscription_url'],
                    partial=False)
            except requests.exceptions.HTTPError, e:
                logger.error("Subscription %s exception %s" % (
                    repo['full_name'], e))
                pass
    return raw_repos


@app.before_request
def before_request():
    if 'github_token' in session:
        g.token = session['github_token']
    else:
        g.token = None


@app.route('/login')
def login():
    github = new_session()
    github.scope = ['repo', 'notifications']
    authorization_url, state = github.authorization_url(authorization_base_url)
    logging.info("authorization_url: %s" % (authorization_url))
    session['github_state'] = state
    return redirect(authorization_url)


@app.route('/logout')
def logout():
    session.pop('github_state', None)
    session.pop('github_token', None)
    return redirect("/")


@app.route('/oauth/callback')
def oauth_authorized():
    github = new_session(session['github_state'])
    token = github.fetch_token(
        access_token_url,
        client_secret=consumer_secret,
        authorization_response=request.url.replace('http', 'https')
    )
    session['github_token'] = token

    return redirect("/")


@app.route('/')
def index():
    if 'github_token' not in session:
        return redirect(url_for('login', next=request.url))
    return render_template('index.html', orgs=fetch_users_repos())


@app.route('/myrepos')
def repos_for_me():
    if 'github_token' not in session:
        return redirect(url_for('login', next=request.url))

    return jsonify({'results': fetch_users_repos()})


if __name__ == '__main__':
    app.run()
