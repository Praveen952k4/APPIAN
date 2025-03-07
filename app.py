from flask import Flask, request, jsonify, render_template
from parameters_extract import analyze_keywords, identify_document
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


app = Flask(__name__)

ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg'}
pytesseract.pytesseract.tesseract_cmd = r"C:\\Tesseract\\Tesseract-OCR\\tesseract.exe"

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


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
        print("------------------")
        print(uploaded_file)
        # Convert PDF to images using the correct Poppler path
        images = convert_from_bytes(file_bytes.getvalue(), poppler_path=r'C:\\Users\\malap\\Downloads\\Release-24.08.0-0\\poppler-24.08.0\\Library\\bin')
        
        # Perform OCR on each image and extract text
        for image in images:
            text += pytesseract.image_to_string(image, lang='eng+hin+tam')  # Adding Tamil language
    except Exception as e:
        print(f"Error performing OCR: {e}")
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
        image = Image.open('aadhar_backside.png')
        
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
    return render_template("main.html") 



@app.route("/upload_file",methods = ["POST"])
def upload_file():

    if 'file' not in request.files:
        return jsonify({"upload_status" : 'not_uploaded' })
        
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({"upload_status" : 'not_uploaded' })

    if file and allowed_file(file.filename):
        
        file_bytes = file.read()
        file_io = io.BytesIO(file_bytes)

    
    
        file_type = detect_file_type(file_bytes)

        extracted_text = ""

        print(file_bytes,file_type)

        if file_type == 'pdf':
            extracted_text = extract_text_with_ocr(file_bytes)
        elif file_type == 'image':
            extracted_text = extract_text_from_image(file_bytes)
        else:
            status = "unsupported"

        document_type = classify_document(extracted_text)
        name, dob, address = analyze_keywords(text=extracted_text)
        if name is not None:
            status = 'upload_different_document'
        else:
            name=name.lower()
            
            mongo_client = MongoDB()
            account_status, accounts = mongo_client.person_id(name=name,dob=dob,address=address)
            
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
                    file_data = file_io
                    bson_file_data = Binary(file_data)

                    file_document = { 
                        'file_type' : file_type,
                        'file_name' : account_no+"_"+file_name,
                        'file_data' : bson_file_data
                        
                    }

                    result = mongo_client.insert_document(account,file_document,document_type)

                    if result:
                        upload_status = 'success'
                        
                    else:
                        upload_status = 'network_error'

                    return jsonify({
                        "upload_status" : upload_status
                    })


                elif account_status == "list_of_accounts":
                    
                    accounts = jsonify(accounts)
                    upload_status = "display_accounts"

                    return jsonify({
                        "upload_status" : upload_status,
                        "file_document" : file_document,
                        "document_type" : document_type,
                        "accounts" : accounts
                    })
                
@app.route("/upload_file_selected_account",methods = ['POST'])
def upload_file_for_selected_account():
    
    mongo_client = MongoDB()
    
    data = request.json 

    file_document = data.get("file_document")
    document_type = data.get("document_type")
    account = data.get("account")

    result = mongo_client.insert_document(account,file_document,document_type)

    if result:
        upload_status = 'success'                   
    else:
        upload_status = 'network_error'
    
    return jsonify({
        "upload_status" : upload_status
    })
    




                
    
    


        
