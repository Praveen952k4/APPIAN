from langchain.prompts import PromptTemplate
from langchain.schema import StrOutputParser, SystemMessage, HumanMessage
from langchain.output_parsers import StructuredOutputParser, ResponseSchema
import google.generativeai as genai
from langchain_google_genai import GoogleGenerativeAI, ChatGoogleGenerativeAI
from langchain.chains.llm import LLMChain
from langchain.memory import ConversationBufferMemory

from constants import GOOGLE_API_KEY

def analyze_keywords(text):
    response_schemas = [
        ResponseSchema(name="name", description="The name of the person example rajesh,pradeep,etc,...."),
        ResponseSchema(name="dob", description="The date of birth (DOB) of the person in YYYY-MM-DD format."),
        ResponseSchema(name="address", description="The address of the person."),
    ]


    output_parser = StructuredOutputParser.from_response_schemas(response_schemas)

    prompt_template = PromptTemplate(
        input_variables=["text"],
        template=(
            "You are an AI model that extracts specific fields from a document. "
            "Your task is to extract the following fields: name, date of birth (DOB), and address. "
            "If a field is not present, return null for that field.\n\n"
            "Here is the input text:\n{text}\n\n"
            "Respond with a JSON object that matches this schema:\n{format_instructions}"
        ),
        partial_variables={"format_instructions": output_parser.get_format_instructions()},
    )

    genai.configure(api_key=GOOGLE_API_KEY)

    llm = GoogleGenerativeAI(model='gemini-1.5-flash',api_key=GOOGLE_API_KEY)

    chain = LLMChain(llm=llm, prompt=prompt_template, output_parser=output_parser)

    response = chain.run({"text":text})

    name = response['name']
    dob = response['dob']
    address = response['address']

    return name, dob, address

def identify_document(text):
    genai.configure(api_key=GOOGLE_API_KEY)
    llm = GoogleGenerativeAI(model='gemini-1.5-flash',google_api_key=GOOGLE_API_KEY)

    prompt_template = PromptTemplate(
            input_variables=["document_text", "document_names"],
            template=(
                "You are a document classifier. Your task is to classify a document based "
                "on its text content into one of the following document types:\n\n"
                "{document_names}\n\n"
                "If the document doesn't match any of these types, classify it as 'Others'.\n\n"
                "Document Text:\n{document_text}\n\n"
                "Output only the document type (e.g., Aadhaar, PAN, Others)."
            )
        )
    output_parser = StrOutputParser()

    document_names = ["Aadhaar", "PAN", "Gas Bill", "Electricity Bill", "Passport", "Marksheet"]

    prompt = prompt_template.format( 
        document_text = text[:1000], #limiting
        document_names = ", ".join(document_names)

    )

    response = llm.invoke(prompt)
    parsed_response = output_parser.parse(response)

    return parsed_response.strip()






def load_document(text, obj):
    global document_text, account_details
    # obj.pop('_id', None)
    # obj.pop('uploaded_documents', None)
    document_text = text
    account_details = str(obj)
    print("tttttttttttttttttttttttt")
    print(document_text,account_details)
    print("Document successfully loaded.")


def chatbot_answer(query):
    global document_text, account_details
    print(document_text)
    print(" -----------------------------")
    print(account_details)
    s=""
    for i in document_text:
        if i!="{" and i!="}" and i!= ":":
            s+=i 
        else:
            s+=" "
    document_text = s
    #memory.chat_memory.add_message({"role": "user", "content": query})
    

    from langchain.prompts import PromptTemplate

    # Ensure the template string is correctly formatted
    template = "You are a helpful assistant. Answer the following question: {query}"

    prompt = PromptTemplate(
        input_variables=["query"],
        template=template
    )
    # System prompt with document and account details
    system_prompt = f"""
    You are a helpful chatbot assistant with access to sensitive user documents and account details. 
    Your task is to provide accurate answers based on the information provided below. 
    Do not answer questions unrelated to the document or account details given to you, if the user asks about name other things that had been given then you can answer.

    Document Information:
    {document_text}

    Account Details:
    {account_details}

    If the user asks about anything outside these contexts, respond with:
    'I can only assist with document or account-related queries.'
    """
    inputs = {
        "chat_history": memory.chat_memory,
        "question": query
    }
    #print(str(memory.chat_memory.messages)+"-------------------")
    # Create prompt template for conversation
    prompt = PromptTemplate(
        input_variables=["chat_history", "question"],
        template=f"""
        {system_prompt}

        Conversation History:
        {{chat_history}}
        
        Answer the following question:
        {{question}}
        """
    )
    
    # Create a chain to process the query
    chain = LLMChain(llm=llm2, prompt=prompt, memory=memory)
    
    # Run the chain and return response
    response = chain.invoke(inputs)
    #memory.chat_memory.add_message({"role": "assistant", "content": response['text']})
    # Basic parsing to ensure clean output
    print(memory.chat_memory.messages)
    if "I can only assist" in response:
        return "I can only assist with document or account-related queries."
    
    return response['text']


  
def reset_memory():
    global memory
    memory.clear()
    memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)

    

document_text = ""
account_details = ""
llm2 = ChatGoogleGenerativeAI(model='gemini-1.5-flash', google_api_key=GOOGLE_API_KEY)
memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)


