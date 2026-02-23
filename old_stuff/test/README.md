Automated tests for the API can be run with httpYac (https://httpyac.github.io/).

All tests can be run with

```
httpyac --all ./*.http
````

See httpyac send -h for more options.

This requires an .env file with the following settings:

```
host=http://127.0.0.1:5000 # When running locally
username="user" # Replace as appropriate
password="password" 
```

