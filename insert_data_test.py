from mongo_connect import client




#establish connection to database
db = client['Weather']
#connect to collection
collection = db['weather']



data = {"name": "John", "age": 30}
collection.insert_one(data)