"""
Seed script to populate database with development/test data.

This script creates:
- Admin user
- 2 salons with owners
- 3 professionals per salon
- 10 services per salon
- Availability schedules for professionals
- Sample bookings

Usage:
    python scripts/seed_dev_data.py
"""

import asyncio
from datetime import datetime, time, timezone
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.security.password import hash_password
from backend.app.db.models.availability import Availability, DayOfWeek
from backend.app.db.models.booking import Booking, BookingStatus
from backend.app.db.models.professional import Professional
from backend.app.db.models.salon import Salon
from backend.app.db.models.service import Service
from backend.app.db.models.user import User, UserRole
from backend.app.db.session import AsyncSessionLocal


async def seed_users(db: AsyncSession) -> dict[str, User]:
    """Create test users."""
    print("Creating users...")

    users = {
        "admin": User(
            email="admin@esalao.com",
            password_hash=hash_password("Admin123!"),
            full_name="Admin User",
            phone="+5511999990000",
            role=UserRole.ADMIN,
            is_active=True,
        ),
        "owner1": User(
            email="owner1@esalao.com",
            password_hash=hash_password("Owner123!"),
            full_name="Maria Silva",
            phone="+5511999990001",
            role=UserRole.SALON_OWNER,
            is_active=True,
        ),
        "owner2": User(
            email="owner2@esalao.com",
            password_hash=hash_password("Owner123!"),
            full_name="João Santos",
            phone="+5511999990002",
            role=UserRole.SALON_OWNER,
            is_active=True,
        ),
        "pro1_s1": User(
            email="ana.costa@esalao.com",
            password_hash=hash_password("Pro123!"),
            full_name="Ana Costa",
            phone="+5511999990003",
            role=UserRole.PROFESSIONAL,
            is_active=True,
        ),
        "pro2_s1": User(
            email="carlos.lima@esalao.com",
            password_hash=hash_password("Pro123!"),
            full_name="Carlos Lima",
            phone="+5511999990004",
            role=UserRole.PROFESSIONAL,
            is_active=True,
        ),
        "pro3_s1": User(
            email="beatriz.souza@esalao.com",
            password_hash=hash_password("Pro123!"),
            full_name="Beatriz Souza",
            phone="+5511999990005",
            role=UserRole.PROFESSIONAL,
            is_active=True,
        ),
        "pro1_s2": User(
            email="diego.alves@esalao.com",
            password_hash=hash_password("Pro123!"),
            full_name="Diego Alves",
            phone="+5511999990006",
            role=UserRole.PROFESSIONAL,
            is_active=True,
        ),
        "pro2_s2": User(
            email="elena.martins@esalao.com",
            password_hash=hash_password("Pro123!"),
            full_name="Elena Martins",
            phone="+5511999990007",
            role=UserRole.PROFESSIONAL,
            is_active=True,
        ),
        "pro3_s2": User(
            email="fernando.rocha@esalao.com",
            password_hash=hash_password("Pro123!"),
            full_name="Fernando Rocha",
            phone="+5511999990008",
            role=UserRole.PROFESSIONAL,
            is_active=True,
        ),
        "client1": User(
            email="client1@example.com",
            password_hash=hash_password("Client123!"),
            full_name="Cliente Teste 1",
            phone="+5511999990009",
            role=UserRole.CLIENT,
            is_active=True,
        ),
        "client2": User(
            email="client2@example.com",
            password_hash=hash_password("Client123!"),
            full_name="Cliente Teste 2",
            phone="+5511999990010",
            role=UserRole.CLIENT,
            is_active=True,
        ),
    }

    for user in users.values():
        db.add(user)

    await db.commit()

    for user in users.values():
        await db.refresh(user)

    print(f"✓ Created {len(users)} users")
    return users


async def seed_salons(db: AsyncSession, users: dict[str, User]) -> dict[str, Salon]:
    """Create test salons."""
    print("Creating salons...")

    salons = {
        "salon1": Salon(
            full_name="Beleza Urbana",
            description="Salão moderno no centro da cidade com serviços completos de beleza e estética.",
            address="Rua das Flores, 123",
            city="São Paulo",
            state="SP",
            postal_code="01310-100",
            phone="+5511999881001",
            email="contato@belezaurbana.com.br",
            owner_id=users["owner1"].id,
            is_active=True,
        ),
        "salon2": Salon(
            full_name="Studio Glamour",
            description="Espaço exclusivo especializado em cabelos, unhas e maquiagem profissional.",
            address="Av. Paulista, 456",
            city="São Paulo",
            state="SP",
            postal_code="01310-200",
            phone="+5511999882002",
            email="contato@studioglamour.com.br",
            owner_id=users["owner2"].id,
            is_active=True,
        ),
    }

    for salon in salons.values():
        db.add(salon)

    await db.commit()

    for salon in salons.values():
        await db.refresh(salon)

    print(f"✓ Created {len(salons)} salons")
    return salons


