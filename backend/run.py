# run.py
# This file is used to run the FastAPI application.
# Run with: python run.py
# Or: uvicorn app.main:app --reload

import uvicorn

if __name__ == "__main__":
    # In order to use reload=True, uvicorn requires the app to be passed 
    # as an import string ("module:app_instance") rather than the app object itself.
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)