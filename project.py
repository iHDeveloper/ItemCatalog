from flask import Flask, render_template
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import SingletonThreadPool
engine = create_engine('sqlite:///startup.db?check_same_thread=False', poolclass=SingletonThreadPool)
app = Flask(__name__)

DBSession = sessionmaker(bind=engine)
session = DBSession()

@app.route('/')
def main():
    return render_template('main.html')


@app.route('/catalog/<catalog>/items')
def showItems(catalog):
    return render_template('items.html')


@app.route('/catalog/<catalog>/<item>')
def showItem(catalog, item):
    return render_template('item.html')

if __name__ == '__main__':
    app.secret_key = 'super_secure'
    app.debug = True
    app.run(host='0.0.0.0', port=8000)

