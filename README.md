# Hyper Local Weather

A Django-based hyperlocal weather application for tracking weather data at specific locations.

## Project Structure

```
GroupProject/
├── Hyper_Local_Weather/       # Main project configuration
│   ├── __init__.py
│   ├── asgi.py                # ASGI configuration
│   ├── settings.py            # Project settings
│   ├── urls.py                # Main URL configuration
│   └── wsgi.py                # WSGI configuration
├── weather/                   # Weather application
│   ├── migrations/            # Database migrations
│   ├── static/weather/        # Static files (CSS, JS)
│   ├── templates/weather/     # App-specific templates
│   ├── admin.py               # Admin interface configuration
│   ├── apps.py                # App configuration
│   ├── models.py              # Database models
│   ├── tests.py               # Unit tests
│   ├── urls.py                # App URL configuration
│   └── views.py               # View functions
├── templates/                 # Global templates
│   └── base.html              # Base template
├── static/                    # Global static files
├── manage.py                  # Django management script
├── requirements.txt           # Python dependencies
└── README.md                  # This file
```

## Features

- **Location Management**: Track multiple weather locations with GPS coordinates
- **Weather Data Storage**: Store historical weather data including:
  - Temperature
  - Humidity
  - Atmospheric pressure
  - Wind speed
  - Weather description
- **Admin Interface**: Easy data management through Django admin
- **Responsive Templates**: Clean, user-friendly interface

## Models

### Location
- name: Location name
- latitude: GPS latitude coordinate
- longitude: GPS longitude coordinate
- created_at: Timestamp of creation
- updated_at: Timestamp of last update

### WeatherData
- location: Foreign key to Location
- temperature: Temperature in Celsius
- humidity: Humidity percentage
- pressure: Atmospheric pressure in hPa
- wind_speed: Wind speed in m/s
- description: Weather description
- recorded_at: Timestamp of weather reading
- created_at: Timestamp of record creation

## Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd GroupProject
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment** (for production)
   ```bash
   # Create a .env file and set your SECRET_KEY
   # Never use the default SECRET_KEY in production!
   echo "SECRET_KEY=your-secret-key-here" > .env
   ```

4. **Run migrations**
   ```bash
   python manage.py migrate
   ```

5. **Create a superuser** (for admin access)
   ```bash
   python manage.py createsuperuser
   ```

6. **Run the development server**
   ```bash
   python manage.py runserver
   ```

7. **Access the application**
   - Main site: http://127.0.0.1:8000/
   - Admin interface: http://127.0.0.1:8000/admin/

## Usage

1. Log in to the admin interface at `/admin/`
2. Add locations with GPS coordinates
3. Add weather data for those locations
4. View locations and their weather data on the main site

## Development

- **Python Version**: 3.12.3
- **Django Version**: 6.0.2
- **Database**: SQLite (default, can be configured for PostgreSQL, MySQL, etc.)

### Security Notes

- The default `SECRET_KEY` in `settings.py` is for development only
- **Never use the default SECRET_KEY in production!**
- For production deployment:
  - Generate a new SECRET_KEY using Django's `get_random_secret_key()` function
  - Store it in environment variables or a secure configuration file
  - Update `DEBUG` to `False`
  - Set `ALLOWED_HOSTS` appropriately
  - Configure HTTPS/SSL settings

## Future Enhancements

- API integration for automatic weather data fetching
- Real-time weather updates
- Data visualization and charts
- Weather forecasting
- Mobile-responsive design improvements
- User authentication and personalization