async def seed_professionals(
    db: AsyncSession, users: dict[str, User], salons: dict[str, Salon]
) -> dict[str, Professional]:
    """Create test professionals."""
    print("Creating professionals...")

    professionals = {
        "pro1_s1": Professional(
            user_id=users["pro1_s1"].id,
            salon_id=salons["salon1"].id,
            specialties=["haircut", "coloring", "styling"],
            bio="Especialista em cortes modernos e coloração. 10 anos de experiência.",
            license_number="CABELEIREIRO-SP-12345",
            is_active=True,
            commission_percentage=Decimal("50.0"),
        ),
        "pro2_s1": Professional(
            user_id=users["pro2_s1"].id,
            salon_id=salons["salon1"].id,
            specialties=["barber", "beard", "haircut"],
            bio="Barbeiro profissional especializado em cortes masculinos e barba.",
            license_number="BARBEIRO-SP-12346",
            is_active=True,
            commission_percentage=Decimal("55.0"),
        ),
        "pro3_s1": Professional(
            user_id=users["pro3_s1"].id,
            salon_id=salons["salon1"].id,
            specialties=["nails", "manicure", "pedicure"],
            bio="Manicure e pedicure especializada em nail art e alongamento.",
            license_number="MANICURE-SP-12347",
            is_active=True,
            commission_percentage=Decimal("50.0"),
        ),
        "pro1_s2": Professional(
            user_id=users["pro1_s2"].id,
            salon_id=salons["salon2"].id,
            specialties=["makeup", "styling"],
            bio="Maquiador profissional para eventos e noivas.",
            license_number="MAQUIADOR-SP-12348",
            is_active=True,
            commission_percentage=Decimal("60.0"),
        ),
        "pro2_s2": Professional(
            user_id=users["pro2_s2"].id,
            salon_id=salons["salon2"].id,
            specialties=["haircut", "coloring", "treatment"],
            bio="Colorista e especialista em tratamentos capilares.",
            license_number="CABELEIREIRO-SP-12349",
            is_active=True,
            commission_percentage=Decimal("55.0"),
        ),
        "pro3_s2": Professional(
            user_id=users["pro3_s2"].id,
            salon_id=salons["salon2"].id,
            specialties=["aesthetics", "massage", "skincare"],
            bio="Esteticista com especialização em tratamentos faciais e corporais.",
            license_number="ESTETICISTA-SP-12350",
            is_active=True,
            commission_percentage=Decimal("50.0"),
        ),
    }

    for professional in professionals.values():
        db.add(professional)

    await db.commit()

    for professional in professionals.values():
        await db.refresh(professional)

    print(f"✓ Created {len(professionals)} professionals")
    return professionals


