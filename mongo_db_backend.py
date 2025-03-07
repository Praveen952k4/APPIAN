from datetime import datetime, timedelta
from pymongo.mongo_client import MongoClient
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import google.generativeai as genai
from langchain_google_genai import GoogleGenerativeAIEmbeddings,GoogleGenerativeAI
from bson import ObjectId

import random
from constants import GOOGLE_API_KEY, MONGODB_URI


def generate_12_digit_number():
    return random.randint(10**11, 10**12 - 1)
class MongoDB:
    def __init__(self):
        uri = MONGODB_URI


        self.client = MongoClient(uri)
    def generate_embeddings(self,texts):
        
        genai.configure(api_key=GOOGLE_API_KEY)
        gemini_model = GoogleGenerativeAIEmbeddings(model='models/embedding-001',google_api_key=GOOGLE_API_KEY)
        embeddings = [gemini_model.embed_documents([text])[0] for text in texts]  # Ensure you pass a list to the model
        
    
        
        
        return np.array(embeddings)
 
    def find_most_similar_vector(self, query_vector: np.ndarray, vectors: np.ndarray):
        """
        Compute cosine similarity between the query vector and a list of vectors, 
        and return the best-matching vector along with its similarity score and index.

        Args:
            query_vector (np.ndarray): The query vector (1D or 2D array).
            vectors (np.ndarray): A 2D array of vectors to compare against.

        Returns:
            tuple: (max_similarity, max_index, best_vector) where
                - max_similarity is the highest cosine similarity value.
                - max_index is the index of the best-matching vector.
                - best_vector is the vector with the highest similarity.
        """
    # Reshape query_vector to 2D (if necessary) for compatibility
        query_vector = query_vector.reshape(1, -1)

    # Compute cosine similarities
        similarities = cosine_similarity(query_vector, vectors).flatten()
        # print(similarities)
    # Find the index of the maximum similarity
        max_index = np.argmax(similarities)
        max_similarity = similarities[max_index]

    # Get the most similar vector
        best_vector = vectors[max_index]
        
        return max_similarity, max_index

    
    def person_id(self,name,dob,address):
        print(address,"hiiiiiiiiiiiiiiiiiiii")
        person_obj = None 
        items = []

        name=name
        

        db = self.client['Accounts']
        collection = db['accounts_details']
        # update_data = { 'name': 'Anita Sharma', 'DOB': '15/04/1992', 'account_number': '2345678901', 'account_type': 'Savings', 'balance': 40000.0, 'contact_number': '9876543211', 'aadhar_number': '2345-6789-0123', 'pan_number': 'BCDEF1234G', 'email': 'anita.sharma@example.com', 'address': '456 Avenue, Chennai, India'}
        # collection.update_one({'_id':ObjectId('676a987c5ca79ef0336e6df3')}, {'$set' :  update_data})
        if name:
            results_for_matching_name = collection.find({"name":name})
            results_list = [dict(document) for document in results_for_matching_name]
            # print(results_list)
            if len(results_list) == 0:
                #new customer (in case of documents like application form)
                account_number = generate_12_digit_number()
                
                person_obj = collection.insert_one({'name':name,"dob":dob,"address":address,"acc_no":account_number})
                
                                
                person_obj = "found"
                items = [dict(collection.find_one({'name':name}))]
                

            elif len(results_list) > 1:

                #more than one customer with same name
                if dob:
                    results_for_matching_name_and_dob = [ document for document in results_list if str(document['dob'])==str(dob)]

                    if len(results_for_matching_name_and_dob) == 1:
                        person_obj = "found"
                        items = [results_for_matching_name_and_dob[0]]
                    elif len(results_for_matching_name_and_dob) > 1:
                        if address:
                            address_list = [document['address'] for document in results_for_matching_name_and_dob]
                            
                            vector_list = self.generate_embeddings(address_list)
                            query_vector = self.generate_embeddings([address])[0]
                    
                            max_similarity, max_index = self.find_most_similar_vector(query_vector, vector_list)
                            if max_similarity >=0.9 :
                                person_obj = "found"
                                items = [document for document in results_for_matching_name_and_dob if document['address']==address_list[max_index]]
                            else:
                                person_obj = "list_of_accounts"
                                
                                # print("hihiiiiiiiiiiiiiiiiiiiiiiiiiii")
                                

                                items = results_for_matching_name_and_dob
                                # print(items)
                        else:
                            person_obj = "list_of_accounts"
                            items = results_for_matching_name_and_dob
                            print("hiitems")
                            for i in items:
                                print(i['name'],i['address'],i['dob'])
                            #print(items)

                    elif len(results_for_matching_name_and_dob) < 1:
                        person_obj = "list_of_accounts"
                        items = results_for_matching_name_and_dob

                elif address:
                    #no dob found in document so trying to match address
                    address_list = [document['address'] for document in results_list]
                    
                    vector_list = self.generate_embeddings(texts = address_list)
                    query_vector = self.generate_embeddings([address])[0]
                   
                    max_similarity, max_index = self.find_most_similar_vector(query_vector, vector_list)

                    print(max_similarity,max_index)
                    if(max_similarity)>=0.9 :
                        person_obj = "found"
                        items = [document for document in results_for_matching_name_and_dob if document['address']==address_list[max_index]]
                    else:
                        person_obj = "list_of_accounts"
                        items = results_list
                else:
                    # no dob and address for people more than 1 with same name, then passed to review ( very rare )
                    person_obj = "list_of_accounts"
                    items = results_list
                    
            elif len(results_list) == 1:

                #only one customer with that name
                person_obj = "found"
                items = results_list
        # print(person_obj, items)
        return person_obj, items
    
    def insert_document(self,account,file_document,document_type):
        db = self.client['Accounts']
        collection = db['accounts_details']
        if not isinstance(account['_id'], ObjectId):
            account['_id'] = ObjectId(account['_id'])
        insert_done = collection.update_one({'_id':account['_id']}, {
        '$set': {'name': account['name'].lower()},          # Update operation for 'name'
        '$push': {'uploaded_documents': file_document}  # Push operation for 'uploaded_documents'
        })
        db1 = self.client['AccountHolderDocuments']
        collection1 = db1['accounts']
        #print(account)
        insert_done1 = collection1.update_one({'_id':account['_id']},{
        '$set': {'name': account['name'].lower()},          # Update operation for 'name'
        '$push': {'uploaded_documents': file_document}  # Push operation for 'uploaded_documents'
        },upsert=True)
        
        db2 = self.client['Documents']
        collection2 = db2[document_type]
        file_document['name'] = account['name'].lower()
        insert_done2 = collection2.insert_one(file_document)
        print(insert_done,insert_done1,insert_done2)
        return insert_done and insert_done1 and insert_done2

    def retrieve_documents(self,account_no):
        base64_data_list = []

        db = self.client['Accounts']
        collection = db['accounts_details']
        account_no = int(account_no)
        
        obj = collection.find_one({"acc_no":account_no})
        
        uploaded_documents_list = list(obj["uploaded_documents"])
        for single_document in uploaded_documents_list:
            base64_data = single_document["file_data"]
            base64_data_list.append(base64_data)

        return base64_data_list,obj
    
    def get_documents_transaction_history(self,selected_date, start_hour, end_hour):
        db = self.client['Accounts']
        collection = db['accounts_details']

        total_documents = collection.find()
        total_documents_length = 0
        return_list = []
        for i in list(total_documents):
            if "uploaded_documents" in dict(i).keys():
                docs = list(dict(i)["uploaded_documents"])
                total_documents_length += len(docs)

                for j in docs:
                    nested_doc = dict(j)
                    if "date" in nested_doc.keys() and "time" in nested_doc.keys():
                        date = nested_doc["date"]
                        time = nested_doc["time"]
                        
                        if start_hour == "All time":
                            if date == selected_date:
                                return_list.append(i['acc_no'],i['name'],date, time, nested_doc["file_type"])
                        else:
                            print("sssssssssssssssssssssssssss")
                            print(start_hour)
                            if time >= start_hour and time <= end_hour and date==selected_date:
                                return_list.append([i['acc_no'],i['name'],date, time, nested_doc["file_type"]])

        return return_list        
                    
                
        return return_list,total_documents_length

    def get_documents_count_hours_length(self,hour):
        db = self.client['Accounts']
        collection = db['accounts_details']

        total_documents = collection.find()
        total_documents_length = 0
      
        for i in list(total_documents):
            docs = list(dict(i)["uploaded_documents"])
            total_documents_length += len(docs)

        return total_documents_length       
    

            

    
# obj = MongoDB()
# response  = obj.upload_documents(name='Sharma',dob=None,address=' Delhi, India')

# print(response)

       



        

# name
# "Anita Sharma"
# DOB
# "15/03/1992"
# account_number
# "2345678901"
# account_type
# "Savings"
# balance
# 40000
# contact_number
# "9876543211"
# aadhar_number
# "2345-6789-0123"
# pan_number
# "BCDEF1234G"
# email
# "anita.sharma@example.com"
# address
# "456 Avenue, Delhi, India"