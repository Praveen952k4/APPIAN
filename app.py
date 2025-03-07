from flask import Flask, request, jsonify, render_template, url_for, redirect
from parameters_extract import analyze_keywords, identify_document,load_document, chatbot_answer,reset_memory
from mongo_db_backend import MongoDB
from bson.binary import Binary
import os
import mimetypes
from pdf2image import convert_from_bytes
import pytesseract
from pdf2image import convert_from_path,convert_from_bytes
from PIL import Image
import magic
from io import BytesIO
from tempfile import NamedTemporaryFile
from drive import upload_file_to_folder, create_nested_folders, create_or_get_folder
import io
import random
import base64
from langchain.memory import ConversationBufferMemory
from datetime import datetime
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadTimeSignature
from flask_mail import Mail, Message
import requests

def get_time():
    now = datetime.now()

    # Extract date and format time to HH:MM as string
    current_date = str(now.date())  # Convert date to string
    current_time = now.strftime("%H:%M")  # Time as string in HH:MM
    return current_date,current_time

app = Flask(__name__,template_folder='templates', static_folder='static')
app.config['SECRET_KEY'] = 'Thisisasecret!'  # Ensure the secret key is set

s = URLSafeTimedSerializer(app.config['SECRET_KEY'])

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USERNAME'] = 'appianhackathan@gmail.com'
app.config['MAIL_PASSWORD'] = 'gvod jshf stez tpew'
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True
mail = Mail(app)

app.config['SMS_TOKEN'] = ""

ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg'}

pytesseract.pytesseract.tesseract_cmd = r"Tesseract-OCR/tesseract.exe"


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Encoding
def encode_base64(text):
    encoded = base64.b64encode(text.encode('utf-8'))
    return encoded.decode('utf-8')

# Decoding
def decode_base64(encoded_text):
    decoded = base64.b64decode(encoded_text)
    return decoded.decode('utf-8')


def detect_file_type(uploaded_file):
    
    mime = magic.Magic(mime=True)
    
    file_type = mime.from_buffer(uploaded_file)

    if 'pdf' in file_type:
        return 'pdf'
    elif 'image' in file_type:
        return 'image'
    else:
        return 'unknown'


def extract_text_with_ocr(uploaded_file):
    text = ""
    try:
        # Read the uploaded file into a BytesIO object
        file_bytes = BytesIO(uploaded_file)
       #print("------------------")
        #print(uploaded_file)
        # Convert PDF to images using the correct Poppler path
        images = convert_from_bytes(file_bytes.getvalue(), poppler_path=r'poppler-24.08.0\\Library\\bin')
        
        # Perform OCR on each image and extract text
        for image in images:
            text += pytesseract.image_to_string(image, lang='eng+hin+tam')  # Adding Tamil language
        #print(text)
    except Exception as e:
        print(f"Error performing OCR: {e}")
    #print(text)
    finally:
        return text


# def extract_text_from_pdf(pdf_path):
#     """
#     Extract text from a PDF using PyMuPDF, fallback to OCR.
#     """
#     text = extract_text_with_pymupdf(pdf_path)
#     if not text.strip():
#         print("No text found with PyMuPDF. Using OCR...")
#         text = extract_text_with_ocr(pdf_path)
#     return text


def extract_text_from_image(uploaded_file):
   
    text = ""
    try:
        # Read the uploaded file into a BytesIO object
        image_bytes = BytesIO(uploaded_file)
        
        # Open the image from the BytesIO object
        image = Image.open("C:\\Users\\malap\\Pictures\\Screenshots\\Screenshot 2025-01-07 113053.png")
        
        # Use pytesseract to extract text from the image
        text = pytesseract.image_to_string(image, lang='tam+eng+hin')
    except Exception as e:
        print(f"Error extracting text from image: {e}")
    
    return text


# --- Document Classification ---
def classify_document(text):
    """
    Classify the document as Aadhaar, PAN, or Voter ID based on keywords.
    """
    aadhaar_keywords = ["aadhaar", "uidai"]

    pan_keywords = ["permanent account number", "income tax department"]

    voter_keywords = ["election commission of india", "epic number", "electoral photo identity card"]
    
    
    text_lower = text.lower()

    if all(keyword in text_lower for keyword in aadhaar_keywords):
        return "aadhaar"
    elif all(keyword in text_lower for keyword in pan_keywords):
        return "pan"
    elif all(keyword in text_lower for keyword in voter_keywords):
        return "voter"
    else:

        #if not able to identify then using gemini model

        identified_document_type = identify_document(text=text)

        return identified_document_type.lower()
    