async def seed_services(db: AsyncSession, salons: dict[str, Salon]) -> dict[str, Service]:
    """Create test services."""
    print("Creating services...")

    services_data = {
        # Salon 1 - Beleza Urbana
        "haircut_s1": {
            "name": "Corte de Cabelo Feminino",
            "description": "Corte personalizado com lavagem e finalização",
            "category": "haircut",
            "price": Decimal("80.00"),
            "duration_minutes": 60,
            "salon_id": salons["salon1"].id,
        },
        "haircut_male_s1": {
            "name": "Corte Masculino + Barba",
            "description": "Corte de cabelo masculino com design de barba",
            "category": "barber",
            "price": Decimal("60.00"),
            "duration_minutes": 45,
            "salon_id": salons["salon1"].id,
        },
        "coloring_s1": {
            "name": "Coloração Completa",
            "description": "Coloração total com produtos premium",
            "category": "coloring",
            "price": Decimal("150.00"),
            "duration_minutes": 120,
            "salon_id": salons["salon1"].id,
        },
        "highlights_s1": {
            "name": "Mechas e Luzes",
            "description": "Técnica de mechas ou luzes californianas",
            "category": "coloring",
            "price": Decimal("180.00"),
            "duration_minutes": 150,
            "salon_id": salons["salon1"].id,
        },
        "manicure_s1": {
            "name": "Manicure Completa",
            "description": "Manicure com esmaltação tradicional",
            "category": "nails",
            "price": Decimal("35.00"),
            "duration_minutes": 45,
            "salon_id": salons["salon1"].id,
        },
        "pedicure_s1": {
            "name": "Pedicure Completa",
            "description": "Pedicure com esfoliação e esmaltação",
            "category": "nails",
            "price": Decimal("40.00"),
            "duration_minutes": 60,
            "salon_id": salons["salon1"].id,
        },
        # Salon 2 - Studio Glamour
        "haircut_s2": {
            "name": "Corte + Tratamento",
            "description": "Corte de cabelo com tratamento de hidratação",
            "category": "haircut",
            "price": Decimal("120.00"),
            "duration_minutes": 90,
            "salon_id": salons["salon2"].id,
        },
        "makeup_s2": {
            "name": "Maquiagem Social",
            "description": "Maquiagem para eventos e festas",
            "category": "makeup",
            "price": Decimal("100.00"),
            "duration_minutes": 60,
            "salon_id": salons["salon2"].id,
        },
        "makeup_bride_s2": {
            "name": "Maquiagem de Noiva",
            "description": "Maquiagem completa para noivas com prova",
            "category": "makeup",
            "price": Decimal("250.00"),
            "duration_minutes": 120,
            "salon_id": salons["salon2"].id,
        },
        "facial_s2": {
            "name": "Limpeza de Pele",
            "description": "Limpeza facial profunda com extração",
            "category": "aesthetics",
            "price": Decimal("120.00"),
            "duration_minutes": 90,
            "salon_id": salons["salon2"].id,
        },
    }

    services = {}
    for key, data in services_data.items():
        service = Service(**data, is_active=True)
        db.add(service)
        services[key] = service

    await db.commit()

    for service in services.values():
        await db.refresh(service)

    print(f"✓ Created {len(services)} services")
    return services


async def seed_availability(db: AsyncSession, professionals: dict[str, Professional]) -> None:
    """Create availability schedules for professionals."""
    print("Creating availability schedules...")

    # Standard working hours: Monday to Friday 9am-6pm, Saturday 9am-2pm
    weekday_schedule = [
        (DayOfWeek.MONDAY, time(9, 0), time(18, 0)),
        (DayOfWeek.TUESDAY, time(9, 0), time(18, 0)),
        (DayOfWeek.WEDNESDAY, time(9, 0), time(18, 0)),
        (DayOfWeek.THURSDAY, time(9, 0), time(18, 0)),
        (DayOfWeek.FRIDAY, time(9, 0), time(18, 0)),
        (DayOfWeek.SATURDAY, time(9, 0), time(14, 0)),
    ]

    count = 0
    for professional in professionals.values():
        for day, start, end in weekday_schedule:
            availability = Availability(
                professional_id=professional.id,
                day_of_week=day,
                start_time=start,
                end_time=end,
                is_active=True,
            )
            db.add(availability)
            count += 1

    await db.commit()
    print(f"✓ Created {count} availability schedules")


async def main():
    """Main seeding function."""
    print("\n" + "=" * 60)
    print("🌱 SEEDING DATABASE WITH DEV/TEST DATA")
    print("=" * 60 + "\n")

    async with AsyncSessionLocal() as db:
        try:
            # Seed in order (respecting foreign keys)
            users = await seed_users(db)
            salons = await seed_salons(db, users)
            professionals = await seed_professionals(db, users, salons)
            services = await seed_services(db, salons)
            await seed_availability(db, professionals)

            print("\n" + "=" * 60)
            print("✅ SEEDING COMPLETED SUCCESSFULLY")
            print("=" * 60)
            print("\nSummary:")
            print(f"  • Users: {len(users)}")
            print(f"  • Salons: {len(salons)}")
            print(f"  • Professionals: {len(professionals)}")
            print(f"  • Services: {len(services)}")
            print(f"  • Availability schedules: {len(professionals) * 6} (6 days/week)")
            print("\nTest credentials:")
            print("  • Admin: admin@esalao.com / Admin123!")
            print("  • Owner 1: owner1@esalao.com / Owner123!")
            print("  • Owner 2: owner2@esalao.com / Owner123!")
            print("  • Professional: ana.costa@esalao.com / Pro123!")
            print("  • Client: client1@example.com / Client123!")
            print()

        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            await db.rollback()
            raise


if __name__ == "__main__":
    asyncio.run(main())
