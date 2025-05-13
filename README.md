Basic Information 

1. Relies on gcloud auth for bucket authentication, if we end up using it (gcloud auth application-default login)

Setup information
1. Install Python3
2. Clone this Repository
3. cd /your/repository/path
4. Create a python virtual environment python3 -m venv .venv)
5. Run 'source .venv/bin/activate'
6. Validate you're running in the virtual environment (which python3)
7. Run 'python3 app.py'

The app will run on localhost:5555 and can be checked for aliveness by queryiung http://localhost:5555/health