def generate_12_digit_number():
    return random.randint(10**11, 10**12 - 1)



@app.route('/')
def index():
    """
    Renders the main landing page of the application.
    """
    
    return render_template("index.html") 


@app.route('/customer')
def about():
    message = request.args.get('message')
    return render_template('customer.html', message=message)

@app.route('/new')
def new():
    return render_template('/new.html')

@app.route('/transaction')
def transaction():
    return render_template('/transaction_history.html')

@app.route('/upload')
def upload():
    return render_template('/upload.html')

@app.route('/test')
def test():
    return render_template('/test.html')

@app.route('/shared_upload')
def shared_upload():
    return render_template('/shared_upload.html')

@app.route('/chat')
def chat():
    return render_template('/chatbot.html')


@app.route("/upload_file",methods = ["POST"])
def upload_file():

    if 'file' not in request.files:
        return jsonify({"upload_status" : 'not_uploaded' })
        
    
    file = request.files['file']
    #print("-"*100)
    #print(file,file.filename)
    if file.filename == '':
        return jsonify({"upload_status" : 'not_uploaded' })

    if file and allowed_file(file.filename):
        
        file_bytes = file.read()
        file_io = io.BytesIO(file_bytes)

    
    
        file_type = detect_file_type(file_bytes)

        extracted_text = ""
        #print("-"*10)
        #print(file_bytes,file_type)

        if file_type == 'pdf':
            extracted_text = extract_text_with_ocr(file_bytes)
            #print(extracted_text)
        elif file_type == 'image':
            extracted_text = extract_text_from_image(file_bytes)
        else:
            status = "unsupported"

        document_type = classify_document(extracted_text)
        
        print(document_type)
        print(extracted_text)
        name, dob, address = analyze_keywords(text=extracted_text)
        print("111111111111111111111111111hi")
        print(name,dob,address)
        if name is None:
            status = 'upload_different_document'
            print(status)
        else:
            name=name.lower()
            
            mongo_client = MongoDB()
            print("-"*200)
            account_status, accounts = mongo_client.person_id(name=name,dob=dob,address=address)
            print("ppppp")
            for i in accounts:
                print(type(i))
            #print(accounts,account_status)
            if account_status is None:
                status = 'upload_different_document'
                return jsonify({
                    "upload_status":status
                })
            else:
               
                if account_status == "found":
                    account = accounts[0]
                    account_no = account['acc_no']

                    file_type = document_type
                    file_name = str(document_type)
                    # file_data = file_io
                    base64_file_data = encode_base64(extracted_text)
                    current_date, current_time = get_time()
                    file_document = { 
                        'date':current_date,
                        'time':current_time,
                        'file_type' : file_type,
                        'file_name' : str(account_no) +"_"+file_name,
                        'file_data' : base64_file_data
                        
                    }

                    result = mongo_client.insert_document(account,file_document,document_type)

                    if result:
                        upload_status = 'success'
                        
                        
                    else:
                        upload_status = 'network_error'

                    folder_name1 = "Documents"
            
                    internal_folder_name1 = document_type

                    folder_id1 = create_or_get_folder(folder_name1)
                    nested_folder_id1 = create_nested_folders(internal_folder_name1,folder_id1)
                    file.seek(0)
                    with NamedTemporaryFile(delete=False) as temp_file1:
                        temp_file1.write(file.read())
                        temp_file1.flush()
                        temp_file1_path = temp_file1.name

                    res1 = upload_file_to_folder(temp_file1, str(account_no) +"_"+name, nested_folder_id1)


                    #Person-wise Heirarchy in Drive
                    
                    file.seek(0)

                    folder_name2 = "Account_Holders"

                    internal_folder_name2 = name

                    folder_id2 = create_or_get_folder(folder_name2)
                    nested_folder_id2 = create_nested_folders(str(account_no)+'_'+internal_folder_name2,folder_id2)

                    with NamedTemporaryFile(delete=False) as temp_file2:
                        temp_file2.write(file.read())
                        temp_file2.flush()
                        temp_file2_path = temp_file2.name

                    res2 = upload_file_to_folder(temp_file2, document_type, nested_folder_id2)
                    
                    print(res1,res2)
                    return jsonify({
                        "upload_status" : upload_status
                    })


                elif account_status == "list_of_accounts":
                    file_type = document_type
                    base64_file_data = encode_base64(extracted_text)
                    current_date, current_time = get_time()
                    file_document = { 
                        'date':current_date,
                        'time':current_time,
                        'file_type' : file_type,
                        'file_data' : base64_file_data
                    }
                    
                    
                    new_accounts = []
                    for i in accounts:
                        new_dict = dict()
                        name = i['name']
                        acc_no = i['acc_no']
                        new_dict['name'] = name
                        new_dict['acc_no'] = acc_no
                        new_dict['_id'] = str(i['_id'])
                        new_accounts.append(new_dict)

                    accounts = list(new_accounts)
                    file.seek(0)
                    upload_status = "display_accounts"
                    file_content = base64.b64encode(file.read()).decode('utf-8')
                    
                    return jsonify({
                        "upload_status" : upload_status,
                        "file_document" : file_document,
                        "document_type" : document_type,
                        "accounts" : accounts,
                        "file_data":file_content
                        
                    })
                
