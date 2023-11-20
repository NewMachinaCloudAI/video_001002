import json
import urllib3
import boto3
import datetime
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

def get_secret_api_key():
    secret_name = "prod/api/key/chatgpt"
    secret_key = "api-key-chatgpt"
    region_name = "us-east-1"

    # Create a Secrets Manager client
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=region_name
    )

    try:
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_name
        )
    except ClientError as e:
        # For a list of exceptions thrown, see
        # https://docs.aws.amazon.com/secretsmanager/latest/apireference/API_GetSecretValue.html
        raise e

    # Decrypts secret using the associated KMS key.
    secret_response = get_secret_value_response[ 'SecretString' ]
    secret_object = json.loads(secret_response) 
    secret_api_key = secret_object['api-key-chatgpt']
    
    # Return secret
    return secret_api_key
    
def get_conversation_history(user_key):
    dynamoDb = boto3.resource('dynamodb')
    table = dynamoDb.Table('Video-000200-UserConversation')
    response = table.query(
        KeyConditionExpression=Key('userKey').eq(user_key)
    )
    return response['Items']

def save_conversation_history(user_key,question,answer):
    date_time = datetime.datetime.now()
    date_time_str = date_time.strftime('%Y-%m-%d %H:%M:%S.%f')
    item_object = {}
    item_object['userKey'] = user_key
    item_object['dateTime'] = date_time_str
    item_object['question'] = question
    item_object['answer'] = answer
    dynamoDb = boto3.resource('dynamodb')
    table = dynamoDb.Table('Video-000200-UserConversation')
    response = table.put_item( Item=item_object )
    
def build_payload(next_question,user_conversation_items):
    messages = []
    
    # Add the base message plus the previous user conversation
    messages.append({"role": "system", "content": f"You are an assistant who answers questions about the world."})
    for user_conversation_item in user_conversation_items:
        json_object = {}
        json_object['role'] = 'user'
        json_object['content'] = user_conversation_item['question']
        messages.append(json_object)
        
        json_object = {}
        json_object['role'] = 'assistant'
        json_object['content'] = user_conversation_item['answer']
        messages.append(json_object)
        
    # Add the next user question
    json_object = {}
    json_object['role'] = 'user'
    json_object['content'] = next_question
    messages.append(json_object)
        
    # Construct the payload
    payload = {
        "model": "gpt-3.5-turbo",
        "temperature" : 1.0,
        "messages" : messages
    }
    return payload
    
def extract_answer_from_response(response):
    response_dictionary = json.loads(response.data.decode('utf-8'))
    choices = response_dictionary['choices']
    choice = choices[0]
    message = choice['message']
    answer = message['content']
    return answer

def lambda_handler(event, context):

    # Initialize key variables
    USER_KEY = "demoUser"
    API_KEY = get_secret_api_key()
    URL = "https://api.openai.com/v1/chat/completions"
    HEADERS = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {API_KEY}"
    }
    
    # get conversation history
    userConversationItems = get_conversation_history(USER_KEY)

    # build prompt for ChatGPT
    question = "Where is the best surfing location in Texas?"
    print("QUESTION--->" + question)
    payload = build_payload(question,userConversationItems)
    encodedPayload = json.dumps(payload)

    # make request to ChatGPT and get response
    http = urllib3.PoolManager()
    response = http.request('POST',
                             URL,
                             headers=HEADERS,
                             body=encodedPayload)
    answer = extract_answer_from_response(response)
    print("ANSWER--->" + answer + "\n" )
    
    # Save conversation
    save_conversation_history(USER_KEY,question,answer)
    
    # TODO implement
    return {
        'statusCode': 200,
        'body': json.dumps('Successful API Call from AWS Lambda to ChatGpt!')
    }