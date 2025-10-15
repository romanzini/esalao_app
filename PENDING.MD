## Upper Database
docker-compose up -d db redis

### Migration core entities: User, Salon, Professional, Service, Availability, Booking
C:/Projetos/esalao_app/.venv/Scripts/python.exe -m alembic revision --autogenerate -m "Add core entities: User, Salon, Professional, Service, Availability, Booking"
