# GroupProject
Django Hyper Local Weather App

4. Create a superuser to access the admin:

   python manage.py createsuperuser

5. Register the app in settings (already added): 'Hyper_Local_Weather'

6. Run the development server on a custom port (optional):

   python manage.py runserver 8000

#Updating map location

1. marker.setLatLng([newLat, newLon]); (setting marker location)

2. mymap.panTo([newLat, newLon]); (setting camera view)

## OpenAQ API Key Setup (UK sensor hex map)

1. Create an OpenAQ account and generate an API key.
2. Copy `.env.example` to a new file named `.env` in the project root.
3. Open `.env` and paste your key:

   `OPENAQ_API_KEY=PASTE_YOUR_OPENAQ_KEY_HERE`

4. Optional second provider key (IQAir):

   `IQAIR_API_KEY=PASTE_YOUR_IQAIR_KEY_HERE`

5. Optional DEFRA provider toggle (no key required):

   `ENABLE_DEFRA_PROVIDER=true`

6. Run the server:

   `python manage.py runserver`

Team note:
- `.env.example` is committed to GitHub for everyone.
- `.env` is ignored by Git, so real keys are never pushed.

Alternative (PowerShell env var)
1. Temporary key for current terminal:

   `$env:OPENAQ_API_KEY = "PASTE_YOUR_OPENAQ_KEY_HERE"`

2. Persist for future terminals:

   `setx OPENAQ_API_KEY "PASTE_YOUR_OPENAQ_KEY_HERE"`

3. Restart terminal/VS Code after `setx`, then run:

   `python manage.py runserver`

Without this key, the UK sensor honeycomb map will stay blank (by design).
