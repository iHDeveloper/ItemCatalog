from flask import Flask, render_template, request, make_response
from flask import redirect, url_for, jsonify
from flask import session as login_session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import SingletonThreadPool
from database import Base, Catalog, User, Item
from oauth2client.client import FlowExchangeError, flow_from_clientsecrets
import string
import random
import json
import httplib2
import requests
DB_URL = 'sqlite:///itemcatalog.db?check_same_thread=False'
engine = create_engine(DB_URL, poolclass=SingletonThreadPool)
app = Flask(__name__)

DBSession = sessionmaker(bind=engine)
session = DBSession()

CLIENT_ID = json.loads(open('client_secrets.json', 'r').read())
CLIENT_ID = CLIENT_ID['web']['client_id']


@app.route('/gconnect', methods=['POST'])
def gconnect():
    """
    Here where the we do the google oauth2 magic
    """
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
        response_json = json.dumps('Failed to upgrade the authorization code')
        response = make_response(response_json, 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    access_token = credentials['access_token']
    api_url = 'https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
    url = (api_url % access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 50)
        response.headers['Content-Type'] = 'application/json'
    gplus_id = credentials['id_token']['sub']
    if result['user_id'] != gplus_id:
        res_json = json.dumps("Token's user ID doesn't match given user ID.")
        response = make_response(res_json, 401)
        response.headers['Content-Type'] = 'application/json'
    if result['issued_to'] != CLIENT_ID:
        res_json = json.dumps("Token's client ID doesn't match app's.")
        response = make_response(res_json, 401)
        print("Token's client ID doesn't match app's")
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_credentials = login_session.get('credentials')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_credentials is not None and gplus_id == stored_gplus_id:
        res_json = json.dumps('Current user is already connected.')
        response = make_response(res_json, 200)
        response.headers['Content-Type'] = 'application/json'

    login_session['credentials'] = credentials
    login_session['gplus_id'] = gplus_id

    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials['access_token'], 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)
    data = json.loads(answer.text)

    login_session['username'] = data["name"]
    login_session['picture'] = data["picture"]
    login_session['email'] = data["email"]

    user_id = getUserID(login_session['email'])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id
    return "Login successfully! Redirecting..."


@app.route('/gdisconect')
def gdisconnect():
    """
    Telling google that this user wants to sign out from our service
    """
    if login_session['credentials'] is None:
        return render_template('error.html')
    credentials = login_session['credentials']
    access_token = credentials['access_token']
    api_url = "https://accounts.google.com/o/oauth2/revoke?token=%s"
    url = (api_url % access_token)
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
    """
    Here we show the login page with all of the requirements
    that we need for the login process
    """
    s = string.ascii_uppercase + string.digits
    state = ''.join(random.choice(s) for x in range(32))
    login_session['state'] = state
    where = 'login.html'
    return render_template(
        where, state=state,
        login_session=login_session,
        CLIENT_ID=CLIENT_ID
    )


@app.route('/')
@app.route('/catalogs')
def main():
    """
    Shows the main page
    """
    isLogined = 'user_id' in login_session
    catgs = session.query(Catalog).all()
    lt = session.query(Item).order_by('created_date').limit(10)
    return render_template(
        'main.html', categories=catgs,
        latestItems=lt, isLogined=isLogined,
        login_session=login_session
    )


@app.route('/catalogs.json')
def catalogsJSON():
    """
    Returns the catalogs and latest items as JSON
    """
    catgs = session.query(Catalog).all()
    lt = session.query(Item).order_by('created_date').limit(10)
    return jsonify(
        Catalogs=[i.serialize for i in catgs],
        LatestItems=[i.serialize for i in lt]
    )


@app.route('/catalogs/new', methods=['GET', 'POST'])
def newCatalog():
    """
    Create catalog if the user is loggined
    """
    if 'user_id' not in login_session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        name = request.form['name']
        catalog = Catalog(name=name, user_id=login_session['user_id'])
        session.add(catalog)
        session.commit()
        return redirect(url_for('main'))
    return render_template('newCatalog.html')


@app.route('/catalog/<catalog_name>/items')
def showItems(catalog_name):
    """
    Show the items of the selected catalog

    catalog_name - The name of the catalog
    """
    catalog = session.query(Catalog).filter_by(name=catalog_name).one()
    items = session.query(Item).filter_by(catalog_id=catalog.id).all()
    return render_template(
        'items.html', items=items,
        catalog=catalog,
        login_session=login_session
    )


