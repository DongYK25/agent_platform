from models.role import Role


LOCATION_ROLE: dict[int, str] = {}


async def update_location_role() -> None:
    roles = await Role.filter(is_deleted=False).all()

    global LOCATION_ROLE
    LOCATION_ROLE = {
        role.id: role.role_name
        for role in roles
    }
