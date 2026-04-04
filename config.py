def get_db():
    host = app.config.get("DB_HOST")
    user = app.config.get("DB_USER")
    password = app.config.get("DB_PASSWORD")
    database = app.config.get("DB_NAME")
    port = int(app.config.get("DB_PORT") or 4000)

    connect_kwargs = dict(
        host=host,
        port=port,
        user=user,
        password=password,
        database=database,
        autocommit=False,
        connection_timeout=15,
        ssl_disabled=False,
    )

    ca_path = os.getenv("DB_SSL_CA", "").strip()
    if ca_path:
        connect_kwargs["ssl_ca"] = ca_path
        connect_kwargs["ssl_verify_cert"] = True

    return mysql.connector.connect(**connect_kwargs)