@app.route('/catalog/<catalog_name>/items.json')
def showItemsJSON(catalog_name):
    """
    Returns the items of the selected catalog as JSON

    catalog_name - The name of the catalog
    """
    catalog = session.query(Catalog).filter_by(name=catalog_name).one()
    items = session.query(Item).filter_by(catalog_id=catalog.id).all()
    return jsonify(
        Catalog=catalog.serialize,
        Items=[i.serialize for i in items]
    )


@app.route('/catalog/<catalog_name>/<item_name>')
def showItem(catalog_name, item_name):
    """
    Show an item with the description of it
    
    catalog_name - The name of the catalog
    item_name - The name of the item
    """
    catalog = session.query(Catalog).filter_by(name=catalog_name).one()
    item = session.query(Item).filter_by(
        catalog_id=catalog.id,
        name=item_name
    ).one()
    return render_template(
        'item.html', item=item,
        catalog=catalog,
        login_session=login_session
    )


@app.route('/catalog/<catalog_name>/<item_name>.json')
def showItemJSON(catalog_name, item_name):
    """
    Returns an item as JSON

    catalog_name - The name of the catalog
    item_name - The name of the item
    """
    catalog = session.query(Catalog).filter_by(name=catalog_name).one()
    item = session.query(Item).filter_by(
        catalog_id=catalog.id,
        name=item_name
    ).one()
    return jsonify(
        Catalog=catalog.serialize,
        Item=item.serialize
    )


@app.route('/catalog/<catalog_name>/new', methods=['GET', 'POST'])
def newItem(catalog_name):
    """
    Create new item in selected catalog

    catalog_name - The name of the catalog
    """
    catalog = session.query(Catalog).filter_by(name=catalog_name).one()
    if request.method == 'POST':
        item = Item(
            name=request.form['name'],
            description=request.form['description'],
            catalog_id=catalog.id
        )
        session.add(item)
        session.commit()
        return redirect(
            url_for('showItems', catalog_name=catalog_name)
        )
    return render_template(
        'newItem.html',
        catalog=catalog
    )


@app.route('/catalog/<catalog_name>/<item_name>/edit', methods=['GET', 'POST'])
def editItem(catalog_name, item_name):
    """
    Edit item of the selected catalog

    catalog_name - The name of the catalog
    item_name - The name of the item
    """
    if 'user_id' not in login_session:
        return redirect(url_for('login'))
    catalog = session.query(Catalog).filter_by(name=catalog_name).one()
    if login_session['user_id'] != catalog.user.id:
        return render_template('unauthorized.html')
    item = session.query(Item).filter_by(
        catalog_id=catalog.id,
        name=item_name
    ).one()
    if request.method == 'POST':
        item.name = request.form['name']
        item.description = request.form['description']
        session.add(item)
        session.commit()
        return redirect(
            url_for('showItems', catalog_name=catalog.name)
        )
    return render_template(
        'editItem.html',
        catalog=catalog,
        item=item
    )


@app.route(
    '/catalog/<catalog_name>/<item_name>/delete',
    methods=['GET', 'POST']
)
def deleteItem(catalog_name, item_name):
    """
    Delete an item in selected catalog

    catalog_name - The name of the catalog
    item_name - The name of the item
    """
    if 'user_id' not in login_session:
        return redirect(url_for('login'))
    catalog = session.query(Catalog).filter_by(name=catalog_name).one()
    if login_session['user_id'] != catalog.user.id:
        return render_template('unauthorized.html')
    item = session.query(Item).filter_by(
        catalog_id=catalog.id,
        name=item_name
    ).one()
    if request.method == 'POST':
        session.delete(item)
        session.commit()
        return redirect(
            url_for('showItems', catalog_name=catalog.name)
        )
    return render_template(
        'deleteItem.html',
        catalog=catalog,
        item=item
    )


def getUserID(email):
    """
    Get the user ID by Email from database

    email - The email of the user to find the id by it in database
    """
    try:
        user = session.query(User).filter_by(email=email).one()
        return user.id
    except:
        return None


def getUserInfo(user_id):
    """
    Get the information of the given user id from database

    user_id - The user id to find it in the database
    """
    user = session.query(User).filter_by(id=user_id).one()
    return user


def createUser(login_session):
    """
    Create a user with data from login session in database

    login_session - the login session of the user
    """
    username = login_session['username']
    email = login_session['email']
    picture = login_session['picture']
    newUser = User(name=username, email=email, picture=picture)
    session.add(newUser)
    session.commit()
    user = session.query(User).filter_by(email=email).one()
    return user.id

if __name__ == '__main__':
    app.secret_key = 'super_secure'
    app.debug = True
    app.run(host='0.0.0.0', port=8000)
