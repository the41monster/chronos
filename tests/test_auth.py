async def test_register(client):
    response = await client.post("/auth/register", json={
        "username": "testuser",
        "email": "testuser@example.com",
        "password": "testpassword"
    })
    assert response.status_code == 201
    data = response.json()
    assert data["username"] == "testuser"
    assert data["email"] == "testuser@example.com"
    assert "password" not in data


async def test_register_duplicate_username(client):
    await client.post("/auth/register", json={
        "username": "testuser",
        "email": "testuser@example.com",
        "password": "testpassword"
    })
    response = await client.post("/auth/register", json={
        "username": "testuser",
        "email": "other@example.com",
        "password": "testpassword"
    })
    assert response.status_code == 400


async def test_login(client):
    await client.post("/auth/register", json={
        "username": "testuser",
        "email": "testuser@example.com",
        "password": "testpassword"
    })
    response = await client.post("/auth/login", json={
        "username": "testuser",
        "password": "testpassword"
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


async def test_me(client, auth_headers):
    response = await client.get("/auth/me", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["username"] == "testuser"


async def test_login_invalid_password(client):
    await client.post("/auth/register", json={
        "username": "testuser",
        "email": "testuser@example.com",
        "password": "testpassword"
    })
    response = await client.post("/auth/login", json={
        "username": "testuser",
        "password": "wrongpassword"
    })
    assert response.status_code == 401


async def test_login_nonexistent_user(client):
    response = await client.post("/auth/login", json={
        "username": "nonexistent",
        "password": "testpassword"
    })
    assert response.status_code == 401


async def test_protected_route_without_token(client):
    response = await client.get("/jobs")
    assert response.status_code == 401
