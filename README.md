# Agora Broadcasting Server

## API DOCS

Install [httpie](https://httpie.org/) to use the examples given below.

### /
  
METHOD: GET  
DESC: Testing Route to check if the server is running.  
RESPONSE: status\_code, message  
EXAMPLE: ```http <API_URL>```
  
### /auth

METHOD: POST  
DESC: Adds details of a new user to the database  
PARAMS: name, uid, broadcaster, channel  
RESPONSE: status\_code, message  
EXAMPLE: ```http -f <API_URL>/auth "name=<name>" "uid=<uid>" "broadcaster=<true/false>" "channel=<channel>" ```
  
### /post
  
METHOD: POST  
DESC: Resolves uid of user and adds message in database for chat  
PARAMS: uid, message  
RESPONSE: status\_code, message  
EXAMPLE: ```http -f <API_URL>/post "uid=<uid>" "message=<message>" ```
