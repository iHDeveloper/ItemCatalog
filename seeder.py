from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import User, Catalog, Item, Base

print("[Seeder] Feeding...")

engine = create_engine('sqlite:///itemcatalog.db')
# Bind the engine to the metadata of the Base class so that the
# declaratives can be accessed through a DBSession instance
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()


def catalog(name, user_id):
    catalog = Catalog(
        name=name, user_id=user_id
    )
    session.add(catalog)
    session.commit()
    return catalog


def item(name, catalog_id, description):
    item = Item(name=name, catalog_id=catalog_id, description=description)
    session.add(item)
    session.commit()
    return item

author = User(
    name="iHDeveloper",
    email="hamzadevelop@gmail.com",
    picture="test_picture"
)
session.add(author)
session.commit()

mouses = catalog("Mouses", author.id)

mouses_v1 = item(
    "Mouse V1",
    mouses.id,
    "The first version of the mouse item."
)
mouses_v1 = item(
    "Mouse V2",
    mouses.id,
    "The second version of the mouse item."
)

keyboards = catalog("Keyboard", author.id)
keyboard_v1 = item(
    "KeyBoard V1",
    keyboards.id,
    "The first version of keyboard"
)
keyboard_v1 = item(
    "KeyBoard V2",
    keyboards.id,
    "The second version of keyboard"
)

print("[Seeder] Successfully! Feeded the database.")
