from dotenv import load_dotenv
import os 
env = load_dotenv()
print(env)

# print(os.environ)
print(os.environ['host'])
print(os.environ['database'])
print(os.environ['port'])
print(os.environ['password'])
print(os.environ['user'])