@app.route("/upload_file_selected_account",methods = ['POST'])
def upload_file_for_selected_account():
    
    mongo_client = MongoDB()
    
    data = request.json 

    file_document = data.get("file_document")
    document_type = data.get("document_type")
    account = data.get("account")
    file_content = data.get("file_data")
    file_data = base64.b64decode(file_content)
    file_document['file_name'] = str(account["acc_no"])+"_"+ document_type
    current_date, current_time = get_time()
    file_document['date'] = current_date
    file_document['time'] = current_time

    result = mongo_client.insert_document(account,file_document,document_type)

    if result:
        upload_status = 'success'                   
    else:
        upload_status = 'network_error'
    folder_name1 = "Documents"
            
    internal_folder_name1 = document_type

    folder_id1 = create_or_get_folder(folder_name1)
    nested_folder_id1 = create_nested_folders(internal_folder_name1,folder_id1)
    # file.seek(0)
    with NamedTemporaryFile(delete=False) as temp_file1:
        temp_file1.write(file_data)
        temp_file1.flush()
        temp_file1_path = temp_file1.name

    res1 = upload_file_to_folder(temp_file1, str(account["acc_no"]) +"_"+account["name"], nested_folder_id1)


                    #Person-wise Heirarchy in Drive
                    
    # file.seek(0)

    folder_name2 = "Account_Holders"

    internal_folder_name2 = account["name"]
    print("pm",type(internal_folder_name2))
    folder_id2 = create_or_get_folder(folder_name2)
    nested_folder_id2 = create_nested_folders(str(account["acc_no"]) +'_'+ str(internal_folder_name2),folder_id2)

    with NamedTemporaryFile(delete=False) as temp_file2:
        temp_file2.write(file_data)
        temp_file2.flush()
        temp_file2_path = temp_file2.name

    res2 = upload_file_to_folder(temp_file2, document_type, nested_folder_id2)
                    
    print(res1,res2)
    return jsonify({
         "upload_status" : upload_status,
         "acc_no":str(account["acc_no"])
    })
    



@app.route("/chatbot_acc_no", methods = ['POST'])
def chatbot_account_no_confirmation():

    data = request.json
    account_no = data.get("account_no")
    print("hiiiiiiiiiiiiii",account_no)
    mongo_client = MongoDB()
    base64_documents_list, obj = mongo_client.retrieve_documents(account_no=account_no)

    document_text = ""

    for single_document in base64_documents_list:
        document_text += decode_base64(single_document)
    
    
    
    

    if document_text == "":
        return jsonify({
            "response" : "Unable to find documents."
        })
    else:
        d = dict(obj)
        account_str = ""
        for i in d.keys():
            if i=="uploaded_documents":
                values = d[i]
                final_doc_str = ""
                for j in list(values):
                    doc_str = ""
                    for k in dict(j).keys():
                        doc_str += (str(k) + ":")
                        doc_str += (str(j[k]) + " ")
                    final_doc_str += (doc_str + "\n")
                account_str += final_doc_str
            else:
                account_str += str(i+":")
                account_str += (str(d[i]) + " ")
        reset_memory()
        load_document(document_text, account_str)
        
        return jsonify({
            "response":"Details loaded, ask queries."
        })

