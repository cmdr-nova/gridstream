import sys
import threading
import logging
import webbrowser
from PyQt5.QtWidgets import QApplication, QMainWindow
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import QUrl
from flask import Flask, render_template, request, redirect, url_for
from sqlalchemy.orm import sessionmaker
from models import Base, Folder, Feed, engine
import feedparser
import math
# This is where I keep all my pie
app = Flask(__name__)
app.secret_key = 'A_RANDOM_GOTDANG_KEY' # Generate a random key and put it here, it's for my flask of whiskey

Session = sessionmaker(bind=engine)
db_session = Session()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def initialize_database():
    logger.info("Initializing database...")
    Base.metadata.create_all(engine)
    add_default_blog_feed()

def add_default_blog_feed():
    default_blog_url = 'https://nova-prime.net/feed.xml'  # I put my own blog here as a default example, but it can be whatever
    default_blog_name = 'cmdr-nova@internet:~$'  # The name of the default blog
    existing_feed = db_session.query(Feed).filter_by(url=default_blog_url).first()
    if not existing_feed:
        new_feed = Feed(name=default_blog_name, url=default_blog_url)
        db_session.add(new_feed)
        db_session.commit()
        logger.info(f"Added default blog feed: {default_blog_name} - {default_blog_url}")
    else:
        logger.info(f"Default blog feed already exists: {default_blog_name} - {default_blog_url}")

@app.route('/')
def index():
    folders = db_session.query(Folder).all()
    feeds = db_session.query(Feed).filter(Feed.folder == None).all()
    all_feeds = db_session.query(Feed).all()
    feed_summaries = get_feed_summaries(all_feeds)
    return render_template('index.html', folders=folders, feeds=feeds, feed_summaries=feed_summaries)

@app.route('/open_about')
def open_about():
    logger.info("open_about route called")
    url = 'https://cmdr-nova.online'  # Replace with your personal website URL
    webbrowser.open(url)
    return '', 204  # No Content response

def get_feed_summaries(feeds):
    summaries = []
    for feed in feeds:
        feed_data = feedparser.parse(feed.url)
        if feed_data.entries:
            entry = feed_data.entries[0]
            title = entry.get('title', 'No title')
            summary = entry.get('summary', entry.get('description', 'No summary'))
            link = url_for('fetch_feed', feed_id=feed.id)
            content = entry.get('content', [{'value': ''}])[0]['value']
            # Truncate the summary text
            summary = (summary[:200] + '...') if len(summary) > 200 else summary
            summaries.append({
                'title': title,
                'summary': summary,
                'link': link,
                'content': content
            })
    return summaries

@app.route('/add_folder', methods=['POST'])
def add_folder():
    folder_name = request.form['folder_name']
    new_folder = Folder(name=folder_name)
    db_session.add(new_folder)
    db_session.commit()
    return redirect(url_for('index'))

@app.route('/add_feed', methods=['POST'])
def add_feed():
    feed_url = request.form['feed_url']
    feed_data = feedparser.parse(feed_url)
    feed_name = feed_data.feed.title if 'title' in feed_data.feed else feed_url
    new_feed = Feed(name=feed_name, url=feed_url)
    db_session.add(new_feed)
    db_session.commit()
    return redirect(url_for('index'))

@app.route('/move_feed', methods=['POST'])
def move_feed():
    feed_url = request.form['feed_url']
    folder_name = request.form['folder_name']
    folder = db_session.query(Folder).filter_by(name=folder_name).first()
    feed = db_session.query(Feed).filter_by(url=feed_url).first()
    feed.folder = folder
    db_session.commit()
    return redirect(url_for('index'))

@app.route('/delete_feed/<int:feed_id>', methods=['POST'])
def delete_feed(feed_id):
    feed = db_session.get(Feed, feed_id)
    db_session.delete(feed)
    db_session.commit()
    return redirect(url_for('index'))

@app.route('/delete_feed_from_folder/<int:feed_id>', methods=['POST'])
def delete_feed_from_folder(feed_id):
    feed = db_session.get(Feed, feed_id)
    folder_name = feed.folder.name  # Access the folder name before deleting the feed
    db_session.delete(feed)
    db_session.commit()
    return redirect(url_for('view_folder', folder_name=folder_name))

@app.route('/rename_folder/<int:folder_id>', methods=['POST'])
def rename_folder(folder_id):
    new_folder_name = request.form['new_folder_name']
    folder = db_session.get(Folder, folder_id)
    folder.name = new_folder_name
    db_session.commit()
    return redirect(url_for('view_folder', folder_name=new_folder_name))

@app.route('/delete_folder/<int:folder_id>', methods=['POST'])
def delete_folder(folder_id):
    folder = db_session.get(Folder, folder_id)
    db_session.delete(folder)
    db_session.commit()
    return redirect(url_for('index'))

@app.route('/folder/<folder_name>')
def view_folder(folder_name):
    folder = db_session.query(Folder).filter_by(name=folder_name).first()
    feeds = folder.feeds
    return render_template('folder.html', folder=folder, feeds=feeds)

@app.route('/add_feed_to_folder/<folder_name>', methods=['POST'])
def add_feed_to_folder(folder_name):
    feed_url = request.form['feed_url']
    feed_data = feedparser.parse(feed_url)
    feed_name = feed_data.feed.title if 'title' in feed_data.feed else feed_url
    folder = db_session.query(Folder).filter_by(name=folder_name).first()
    new_feed = Feed(name=feed_name, url=feed_url, folder=folder)
    db_session.add(new_feed)
    db_session.commit()
    return redirect(url_for('view_folder', folder_name=folder_name))

@app.route('/fetch_feed/<int:feed_id>')
def fetch_feed(feed_id):
    feed = db_session.get(Feed, feed_id)
    feed_data = feedparser.parse(feed.url)
    page = request.args.get('page', 1, type=int)
    per_page = 3
    total_entries = len(feed_data.entries)
    paginated_entries = feed_data.entries[(page - 1) * per_page: page * per_page]
    total_pages = math.ceil(total_entries / per_page)
    return render_template('feed.html', feed=feed_data, entries=paginated_entries, page=page, total_pages=total_pages, feed_id=feed_id)

@app.route('/fetch_feed_from_folder/<folder_name>/<int:feed_id>')
def fetch_feed_from_folder(folder_name, feed_id):
    feed = db_session.get(Feed, feed_id)
    feed_data = feedparser.parse(feed.url)
    page = request.args.get('page', 1, type=int)
    per_page = 3
    total_entries = len(feed_data.entries)
    paginated_entries = feed_data.entries[(page - 1) * per_page: page * per_page]
    total_pages = math.ceil(total_entries / per_page)
    return render_template('feed.html', feed=feed_data, entries=paginated_entries, page=page, total_pages=total_pages, feed_id=feed_id)

# PyQt5 application
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('GridStream')
        self.setGeometry(100, 100, 1280, 720)
        self.browser = QWebEngineView()
        self.browser.setUrl(QUrl('http://127.0.0.1:5000'))
        self.setCentralWidget(self.browser)

if __name__ == '__main__':
    initialize_database()  # Set us up the database and add the default blog feed, all your blog are belong to me

    # Run Flask application in a separate thread, because this can totally actually be run in a browser rather than a PyQt5 app, if you want? 
    flask_thread = threading.Thread(target=app.run, kwargs={'debug': False, 'use_reloader': False})
    flask_thread.daemon = True
    flask_thread.start()

    # Run PyQt5 application
    qt_app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    sys.exit(qt_app.exec_())
