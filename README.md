# Agora Broadcasting Server

## API DOCS

### /

METHOD: GET
DESC: Testing Route to check if the server is running.
RESPONSE: status\_code, message

### /auth

METHOD: POST
DESC: Adds details of a new user to the database
PARAMS: name, uid, broadcaster
RESPONSE: status\_code, message

### /post

METHOD: POST
DESC: Resolves uid of user and adds message in database for chat
PARAMS: channel, uid, message
RESPONSE: status\_code, message
