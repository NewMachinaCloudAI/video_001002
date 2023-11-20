# video_001002
AWS Lambda + ChatGPT + DynamoDb

This is a simple proof of concept Lambda function that maintains conversational history using DynamoDb and sends prompts to OpenAI ChatGPT via API.  The conversational context is supplied on each call to the API so ChatGPT can answer with the context of previous questions and answers.
