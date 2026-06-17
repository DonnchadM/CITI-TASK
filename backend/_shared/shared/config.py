"""Environment-driven configuration.

Database credentials are injected into every Lambda by Terraform (see
``infra/locals.tf``). ``IS_LOCAL`` distinguishes local LocalStack runs from AWS:
locally PostgreSQL has no TLS, while AWS Aurora requires ``sslmode=require``.
"""

import os

IS_LOCAL: bool = os.getenv("IS_LOCAL", "false").lower() == "true"


def postgres_dsn() -> str:
    """Build the PostgreSQL connection string from injected environment variables.

    Defaults mirror the local development stack so the module also works when run
    directly (e.g. tests) without the Lambda environment present.
    """
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    user = os.getenv("POSTGRES_USER", "postgres")
    password = os.getenv("POSTGRES_PASS", "postgres123")
    dbname = os.getenv("POSTGRES_NAME", "postgres")
    sslmode = "disable" if IS_LOCAL else "require"
    return (
        f"host={host} port={port} user={user} password={password} "
        f"dbname={dbname} sslmode={sslmode} connect_timeout=15"
    )
