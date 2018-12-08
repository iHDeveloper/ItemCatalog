from flask import Flask, render_template, request, make_response, redirect, url_for
from flask import session as login_session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import SingletonThreadPool
from database import Base, Catalog, User, Item
from oauth2client.client import FlowExchangeError, flow_from_clientsecrets
import string, random, json, httplib2, requests
engine = create_engine('sqlite:///itemcatalog.db?check_same_thread=False', poolclass=SingletonThreadPool)
app = Flask(__name__)

DBSession = sessionmaker(bind=engine)
session = DBSession()

CLIENT_ID = json.loads(open('client_secrets.json', 'r').read())['web']['client_id']

@app.route('/gconnect', methods=['POST'])
def gconnect():
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invaild state parameter'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    
    code = request.data
    try:
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = json.loads(oauth_flow.step2_exchange(code).to_json())
    except FlowExchangeError:
        response = make_response(json.dumps('Failed to upgrade the authorization code'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    access_token = credentials['access_token']
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s' % access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 50)
        response.headers['Content-Type'] = 'application/json'
    gplus_id = credentials['id_token']['sub']
    if result['user_id'] != gplus_id:
        response = make_response(json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
    if result['issued_to'] != CLIENT_ID:
        response = make_response(json.dumps("Token's client ID doesn't match app's."), 401)
        print("Token's client ID doesn't match app's")
        response.headers['Content-Type'] = 'application/json'
        return response
    
    stored_credentials = login_session.get('credentials')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_credentials is not None and gplus_id == stored_gplus_id:
        response = make_response(json.dumps('Current user is already connected.'), 200)
        response.headers['Content-Type'] = 'application/json'
    
    login_session['credentials'] = credentials
    login_session['gplus_id'] = gplus_id

    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials['access_token'], 'alt': 'json' }
    answer = requests.get(userinfo_url, params=params)
    data = json.loads(answer.text)

    login_session['username'] = data["name"]
    login_session['picture'] = data["picture"]
    login_session['email'] = data["email"]

    user_id = getUserID(login_session['email'])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id
    return "Login successfully! Redirecting...";


@app.route('/gdisconect')
def gdisconnect():
    if login_session['credentials'] is None:
        return render_template('error.html')
    credentials = login_session['credentials']
    access_token = credentials['access_token']
    url = ( "https://accounts.google.com/o/oauth2/revoke?token=%s" % access_token ) 
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]
    if result['status'] == '200':
        del login_session['credentials']
        del login_session['gplus_id']
        del login_session['username']
        del login_session['email']
        del login_session['picture']
        return redirect(url_for('main'))
    else:
        return render_template('error.html')


@app.route('/login')
def login():
    state = ''.join(random.choice(string.ascii_uppercase + string.digits) for x in range(32))
    login_session['state'] = state
    return render_template('login.html', state = state, login_session = login_session)


@app.route('/')
def main():
    categories = session.query(Catalog).all()
    latestItems = session.query(Item).order_by('created_date').limit(10)
    return render_template('main.html', categories = categories, latestItems = latestItems, login_session = login_session)


@app.route('/catalogs/new', methods=['GET', 'POST'])
def newCatalog(catalog_name):
    if request.method == 'POST':
        catalog = Catalog(name = request.form['name'], user_id = login_session['user_id'])
        session.add(catalog)
        session.commit()
        return redirect(url_for('main'))
    return render_template('newCatalog.html', catalog = catalog)


@app.route('/catalog/<catalog_name>/items')
def showItems(catalog_name):
    catalog = session.query(Catalog).filter_by(name = catalog_name).one()
    items = session.query(Item).filter_by(catalog_id = catalog.id).all()
    return render_template('items.html', items = items, catalog = catalog, login_session = login_session)


@app.route('/catalog/<catalog_name>/<item_name>')
def showItem(catalog_name, item_name):
    catalog = session.query(Catalog).filter_by(name = catalog_name).one()
    item = session.query(Item).filter_by(catalog_id = catalog.id, name = item_name).one()
    return render_template('item.html', item = item, catalog = catalog, login_session = login_session)


@app.route('/catalog/<catalog_name>/<item_name>/edit', methods=['GET', 'POST'])
def editItem(catalog_name, item_name):
    catalog = session.query(Catalog).filter_by(name = catalog_name).one()
    item = session.query(Item).filter_by(catalog_id = catalog.id, name = item_name).one()
    if request.method == 'POST':
        item.name = request.form['name']
        item.description = request.form['description']
        session.add(item)
        session.commit()
        return redirect(url_for('showItems', catalog_name = catalog.name))
    return render_template('editItem.html', catalog = catalog, item = item)


@app.route('/catalog/<catalog_name>/<item_name>/delete', methods=['GET', 'POST'])
def deleteItem(catalog_name, item_name):
    catalog = session.query(Catalog).filter_by(name = catalog_name).one()
    item = session.query(Item).filter_by(catalog_id = catalog.id, name = item_name).one()
    if request.method == 'POST':
        session.delete(item)
        session.commit()
        return redirect(url_for('showItems', catalog_name = catalog.name))
    return render_template('deleteItem.html', catalog = catalog, item = item)


def getUserID(email):
    try:
        user = session.query(User).filter_by(email = email).one()
        return user.id
    except:
        return None


def getUserInfo(user_id):
    user = session.query(User).filter_by(id = user_id).one()
    return user


def createUser(login_session):
    username = login_session['username']
    email = login_session['email']
    picture = login_session['picture']
    newUser = User(name = username, email = email, picture = picture)
    session.add(newUser)
    session.commit()
    user = session.query(User).filter_by(email = email).one()
    return user.id

if __name__ == '__main__':
    app.secret_key = 'super_secure'
    app.debug = True
    app.run(host='0.0.0.0', port=8000)

