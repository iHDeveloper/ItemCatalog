# Item Catalog
An application that shows your items in catalog to everyone.

## How to make Google OAuth2 Provider?
- Open [Google OAuth2 Provider](https://console.developers.google.com)
- Go to `Credentials`
- Click on `Create credentials` and choose `OAuth Client ID`
- Choose `Web Application`
- Set the name `Item Catalog`
- Add `http://localhost:8000`in **Authorized JavaScript origins** and **Authorized redirect URIs**
- Click on `Create`
- Click on `Item Catalog` from the credentials list
- Download the credentials as JSON by clicking `Download JSON`
- Rename the credentials JSON to `client_secret.json`
- Put it in the project directory
- There you go

## Getting Started
- Install [Vagrant]() and [Virtual Box]()
- Clone the [fullstack-nanodegree-vm]()
- Launch the **Vagrant** VM by `vagrant up`
- Open the **Vagrant** SSH by `vagrant ssh`
- In the terminal write `cd /vagrant/catalog`
- Initialize a local git by `git init`
- Add a remote to this repoistory by `git remote add origin https://github.com/iHDeveloper/ItemCatalog`
- Pull from that remote from branch `master` by `git pull origin master`
- Checkout `How to make Google OAuth2 Provider`
- Setup the database using `python database.py`
- Feed this database with some data `python seeder.py` **( optional )**
- Run the application `python application.py`
- Enjoy using the app :)
