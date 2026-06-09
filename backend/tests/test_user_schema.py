from app.schemas.user import UserCreate, UserUpdate


def test_user_create_accepts_camel_case_admin_payload():
    payload = {
        "username": "student01",
        "phone": "13800000001",
        "password": "123456",
        "realName": "Test Student",
        "role": "student",
        "storeId": 3,
        "isActive": True,
    }

    user = UserCreate.model_validate(payload)

    assert user.real_name == "Test Student"
    assert user.store_id == 3
    assert user.is_active is True


def test_user_update_accepts_camel_case_admin_payload():
    payload = {
        "realName": "Updated Student",
        "storeId": 5,
        "isActive": False,
    }

    user = UserUpdate.model_validate(payload)

    assert user.real_name == "Updated Student"
    assert user.store_id == 5
    assert user.is_active is False
