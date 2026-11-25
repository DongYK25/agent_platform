from tortoise.contrib.fastapi import RegisterTortoise

from core.config import settings


TORTOISE_ORM = {
    "connections": {
        "default": {
            "engine": "tortoise.backends.asyncpg",
            "credentials": {
                "host": settings.DB_HOST,
                "port": settings.DB_PORT,
                "user": settings.DB_USER,
                "password": settings.DB_PASSWORD,
                "database": settings.DB_NAME,
            },
        }
    },
    "apps": {
        "models": {
            "models": ["models"],

        }
    },
}


register_orm = RegisterTortoise(
    config=TORTOISE_ORM,
    generate_schemas=False,
)