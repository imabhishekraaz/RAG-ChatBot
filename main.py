import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()

# ChatOpenAI class call karein (module nahi)
llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.3,
    api_key=os.getenv("SECRET_KEY")
)

response = llm.invoke("Hello!")
print(response.content)