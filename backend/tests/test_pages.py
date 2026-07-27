def test_public_pages_are_available(client) -> None:
    pages = {
        "/": "Tus botellas pueden convertirse",
        "/registro": "Crear cuenta",
        "/iniciar-sesion": "Iniciar sesión",
    }

    for path, expected_text in pages.items():
        response = client.get(path)
        assert response.status_code == 200
        assert expected_text in response.text

    home = client.get("/")
    assert "Reciclar en tres pasos" in home.text
    assert "BENEFICIOS COMPARTIDOS" in home.text


def test_static_styles_are_available(client) -> None:
    response = client.get("/static/css/styles.css")

    assert response.status_code == 200
    assert "--green-900" in response.text
    assert "[hidden]" in response.text