@app.route("/chatbot_response",methods=["POST"])
def chatbot_response():
    data = request.json 
    query = data.get("query")
    print(query,"query")
    response = chatbot_answer(query)
    print(response)
    return jsonify({
        "response" : response
    })

@app.route("/filter_hours",methods = ['POST'])
def filter_hours():
    mongo_client = MongoDB()
    data = request.json
    hours = data.get("hours")
    total_doc_len = mongo_client.get_documents_count_hours_length(hours)
    return jsonify({
        "doc_length":total_doc_len
    })

@app.route("/transaction_history",methods = ['POST'])
def transaction_history():
    mongo_client = MongoDB()
    data = request.json
    selected_date = data.get("selected_date")
    start_hour = data.get("start_hour")
    end_hour = data.get("end_hour")
    return_list = mongo_client.get_documents_transaction_history(selected_date=selected_date,start_hour=start_hour,end_hour=end_hour)
    final_return_list = []
    for i in return_list:
        new_dict = dict()
        new_dict["account_number"] = i[0]
        new_dict["name"] = i[1]
        new_dict["uploaded_date"] = i[2]
        new_dict["uploaded_time"] = i[3]
        new_dict["uploaded_documents"] = i[4]
        final_return_list.append(new_dict)

    
    return jsonify({
        "rows_list":final_return_list
    })

@app.route('/generate_upload_link', methods=['POST'])
def generate_upload_link():
    data = request.json
    user_data = data.get('user_data')
    if not user_data:
        return jsonify({"error": "No user data provided"}), 400
    token = s.dumps(user_data, salt=app.config['SECRET_KEY'])
    upload_link = url_for('shared', token=token, _external=True)
    return jsonify({"upload_link": upload_link})

@app.route('/shared/<token>')
def shared(token):
    try:
        user_data = s.loads(token, salt=app.config['SECRET_KEY']) 
        if not user_data:
            return jsonify({"error": "Invalid or expired token"}), 400
        print(user_data)
        return render_template('shared_upload.html', token=token, user_data=user_data)
    except (SignatureExpired, BadTimeSignature):
        return jsonify({"error": "Invalid or expired token"}), 400
    
@app.route('/fetch_and_display',methods = ['GET'])
def fetch_accounts():
    mongo_client = MongoDB()
   
    db = mongo_client.client['Accounts']
    collection = db['accounts_details']

    accounts = collection.find({})
    l=[]
    for i in accounts:
        d=dict()
        doc = dict(i)
        print(doc)
        name = doc['name']
        dob = doc['dob']
        phone = doc['phone']
        email = doc['email']
        d['name'] = name
        d['dob'] = dob 
        d['phone'] = phone
        d['email'] = email
        l.append(d)
    return jsonify({
        "accounts":l
    })
        
@app.route('/send_mail',methods = ['POST'])
def send_mail():
    email = request.form.get('email')
    shared_link = request.form.get('shared_link')
    name = request.form.get('name')
    msg = Message(subject='Shared Upload Link',
                    sender=app.config.get("MAIL_USERNAME"),
                    recipients=[email, 'sandeepadithya.k@gmail.com'])
    
    msg.body = f"Hello {name},\n\nYou have been shared a file upload link. Please click on the link below to upload your documents.\n\n{shared_link}\n\nRegards,\nTeam DataHive"

    mail.send(msg)
    return redirect(url_for('about', message="Email sent successfully!"))

@app.route('/send_sms',methods = ['POST'])
def send_sms():
    # phone = request.form.get('phone')
    phone = "9025081684"

    shared_link = request.form.get('shared_link')
    name = request.form.get('name')
    headers = {
        'authToken': app.config['SMS_TOKEN']
    }
    # url = "https://cpaas.messagecentral.com/verification/v3/send?countryCode=91&customerId=C-6CD107773A334D9&senderId=UTOMOB&type=SMS&flowType=SMS&mobileNumber="+phone+"&message="+f"Hello {name},\n\nYou have been shared a file upload link. Please click on the link below to upload your documents.\n\n{shared_link}\n\nRegards,\nTeam DataHive"
    url = "https://cpaas.messagecentral.com/verification/v3/send?countryCode=91&customerId=C-6CD107773A334D9&senderId=UTOMOB&type=SMS&flowType=SMS&mobileNumber=8248574617&message=Welcome to Message Central. We are delighted to have you here! - Powered by DataHive"
    response = requests.post(url, headers=headers)

    return response.json()


if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0")
