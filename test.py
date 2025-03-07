
# from pymongo.mongo_client import MongoClient
# from constants import GOOGLE_API_KEY, MONGODB_URI
# from app import encode_base64, decode_base64
# from parameters_extract import load_document, chatbot_answer,memory
# uri = MONGODB_URI

# # Create a new client and connect to the server
# client = MongoClient(uri)

# # Send a ping to confirm a successful connection
# try:
#     client.admin.command('ping')
#     print("Pinged your deployment. You successfully connected to MongoDB!")
# except Exception as e:
#     print(e)

# encoded_text = encode_base64('permenanetaccountnumber pradeep number')
# print(encoded_text)

# decoded = decode_base64(encoded_text)
# print(decoded)
# document = ""

# d = {'name1':'Pradeep','account_no':12345}

# for i in d.keys():
#     document += str(i+":")
#     document += str(d[i])
# #reset_memory()
# load_document(decoded, document)

# response = chatbot_answer('what was the name?')

# print(response)





